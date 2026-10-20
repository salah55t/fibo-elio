#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_fe1918.py — اختبارات FE1.9.18 «درجة الثقة المركبة + كبح تقليب المزودين»

الخلفية (طلب المستخدم): «طبق الاقتراحات وراجع لوحة التحكم بوتنا شبه ميت او صارم بزيادة»
تشخيص اللقطة الحية: pending_n=3 لكن R:R محقق مقلوب (متوسط خسارة -85$ مقابل ربح +42$)،
rejected_old_structure=309 القاتل الأول، و«عاد BINANCE» ×5 في 30ث أغرقت خلاصة اللوحة.

الجولات:
  1) RSI وايلدر: تناوب متعادل = 50، صعود أحادي = 100، محاذاة الطول، بيانات ناقصة
  2) composite_confidence: بنية + انحراف RSI (عقوبة/أعلام late_w5) + إرشادات الحجم
     (أوزان لا بوابات) + النضارة + جودة الصفقة — الأصح أعلى درجة من المنحرف
  3) بوابة الثقة الأرضية: None يمر (تراث)، تحت الأرضية يُرفض بسبب مسمّى، فوقها يمر
  4) توصيل scan_cycle: الحساب مرة لكل رمز + البوابة قبل الإنشاء + العداد الجديد
  5) create_pending_signal: الثقة تُخزن في fib_json وتصل التلغرام (سطر الثقة + تحذير)
  6) كبح تقليب المزودين: العودة داخل السكن بلا إشعار، خارج السكن تُعلن، deactivated_at يُوثق
  7) كتم خلاصة اللوحة: الرسالة الحرفية نفسها خلال النافذة تُدرج مرة واحدة
  8) حزام القياس التاريخي: سلّم الأهداف ومرآة المراحل حسابيًا + وجود السكربت
  9) تزامن اللوحة والإصدار (شارة الثقة + بوابة العداد + صدى الحماية)

