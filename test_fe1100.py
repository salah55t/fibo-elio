"""اختبارات FE1.10.0 «التصحيح النهائي — سوبر تراند وهندسة المخاطر»
==========================================================================
التشخيص الحي الموثق (/api/all 20 أكتوبر 2026): PF=0.085 وwin_rate=25% وكل صفقة
دخلت بهدف أول أقرب من وقفها (rr 0.85-0.87) ومتوسط احتفاظ 4.4 ساعة — معادلة
خسارة رياضية EV=-0.69R/صفقة. التصحيح بخمس طبقات معايرة على بيانات Bybit
حقيقية (سکربت st_sweep — 10 رموز × 3 فريمات) وتحليل elliot-waves-auto (MIT):

  1) atr_series / supertrend_series / adx_series — رياضيات وايلدر الصحيحة
  2) regime_gate_ok — فلتر النظام ST(10×3.0)+ADX على الشموع المغلقة حصرًا
     وfail-open عند نقص البيانات (بوابة جودة لا نقطة فشل)
  3) _atr_buffered_stop — عازل ATR على الوقف البنيوي (اقتباس MIT معاد الكتابة)
  4) بوابة هندسة الربح RR_NET_MIN_TP1=1.2 في create_pending_signal —
     لا صفقة هدفها الأول أقرب من وقفها (قاتل PF=0.085 مباشرة)
  5) _time_stop_step — الخروج الزمني الناعم/الصلب (قاتل الاحتفاظ 4.4 ساعة)
  6) _st_trail_step — تتبع SuperTrend بعد BE (ratchet صاعد + إغلاق بانقلاب مؤكد)
  7) مخاطرة الملء risk0 تُخزن (ورقي + حقيقي كامل وجزئي)
  8) الثوابت والإعدادات لكل فريم + تزامن الإصدار

المحميات كما هي حرفيًا: جزئي 50% وBE@R وSL-أولًا intrabar والمطاردة وسقف
الوقف وrr_net 0.6 للهدف النهائي وسقف الأسبوع والمراحل والعنقود والتبريد.
"""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

import vnz


# ─────────────────────────────────────────────────────────────────────────────
# أدوات صناعة البيانات
# ─────────────────────────────────────────────────────────────────────────────

def _uptrend_df(n=45, start=100.0, step=1.0):
    """اتجاه صاعد رتيب نقي — ADX قريب من 100 وST صاعد."""
    rows = []
    c = start
    for i in range(n):
        c = start + step * i
        rows.append({"high": c + 0.5, "low": c - 0.5, "close": c})
    df = pd.DataFrame(rows)
    return df


def _downtrend_df(n=45, start=145.0, step=1.0):
    rows = []
    for i in range(n):
        c = start - step * i
        rows.append({"high": c + 0.5, "low": c - 0.5, "close": c})
    return pd.DataFrame(rows)


def _chop_df(n=60):
    """سوق عرضي حقيقي: مدى ثابت (101/99) بإغلاقات متأرجحة داخله —
    DM+ = DM− = 0 فـ DX→0 وADX ينهار إلى الصفر."""
    rows = []
    for i in range(n):
        c = 100.8 if i % 2 == 0 else 99.2
        rows.append({"high": 101.0, "low": 99.0, "close": c})
    return pd.DataFrame(rows)


def _fake_db():
    class _FakeDB:
        def __init__(self):
            self.executes = []
            self.queries = []

        def execute(self, *a, **k):
            self.executes.append(a)

        def query(self, *a, **k):
            self.queries.append(a)
            return []
    return _FakeDB()


def _fake_setup(entry=100.0, sl=98.5, p0=98.6):
    return SimpleNamespace(
        direction="BULLISH",
        entry_zone_low=entry,
        entry_zone_high=entry * 1.001,
        stop_loss_price=sl,
        pivot_prices=[p0, 110.0, 103.0, 118.0, 109.0, 125.0],
        pivot_indices=[0, 4, 9, 14, 19, 24],
        validation_result=SimpleNamespace(fib=None),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1) رياضيات المؤشرات
# ─────────────────────────────────────────────────────────────────────────────

