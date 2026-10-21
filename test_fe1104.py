#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات FE1.10.4 «تدفق الأوامر — CVD يؤكد الموجات + بروفايل الحجم×فيبو + جدران السيولة كأهداف»
====================================================================================================
الطلب الحرفي للمستخدم: «اعتمادا على المشاريع التالية انجز مايلي: (1) استخدام CVD لتأكيد
عدّ الموجات (من Flowsurface وFlowMap) (2) دمج Volume Profile مع مستويات فيبوناتشي (من
FlowMap وOrderFlowMap) (3) جدران السيولة كأهداف للموجات (فكرة Liquidity Radar من OrderFlowMap)».

ما يُغطيه الملف:
  1) CVD: سلسلة taker من كلاين باينانس الخام (2×takerBuy−volume تراكمية) + فشل الجلب
     يخزَّن سلبيًا (لا مطرقة) + المتراكم الحي من علم الصانع m في @trade + دمج raw_handle_message.
  2) cvd_wave_check: تأكيد/تعارض (taker فقط يقتل)/انحراف W5 علم لا حقض/التقدير لا يقتل/غياب محايد.
  3) Volume Profile: توزيع الشموع على المدى (مجموع الدلاء = مجموع الحجم) وPOC ومنطقة 70% وتلاقي الدخول.
  4) Liquidity Radar: قاعدة الجدار 2.2×المتوسط + الأرضية الاسمية + الاستمرارية المضادة للـspoofing
     + دمج الجدران كسلالم أهداف بنفس بوابات الدرجات (rr خام/rr_net/الفجوة/السقوف) وسلّم الموجات باقٍ.
  5) create_pending_signal: الجدران تدخل tp_stages/fib_json (tp_bases/wall_targets/walls) والتلغرام،
     وبدون OFLOW السلوك التراثي حرفيًا (لا مفاتيح ولا شبكة).
  6) composite_confidence: مكوّنا cvd/vp يُضافان حصرًا مع oflow (التراث بلا إضافة).
  7) /health قسم orderflow + صدى الحماية + تزامن الإصدار FE1.10.4.