تشغيل: pytest test_fe1918.py -v   (من داخل مجلد المشروع)
"""

import inspect
import importlib.util
import json
import math
import os
import sqlite3
import time

import pandas as pd
import pytest

import vnz
import panel
vnz.DASHBOARD_PROTECTED = False  # بيئة الاختبار: بلا مصادقة (نفس عقد test_fe100)


# ─────────────────────────────────────────────────────────────────────────────
# مصانع (نفس عقد test_fe100/test_fe1914)
# ─────────────────────────────────────────────────────────────────────────────

def leg_candles(start, end, n, t0, vol=1000.0):
    rows, step = [], (end - start) / n
    for i in range(n):
        o = start + step * i
        c = start + step * (i + 1)
        rows.append((t0 + i * 3600_000, o, max(o, c) * 1.0005,
                     min(o, c) * 0.9995, c, vol))
    return rows


DET = None


def impulse_df():
    """دافع صاعد مصطنع: P0=100 P1=120 P2=110 P3=140 P4=125 P5=135 (نمط test_fe100)."""
    pts = [(100.0, 120.0, 5), (120.0, 110.0, 4), (110.0, 140.0, 6),
           (140.0, 125.0, 4), (125.0, 135.0, 4)]
    rows, t = [], 1_700_000_000_000
    for a, b, n in pts:
        rows += leg_candles(a, b, n, t)
        t += n * 3600_000
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df["symbol"], df["timeframe"] = "TEST/USDT", "1h"
    return df[["timestamp", "open", "high", "low", "close", "volume", "symbol", "timeframe"]]


class _StubFib:
    def __init__(self, in_zone=True, w2=0.5, w4=0.3):
        self.wave2_retrace_pct = w2
        self.wave4_retrace_pct = w4
        self.wave2_in_zone = in_zone
        self.wave4_in_zone = in_zone


class _StubValidation:
    def __init__(self, fib=None):
        self.fib = fib or _StubFib()


def make_setup(prices=None, indices=None, n_bars=100, fib=None):
    from engine.pattern_detector import DetectedSetup
    P = prices or [100.0, 120.0, 110.0, 140.0, 125.0, 135.0]
    idx = indices or [0, 10, 20, 30, 40, 95]
    return DetectedSetup(
        symbol="TEST/USDT", timeframe="1h", direction="BULLISH",
        pivot_indices=idx,
        pivot_timestamps=[pd.Timestamp("2026-01-01", tz="UTC")] * 6,
        pivot_prices=P,
        validation_result=_StubValidation(fib),
        detected_at=pd.Timestamp("2026-01-01", tz="UTC"),
    )


def divergence_df():
    """df بانحراف RSI: W3 صعود قوي (RSI مرتفع عند P3=140@29) ثم W5 متعِب متذبذب
    إلى قمة أعلى 155@95 مع RSI أدنى — والحجم: W3 الأعلى وW5 لا يتجاوزه."""
    closes = []
    closes += list(pd.Series([100 + (120 - 100) * (i + 1) / 10 for i in range(10)]))   # W1
    closes += list(pd.Series([120 - (120 - 110) * (i + 1) / 10 for i in range(10)]))   # W2
    closes += list(pd.Series([110 + (140 - 110) * (i + 1) / 10 for i in range(10)]))   # W3 قوي
    closes += list(pd.Series([140 - (140 - 125) * (i + 1) / 10 for i in range(10)]))   # W4
    # W5 متعب: +3/-2 متناوب من 125 → قمة 155 (أعلى من P3) مع RSI متدنٍ — 60 شمعة
    px = 125.0
    for k in range(60):
        px += 3.0 if k % 2 == 0 else -2.0
        closes.append(px)
    vols = [100.0] * 10 + [500.0] * 10 + [2000.0] * 10 + [800.0] * 10 + [500.0] * 60
    n = len(closes)
    assert n == 100 and len(vols) == n
    t0 = 1_700_000_000_000
    rows = [(t0 + i * 3600_000, closes[i], closes[i] * 1.0005,
             closes[i] * 0.9995, closes[i], vols[i]) for i in range(n)]
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df["symbol"], df["timeframe"] = "TEST/USDT", "1h"
    return df[["timestamp", "open", "high", "low", "close", "volume", "symbol", "timeframe"]]


@pytest.fixture()
def clean_db(tmp_path, monkeypatch):
    monkeypatch.setattr(vnz, "USE_POSTGRES", False)
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    old = vnz.db.conn
    vnz.db.conn = conn
    vnz.init_db()
    vnz.set_paper_balance(vnz.PAPER_BALANCE_START)
    yield vnz.db
    vnz.db.conn = old
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 1 — RSI وايلدر
# ─────────────────────────────────────────────────────────────────────────────

class TestRsiSeries:
    def test_alternating_is_fifty(self):
        closes = [100.0, 101.0, 100.0, 101.0] * 10
        arr = vnz.rsi_series(closes, period=14)
        assert len(arr) == len(closes)
        assert all(v is None for v in arr[:14])
        assert math.isclose(arr[14], 50.0, abs_tol=0.5)
        assert 48.0 <= arr[-1] <= 55.0  # وايلدر يتذبذب حول 50 حسب طور الشمعة الأخيرة

    def test_monotonic_rise_is_hundred(self):
        closes = [100.0 + i for i in range(40)]
        arr = vnz.rsi_series(closes, period=14)
        assert arr[-1] == 100.0

    def test_short_input_empty(self):
        assert vnz.rsi_series([100.0, 101.0], period=14) == []
        assert vnz.rsi_series([], period=14) == []

    def test_divergence_df_rsi_falls_from_w3_to_w5(self):
        df = divergence_df()
        arr = vnz.rsi_series(df["close"].tolist(), period=14)
        r3, r5 = arr[29], arr[95]
        assert r3 is not None and r5 is not None
        assert r3 > 70.0 and r5 < r3  # قمة أعلى زخم أدنى = انحراف هابط


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 2 — composite_confidence
# ─────────────────────────────────────────────────────────────────────────────

class TestCompositeConfidence:
    def test_score_bounds_and_parts(self):
        s = make_setup()
        c = vnz.composite_confidence(s, None, rsi_arr=None, rr_net=None, stop_pct=None)
        assert 0.0 <= c["score"] <= 100.0
        assert set(c["parts"]) == {"structure", "rsi", "volume", "freshness", "rr", "stop"}

    def test_fresh_structure_scores_higher(self):
        fresh = make_setup(indices=[0, 10, 20, 30, 40, 95])
        stale = make_setup(indices=[0, 10, 20, 30, 40, 5])  # عمر P5 = 94 شمعة
        df = divergence_df()  # 100 شمعة — المحاور داخل المدى
        cf = vnz.composite_confidence(fresh, df, rsi_arr=None)
        cs = vnz.composite_confidence(stale, df, rsi_arr=None)
        assert cf["flags"]["p5_age"] == 4
        assert cs["flags"]["p5_age"] == 94
        assert cf["parts"]["freshness"] > cs["parts"]["freshness"]
        assert cf["score"] > cs["score"]

    def test_rsi_divergence_penalizes_and_flags(self):
        df = divergence_df()
        rsi_arr = vnz.rsi_series(df["close"].tolist())
        P = [100.0, 120.0, 110.0, 140.0, 125.0, 155.0]
        s = make_setup(prices=P)  # P5=155 أعلى من P3=140 مع RSI أدنى
        c = vnz.composite_confidence(s, df, rsi_arr=rsi_arr)
        assert c["flags"]["rsi_div"] is True
        assert c["flags"]["late_w5"] is True   # طول W5 (0.215) تجاوز W1 (0.182)
        assert c["parts"]["rsi"] == 0.0
        # نفس البنية بلا RSI = محايد (5) — الانحراف عقوبة صريحة لا إعدام
        c_neutral = vnz.composite_confidence(s, df, rsi_arr=None)
        assert c_neutral["score"] > c["score"]

    def test_volume_guidelines_are_weights_not_gates(self):
        df = divergence_df()
        P = [100.0, 120.0, 110.0, 140.0, 125.0, 155.0]
        s = make_setup(prices=P)
        c_ok = vnz.composite_confidence(s, df, rsi_arr=None)   # W3=2000 > W1=100 وW5=500 ≤ W3
        assert c_ok["flags"]["vol_ok"] is True
        assert c_ok["parts"]["volume"] == 10.0
        df_flat = df.copy()
        df_flat["volume"] = 1000.0  # إرشاد واحد فقط متحقق (W5≤W3) — خصم وزن لا رفض بوابة
        c_bad = vnz.composite_confidence(s, df_flat, rsi_arr=None)
        assert c_bad["parts"]["volume"] == 5.0
        assert c_bad["flags"]["vol_ok"] is False
        assert c_ok["score"] > c_bad["score"]

    def test_trade_quality_component(self):
        s = make_setup()
        c_hi = vnz.composite_confidence(s, None, rr_net=1.2, stop_pct=1.0)
        c_lo = vnz.composite_confidence(s, None, rr_net=0.2, stop_pct=3.4)
        assert c_hi["parts"]["rr"] == 12.0
        assert c_hi["parts"]["rr"] > c_lo["parts"]["rr"]
        assert c_hi["parts"]["stop"] >= c_lo["parts"]["stop"]

    def test_neutral_on_failure(self):
        s = make_setup()
        c = vnz.composite_confidence(s, "not-a-df", rsi_arr="bad")
        assert 0.0 <= c["score"] <= 100.0  # لا انهيار — درجة محايدة


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 3 — بوابة الثقة الأرضية
# ─────────────────────────────────────────────────────────────────────────────

class TestConfidenceGate:
    def test_none_passes_legacy(self):
        ok, why = vnz.confidence_gate_ok(None)
        assert ok is True and why == ""

    def test_below_floor_rejected_with_reason(self, monkeypatch):
        monkeypatch.setattr(vnz, "CONFIDENCE_FLOOR", 30.0)
        ok, why = vnz.confidence_gate_ok(
            {"score": 18.0, "flags": {"rsi_div": True, "p5_age": 95}})
        assert ok is False
        assert "درجة الثقة 18/100" in why
        assert "انحراف RSI" in why and "95 شمعة" in why

    def test_above_floor_passes(self, monkeypatch):
        monkeypatch.setattr(vnz, "CONFIDENCE_FLOOR", 30.0)
        ok, _ = vnz.confidence_gate_ok({"score": 45.5, "flags": {}})
        assert ok is True

    def test_floor_zero_disables(self, monkeypatch):
        monkeypatch.setattr(vnz, "CONFIDENCE_FLOOR", 0.0)
        ok, _ = vnz.confidence_gate_ok({"score": 5.0, "flags": {}})
        assert ok is True


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 4 — توصيل scan_cycle
# ─────────────────────────────────────────────────────────────────────────────

class TestScanWiring:
    def test_scan_cycle_uses_confidence(self):
        src = inspect.getsource(vnz.scan_cycle)
        assert "rsi_series(df[\"close\"].tolist())" in src
        assert "composite_confidence(best, df, rsi_arr=rsi_arr" in src
        assert "confidence_gate_ok(conf18)" in src
        assert "confidence=conf18" in src
        assert "rejected_low_confidence" in src

    def test_counter_exists(self):
        with vnz.scan_stats_lock:
            assert "rejected_low_confidence" in vnz.scan_stats
            assert "conf_scores" in vnz.scan_stats

    def test_protection_echo(self):
        src = inspect.getsource(vnz.api_all)
        assert "confidence_floor" in src
        assert "provider_recovery_dwell_sec" in src
        assert "panel_notif_dedup_sec" in src


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 5 — create_pending_signal مع الثقة
# ─────────────────────────────────────────────────────────────────────────────

class TestPendingSignalConfidence:
    def _setup_for(self):
        setups = DET_scan(impulse_df())
        return [s for s in setups if s.direction == "BULLISH"][-1]

    def test_confidence_stored_and_telegramed(self, clean_db, monkeypatch):
        s = self._setup_for()
        captured = []
        monkeypatch.setattr(vnz, "send_telegram_message",
                            lambda m: captured.append(m))
        conf = {"score": 72.5,
                "parts": {"structure": 35.0, "rsi": 0.0, "volume": 10.0,
                          "freshness": 14.4, "rr": 9.0, "stop": 4.1},
                "flags": {"rsi_div": True, "late_w5": True, "vol_ok": False}}
        assert vnz.create_pending_signal("TEST/USDT", s, last_close=128.0,
                                         confidence=conf) is True
        row = clean_db.query("SELECT * FROM signals ORDER BY id DESC LIMIT 1", one=True)
        fib = json.loads(row["fib_json"])
        assert fib["confidence"] == 72.5
        assert fib["conf_parts"]["structure"] == 35.0
        assert fib["rsi_div"] is True and fib["late_w5"] is True and fib["vol_ok"] is False
        assert captured and "الثقة: 72.5/100" in captured[0]
        assert "انحراف RSI" in captured[0]  # تحذير الخامس المتأخر

    def test_without_confidence_legacy_unchanged(self, clean_db, monkeypatch):
        s = self._setup_for()
        captured = []
        monkeypatch.setattr(vnz, "send_telegram_message", lambda m: captured.append(m))
        assert vnz.create_pending_signal("TEST/USDT", s, last_close=128.0) is True
        row = clean_db.query("SELECT * FROM signals ORDER BY id DESC LIMIT 1", one=True)
        fib = json.loads(row["fib_json"])
        assert "confidence" not in fib  # السلوك التراثي بلا ثقة
        assert captured and "الثقة" not in captured[0]


def DET_scan(df):
    from engine.pattern_detector import DetectorConfig, PivotDetector
    det = PivotDetector(DetectorConfig(method="zigzag", deviation_threshold=0.01,
                                       price_source="close", min_wave_bars=2))
    return det.scan(df)


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 6 — كبح تقليب المزودين
# ─────────────────────────────────────────────────────────────────────────────

def _reset_providers():
    with vnz.provider_lock:
        vnz.provider_state.clear()
        vnz.active_source["name"] = None
        vnz.active_source["since"] = None


class TestProviderDwell:
    def test_recovery_within_dwell_is_silent(self, monkeypatch):
        _reset_providers()
        captured = []
        monkeypatch.setattr(vnz, "log_and_notify", lambda *a, **k: captured.append(a))
        monkeypatch.setattr(vnz, "PROVIDER_RECOVERY_DWELL_SEC", 300)
        with vnz.provider_lock:
            vnz.active_source["name"] = "bybit"
            vnz.provider_state["binance"] = {
                "ok": 0, "fail": 0, "last_error": "", "last_ok_at": None,
                "cooldown_until": 0.0, "deactivated_at": time.time() - 10.0}
        vnz._mark_provider_ok("binance")
        assert vnz.active_source["name"] == "binance"  # العودة فعلية دائمًا
        assert captured == []                           # لكن داخل السكن بلا إشعار

    def test_recovery_after_real_outage_announced(self, monkeypatch):
        _reset_providers()
        captured = []
        monkeypatch.setattr(vnz, "log_and_notify", lambda *a, **k: captured.append(a))
        monkeypatch.setattr(vnz, "PROVIDER_RECOVERY_DWELL_SEC", 300)
        with vnz.provider_lock:
            vnz.active_source["name"] = "bybit"
            vnz.provider_state["binance"] = {
                "ok": 0, "fail": 0, "last_error": "", "last_ok_at": None,
                "cooldown_until": 0.0, "deactivated_at": time.time() - 900.0}
        vnz._mark_provider_ok("binance")
        assert any("عاد مزود البيانات الأساسي BINANCE" in (a[1] if len(a) > 1 else "")
                   for a in captured)

    def test_deactivated_at_tracked_on_transition_away(self, monkeypatch):
        _reset_providers()
        monkeypatch.setattr(vnz, "log_and_notify", lambda *a, **k: None)
        with vnz.provider_lock:
            vnz.active_source["name"] = "binance"
        vnz._mark_provider_ok("bybit", notify_transition=False)
        assert "deactivated_at" in vnz.provider_state["binance"]
        assert vnz.active_source["name"] == "bybit"

    def test_boot_first_announce_unaffected(self, monkeypatch):
        _reset_providers()
        captured = []
        monkeypatch.setattr(vnz, "log_and_notify", lambda *a, **k: captured.append(a))
        vnz._mark_provider_ok("binance")  # الإقلاع: بلا prev — يُعلن دائمًا
        assert any("منذ الإقلاع" in (a[1] if len(a) > 1 else "") for a in captured)


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 7 — كتم خلاصة اللوحة
# ─────────────────────────────────────────────────────────────────────────────

class TestPanelDedup:
    def test_identical_message_inserted_once(self, clean_db, monkeypatch):
        vnz._panel_dedup.clear()
        monkeypatch.setattr(vnz, "PANEL_NOTIF_DEDUP_SEC", 60)
        vnz.log_and_notify("info", "رسالة اختبار خلاصة X1", "INFO")
        vnz.log_and_notify("info", "رسالة اختبار خلاصة X1", "INFO")
        vnz.log_and_notify("info", "رسالة اختبار خلاصة X1", "INFO")
        row = clean_db.query("SELECT COUNT(*) AS n FROM notifications WHERE message=%s",
                             ("رسالة اختبار خلاصة X1",), one=True)
        assert row["n"] == 1
        monkeypatch.setattr(vnz, "PANEL_NOTIF_DEDUP_SEC", 0)  # التعطيل بالصفر
        vnz.log_and_notify("info", "رسالة اختبار خلاصة X1", "INFO")
        row = clean_db.query("SELECT COUNT(*) AS n FROM notifications WHERE message=%s",
                             ("رسالة اختبار خلاصة X1",), one=True)
        assert row["n"] == 2
        vnz._panel_dedup.clear()

    def test_distinct_messages_not_affected(self, clean_db, monkeypatch):
        vnz._panel_dedup.clear()
        monkeypatch.setattr(vnz, "PANEL_NOTIF_DEDUP_SEC", 60)
        vnz.log_and_notify("info", "رسالة أ Y1", "INFO")
        vnz.log_and_notify("info", "رسالة ب Y2", "INFO")
        row = clean_db.query("SELECT COUNT(*) AS n FROM notifications "
                             "WHERE message IN (%s,%s)",
                             ("رسالة أ Y1", "رسالة ب Y2"), one=True)
        assert row["n"] == 2
        vnz._panel_dedup.clear()


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 8 — حزام القياس التاريخي (الاقتباس 4)
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestHarness:
    @pytest.fixture(scope="class")
    def bt(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "scripts", "fe1918_backtest.py")
        assert os.path.exists(path)
        spec = importlib.util.spec_from_file_location("fe1918_backtest", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_ladder_rungs_match_production_formulas(self, bt):
        rungs = bt.ladder_rungs(100.0, 120.0, 110.0, 140.0)
        assert rungs[0][1] == pytest.approx(130.0)          # W5=W1 من P2
        assert rungs[1][1] == pytest.approx(110 + 0.618 * 30)  # 0.618×W3
        assert rungs[2][1] == pytest.approx(110 + 1.618 * 20)  # 1.618×W1 من P2 (نفس الإنتاج: test_fe100)

    def test_rr_net_mirror_charges_fees(self, bt):
        gross = (150.0 - 128.54) / (128.54 - 99.9)
        net = bt.rr_net_value(128.54, 99.9, 150.0)
        assert net == pytest.approx(gross - (0.002 * 128.54) / 28.64, rel=1e-6)
        assert net < gross

    def test_staged_targets_cap_and_floor(self, bt):
        rungs = bt.ladder_rungs(100.0, 120.0, 110.0, 140.0)
        # هندسة سكالبينج: دخول 128.54/وقف 119 (مسافة 9.54) — درجة 1.618×W1=142.36 تعبر الأرضية
        stages, _ = bt.staged_targets(128.54, 119.0, rungs, weekly_hi=138.0, rr_floor=0.6)
        assert stages == [pytest.approx(138.0)]  # 142.36 قُص على سقف الأسبوع وبقي مؤهلًا
        stages2, _ = bt.staged_targets(128.54, 119.0, rungs, weekly_hi=None, rr_floor=0.6)
        assert stages2 == [pytest.approx(142.36)]
        stages3, _ = bt.staged_targets(128.54, 119.0, rungs, weekly_hi=132.0, rr_floor=0.6)
        assert stages3 == []  # القص على 132 يسقط تحت أرضية rr_net — لا مراحل


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 9 — تزامن اللوحة والإصدار
# ─────────────────────────────────────────────────────────────────────────────

class TestPanelSync:
    def test_versions(self):
        assert vnz.BOT_VERSION == "FE1.10.4"
        assert panel.BOT_VERSION == "FE1.10.4"

    def test_panel_has_confidence_ui(self):
        html = panel.PANEL_HTML
        assert "function confBadge(x)" in html
        assert "conf-hi" in html and "conf-mid" in html and "conf-lo" in html
        assert "rejected_low_confidence" in html          # خريطة البوابات
        assert "متوسط الثقة" in html                       # ملخص الثقة في شريط البوابات
        assert "confBadge(s.fib)" in html                  # صفوف الصفقات
        assert "confBadge(x)" in html                      # الالتقاطات

    def test_conf_badge_logic_boundaries(self):
        # محاكاة منطق الشارة: ≥70 أخضر، 50-69 عنبري، <50 رمادي، غياب = بلا شارة
        def cls_of(c):
            return 'conf-hi' if c >= 70 else ('conf-mid' if c >= 50 else 'conf-lo')
        assert cls_of(72) == "conf-hi"
        assert cls_of(55) == "conf-mid"
        assert cls_of(18) == "conf-lo"