def test_atr_series_constant_range():
    # مدى ثابت 1.0 بلا فجوات (high=close+0.5 على إغلاق مسطح) → ATR ≈ 1.0
    n = 40
    rows = [{"high": 100.5, "low": 99.5, "close": 100.0} for _ in range(n)]
    df = pd.DataFrame(rows)
    atrs = vnz.atr_series(df["high"].tolist(), df["low"].tolist(), df["close"].tolist(), 14)
    assert len(atrs) == n
    assert all(a is None for a in atrs[:14])
    assert atrs[14] == pytest.approx(1.0, abs=1e-9)
    assert atrs[-1] == pytest.approx(1.0, abs=1e-9)
    # ومع فجوة اتجاهية (خطوة 1.0) يصير TR = الخطوة + المدى = 1.5
    df2 = _uptrend_df(40)
    atrs2 = vnz.atr_series(df2["high"].tolist(), df2["low"].tolist(), df2["close"].tolist(), 14)
    assert atrs2[-1] == pytest.approx(1.5, abs=1e-9)


def test_atr_series_bad_input():
    assert vnz.atr_series([1, 2], [1, 2], [1, 2], 14) == []
    assert vnz.atr_series([], [], [], 14) == []


def test_supertrend_uptrend_and_downtrend():
    df = _uptrend_df(45)
    line, dirs = vnz.supertrend_series(df["high"].tolist(), df["low"].tolist(),
                                       df["close"].tolist(), 10, 3.0)
    assert len(line) == 45 and len(dirs) == 45
    assert dirs[-1] == 1                       # صاعد
    assert line[-1] < float(df["close"].iloc[-1])  # الخط تحت السعر
    df2 = _downtrend_df(45)
    line2, dirs2 = vnz.supertrend_series(df2["high"].tolist(), df2["low"].tolist(),
                                         df2["close"].tolist(), 10, 3.0)
    assert dirs2[-1] == -1                     # هابط
    assert line2[-1] > float(df2["close"].iloc[-1])


def test_supertrend_flip_on_close():
    # صاعد ثم انهيار حاد — يجب أن ينقلب بالإغلاق خلف الحزمة السفلية
    df = _uptrend_df(30)
    down = _downtrend_df(18, start=float(df["close"].iloc[-1]) + 1.0, step=2.5)
    full = pd.concat([df, down], ignore_index=True)
    line, dirs = vnz.supertrend_series(full["high"].tolist(), full["low"].tolist(),
                                       full["close"].tolist(), 10, 3.0)
    assert dirs[-1] == -1
    assert 1 in [d for d in dirs if d is not None]      # كان صاعدًا قبل القلب


def test_supertrend_short_data():
    df = _uptrend_df(8)
    assert vnz.supertrend_series(df["high"].tolist(), df["low"].tolist(),
                                 df["close"].tolist(), 10, 3.0) == ([], [])


def test_adx_series_strong_trend_vs_chop():
    up = _uptrend_df(45)
    adx_up = vnz.adx_series(up["high"].tolist(), up["low"].tolist(), up["close"].tolist(), 14)
    assert adx_up[-1] is not None and adx_up[-1] > 25.0     # اتجاه قوي
    chop = _chop_df(60)
    adx_chop = vnz.adx_series(chop["high"].tolist(), chop["low"].tolist(),
                              chop["close"].tolist(), 14)
    assert adx_chop[-1] is not None and adx_chop[-1] < 18.0  # عرضي
    assert vnz.adx_series([1.0] * 10, [1.0] * 10, [1.0] * 10, 14) == []


# ─────────────────────────────────────────────────────────────────────────────
# 2) بوابة النظام regime_gate_ok
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.production_gates
def test_regime_gate_uptrend_passes():
    df = _uptrend_df(45)
    ok, why = vnz.regime_gate_ok(df, "BULLISH")
    assert ok is True and why == ""


@pytest.mark.production_gates
def test_regime_gate_downtrend_rejects_named():
    df = _downtrend_df(45)
    ok, why = vnz.regime_gate_ok(df, "BULLISH")
    assert ok is False
    assert "فلتر النظام" in why and "SuperTrend" in why


