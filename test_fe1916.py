#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات FE1.9.16 «إكمال حزمة OpenStock فوق 1.9.15»
=====================================================
«نفذ الحزمة كاملة» — النافذة العائمة نفذها FE1.9.15 بمودال أكمل، وهنا القطع
الفريدة المتبقية من تحليل openstock-analysis-1 (أنماط مُعاد كتابتها — AGPL):

  ③ SWR للشموع: /api/klines كاش أولًا + ملء عند الفراغ (dedup in-flight + سقف
     تزامن 2 + تبريد فشل 60ث) + تحديث خلفي عند القِدم — أي رمز يُرسم حتى بلا مسح
  ② الحالة الفارغة الصادقة داخل المودال: سبب مسمّى من الخادم + مسح أثر الرمز السابق
  ④ وميض القيم باتجاه: أخضر صعود/أحمر نزول (نمط PriceFlash) — بلا رقم = محايد
  ⑤ الحجز الذري للإشعارات: notify_claim يصمد عبر إعادة التشغيل (الكتم الحرفي
     في الذاكرة كان يُمسح بكل نشر) — مربوط بالمتدهور والغلق اليدوي + fail-open

ما يُغطيه الملف:
  1) جدول notify_claim: الوجود، أول حجز يفوز والتالي يُحجب، المفتاح الفارغ، fail-open
  2) log_and_notify claim_key: تلغرام مرة واحدة واللوحة تستقبل الكل
  3) ربط الوضع المتدهور + الغلق اليدوي: حجز فعلي عبر المسارين الحقيقيين
     (محاكاة إعادة تشغيل = مسح حالة الذاكرة لا يكرر الإرسال)
  4) /api/klines SWR: fill-on-miss (filled/fill_source)، القِدم (stale + تحديث
     خلفي)، الكاش الطازج (بلا تحديث)، السبب المسمّى عند الفراغ
  5) _klines_fetch_fill: dedup (جلب واحد لنداءين متزامنين)، تبريد الفشل،
     العودة بعد التبريد
  6) /health: كتلتي kline_fill وnotify_claim
  7) اللوحة (بنية FE1.9.15 المودالية): طبقة الفراغ الصادقة + أسباب مسمّاة +
     مسح أثر الرمز السابق (شموع/خطوط/طبقة المحرك) + flash-up/flash-down +
     شارة «جُلبت الآن» + بقاء مودال 1.9.15 كما هو
  8) تزامن الإصدار vnz/panel
