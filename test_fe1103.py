#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات FE1.10.4 «إزالة شرط سقف الأسبوع»
==========================================
الطلب الحرفي للمستخدم: «قم بازالة شرط هدف فوق سقف الاسبوع».

ما يُغطيه الملف:
  1) الافتراضي: TP_WEEK_CAP_ENABLED=0 — لا قصّ ولا رفض سقف ولا تسوية أهداف حية،
     وسلّم المراحل TP1→TP3 باقٍ مستقلًا عن السقف (فصل FE1.10.4).
  2) create_pending_signal: صفر نداءات weekly_high والسقف معطل — الإشارة تولد
     بمراحل خام غير مقصوصة حتى لو كانت القمة (لو جُلبت) ستقتل كل الدرجات.
  3) build_staged_targets: weekly_hi=None أو غير موجبة = بلا قصّ على الإطلاق.
  4) انهيار المراحل داخل الباني بلا سقف = السلوك التراثي حرفيًا (أقرب درجة خام
     ≥ TP_MIN_RR) وتصنيفها بوابات الإنشاء العامة بصدق (rejected_rr_net).
  5) reconcile_live_targets: عودة مبكرة قبل أي قراءة DB — صفر عمل والسقف معطل.
  6) register_detection: العرض الهدف الخام بلا سقف (عقد الصدق).
  7) السقف يعود كاملًا بتفعيل صريح TP_WEEK_CAP_ENABLED=1 (بلا أي تغيير كود).
  8) تزامن الإصدار FE1.10.4.