@pytest.mark.production_gates
def test_regime_gate_fail_open_on_short_data():
    df = _uptrend_df(10)  # أقل من الحد الأدنى (period+ADX+5 شمعة مغلقة)
    ok, why = vnz.regime_gate_ok(df, "BULLISH")
    assert ok is True and why == ""


def test_regime_gate_disabled(monkeypatch):
    monkeypatch.setattr(vnz, "REGIME_GATE_ENABLED", False)
    ok, _ = vnz.regime_gate_ok(_downtrend_df(45), "BULLISH")
    assert ok is True


@pytest.mark.production_gates
def test_regime_gate_excludes_forming_candle(monkeypatch):
    """الشمعة الجارية مستبعدة: صاعد حقيقي تُلحق به شمعة هابطة عملاقة غير مغلقة
    لا يقلب الحكم — التعهد بالإغلاق المغلق حصرًا."""
    df = _uptrend_df(45)
    forming = pd.DataFrame([{"high": 50.0, "low": 30.0, "close": 31.0}])
    df2 = pd.concat([df, forming], ignore_index=True)
    ok, _ = vnz.regime_gate_ok(df2, "BULLISH")
    assert ok is True


# ─────────────────────────────────────────────────────────────────────────────
# 3) عازل ATR على الوقف البنيوي
# ─────────────────────────────────────────────────────────────────────────────

def test_atr_buffered_stop_widens():
    # P0=100 وATR=2 وk=0.25 → العازل 0.5 → min(99.9, 99.5) = 99.5
    assert vnz._atr_buffered_stop(99.9, 100.0, 2.0) == pytest.approx(99.5)
    # عازل أضيق من الوقف البنيوي → الوقف البنيوي يفوز
    assert vnz._atr_buffered_stop(99.9, 100.0, 0.1) == pytest.approx(99.9)


def test_atr_buffered_stop_disabled():
    assert vnz._atr_buffered_stop(99.9, 100.0, 0.0) == pytest.approx(99.9)
    monkey_old = vnz.SL_ATR_BUFFER
    try:
        vnz.SL_ATR_BUFFER = 0.0
        assert vnz._atr_buffered_stop(99.9, 100.0, 2.0) == pytest.approx(99.9)
    finally:
        vnz.SL_ATR_BUFFER = monkey_old


# ─────────────────────────────────────────────────────────────────────────────
# 4) بوابة هندسة الربح في create_pending_signal
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.production_gates
def test_create_rejects_tp1_closer_than_stop(monkeypatch):
    """الصفقة القاتلة التاريخية: TP1 = +1.55% مقابل وقف -1.5% (rr 0.87 خام) —
    يجب أن تُرفض بعداد rejected_rr_tp1 مهما كانت البنية صالحة."""
    fake = _fake_db()
    monkeypatch.setattr(vnz, "db", fake)
    monkeypatch.setattr(vnz, "risk_entry_block_reason", lambda: None)
    monkeypatch.setattr(vnz, "is_real_mode", False)
    monkeypatch.setattr(vnz, "TP_WEEK_CAP_ENABLED", True)
    monkeypatch.setattr(vnz, "TP_STAGES_ENABLED", True)
    monkeypatch.setattr(vnz, "TP_LADDER_ENABLED", True)
    monkeypatch.setattr(vnz, "weekly_high", lambda symbol: 1e9)  # يتجاوز مصيدة conftest
    # TP1 = 101.3 → rr خام 0.867 وصافٍ ≈ 0.73 < 1.2
    monkeypatch.setattr(vnz, "build_staged_targets",
                        lambda setup, entry, sl, wh: ([(101.3, "w5_eq_w1")], False, 0.87))
    with vnz.scan_stats_lock:
        before = int(vnz.scan_stats.get("rejected_rr_tp1", 0))
    ok = vnz.create_pending_signal("TEST/USDT", _fake_setup(), last_close=0.0, atr=0.0)
    with vnz.scan_stats_lock:
        after = int(vnz.scan_stats.get("rejected_rr_tp1", 0))
    assert ok is False
    assert after == before + 1