"""

import threading
import time

import pytest

import vnz
vnz.DASHBOARD_PROTECTED = False  # بيئة الاختبار: بلا مصادقة
import panel


# ─────────────────────────────────────────────────────────────────────────────
# أدوات
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def clean_db(monkeypatch):
    """قاعدة SQLite مؤقتة لكل اختبار — عزل كامل (نفس نمط test_fe19100)."""
    monkeypatch.setattr(vnz, "USE_POSTGRES", False)
    import sqlite3
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    old = vnz.db.conn
    vnz.db.conn = conn
    vnz.init_db()
    vnz._notify_claim_state.update({"wins": 0, "blocks": 0, "errors": 0, "last_key": None})
    yield
    vnz.db.conn = old


@pytest.fixture()
def fresh_fill_state():
    """تصفير حالة المسار الجديد قبل/بعد كل اختبار يلمسها."""
    vnz._klines_fail_until.clear()
    vnz._klines_inflight.clear()
    for k in ("fills", "dedup_waits", "cooldown_skips", "bg_refresh"):
        vnz._klines_fill_state[k] = 0
    vnz._klines_fill_state["last_fill"] = None
    yield
    vnz._klines_fail_until.clear()
    vnz._klines_inflight.clear()


def seed_cache(symbol="TEST/USDT", tf="5m", n=50, step_ms=300_000, base_ts=None):
    """بذر شموع مغلقة عبر الكاتب الحقيقي — base_ts=None يعني طازجًا (آخرها مغلقة
    منذ لحظة الفحص بعمر 5د — داخل نافذة النداهة period+SWR_TTL=6د)."""
    if base_ts is None:
        base_ts = int(time.time() * 1000) - (n - 1) * step_ms - step_ms
    vnz._kline_cache_max_ts.pop((symbol, tf), None)
    rows = [[base_ts + i * step_ms, 100.0 + i, 101.0 + i, 99.0 + i, 100.5 + i, 10.0]
            for i in range(n)]
    vnz._kline_cache_write(symbol, tf, rows)
    return rows


REAL_FILL = vnz._klines_fetch_fill  # الأصل قبل عزل conftest — تُعيده اختبارات الدالة نفسها


def client():
    return vnz.app.test_client()


# ─────────────────────────────────────────────────────────────────────────────
# 1) جدول notify_claim — الحجز الذري
# ─────────────────────────────────────────────────────────────────────────────

def test_notify_claim_table_exists(clean_db):
    row = vnz.db.query("SELECT name FROM sqlite_master WHERE type='table' AND name='notify_claim'", one=True)
    assert row is not None, "جدول الحجز موجود بعد init_db"


def test_tg_claim_once_first_wins_then_blocked(clean_db):
    assert vnz.tg_claim_once("ev:1") is True, "أول حجز يفوز"
    assert vnz.tg_claim_once("ev:1") is False, "الحجز نفسه يُحجب ثانيًا"
    assert vnz.tg_claim_once("ev:2") is True, "مفتاح آخر يفوز"
    assert vnz._notify_claim_state["wins"] == 2
    assert vnz._notify_claim_state["blocks"] == 1


def test_tg_claim_once_empty_key_passthrough(clean_db):
    assert vnz.tg_claim_once(None) is True
    assert vnz.tg_claim_once("") is True
    assert vnz._notify_claim_state["wins"] == 0


def test_tg_claim_once_persists_across_restart(clean_db):
    """جوهر الفائدة: الكتم الحرفي في الذاكرة يُمسح بكل نشر — الحجز في القاعدة يبقى."""
    assert vnz.tg_claim_once("boot-event") is True
    row = vnz.db.query("SELECT key, claimed_at FROM notify_claim WHERE key='boot-event'", one=True)
    assert row is not None and row["claimed_at"], "الحجز مكتوب في القاعدة"
    assert vnz.tg_claim_once("boot-event") is False, "ما بعد الإقلاع يُحجب أيضًا"


def test_tg_claim_once_fail_open_on_db_error(clean_db, monkeypatch):
    """فشل الحجز (قاعدة ميتة) لا يبتلع الإشعار أبدًا — fail-open."""
    def boom(*a, **k):
        raise RuntimeError("db down")
    monkeypatch.setattr(vnz.db, "query", boom)
    assert vnz.tg_claim_once("x") is True
    assert vnz._notify_claim_state["errors"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 2) log_and_notify مع claim_key — تلغرام مرة واللوحة كل شيء
# ─────────────────────────────────────────────────────────────────────────────

def test_log_and_notify_claim_sends_once_panel_gets_all(clean_db, monkeypatch):
    # [FE1.9.18] كتم الخلاصة معطّل هنا — هذا الاختبار يختبر الحجز الذري حصرًا (كتم الخلاصة له اختباره في test_fe1918)
    monkeypatch.setattr(vnz, "PANEL_NOTIF_DEDUP_SEC", 0)
    sent = []
    monkeypatch.setattr(vnz, "send_telegram_message", lambda m: sent.append(m))
    monkeypatch.setattr(vnz, "TELEGRAM_ALERT_TYPES", ("RISK_CUT",))
    vnz.log_and_notify("warning", "قفل A", "RISK_CUT", claim_key="rg:day1")
    vnz.log_and_notify("warning", "قفل A", "RISK_CUT", claim_key="rg:day1")  # نفس الحدث بعد «إعادة تشغيل»
    vnz.log_and_notify("warning", "قفل B", "RISK_CUT", claim_key="rg:day1-b")
    assert len(sent) == 2, "الحدث المنطقي نفسه مرتين = إرسال واحد، والحدث الآخر يُرسل"
    rows = vnz.db.query("SELECT message FROM notifications ORDER BY id")
    assert len(rows) == 3, "اللوحة تستقبل كل شيء بلا أي تصفية"


def test_log_and_notify_no_claim_key_old_behavior(clean_db, monkeypatch):
    sent = []
    monkeypatch.setattr(vnz, "send_telegram_message", lambda m: sent.append(m))
    monkeypatch.setattr(vnz, "TELEGRAM_ALERT_TYPES", ("X",))
    vnz.log_and_notify("info", "م1", "X")
    vnz.log_and_notify("info", "م2", "X")
    assert len(sent) == 2, "بلا claim_key السلوك القديم كما هو"


# ─────────────────────────────────────────────────────────────────────────────
# 3) الربط الحقيقي: المتدهور + الغلق اليدوي
# ─────────────────────────────────────────────────────────────────────────────

def test_degraded_announce_claimed_across_restart(clean_db, monkeypatch):
    sent = []
    monkeypatch.setattr(vnz, "send_telegram_message", lambda m: sent.append(m))
    monkeypatch.setattr(vnz, "TELEGRAM_ALERT_TYPES", ("DATA_DEGRADED",))
    vnz._kline_cache_note_degraded(True)
    assert len(sent) == 1, "بلاغ التدهور يُرسل أول مرة"
    # «إعادة تشغيل»: حالة الذاكرة تصفر لكن القاعدة تحمل حجز اليوم
    vnz._kline_cache_state["degraded"] = False
    vnz._kline_cache_note_degraded(True)
    assert len(sent) == 1, "إعادة النشر أثناء التدهور لا تكرر البلاغ (حجز يومي)"
    vnz._kline_cache_note_degraded(False)  # نظافة حالة للاختبارات التالية


def test_manual_close_required_claimed_under_race(clean_db, monkeypatch):
    """سباق المسارين: مسارا فشل متزامنان يقرآن meta قبل أن يكتب أي منهما —
    كلاهما يجتاز حارس 600ث لكن الحجز الذري يضمن تلغرامًا واحدًا."""
    sent = []
    monkeypatch.setattr(vnz, "send_telegram_message", lambda m: sent.append(m))
    monkeypatch.setattr(vnz, "TELEGRAM_ALERT_TYPES", ("MANUAL_CLOSE_REQUIRED",))
    sig = {"id": 77, "symbol": "AAA/USDT", "quantity": 1.0, "meta_json": "{}"}
    vnz._flag_manual_close_required(sig, 123.0, "هدفها لمس")
    # «المسار الثاني» في نفس اللحظة: meta لم يُرَ — نموذج السباق بإعادة meta فارغة
    sig2 = {"id": 77, "symbol": "AAA/USDT", "quantity": 1.0, "meta_json": "{}"}
    vnz._flag_manual_close_required(sig2, 123.0, "هدفها لمس")
    assert len(sent) == 1, "الحجز الذري يمنع التكرار رغم سباق meta"
    rows = vnz.db.query("SELECT key FROM notify_claim WHERE key LIKE 'mcr:77:%'")
    assert len(rows) == 1, "مفتاح الحجز باسم الصفقة واليوم"


# ─────────────────────────────────────────────────────────────────────────────
# 4) /api/klines — SWR
# ─────────────────────────────────────────────────────────────────────────────

def test_klines_fill_on_miss_serves_fresh_symbol(clean_db, monkeypatch, fresh_fill_state):
    """الجذر: رمز بلا كاش إطلاقًا (لم يدخل المسح) يُرسم الآن — جلب فوري وخدمة."""
    monkeypatch.setattr(vnz, "WS_ENABLED", False)
    # آخر شمعة مغلقة فعليًا (قبل فترة كاملة) — الكاتب الحقيقي يقصّ الجارية
    fresh_rows = [[int(time.time() * 1000) - i * 300_000, 10 + i, 11 + i, 9 + i, 10.5 + i, 5]
                  for i in range(1, 61)][::-1]

    def fake_fill(symbol, tf, limit, wait=True):
        vnz._kline_cache_write(symbol, tf, fresh_rows)  # fetch_ohlcv_raw تكتب الكاش بنفسها
        return fresh_rows, "bybit", "ok"

    monkeypatch.setattr(vnz, "_klines_fetch_fill", fake_fill)
    body = client().get("/api/klines?symbol=NEWX/USDT&tf=5m&limit=60").get_json()
    assert body["count"] == 60 and body["filled"] is True and body["fill_source"] == "bybit"
    ts = [c[0] for c in body["candles"]]
    assert ts == sorted(ts), "تصاعدي صارم بعد الملء"
    assert body["source"] in ("cache", "cache+live")


def test_klines_empty_has_named_reason(clean_db, monkeypatch):
    """الحالة الفارغة الصادقة: سبب مسمّى من الخادم (التبريد هنا من عزل conftest)."""
    monkeypatch.setattr(vnz, "WS_ENABLED", False)
    body = client().get("/api/klines?symbol=VOID/USDT&tf=5m&limit=50").get_json()
    assert body["candles"] == [] and body["source"] == "none"
    assert body.get("reason") in ("waited", "cooldown", "inflight", "busy", "failed", "no_data")
    assert body["filled"] is False


def test_klines_bad_symbol_reason(clean_db, monkeypatch):
    monkeypatch.setattr(vnz, "WS_ENABLED", False)
    body = client().get("/api/klines?symbol=NOPE&tf=5m").get_json()
    assert body["candles"] == [] and body.get("reason") == "bad_symbol"


def test_klines_stale_cache_served_and_refresh_kicked(clean_db, monkeypatch, fresh_fill_state):
    """قِدم الكاش لا يبطئ العرض: يُخدم فورًا ويُطلب تحديثه خلفيًا."""
    monkeypatch.setattr(vnz, "WS_ENABLED", False)
    old_ts = int(time.time() * 1000) - 3 * 3600 * 1000 - 40 * 300_000  # منذ 3 ساعات — قديم ل5m (وأغلقت كلها)
    seed_cache(n=40, base_ts=old_ts)
    kicked = []
    monkeypatch.setattr(vnz, "_klines_bg_refresh", lambda s, t, l: kicked.append((s, t)) or True)
    body = client().get("/api/klines?symbol=TEST/USDT&tf=5m&limit=50").get_json()
    assert body["count"] == 40 and body["stale"] is True
    assert kicked == [("TEST/USDT", "5m")], "التحديث الخلفي طُلب مرة للرمز القديم"


def test_klines_fresh_cache_no_refresh(clean_db, monkeypatch, fresh_fill_state):
    monkeypatch.setattr(vnz, "WS_ENABLED", False)
    seed_cache(n=40)  # طازج (الآن)
    kicked = []
    monkeypatch.setattr(vnz, "_klines_bg_refresh", lambda s, t, l: kicked.append(1) or True)
    body = client().get("/api/klines?symbol=TEST/USDT&tf=5m&limit=50").get_json()
    assert body["count"] == 40 and body["stale"] is False and kicked == []


def test_klines_cache_last_ts_helper(clean_db):
    assert vnz._klines_cache_last_ts("NONE/USDT", "5m") == 0
    rows = seed_cache(n=10)
    assert vnz._klines_cache_last_ts("TEST/USDT", "5m") == int(rows[-1][0])
    assert vnz._klines_cache_is_stale("TEST/USDT", "5m") is False


# ─────────────────────────────────────────────────────────────────────────────
# 5) _klines_fetch_fill — dedup + تبريد الفشل
# ─────────────────────────────────────────────────────────────────────────────

def test_fetch_fill_dedup_single_fetch(clean_db, monkeypatch, fresh_fill_state):
    """نداءان متزامنان لنفس الرمز → جلب مزود واحد فعليًا (نمط in-flight)."""
    monkeypatch.setattr(vnz, "_klines_fetch_fill", REAL_FILL)  # استعادة الأصل من عزل conftest
    calls = []
    rows = [[int(time.time() * 1000) - i * 300_000, 10, 11, 9, 10.5, 5] for i in range(1, 6)][::-1]

    def slow_fetch(symbol, timeframe, limit):
        calls.append((symbol, timeframe))
        time.sleep(0.4)
        vnz._kline_cache_write(symbol, timeframe, rows)
        return rows, "okx"

    monkeypatch.setattr(vnz, "fetch_ohlcv_raw", slow_fetch)
    t = threading.Thread(target=lambda: vnz._klines_fetch_fill("DDD/USDT", "5m", 180))
    t.start()
    time.sleep(0.08)  # الأول داخل الجلب — الثاني يمر من الطريق المنتظر
    _r, _s, status2 = vnz._klines_fetch_fill("DDD/USDT", "5m", 180)
    t.join()
    assert status2 == "waited", "المستدعي الثاني انتظر الحدث لا جلبًا ثانيًا"
    assert len(calls) == 1, "جلب واحد فعلي"
    _r, _s, status3 = vnz._klines_fetch_fill("DDD/USDT", "5m", 180)
    assert status3 == "ok" and len(calls) == 2  # الثالث جلب جديد (الحادثة انتهت) — مقبول
    assert vnz._klines_fill_state["dedup_waits"] == 1


def test_fetch_fill_failure_cooldown(clean_db, monkeypatch, fresh_fill_state):
    """المزود الذي عجز للتو لا يُستنزف بكل نبضة شارت — تبريد 60ث (نمط RecentFailure)."""
    monkeypatch.setattr(vnz, "_klines_fetch_fill", REAL_FILL)
    calls = []
    monkeypatch.setattr(vnz, "fetch_ohlcv_raw", lambda s, t, l: calls.append(1) or (None, None))
    _r, _s, st1 = vnz._klines_fetch_fill("FFF/USDT", "5m", 180)
    assert st1 == "failed"
    _r, _s, st2 = vnz._klines_fetch_fill("FFF/USDT", "5m", 180)
    assert st2 == "cooldown" and len(calls) == 1, "ضمن التبريد لا مزود يُلمس"
    assert vnz._klines_fill_state["cooldown_skips"] == 1
    vnz._klines_fail_until.pop("FFF/USDT|5m", None)  # انقضاء التبريد
    _r, _s, st3 = vnz._klines_fetch_fill("FFF/USDT", "5m", 180)
    assert st3 == "failed" and len(calls) == 2, "بعد التبريد عادت المحاولة"


def test_fetch_fill_exception_cooldowns_too(clean_db, monkeypatch, fresh_fill_state):
    monkeypatch.setattr(vnz, "_klines_fetch_fill", REAL_FILL)

    def boom(*a):
        raise RuntimeError("net down")
    monkeypatch.setattr(vnz, "fetch_ohlcv_raw", boom)
    _r, _s, st = vnz._klines_fetch_fill("GGG/USDT", "5m", 180)
    assert st == "failed"
    assert "GGG/USDT|5m" in vnz._klines_fail_until, "الاستثناء يدخل التبريد كذلك"


def test_bg_refresh_disabled_and_inflight_guard(clean_db, monkeypatch, fresh_fill_state):
    monkeypatch.setattr(vnz, "KLINE_BG_REFRESH", False)
    assert vnz._klines_bg_refresh("X/USDT", "5m", 180) is False
    monkeypatch.setattr(vnz, "KLINE_BG_REFRESH", True)
    vnz._klines_inflight["X/USDT|5m"] = threading.Event()  # جلب جارٍ
    assert vnz._klines_bg_refresh("X/USDT", "5m", 180) is False, "لا خيط ثانٍ لنفس الرمز"
    vnz._klines_inflight.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 6) /health
# ─────────────────────────────────────────────────────────────────────────────

def test_health_has_new_blocks(clean_db, monkeypatch):
    monkeypatch.setattr(vnz, "WS_ENABLED", False)
    body = client().get("/health").get_json()
    assert body["version"] == "FE1.10.0"
    kf = body["kline_fill"]
    assert kf["enabled"] is True and "fills" in kf and "cooldown_skips" in kf
    nc = body["notify_claim"]
    assert {"wins", "blocks", "errors"} <= set(nc)


# ─────────────────────────────────────────────────────────────────────────────
# 7) اللوحة (بنية FE1.9.15 المودالية) — الحالة الصادقة + الوميض باتجاه
# ─────────────────────────────────────────────────────────────────────────────

def test_panel_honest_empty_state_inside_modal():
    h = panel.PANEL_HTML
    assert 'id="chart-modal"' in h, "مودال FE1.9.15 باقٍ كما هو"
    assert 'id="chart-empty"' in h and 'id="chart-empty-reason"' in h, "طبقة الفراغ الصادقة داخل المودال"
    assert "لا شموع لهذا الرمز بعد" in h
    assert "WHY" in h and "cooldown" in h and "failed" in h, "أسباب مسمّاة تُترجم للعربية"
    assert "reason" in h, "قراءة سبب الخادم"
    # مسح أثر الرمز السابق: شموع + خطوط + طبقة المحرك
    assert "CSERIES.setData([])" in h and "chartApplyOverlays()" in h
    assert "ewxClear()" in h, "طبقة موجات المحرك تُمسح أيضًا"


def test_panel_directional_flash():
    h = panel.PANEL_HTML
    assert ".val.flash-up" in h and ".val.flash-down" in h, "توهج أخضر/أحمر بالCSS"
    assert "flash-up" in h and "flash-down" in h, "المراقب يوزع الاتجاه"
    assert "numOf" in h, "مستخرج رقمي — غير العددي يعود للمحايد"


def test_panel_fill_badge_and_swrnote():
    h = panel.PANEL_HTML
    assert "جُلبت الآن من" in h, "شارة الملء الفوري"
    assert "يُنعّش خلفيًا" in h, "شفافية التحديث الخلفي"
    assert "SWR [FE1.9.16]" in h, "عنوان المودال يصدّق عن مصدر الشموع الجديد"


# ─────────────────────────────────────────────────────────────────────────────
# 8) تزامن الإصدار
# ─────────────────────────────────────────────────────────────────────────────

def test_version_sync_vnz_panel():
    assert vnz.BOT_VERSION == "FE1.10.0"
    assert panel.BOT_VERSION == "FE1.10.0"
    assert panel.BOT_VERSION == vnz.BOT_VERSION