التصميم: weekly_high معزولة عن الشبكة في كل الاختبارات (conftest autouse)،
وهنا تُستبدل بوظيفة ترمي AssertionError لإثبات أنها لا تُستدعى أصلًا.
"""

import json
from types import SimpleNamespace

import pytest

import vnz
vnz.DASHBOARD_PROTECTED = False  # بيئة الاختبار: بلا مصادقة
import panel


# ─────────────────────────────────────────────────────────────────────────────
# أدوات
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def clean_db(monkeypatch):
    """قاعدة SQLite مؤقتة لكل اختبار — عزل كامل."""
    monkeypatch.setattr(vnz, "USE_POSTGRES", False)
    import sqlite3
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    old = vnz.db.conn
    vnz.db.conn = conn
    vnz.init_db()
    yield
    vnz.db.conn = old


@pytest.fixture()
def tg_off(monkeypatch):
    monkeypatch.setattr(vnz, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(vnz, "TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr(vnz, "_tg_dedup", {})
    yield


def ladder_of(pairs):
    """سلّم ثابت للاختبار — يستبدل compute_tp_ladder داخل build_staged_targets."""
    return [(p, b) for p, b in pairs]


def _creation_setup():
    """إعداد صالح: دخول 100/وقف 98 وسلّم فوق الدخول (104/106/108)."""
    return SimpleNamespace(
        direction="BULLISH", timeframe="1h",
        entry_zone_low=100.0, entry_zone_high=101.0, stop_loss_price=98.0,
        pivot_prices=[100.0, 110.0, 102.0, 124.0, 106.0, 118.0],
        validation_result=SimpleNamespace(fib=None),
    )


def _weekly_high_must_not_be_called(symbol):
    raise AssertionError("weekly_high استُدعيت والسقف معطل!")


# ─────────────────────────────────────────────────────────────────────────────
# 1) الافتراضي بعد الإزالة
# ─────────────────────────────────────────────────────────────────────────────

def test_weekly_cap_disabled_by_default_and_ladder_independent():
    # [FE1.10.4] قرار المستخدم: السقف معطل افتراضيًا — والسلّم المرحلي باقٍ مستقلًا
    assert vnz.TP_WEEK_CAP_ENABLED is False
    assert vnz.TP_STAGES_ENABLED is True
    assert vnz.TP_LADDER_ENABLED is True
    assert vnz.TP_WEEK_CAP_DAYS == 7  # نافذة القمة باقية للتفعيل الاختياري


# ─────────────────────────────────────────────────────────────────────────────
# 2) create_pending_signal — صفر نداءات قمة والسقف معطل
# ─────────────────────────────────────────────────────────────────────────────

def test_create_never_fetches_weekly_high_when_cap_disabled(clean_db, tg_off, monkeypatch):
    monkeypatch.setattr(vnz, "weekly_high", _weekly_high_must_not_be_called)
    monkeypatch.setattr(vnz, "compute_tp_ladder",
                        lambda s: ladder_of([(104.0, "w5_eq_w1"), (106.0, "w5_0618_w3"),
                                             (108.0, "ext_1618")]))
    # هذه الهندسة كانت قديمًا تُرفض برفض سقف الأسبوع لو كانت القمة 101.5 — الآن تولد
    assert vnz.create_pending_signal("TEST/USDT", _creation_setup(), last_close=0) is True
    row = vnz.db.query("SELECT * FROM signals ORDER BY id DESC LIMIT 1")[0]
    assert row["weekly_high"] is None
    assert row["tp1"] == pytest.approx(104.0)
    assert row["tp3"] == pytest.approx(108.0)
    assert row["take_profit"] == pytest.approx(108.0)
    fj = json.loads(row["fib_json"])
    assert fj["weekly_capped"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 3) build_staged_targets — بلا قمة تعبر الدرجات الخام
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("hi", [None, 0.0, -5.0])
def test_build_staged_targets_no_cap_when_weekly_hi_missing(monkeypatch, hi):
    monkeypatch.setattr(vnz, "compute_tp_ladder",
                        lambda s: ladder_of([(104.0, "w5_eq_w1"), (106.0, "w5_0618_w3"),
                                             (108.0, "ext_1618")]))
    s = SimpleNamespace(direction="BULLISH", pivot_prices=[100.0] * 6, timeframe="1h")
    stages, capped, best = vnz.build_staged_targets(s, 100.0, 98.0, hi)
    assert [p for p, _ in stages] == [104.0, 106.0, 108.0], "بلا سقف تعبر الدرجات كما هي"
    assert capped is False, "لا ادعاء قصّ بلا سقف"
    assert best == pytest.approx(4.0)  # (108-100)/2


# ─────────────────────────────────────────────────────────────────────────────
# 4) انهيار المراحل بلا سقف = السلوك التراثي وتصنيف صادق
# ─────────────────────────────────────────────────────────────────────────────

def _rrnet_setup():
    """هندسة test_fe193: دخول 109.27/وقف 89.91 (مخاطرة 19.36) — درجة 119 تحقق
    0.50R خامًا لكن rr_net ≈ 0.49 تحت الأرضية المرفوعة 0.9."""
    return SimpleNamespace(
        direction="BULLISH", timeframe="1h",
        entry_zone_low=109.27, entry_zone_high=110.0, stop_loss_price=89.91,
        pivot_prices=[90.0, 100.0, 100.0, 115.0, 104.0, 108.0],
        validation_result=SimpleNamespace(fib=None),
    )


def test_collapsed_stages_fall_back_to_legacy_rung_and_honest_rr_net_gate(
        clean_db, tg_off, monkeypatch):
    """درجة تخلف أرضية R:R الصافي داخل الباني بلا سقف → الهدف التراثي (أقرب درجة
    خام مؤهلة) → بوابة rejected_rr_net العامة تصنّفها بصدق كما قبل FE1.9.9."""
    monkeypatch.setattr(vnz, "compute_take_profit", lambda s: 105.0)
    monkeypatch.setattr(vnz, "compute_tp_ladder", lambda s: [(119.0, "w5_eq_w1")])
    monkeypatch.setattr(vnz, "RR_NET_MIN", 0.9)
    with vnz.scan_stats_lock:
        vnz.scan_stats["rejected_rr_net"] = 0
    assert vnz.create_pending_signal("TEST/USDT", _rrnet_setup(), last_close=0) is False
    reason = vnz._get_reject_reason("TEST/USDT") or ""
    assert "R:R" in reason, f"التصنيف الصادق مفقود: {reason}"
    assert "غير منطقية" not in reason, "التصنيف المضلل ظهر مجددًا"
    with vnz.scan_stats_lock:
        assert vnz.scan_stats["rejected_rr_net"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 5) reconcile_live_targets — عودة مبكرة بلا أي قراءة DB
# ─────────────────────────────────────────────────────────────────────────────

def test_reconcile_noop_when_cap_disabled(clean_db, monkeypatch):
    vnz._TP_RECONCILE_LAST["at"] = 0.0  # تجاوز بوابة الإيقاع — العودة عبر بوابة العلم

    def _boom(*a, **k):
        raise AssertionError("تسوية الأهداف تعمل والسقف معطل!")

    monkeypatch.setattr(vnz.db, "query", _boom)
    vnz.reconcile_live_targets()  # لا استثناء — عادت قبل أي قراءة
    assert vnz._TP_RECONCILE_LAST["at"] == 0.0, "لا يُسجَّل إيقاع تسوية معطل"


# ─────────────────────────────────────────────────────────────────────────────
# 6) register_detection — العرض الهدف الخام بلا سقف
# ─────────────────────────────────────────────────────────────────────────────

def test_register_detection_shows_raw_target_when_cap_disabled(clean_db, monkeypatch):
    monkeypatch.setattr(vnz, "weekly_high", _weekly_high_must_not_be_called)
    setup = _creation_setup()
    raw_tp = vnz.compute_take_profit(setup)
    vnz.register_detection("TEST/USDT", setup, traded=False)
    det = vnz.recent_detections[0]
    assert det["take_profit"] == pytest.approx(raw_tp), "العرض بلا قصّ — الهدف الخام صادق"
    assert det["weekly_high"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 7) السقف يعود بتفعيل صريح — بلا أي تغيير كود
# ─────────────────────────────────────────────────────────────────────────────

def test_cap_still_available_behind_explicit_flag(clean_db, tg_off, monkeypatch):
    monkeypatch.setattr(vnz, "TP_WEEK_CAP_ENABLED", True)
    calls = []

    def _wh(symbol):
        calls.append(symbol)
        return 100.5  # قمة تلتهم كل الدرجات بعد القص (دخول 100)

    monkeypatch.setattr(vnz, "weekly_high", _wh)
    n0 = vnz.scan_stats["rejected_weekly_cap"]
    ok = vnz.create_pending_signal("TEST/USDT", _creation_setup(), last_close=0)
    assert ok is False, "مع سقف مفعّل: لا هدف واقعي تحت القمة = رفض كما في FE1.9.9"
    assert calls == ["TEST/USDT"], "القمة تُجلب مرة واحدة عندما السقف مفعّل"
    with vnz.scan_stats_lock:
        assert vnz.scan_stats["rejected_weekly_cap"] == n0 + 1


# ─────────────────────────────────────────────────────────────────────────────
# 8) تزامن الإصدار
# ─────────────────────────────────────────────────────────────────────────────

def test_version_sync():
    assert vnz.BOT_VERSION == "FE1.10.4"
    assert panel.BOT_VERSION == "FE1.10.4"