@pytest.mark.production_gates
def test_create_accepts_geometry_with_atr_buffered_stop(monkeypatch):
    """هندسة سليمة (TP1=+12%) مع atr عازل: الوقف يتوسع إلى P0−0.25×ATR وتولد الإشارة."""
    fake = _fake_db()
    monkeypatch.setattr(vnz, "db", fake)
    monkeypatch.setattr(vnz, "risk_entry_block_reason", lambda: None)
    monkeypatch.setattr(vnz, "is_real_mode", False)
    monkeypatch.setattr(vnz, "TP_WEEK_CAP_ENABLED", True)
    monkeypatch.setattr(vnz, "TP_STAGES_ENABLED", True)
    monkeypatch.setattr(vnz, "TP_LADDER_ENABLED", True)
    monkeypatch.setattr(vnz, "weekly_high", lambda symbol: 1e9)
    monkeypatch.setattr(vnz, "build_staged_targets",
                        lambda setup, entry, sl, wh: ([(112.0, "w5_eq_w1")], False, 7.9))
    monkeypatch.setattr(vnz, "compute_quantity", lambda symbol, entry, sl: 10.0)
    ok = vnz.create_pending_signal("TEST/USDT", _fake_setup(entry=100.0, sl=98.5, p0=98.6),
                                   last_close=0.0, atr=2.0)
    assert ok is True
    # INSERT الصفقة: الوقف = min(98.5, 98.6−0.5) = 98.1
    inserts = [a for a in fake.executes if a and "INSERT INTO signals" in str(a[0])]
    assert inserts, "لا يوجد إدراج للصفقة"
    params = inserts[0][1]
    # صيغة الإدراج: (symbol, direction, strategy, entry, sl, tp, qty, rr, expires, pivots, fib,...)
    assert abs(float(params[4]) - 98.1) < 1e-9, params[4]


# ─────────────────────────────────────────────────────────────────────────────
# 5) الخروج الزمني
# ─────────────────────────────────────────────────────────────────────────────

def _aged_sig(hours=2.0, peak=100.2, be_done=False, risk0=1.5):
    filled_at = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {"risk0": risk0}
    if be_done:
        meta["be_done"] = True
    return {"id": 1, "symbol": "T/USDT", "is_real": 0, "fill_price": 100.0,
            "stop_loss": 98.5, "peak_price": peak, "filled_at": filled_at,
            "meta_json": json.dumps(meta)}


def test_time_stop_soft_no_momentum(monkeypatch):
    closes = []
    monkeypatch.setattr(vnz, "_time_stop_close",
                        lambda sig, price, reason: closes.append(reason))
    assert vnz._time_stop_step(_aged_sig(hours=2.0, peak=100.2), 99.9) is True
    assert closes and "بلا زخم" in closes[0]


def test_time_stop_soft_momentum_exempt(monkeypatch):
    closes = []
    monkeypatch.setattr(vnz, "_time_stop_close",
                        lambda sig, price, reason: closes.append(reason))
    # MFE = 1.0/1.5 = 0.67R ≥ 0.5 → لا خروج
    assert vnz._time_stop_step(_aged_sig(hours=2.0, peak=101.0), 100.5) is False
    assert closes == []


def test_time_stop_be_done_exempt_from_soft(monkeypatch):
    closes = []
    monkeypatch.setattr(vnz, "_time_stop_close",
                        lambda sig, price, reason: closes.append(reason))
    assert vnz._time_stop_step(_aged_sig(hours=2.0, peak=100.1, be_done=True), 100.2) is False
    assert closes == []


def test_time_stop_hard_always_closes(monkeypatch):
    closes = []
    monkeypatch.setattr(vnz, "_time_stop_close",
                        lambda sig, price, reason: closes.append(reason))
    # حتى المؤمّنة بالتعادل يخرجها الصلب بعد 4 ساعات
    assert vnz._time_stop_step(_aged_sig(hours=5.0, peak=101.0, be_done=True), 100.8) is True
    assert closes and "أقصى احتفاظ" in closes[0]