التصميم: كل اختبارات الإرث ترى OFLOW_ENABLED=False من مصيدة conftest الجديدة؛ هنا تُفعَّل
الطبقة صراحةً لكل اختبار وتُعزل الشبكة بكلها (كلاين taker والدفتر وظائف مصطنعة بلا نداءات).
"""

import json
import time
from types import SimpleNamespace

import pandas as pd
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


def make_df(closes, highs=None, lows=None, vols=None, forming=True):
    """إطار شموع ببنية fetch_ohlcv_df الحرفية — آخر صف شمعة جارية افتراضيًا."""
    n = len(closes)
    highs = highs or [c * 1.01 for c in closes]
    lows = lows or [c * 0.99 for c in closes]
    vols = vols or [10.0 + (i % 5) for i in range(n)]
    base = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp() * 1000)
    rows = [[base + i * 300000, closes[i] * 0.999, highs[i], lows[i], closes[i], vols[i]]
            for i in range(n)]
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df["symbol"] = "TEST/USDT"
    df["timeframe"] = "5m"
    return df[["timestamp", "open", "high", "low", "close", "volume", "ts"]]


def _setup(direction="BULLISH", indices=None, prices=None):
    return SimpleNamespace(
        direction=direction, timeframe="5m",
        entry_zone_low=100.0, entry_zone_high=101.0, stop_loss_price=98.0,
        pivot_indices=indices or [2, 8, 12, 20, 26, 32],
        pivot_prices=prices or [100.0, 110.0, 102.0, 124.0, 106.0, 118.0],
        validation_result=SimpleNamespace(fib=None),
    )


def seed_cvd(series, method="taker"):
    """زرع سلسلة CVD في الكاش — بلا شبكة إطلاقًا."""
    vnz._cvd_cache["TEST/USDT"] = (time.time(), list(series), method)


def oflow_on(monkeypatch):
    """تفعيل الطبقة لهذا الاختبار (تتخطى مصيدة conftest — monkeypatch لاحق يطغى)."""
    monkeypatch.setattr(vnz, "OFLOW_ENABLED", True)


# ─────────────────────────────────────────────────────────────────────────────
# 1) سلسلة CVD من كلاين taker
# ─────────────────────────────────────────────────────────────────────────────

def test_cvd_taker_series_cumsum(monkeypatch):
    """الصف الخام بعمود taker (فهرس 9) يتحول إلى CVD تراكمي = Σ(2×takerBuy − volume)."""
    oflow_on(monkeypatch)
    # كلاين باينانس الخام 12 عمودًا — الفهرس 9 هو takerBuyBaseAssetVolume (دلتا = 2×8−10 = 6)
    kl = [[i * 300000, 100, 101, 99, 100.5, 10.0, 0, 0, 0, 8.0, 0, 0] for i in range(15)]
    ex = SimpleNamespace(publicGetKlines=lambda params: kl)
    monkeypatch.setitem(vnz.EXCHANGES, "binance", ex)
    monkeypatch.setattr(vnz, "_bin_rest_gate", lambda w, p="": None)
    out = vnz._cvd_refresh("TEST/USDT")
    assert out is not None and out[1] == "taker"
    series = out[0]
    assert len(series) == 15
    assert series[0] == pytest.approx(6.0)
    assert series[-1] == pytest.approx(90.0)  # 6 × 15
    assert vnz._cvd_stats["fetch_ok"] >= 1


def test_cvd_refresh_failure_negative_cache(monkeypatch):
    """فشل الجلب يخزَّن سلبيًا حتى نهاية TTL — النداء التالي لا يطرق المزود (لا مطرقة)."""
    oflow_on(monkeypatch)
    calls = {"n": 0}

    def boom(_ex, _s, _tf, _lim):
        calls["n"] += 1
        raise RuntimeError("انقطاع")

    ex = SimpleNamespace(publicGetKlines=boom)
    monkeypatch.setitem(vnz.EXCHANGES, "binance", ex)
    monkeypatch.setattr(vnz, "_bin_rest_gate", lambda w, p="": None)
    monkeypatch.setattr(vnz, "_binance_raw_klines_taker", boom)
    assert vnz._cvd_refresh("FAIL/USDT") is None
    assert vnz._cvd_refresh("FAIL/USDT") is None
    assert calls["n"] == 2  # كل نداء _cvd_refresh محاولة واحدة — الكاش السلبي يمنع التسلسل المطارِق
    assert vnz._cvd_cache["FAIL/USDT"][2] == "none"


# ─────────────────────────────────────────────────────────────────────────────
# 2) المتراكم الحي من تيك @trade (علم الصانع)
# ─────────────────────────────────────────────────────────────────────────────

def test_raw_cvd_accumulator_and_delta():
    """m=True (المشتري صانع) = بيع taker — الدلتا الحية شراء−بيع ودلو الفريم يتجدد."""
    vnz._raw_cvd.clear()
    vnz._raw_cvd_apply("T/USDT", 5.0, False)   # شراء 5
    vnz._raw_cvd_apply("T/USDT", 2.0, True)    # بيع 2
    assert vnz.raw_cvd_current_delta("T/USDT") == pytest.approx(3.0)
    st = vnz._raw_cvd["T/USDT"]
    assert st["buy"] == pytest.approx(5.0) and st["sell"] == pytest.approx(2.0)
    st["bucket"] = -1  # فرض تجدد الدلو
    vnz._raw_cvd_apply("T/USDT", 1.0, True)
    assert vnz.raw_cvd_current_delta("T/USDT") == pytest.approx(-1.0)  # الدلو تصفّر ثم بيع 1
    assert vnz.raw_cvd_current_delta("NOPE/USDT") is None
    vnz._raw_cvd.clear()


def test_raw_handle_message_feeds_cvd(monkeypatch):
    """@trade مع q وm يغذي المتراكم — الحقول التي كانت تُرمى في FE1.10.4."""
    vnz._raw_cvd.clear()
    saved_state = dict(vnz._raw_state)  # عدادات عامة مشتركة — تُستعاد بعد الاختبار
    monkeypatch.setitem(vnz._raw_mid_to_symbol, "btcusdt", "BTC/USDT")
    monkeypatch.setattr(vnz, "ws_apply_price", lambda s, p, src: True)
    vnz._raw_trigger_levels.pop("BTC/USDT", None)
    msg = json.dumps({"stream": "btcusdt@trade",
                      "data": {"p": "50000", "q": "0.5", "m": False}})  # مهاجم مشترٍ
    assert vnz.raw_handle_message(msg) == "trade"
    assert vnz.raw_cvd_current_delta("BTC/USDT") == pytest.approx(0.5)
    msg2 = json.dumps({"stream": "btcusdt@trade",
                       "data": {"p": "50001", "q": "0.2", "m": True}})  # مهاجم بائع
    vnz.raw_handle_message(msg2)
    assert vnz.raw_cvd_current_delta("BTC/USDT") == pytest.approx(0.3)
    vnz._raw_cvd.clear()
    with vnz._raw_state_lock:  # استعادة عدادات _raw_state العامة — لا تلوث لاختبار fe197
        vnz._raw_state.clear()
        vnz._raw_state.update(saved_state)


# ─────────────────────────────────────────────────────────────────────────────
# 3) cvd_wave_check — تأكيد عدّ الموجات
# ─────────────────────────────────────────────────────────────────────────────

def test_cvd_confirms_bullish(monkeypatch):
    """ميل taker صاعد لبنيه صاعدة = confirms بنقاط كاملة."""
    oflow_on(monkeypatch)
    df = make_df([100 + i * 0.1 for i in range(41)])
    seed_cvd([float(i) for i in range(41)], "taker")  # ميل صاعد قوي
    res = vnz.cvd_wave_check("TEST/USDT", _setup(), df)
    assert res["state"] == "confirms" and res["veto"] is False
    assert res["pts"] == 10.0 and res["method"] == "taker"


def test_cvd_conflict_vetoes_taker_only(monkeypatch):
    """بيع taker صافٍ قوي ضد بنية صاعدة = conflict + حقض (taker فقط)."""
    oflow_on(monkeypatch)
    df = make_df([100 + i * 0.1 for i in range(41)])
    # ميل هابط 3/شمعة × نافذة 6 = −18 مقابل وسيط حجم 12 → slope_norm = −1.5 ≤ −1.0 (عتبة الحقض)
    seed_cvd([float(123 - 3 * i) for i in range(41)], "taker")
    res = vnz.cvd_wave_check("TEST/USDT", _setup(), df)
    assert res["state"] == "conflict" and res["veto"] is True and res["pts"] == 0.0


def test_cvd_estimate_never_vetoes(monkeypatch):
    """التقدير الموضعي (ohlc_est) حتى لو عارض بقوة = soft_against بلا حقض — صدق المصدر."""
    oflow_on(monkeypatch)
    closes = [100.0] * 41
    highs = [101.0] * 41
    lows = [99.0] * 41
    vols = [10.0] * 41
    # إغلاق عند القاع دائمًا → دلتا تقديرية سالبة بقوة
    df = make_df(closes, highs, lows, vols)
    df.loc[df.index[:-1], "close"] = df.loc[df.index[:-1], "low"]  # الإغلاق = القاع
    vnz._cvd_cache.clear()  # لا كاش → تقدير من الشموع
    res = vnz.cvd_wave_check("TEST/USDT", _setup(), df)
    assert res["method"] == "ohlc_est"
    assert res["veto"] is False
    assert res["state"] in ("soft_against", "neutral", "confirms")  # الحقض محظور على التقدير


def test_cvd_divergence_w5_flag(monkeypatch):
    """CVD عند P5 أدنى منه عند P3 مع قمة سعرية أعلى = علم انحراف (لا حقض) و0 نقاط."""
    oflow_on(monkeypatch)
    df = make_df([100 + (i % 3) * 0.05 for i in range(41)])
    # سلسلة تنحدر بعد الفهرس 20 (P3) — القمة السعرية P5 (32) أعلى لكن الدلتا أدنى
    series = [10.0] * 21 + [10.0 - (i - 20) * 0.2 for i in range(21)]
    seed_cvd(series, "taker")
    setup = _setup(prices=[100.0, 110.0, 102.0, 118.0, 106.0, 124.0])  # P5 أعلى من P3
    res = vnz.cvd_wave_check("TEST/USDT", setup, df)
    assert res["div_w5"] is True and res["state"] == "divergence"
    assert res["veto"] is False and res["pts"] == 0.0


def test_cvd_missing_data_neutral(monkeypatch):
    """غياب البيانات (df قصير) = محايد fail-open — البوابة جودة لا نقطة فشل."""
    oflow_on(monkeypatch)
    df = make_df([100.0 + i * 0.1 for i in range(8)])
    res = vnz.cvd_wave_check("TEST/USDT", _setup(), df)
    assert res["state"] == "neutral" and res["veto"] is False and res["pts"] == 5.0


def test_cvd_gate_disabled_no_veto(monkeypatch):
    """CVD_GATE_ENABLED=0 (مع OFLOW مفعل) = فحص محايد — لا حقض ولا نقاط."""
    oflow_on(monkeypatch)
    monkeypatch.setattr(vnz, "CVD_GATE_ENABLED", False)
    df = make_df([100 + i * 0.1 for i in range(41)])
    res = vnz.cvd_wave_check("TEST/USDT", _setup(), df)
    assert res["state"] == "neutral" and res["method"] == "none"


# ─────────────────────────────────────────────────────────────────────────────
# 4) Volume Profile + تلاقي فيبوناتشي
# ─────────────────────────────────────────────────────────────────────────────

def test_volume_profile_totals_and_poc(monkeypatch):
    """مجموع الدلاء = مجموع الحجم حرفيًا (التوزيع محفوظ) وPOC في منطقة التكدس."""
    oflow_on(monkeypatch)
    closes = []
    highs, lows, vols = [], [], []
    for i in range(60):
        dense = (i % 20) in (1, 2)  # تكدس الحجم عند الإغلاقين 99.2/99.4
        c = 99.0 + (i % 20) * 0.2
        closes.append(c)
        highs.append(c + 0.1)
        lows.append(c - 0.1)
        vols.append(50.0 if dense else 1.0)
    df = make_df(closes, highs, lows, vols)
    vp = vnz.volume_profile(df, bins=40)
    assert vp is not None
    assert vp["total"] == pytest.approx(sum(vols[:-1]), rel=1e-6)  # المغلقة حصرًا — الشمعة الجارية مستبعدة
    assert vp["val"] < vp["poc"] < vp["vah"]
    assert abs(vp["poc"] - 99.3) < 0.6  # POC داخل نطاق التكدس المصنوع
    assert vp["method"] == "kline_spread"


def test_volume_profile_insufficient_data(monkeypatch):
    oflow_on(monkeypatch)
    assert vnz.volume_profile(make_df([100.0 + i for i in range(10)])) is None
    assert vnz.volume_profile(None) is None


def test_vp_confluence_nodes(monkeypatch):
    """الدخول عند POC يعطي (POC، 5) — بعيد عن كل العقد = (None، 0)."""
    oflow_on(monkeypatch)
    vp = {"poc": 100.0, "vah": 102.0, "val": 98.5, "hvn": [101.0], "total": 100.0,
          "bins": 48, "method": "kline_spread"}
    assert vnz.vp_confluence(vp, 100.02, atr=0.5) == ("POC", 5.0)
    assert vnz.vp_confluence(vp, 101.01, atr=0.5) == ("HVN", 3.0)
    assert vnz.vp_confluence(vp, 105.0, atr=0.5) == (None, 0.0)
    assert vnz.vp_confluence(None, 100.0) == (None, 0.0)


def test_build_oflow_info_vp_node(monkeypatch):
    """build_oflow_info يربط تلاقي منطقة الدخول مع عقدة البروفايل (فيبو×حجم)."""
    oflow_on(monkeypatch)
    closes = [100.0 + (i % 7) * 0.05 for i in range(60)]
    df = make_df(closes)
    setup = _setup()
    setup.entry_zone_low = float(df["close"].iloc[10])  # داخل منطقة التكدس نفسها
    info = vnz.build_oflow_info("TEST/USDT", setup, df, atr=0.0)
    assert "vp" in info
    assert info["vp"]["node"] in ("POC", "VAH", "VAL", "HVN", None)
    assert "poc" in info["vp"]


# ─────────────────────────────────────────────────────────────────────────────
# 5) Liquidity Radar — الجدران كأهداف
# ─────────────────────────────────────────────────────────────────────────────

def _fake_book(ask_wall_price=107.0, ask_wall_qty=None):
    """دفتر مصنوع: جدران متوسطة 100k$ لكل دلو 0.1% وجدار ضخم عند السعر المعطى."""
    def book(symbol):
        asks, bids = [], []
        for i in range(1, 60):
            p = 100.0 + i * 0.1
            asks.append([round(p, 4), 1000.0])  # 100k$ لكل مستوى
            bids.append([round(100.0 - i * 0.1, 4), 1000.0])
        # جدار ضخم: 4 مستويات متجاورة عند 107.0-107.3 (دلو 0.1% واحد = 400k$)
        for k in range(4):
            asks.append([round(ask_wall_price + k * 0.02, 4), ask_wall_qty or 5000.0])
        asks.sort(key=lambda x: x[0])
        bids.sort(key=lambda x: x[0], reverse=True)
        return {"bids": bids, "asks": asks, "source": "fake"}
    return book


def test_cluster_walls_orderflowmap_rule(monkeypatch):
    """قاعدة OrderFlowMap: دلو ≥ 2.2×متوسط + أرضية اسمية = جدار — والتاجر لا يمر بلا الأرضية."""
    oflow_on(monkeypatch)
    monkeypatch.setattr(vnz, "LIQ_WALL_MULT", 2.2)
    monkeypatch.setattr(vnz, "LIQ_WALL_MIN_NOTIONAL", 8000.0)
    # 40 مستوى عاديًا: دلو 0.1% يحوي مستويين ≈ 2k$ لكل دلو
    levels = [[100.0 + i * 0.05, 10.0] for i in range(40)]
    walls = vnz._cluster_walls(levels, "ask", 100.0)
    assert walls == []  # لا جدران — كل الدلاء متساوية
    # جدار ضخم: 4 مستويات متجاورة داخل دلو واحد عند ~101.0 (40k$ = 21× المتوسط)
    levels += [[101.0 + k * 0.02, 100.0] for k in range(4)]
    walls = vnz._cluster_walls(levels, "ask", 100.0)
    assert len(walls) == 1 and walls[0]["side"] == "ask"
    assert walls[0]["notional"] == pytest.approx(43_443.5, rel=1e-3)  # الجدار + مستويا الدلو النظاميان


def test_liq_persistence_anti_spoof(monkeypatch):
    """الجدار في الجلب الأول بلا persisted وفي الثاني (خلال 10د) persisted=True."""
    oflow_on(monkeypatch)
    monkeypatch.setattr(vnz, "_fetch_book_raw", _fake_book())
    vnz._liq_cache.clear()
    vnz._liq_wall_mem.clear()
    s1 = vnz.liquidity_walls("TEST/USDT", 100.0)
    assert s1 is not None and s1["ask_walls"]
    w1 = s1["ask_walls"][-1]
    with vnz._liq_lock:
        vnz._liq_cache.pop("TEST/USDT")  # إسقاط كاش اللقطة فقط — ذاكرة الاستمرارية باقية
    s2 = vnz.liquidity_walls("TEST/USDT", 100.0)  # جلب جديد يرى الجدار نفسه في الذاكرة
    w2 = s2["ask_walls"][-1]
    assert w2["persisted"] is True and w1["persisted"] is False


def test_merge_wall_targets_qualification(monkeypatch):
    """الجدران تُؤهَّل ببوابات الدرجات: rr خام ≥ TP_MIN_RR وrr_net ≥ RR_NET_MIN وفجوة 0.2R."""
    oflow_on(monkeypatch)
    monkeypatch.setattr(vnz, "LIQ_RADAR_ENABLED", True)
    monkeypatch.setattr(vnz, "LIQ_WALL_MAX_TARGETS", 2)
    monkeypatch.setattr(vnz, "LIQ_WALL_MAX_R", 3.0)
    monkeypatch.setattr(vnz, "RR_NET_MIN", 0.3)
    monkeypatch.setattr(vnz, "TP_MIN_RR", 0.5)
    entry, sl = 100.0, 98.0
    walls = {"ask_walls": [
        {"price": 100.4, "notional": 50_000.0, "persisted": True},   # rr 0.2 < 0.5 — مهدر
        {"price": 101.9, "notional": 50_000.0, "persisted": True},   # فجوته عن 102.0 = 0.1R < 0.2R — مهدر
        {"price": 104.5, "notional": 50_000.0, "persisted": True},   # مؤهل (فجوة 2.5R وrr 2.25)
        {"price": 108.0, "notional": 50_000.0, "persisted": True},   # خلف حد LIQ_WALL_MAX_R=3R (106) — مستبعد
    ], "bid_walls": []}
    merged, used = vnz.merge_wall_targets([(102.0, "w5_eq_w1")], walls, entry, sl)
    assert used == 1
    bases = [b for _, b in merged]
    assert bases == ["w5_eq_w1", "liq_wall"]  # السلّم يبقى والجدار يتدرج بعده تصاعديًا
    assert merged[0][0] == 102.0 and merged[1][0] == 104.5


def test_merge_wall_targets_cap_and_spoof(monkeypatch):
    """سقف LIQ_WALL_MAX_TARGETS يُطبَّق والجدار الوهمي (غير مستمر وغير ضخم) يُرفض."""
    oflow_on(monkeypatch)
    monkeypatch.setattr(vnz, "LIQ_RADAR_ENABLED", True)
    monkeypatch.setattr(vnz, "LIQ_WALL_MAX_TARGETS", 2)
    monkeypatch.setattr(vnz, "LIQ_WALL_MIN_NOTIONAL", 8000.0)
    monkeypatch.setattr(vnz, "RR_NET_MIN", 0.3)
    entry, sl = 100.0, 98.0
    walls = {"ask_walls": [
        {"price": 104.0, "notional": 60_000.0, "persisted": False},  # ضخم (≥3×الأرضية) — يقبل
        {"price": 105.0, "notional": 60_000.0, "persisted": True},   # مستمر — يقبل
        {"price": 106.0, "notional": 20_000.0, "persisted": False},  # وهمي (وحدُه دون 3×) — يرفض
    ], "bid_walls": []}
    merged, used = vnz.merge_wall_targets([], walls, entry, sl)
    assert used == 2 and [b for _, b in merged] == ["liq_wall", "liq_wall"]


def test_merge_wall_targets_disabled(monkeypatch):
    """الطبقة/الرادار معطلان = المراحل تعود كما هي حرفيًا وصفر إضافة."""
    oflow_on(monkeypatch)
    monkeypatch.setattr(vnz, "LIQ_RADAR_ENABLED", False)
    stages = [(104.0, "w5_eq_w1")]
    merged, used = vnz.merge_wall_targets(stages, {"ask_walls": [
        {"price": 108.0, "notional": 99_000.0, "persisted": True}], "bid_walls": []}, 100.0, 98.0)
    assert used == 0 and merged == stages


# ─────────────────────────────────────────────────────────────────────────────
# 6) التكامل — create_pending_signal
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def creation_env(monkeypatch, clean_db, tg_off):
    """بيئة إنشاء معزولة: سلّم ثابت + رادار مصنوع + CVD مؤكد في الكاش."""
    oflow_on(monkeypatch)
    monkeypatch.setattr(vnz, "CVD_GATE_ENABLED", True)
    monkeypatch.setattr(vnz, "LIQ_RADAR_ENABLED", True)
    monkeypatch.setattr(vnz, "RR_NET_MIN", 0.3)
    monkeypatch.setattr(vnz, "MAX_STOP_PCT", 0.0)
    monkeypatch.setattr(vnz, "RR_NET_MIN_TP1", 0.0)
    monkeypatch.setattr(vnz, "compute_tp_ladder",
                        lambda setup: [(104.0, "w5_eq_w1"), (106.0, "w5_0618_w3")])
    monkeypatch.setattr(vnz, "liquidity_walls",
                        lambda sym, ref: {"ask_walls": [
                            {"price": 105.3, "notional": 250_000.0, "persisted": True}],
                            "bid_walls": [{"price": 97.5, "notional": 90_000.0,
                                           "persisted": True}], "source": "fake"})
    seed_cvd([float(i) for i in range(60)], "taker")  # ميل مؤكد
    yield
    vnz._cvd_cache.clear()


def test_create_signal_wall_target_and_fib(creation_env):
    """الجدار المؤهل يدخل السلّم (tp_bases/wall_targets/walls) وسطر التدفق يصل التلغرام."""
    sent = {}
    monkeypatch_send = SimpleNamespace()
    orig = vnz.log_and_notify

    def capture(level, msg, tag):
        sent["msg"] = msg
        return orig(level, msg, tag)

    vnz.log_and_notify = capture
    try:
        setup = _creation_setup = SimpleNamespace(
            direction="BULLISH", timeframe="1h",
            entry_zone_low=100.0, entry_zone_high=101.0, stop_loss_price=98.0,
            pivot_prices=[100.0, 110.0, 102.0, 124.0, 106.0, 118.0],
            validation_result=SimpleNamespace(
                fib=SimpleNamespace(wave2_retrace_pct=0.5, wave4_retrace_pct=0.3,
                                    wave2_in_zone=True, wave4_in_zone=True)),
        )
        ok = vnz.create_pending_signal(
            "TEST/USDT", setup,
            oflow={"cvd": {"state": "confirms", "method": "taker", "slope_norm": 0.8,
                            "div_w5": False, "veto": False, "pts": 10.0},
                    "vp": {"node": "POC", "poc": 100.2, "vah": 101.5, "val": 99.1,
                            "hvn": []}})
        assert ok is True
        row = vnz.db.query("SELECT * FROM signals WHERE symbol='TEST/USDT'")[0]
        fib = json.loads(row["fib_json"])
        assert fib["wall_targets"] >= 1
        assert "liq_wall" in fib["tp_bases"]
        assert 105.3 in [float(x) for x in fib["tp_stages"]]
        assert fib["cvd"]["state"] == "confirms" and fib["cvd"]["method"] == "taker"
        assert fib["vp"]["node"] == "POC"
        assert fib["walls"]["source"] == "fake"
        assert fib["walls"]["bid_below"][0]["price"] == pytest.approx(97.5)
        assert "جدار سيولة كهدف" in sent["msg"]
        assert "CVD مؤكد" in sent["msg"]
        assert "فيبو عند POC" in sent["msg"]
        assert vnz.scan_stats["wall_targets_used"] >= 1
    finally:
        vnz.log_and_notify = orig


def test_create_signal_legacy_without_oflow(monkeypatch, clean_db, tg_off):
    """OFLOW معطل (مصيدة conftest) = السلوك التراثي حرفيًا: لا مفاتيح ولا شبكة."""
    calls = {"n": 0}

    def must_not_fetch(sym, ref):
        calls["n"] += 1
        raise AssertionError("liquidity_walls استُدعيت والطبقة معطلة!")

    monkeypatch.setattr(vnz, "liquidity_walls", must_not_fetch)
    monkeypatch.setattr(vnz, "RR_NET_MIN", 0.3)
    monkeypatch.setattr(vnz, "MAX_STOP_PCT", 0.0)
    monkeypatch.setattr(vnz, "RR_NET_MIN_TP1", 0.0)
    monkeypatch.setattr(vnz, "compute_tp_ladder",
                        lambda setup: [(104.0, "w5_eq_w1"), (106.0, "w5_0618_w3")])
    setup = SimpleNamespace(
        direction="BULLISH", timeframe="1h",
        entry_zone_low=100.0, entry_zone_high=101.0, stop_loss_price=98.0,
        pivot_prices=[100.0, 110.0, 102.0, 124.0, 106.0, 118.0],
        validation_result=SimpleNamespace(fib=None),
    )
    assert vnz.create_pending_signal("TEST/USDT", setup) is True
    row = vnz.db.query("SELECT fib_json FROM signals WHERE symbol='TEST/USDT'")[0]
    fib = json.loads(row["fib_json"])
    assert "cvd" not in fib and "vp" not in fib and "walls" not in fib
    assert fib["wall_targets"] == 0
    assert fib["tp_bases"] == ["w5_eq_w1", "w5_0618_w3"]  # أسس السلّم صادقة بلا OFLOW أيضًا
    assert calls["n"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 7) درجة الثقة + /health + اللوحة + تزامن الإصدار
# ─────────────────────────────────────────────────────────────────────────────

def test_composite_confidence_oflow_parts(creation_env):
    """مكوّنا cvd/vp يُضافان حصرًا مع oflow — والتراث بلا oflow بحسابه الحرفي."""
    setup = SimpleNamespace(
        direction="BULLISH", timeframe="1h",
        entry_zone_low=100.0, entry_zone_high=101.0, stop_loss_price=98.0,
        pivot_indices=[2, 8, 12, 20, 26, 32],
        pivot_prices=[100.0, 110.0, 102.0, 124.0, 106.0, 118.0],
        validation_result=SimpleNamespace(fib=None),
    )
    df = make_df([100.0 + (i % 7) * 0.05 for i in range(41)])
    legacy = vnz.composite_confidence(setup, df)
    assert "cvd" not in legacy["parts"] and "vp" not in legacy["parts"]
    info = vnz.build_oflow_info("TEST/USDT", setup, df, atr=0.5)
    with_of = vnz.composite_confidence(setup, df, oflow=info)
    assert "cvd" in with_of["parts"] and "vp" in with_of["parts"]
    assert with_of["parts"]["cvd"] == 10.0  # السلسلة المزروعة مؤكدة
    assert with_of["score"] >= legacy["score"] - 0.01


def test_health_orderflow_section(monkeypatch):
    """/health يعرض قسم orderflow بعداداته (معطلًا في بيئة الاختبار من مصيدة conftest)."""
    client = vnz.app.test_client()
    d = client.get("/health").get_json()
    of = d["orderflow"]
    assert of["enabled"] is False  # مصيدة الاختبار تعطل الطبقة
    assert "cvd_cache_syms" in of and "liq_fetch_ok" in of
    # العدادات تراكمية عبر ملف الاختبار (اختبار الإنشاء أعلاه رفع wall_targets_used)
    assert isinstance(of["rejected_cvd_conflict"], int) and isinstance(of["wall_targets_used"], int)


def test_protection_echo_oflow(clean_db, monkeypatch):
    """صدى الحماية يحمل أعلام الطبقة للوحة."""
    client = vnz.app.test_client()
    d = client.get("/api/all").get_json()
    prot = d["protection"]
    assert prot["oflow_enabled"] is False  # مصيدة الاختبار
    assert "cvd_slope_window" in prot and "liq_wall_mult" in prot


def test_panel_badges_and_version():
    """اللوحة: شارات CVD/حجم/جدار + بوابة تعارض CVD + تزامن الإصدار FE1.10.4."""
    html = panel.PANEL_HTML
    assert "CVD✓" in html and "CVD⚠" in html
    assert "حجم·" in html and "جدار×" in html
    assert "rejected_cvd_conflict" in html and "تعارض CVD" in html
    assert panel.BOT_VERSION == "FE1.10.4"
    assert vnz.BOT_VERSION == panel.BOT_VERSION == "FE1.10.4"


def test_boot_validation_ranges():
    """التحقق البيئي يقبل الافتراضيات ويصرخ بنطاق مسمّى على قيمة فاسدة."""
    vnz._validate_boot_config()  # لا استثناء على الافتراضيات
    old = vnz.VP_BINS
    try:
        vnz.VP_BINS = 3  # تحت الأرضية 8
        with pytest.raises(ValueError, match="VP_BINS"):
            vnz._validate_boot_config()
    finally:
        vnz.VP_BINS = old