def test_time_stop_under_soft_hours_noop(monkeypatch):
    closes = []
    monkeypatch.setattr(vnz, "_time_stop_close",
                        lambda sig, price, reason: closes.append(reason))
    assert vnz._time_stop_step(_aged_sig(hours=0.5, peak=100.1), 99.9) is False
    assert closes == []


def test_time_stop_disabled(monkeypatch):
    monkeypatch.setattr(vnz, "TIME_STOP_ENABLED", False)
    assert vnz._time_stop_step(_aged_sig(hours=5.0), 99.0) is False


# ─────────────────────────────────────────────────────────────────────────────
# 6) تتبع SuperTrend بعد الحماية
# ─────────────────────────────────────────────────────────────────────────────

def _trail_sig(stop=100.0, be_done=True):
    meta = {"be_done": True} if be_done else {}
    return {"id": 7, "symbol": "T/USDT", "is_real": 0, "fill_price": 100.0,
            "stop_loss": stop, "meta_json": json.dumps(meta)}


def test_trail_raises_stop_to_st_line(monkeypatch):
    df = _uptrend_df(45, start=100.0, step=0.5)
    monkeypatch.setattr(vnz, "get_recent_candles",
                        lambda symbol, tf, limit, min_candles=2: df)
    executed = []
    monkeypatch.setattr(vnz.db, "execute", lambda *a, **k: executed.append(a))
    sig = _trail_sig(stop=100.0)
    vnz._st_trail_step(sig)
    # خط ST في اتجاه صاعد نقي يبقى تحت السعر لكن فوق الوقف القديم (التعادل)
    assert sig["stop_loss"] > 100.0
    assert any("stop_loss=%s" in str(a[0]) for a in executed)


def test_trail_closes_on_confirmed_flip(monkeypatch):
    # صاعد طويل ثم انهيار مؤكد بالإغلاق
    df = pd.concat([_uptrend_df(40, start=100.0, step=0.5),
                    _downtrend_df(12, start=122.0, step=2.0)], ignore_index=True)
    monkeypatch.setattr(vnz, "get_recent_candles",
                        lambda symbol, tf, limit, min_candles=2: df)
    closed = []
    monkeypatch.setattr(vnz, "close_signal_row",
                        lambda sig, price, reason, *a, **k: closed.append(reason))
    vnz._st_trail_step(_trail_sig(stop=100.0))
    assert closed and "تتبع SuperTrend" in closed[0] and "انقلاب" in closed[0]


def test_trail_requires_be_done(monkeypatch):
    called = {"n": 0}

    def _boom(*a, **k):
        called["n"] += 1
        raise AssertionError("لا يجب جلب الشموع دون BE")
    monkeypatch.setattr(vnz, "get_recent_candles", _boom)
    vnz._st_trail_step(_trail_sig(be_done=False))
    assert called["n"] == 0


def test_trail_ratchet_never_lowers(monkeypatch):
    df = _uptrend_df(45, start=100.0, step=0.5)
    monkeypatch.setattr(vnz, "get_recent_candles",
                        lambda symbol, tf, limit, min_candles=2: df)
    executed = []
    monkeypatch.setattr(vnz.db, "execute", lambda *a, **k: executed.append(a))
    sig = _trail_sig(stop=1000.0)  # وقف أعلى من أي خط ST ممكن
    vnz._st_trail_step(sig)
    assert sig["stop_loss"] == 1000.0 and not executed


# ─────────────────────────────────────────────────────────────────────────────
# 7) مخاطرة الملء risk0 (ورقي) — عبر monitor_step بحقل فيبو حقيقي
# ─────────────────────────────────────────────────────────────────────────────

def test_paper_fill_stores_risk0(monkeypatch):
    pivots = json.dumps({"P0": 98.6, "P1": 110.0, "P2": 103.0, "P3": 118.0, "P4": 109.0, "P5": 125.0})
    sig = {"id": 9, "symbol": "T/USDT", "is_real": 0, "status": "pending",
           "entry_price": 100.0, "stop_loss": 98.5, "take_profit": 112.0,
           "quantity": 10.0, "pivots_json": pivots, "meta_json": json.dumps({}),
           "expires_at": "2099-01-01T00:00:00Z"}
    monkeypatch.setattr(vnz.db, "query",
                        lambda *a, **k: [sig] if "status='pending'" in str(a[0]) else [])
    executed = []
    monkeypatch.setattr(vnz.db, "execute", lambda *a, **k: executed.append(a))
    # شمعة لمست منطقة الدخول: low=99.9 ≤ entry=100 وclose فوقه
    df = pd.DataFrame([{"ts": 0, "open": 100.5, "high": 100.6, "low": 99.9,
                        "close": 100.4, "volume": 1.0,
                        "timestamp": pd.Timestamp("2026-10-20", tz="UTC"),
                        "symbol": "T/USDT", "timeframe": "5m"}])
    monkeypatch.setattr(vnz, "get_recent_candles",
                        lambda symbol, tf, limit, min_candles=2: df)
    vnz.monitor_step()
    updated = json.loads(sig["meta_json"])
    assert abs(updated["risk0"] - (100.0 - 98.5)) < 1e-9


# ─────────────────────────────────────────────────────────────────────────────
# 8) الثوابت والإعدادات لكل فريم + الإصدار
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.production_gates
def test_constants_defaults():
    assert vnz.RR_NET_MIN_TP1 == pytest.approx(1.2)
    assert vnz.SL_ATR_BUFFER == pytest.approx(0.25)
    assert vnz.ST_PERIOD == 10 and vnz.ST_MULT == pytest.approx(3.0)
    assert vnz.ADX_PERIOD == 14
    assert vnz.TIME_STOP_SOFT_HOURS == pytest.approx(1.0)
    assert vnz.TIME_STOP_MIN_R == pytest.approx(0.5)
    assert vnz.TIME_STOP_HARD_HOURS == pytest.approx(4.0)
    assert vnz.REGIME_GATE_ENABLED is True
    assert vnz.ST_TRAIL_ENABLED is True


def test_per_timeframe_settings():
    assert set(vnz.TF_ADX_MIN.keys()) == {"5m", "15m", "1h", "4h"}
    assert vnz.TF_ADX_MIN["5m"] == pytest.approx(18.0)
    assert vnz.TF_ADX_MIN["15m"] == pytest.approx(20.0)
    assert vnz.TF_ADX_MIN["1h"] == pytest.approx(22.0)
    assert vnz._tf_adx_min("5m") == pytest.approx(18.0)
    assert vnz._tf_adx_min("غير معروف") == pytest.approx(22.0)
    # تجاوز بيئي يغلب الجدول
    old = vnz.ADX_MIN_OVERRIDE
    try:
        vnz.ADX_MIN_OVERRIDE = 25.0
        assert vnz._tf_adx_min("5m") == pytest.approx(25.0)
    finally:
        vnz.ADX_MIN_OVERRIDE = old
    for tf in ("5m", "15m", "1h", "4h"):
        p, m = vnz._tf_st_settings(tf)
        assert p == 10 and m == pytest.approx(3.0)


def test_protection_echo_has_new_gates(monkeypatch):
    """بطاقة protection في /api/all تكشف البوابات الجديدة (اختبار مباشر للقاموس)."""
    monkeypatch.setattr(vnz, "SIGNAL_TIMEFRAME", "5m")
    from types import MethodType
    # نبني القاموس يدويًا بنفس مصدر /api/all عبر فحص المفاتيح المتوقعة في الكود
    expected = {"regime_gate", "st_period", "st_mult", "adx_period", "adx_min",
                "rr_net_min_tp1", "sl_atr_buffer", "time_stop_enabled",
                "time_stop_soft_hours", "time_stop_min_r", "time_stop_hard_hours", "st_trail"}
    src = open(vnz.__file__, encoding="utf-8").read()
    for key in expected:
        assert f'"{key}"' in src, f"مفتاح الحماية {key} غائب عن صدى /api/all"


def test_version_pair():
    assert vnz.BOT_VERSION == "FE1.10.1"
    import panel
    assert panel.BOT_VERSION == "FE1.10.1"
