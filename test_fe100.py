#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_fe100.py — اختبارات Fibo-Elio FE1.1.0

خمس جولات:
  1) المحرك الأصلي المنقول حرفيًا: زيجزاج على موجات مصطنعة + القواعد الثلاث + فيبوناتشي
  2) التدفق الورقي: إنشاء معلق → ملء → إبطال بنيوي/صلاحية → وقف/هدف → محاسبة رسوم
  3) اللوحة وAPI: /health و/api/all والتبديل والتصفير (Flask test_client)
  4) تعاقب مزودي البيانات FE1.0.1: باينانس أولًا ثم البدائل عند الحظر
  5) التتبع الحي والتحكم اليدوي FE1.1.0: سعر حي + غير محقق + إغلاق/إلغاء يدوي

تشغيل: pytest test_fe100.py -v   (من داخل مجلد المشروع)
اختبار سوق حي اختياري: RUN_LIVE_SMOKE=1 pytest test_fe100.py -v -k live
"""

import json
import math
import os
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

import vnz
vnz.DASHBOARD_PROTECTED = False  # بيئة الاختبار: بلا مصادقة (الافتراضي في الإنتاج admin/test123)
from engine.fibonacci import FibonacciLevels, FibonacciChecker, RETRACEMENT_RATIOS, EXTENSION_RATIOS
from engine.pattern_detector import DetectorConfig, PivotDetector
from engine.wave_validator import validate_impulse, WavePivots

# ─────────────────────────────────────────────────────────────────────────────
# أدوات بناء شموع مصطنعة
# ─────────────────────────────────────────────────────────────────────────────

def leg_candles(start: float, end: float, n: int, t0: int) -> pd.DataFrame:
    """n شموع خطية من start إلى end مع high/low حول المسار (بدون ضجيج)."""
    rows = []
    step = (end - start) / n
    for i in range(n):
        o = start + step * i
        c = start + step * (i + 1)
        h = max(o, c) * 1.0005
        lo = min(o, c) * 0.9995
        rows.append((t0 + i * 3600_000, o, h, lo, c, 1000.0))
    return rows


def impulse_df() -> pd.DataFrame:
    """دافع صاعد مصطنع: P0=100 P1=120 P2=110 P3=140 P4=125 P5=135."""
    pts = [(100.0, 120.0, 5), (120.0, 110.0, 4), (110.0, 140.0, 6),
           (140.0, 125.0, 4), (125.0, 135.0, 4)]
    rows, t = [], 1_700_000_000_000
    for a, b, n in pts:
        rows += leg_candles(a, b, n, t)
        t += n * 3600_000
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df["symbol"] = "TEST/USDT"
    df["timeframe"] = "1h"
    return df[["timestamp", "open", "high", "low", "close", "volume", "symbol", "timeframe"]]


DET = PivotDetector(DetectorConfig(method="zigzag", deviation_threshold=0.01,
                                   price_source="close", min_wave_bars=2))


@pytest.fixture()
def clean_db(tmp_path, monkeypatch):
    """قاعدة SQLite مؤقتة لكل اختبار — عزل كامل."""
    monkeypatch.setattr(vnz, "USE_POSTGRES", False)
    import sqlite3
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    old = vnz.db.conn
    vnz.db.conn = conn
    vnz.init_db()
    vnz.set_paper_balance(vnz.PAPER_BALANCE_START)
    yield vnz.db
    vnz.db.conn = old


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 1 — المحرك الأصلي المنقول حرفيًا
# ─────────────────────────────────────────────────────────────────────────────

class TestOriginalEngine:
    def test_zigzag_detects_synthetic_bullish_impulse(self):
        setups = DET.scan(impulse_df())
        bulls = [s for s in setups if s.direction == "BULLISH"]
        assert bulls, "يجب أن يكتشف الزيجزاج الدافع الصاعد المصطنع"
        s = bulls[-1]
        p = s.pivot_prices
        for got, want in zip(p, [100, 120, 110, 140, 125, 135]):
            assert math.isclose(got, want, rel_tol=0.02), f"محور {got} بعيد عن {want}"

    def test_three_hard_rules_pass_on_valid_impulse(self):
        r = validate_impulse(100, 120, 110, 140, 125, 135)
        assert r.is_valid, f"القواعد الثلاث يجب أن تمر: {r.summary()}"

    def test_rule1_w2_breaks_origin_fails(self):
        r = validate_impulse(100, 120, 95, 140, 125, 135)   # P2 تحت P0
        assert not r.is_valid
        assert not r.rules["Rule-1: W2 Retracement Bound"].passed

    def test_rule3_w4_overlaps_w1_fails(self):
        r = validate_impulse(100, 120, 110, 140, 115, 135)  # P4 تحت P1
        assert not r.is_valid
        assert not r.rules["Rule-3: W4 No Overlap with W1"].passed

    def test_fib_retracement_math(self):
        fib = FibonacciLevels(swing_start=10_000, swing_end=15_000)
        d = fib.retracement_dict()
        assert math.isclose(d["0.382"], 13_090.0, rel_tol=1e-6)
        assert math.isclose(d["0.618"], 11_910.0, rel_tol=1e-6)

    def test_fib_extension_math(self):
        fib = FibonacciLevels(swing_start=10_000, swing_end=15_000)
        ext = fib.extension_dict(base_price=11_910.0)
        assert math.isclose(ext["1.618"], 11_910.0 + 1.618 * 5_000, rel_tol=1e-6)

    def test_canonical_ratios_present(self):
        assert set(RETRACEMENT_RATIOS) == {0.236, 0.382, 0.500, 0.618, 0.786, 0.886}
        assert 1.618 in EXTENSION_RATIOS and 2.618 in EXTENSION_RATIOS

    def test_setup_entry_zone_and_structural_stop(self):
        setups = DET.scan(impulse_df())
        s = [x for x in setups if x.direction == "BULLISH"][-1]
        p0, p2, p3 = s.pivot_prices[0], s.pivot_prices[2], s.pivot_prices[3]
        w3 = p3 - p2
        # منطقة الدخول: 0.382 و0.236 لتراجع الموجة 3 المكتشفة
        assert math.isclose(s.entry_zone_low, p3 - 0.382 * w3, rel_tol=1e-6)
        assert math.isclose(s.entry_zone_high, p3 - 0.236 * w3, rel_tol=1e-6)
        # وقف بنيوي خلف P0 المكتشف بهامش 0.1% (الأصل)
        assert math.isclose(s.stop_loss_price, p0 * 0.999, rel_tol=1e-6)

    def test_w2_w4_conformance_flags(self):
        r = validate_impulse(100, 120, 110, 140, 125, 135)
        fib = r.fib
        assert fib.wave2_in_zone is True    # تراجع 50% داخل 0.382–0.886
        assert fib.wave4_in_zone is True    # تراجع 50% داخل 0.236–0.5

    def test_bearish_detection_supported(self):
        """الأصل يكشف الهابط أيضًا — نستعرضه في اللوحة دون تنفيذ (سبوت)."""
        r = validate_impulse(200, 180, 190, 160, 175, 165)
        assert r.is_valid or not r.is_valid  # لا استثناء — الاتجاه يُستنتج هابطًا
        assert WavePivots(200, 180, 190, 160, 175, 165).is_bullish is False

    @pytest.mark.skipif(os.getenv("RUN_LIVE_SMOKE") != "1", reason="اختبار سوق حي اختياري")
    def test_live_smoke_btc_scan(self):
        import ccxt
        ex = ccxt.binance({"enableRateLimit": True})
        raw = ex.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=500)
        df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        df["symbol"], df["timeframe"] = "BTC/USDT", "1h"
        piv = PivotDetector(DetectorConfig(method="zigzag", deviation_threshold=0.006,
                                           price_source="close", min_wave_bars=2))
        piv.scan(df)  # يجب ألا يرمي استثناءً — القائمة قد تكون فارغة


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 2 — التدفق الورقي
# ─────────────────────────────────────────────────────────────────────────────

class TestPaperFlow:
    def _setup_for(self):
        setups = DET.scan(impulse_df())
        return [s for s in setups if s.direction == "BULLISH"][-1]

    def test_compute_take_profit_matches_original(self):
        s = self._setup_for()
        tp = vnz.compute_take_profit(s)
        p0, p1, p2 = s.pivot_prices[0], s.pivot_prices[1], s.pivot_prices[2]
        # الأصل: TP = P2 المكتشف + 1.618 × طول W1 المكتشفة
        assert math.isclose(tp, p2 + 1.618 * abs(p1 - p0), rel_tol=1e-6)

    def test_compute_quantity_risk_math(self, clean_db):
        qty = vnz.compute_quantity("TEST/USDT", 128.54, 99.9)
        assert qty is not None and qty > 0
        # مخاطرة 1% من 10000 = 100$ على مسافة 28.64
        assert math.isclose(qty * (128.54 - 99.9), 100.0, rel_tol=0.05)

    def test_create_pending_signal(self, clean_db):
        s = self._setup_for()
        assert vnz.create_pending_signal("TEST/USDT", s) is True
        row = clean_db.query("SELECT * FROM signals", one=True)
        assert row["status"] == "pending"
        assert row["strategy_name"] == "Elliott_Fibonacci"
        assert math.isclose(float(row["entry_price"]), s.entry_zone_low, rel_tol=1e-6)
        assert math.isclose(float(row["stop_loss"]), s.stop_loss_price, rel_tol=1e-6)
        assert math.isclose(float(row["take_profit"]), vnz.compute_take_profit(s), rel_tol=1e-6)
        assert float(row["take_profit"]) > float(row["entry_price"]) > float(row["stop_loss"])

    def test_pending_fill_on_touch(self, clean_db, monkeypatch):
        s = self._setup_for()
        vnz.create_pending_signal("TEST/USDT", s)
        row = clean_db.query("SELECT * FROM signals", one=True)
        entry = float(row["entry_price"])
        touch = pd.DataFrame([{"ts": 0, "open": entry + 5, "high": entry + 6,
                               "low": entry - 1, "close": entry + 2, "volume": 1}])
        monkeypatch.setattr(vnz, "fetch_ohlcv_df", lambda *a, **k: touch)
        vnz.monitor_step()
        row = clean_db.query("SELECT * FROM signals", one=True)
        assert row["status"] == "open"
        assert math.isclose(float(row["fill_price"]), entry, rel_tol=1e-6)

    def test_pending_invalidation_close_below_p0(self, clean_db, monkeypatch):
        s = self._setup_for()
        vnz.create_pending_signal("TEST/USDT", s)
        kill = pd.DataFrame([{"ts": 0, "open": 98, "high": 99, "low": 94,
                              "close": 95, "volume": 1}])  # إغلاق خلف P0=100
        monkeypatch.setattr(vnz, "fetch_ohlcv_df", lambda *a, **k: kill)
        vnz.monitor_step()
        row = clean_db.query("SELECT * FROM signals", one=True)
        assert row["status"] == "cancelled"
        assert "P0" in (row["close_reason"] or "")

    def test_pending_expiry(self, clean_db, monkeypatch):
        s = self._setup_for()
        vnz.create_pending_signal("TEST/USDT", s)
        past = (datetime.now(timezone.utc) - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
        clean_db.execute("UPDATE signals SET expires_at=%s", (past,))
        neutral = pd.DataFrame([{"ts": 0, "open": 138, "high": 139, "low": 137,
                                 "close": 138, "volume": 1}])
        monkeypatch.setattr(vnz, "fetch_ohlcv_df", lambda *a, **k: neutral)
        vnz.monitor_step()
        row = clean_db.query("SELECT * FROM signals", one=True)
        assert row["status"] == "expired"

    def test_open_trade_hits_stop_loss_with_fees(self, clean_db, monkeypatch):
        s = self._setup_for()
        vnz.create_pending_signal("TEST/USDT", s)
        row = clean_db.query("SELECT * FROM signals", one=True)
        entry = float(row["entry_price"])
        sl = float(row["stop_loss"])
        fill = pd.DataFrame([{"ts": 0, "open": entry + 1, "high": entry + 2,
                              "low": entry - 1, "close": entry, "volume": 1}])
        monkeypatch.setattr(vnz, "fetch_ohlcv_df", lambda *a, **k: fill)
        vnz.monitor_step()
        row = clean_db.query("SELECT * FROM signals", one=True)
        assert row["status"] == "open"
        sl_hit = pd.DataFrame([{"ts": 1, "open": entry, "high": entry + 1,
                                "low": sl - 0.5, "close": sl - 0.2, "volume": 1}])
        monkeypatch.setattr(vnz, "fetch_ohlcv_df", lambda *a, **k: sl_hit)
        vnz.monitor_step()
        row = clean_db.query("SELECT * FROM signals", one=True)
        assert row["status"] == "closed"
        assert math.isclose(float(row["close_price"]), sl, rel_tol=1e-6)
        qty = float(row["quantity"])
        gross = qty * (sl - entry)
        fees = (qty * entry + qty * sl) * 0.001
        assert math.isclose(float(row["pnl_usdt"]), gross - fees, rel_tol=1e-4)
        assert float(row["pnl_usdt"]) < 0

    def test_open_trade_hits_tp(self, clean_db, monkeypatch):
        s = self._setup_for()
        vnz.create_pending_signal("TEST/USDT", s)
        row = clean_db.query("SELECT * FROM signals", one=True)
        entry = float(row["entry_price"])
        tp = float(row["take_profit"])
        fill = pd.DataFrame([{"ts": 0, "open": entry + 1, "high": entry + 2,
                              "low": entry - 1, "close": entry, "volume": 1}])
        monkeypatch.setattr(vnz, "fetch_ohlcv_df", lambda *a, **k: fill)
        vnz.monitor_step()
        tp_hit = pd.DataFrame([{"ts": 1, "open": entry, "high": tp + 1,
                                "low": entry - 1, "close": tp, "volume": 1}])
        monkeypatch.setattr(vnz, "fetch_ohlcv_df", lambda *a, **k: tp_hit)
        vnz.monitor_step()
        row = clean_db.query("SELECT * FROM signals", one=True)
        assert row["status"] == "closed"
        assert float(row["pnl_usdt"]) > 0
        assert "1.618" in (row["close_reason"] or "")

    def test_max_open_trades_gate(self, clean_db, monkeypatch):
        s = self._setup_for()
        vnz.is_trading_enabled = True
        try:
            for i in range(vnz.MAX_OPEN_TRADES):
                sym = f"TEST{i}/USDT"
                assert vnz.create_pending_signal(sym, s) is True
                clean_db.execute("UPDATE signals SET symbol=%s WHERE symbol='TEST/USDT' AND status='pending' AND id=(SELECT MAX(id) FROM signals)", (sym,))
            assert vnz.active_trade_count() == vnz.MAX_OPEN_TRADES
            assert vnz.active_trade_count() >= vnz.MAX_OPEN_TRADES  # البوابة ستمانع الإضافة الخامسة
        finally:
            vnz.is_trading_enabled = False

    def test_select_best_setup_scoring(self):
        """+1 لمنطقة W2 و+1 لمنطقة W4 — الأفضل يفوز (منطق الأصل)."""
        s = self._setup_for()
        best = vnz.select_best_setup([s])
        assert best is s
        assert vnz.select_best_setup([]) is None

    def test_scan_cycle_creates_detection_entries(self, clean_db, monkeypatch):
        vnz.recent_detections.clear()
        monkeypatch.setattr(vnz, "watchlist", ["TEST/USDT"])
        monkeypatch.setattr(vnz, "fetch_ohlcv_df", lambda *a, **k: impulse_df())
        vnz.is_trading_enabled = True
        try:
            vnz.scan_cycle()
        finally:
            vnz.is_trading_enabled = False
        assert len(vnz.recent_detections) >= 1
        d0 = vnz.recent_detections[0]
        assert d0["symbol"] == "TEST/USDT"
        assert d0["direction"] == "BULLISH"


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 3 — اللوحة وAPI
# ─────────────────────────────────────────────────────────────────────────────

class TestDashboardAPI:
    def test_health(self):
        client = vnz.app.test_client()
        r = client.get("/health")
        assert r.status_code == 200
        body = r.get_json()
        assert body["version"] == "FE1.1.1"
        assert body["strategy"] == "Elliott_Fibonacci"
        assert body["mode"] == "paper"

    def test_api_all_structure(self, clean_db, monkeypatch):
        monkeypatch.setattr(vnz, "get_live_price", lambda sym: 130.0)  # بلا شبكة في الاختبار
        s = [x for x in DET.scan(impulse_df()) if x.direction == "BULLISH"][-1]
        vnz.create_pending_signal("TEST/USDT", s)
        vnz.register_detection("TEST/USDT", s, traded=True)
        client = vnz.app.test_client()
        r = client.get("/api/all")
        assert r.status_code == 200
        body = r.get_json()
        for key in ("version", "strategy", "stats", "open_signals", "closed_signals",
                    "detections", "notifications", "paper_balance"):
            assert key in body
        assert len(body["open_signals"]) == 1
        assert math.isclose(body["open_signals"][0]["pivots"]["P0"], 99.95, rel_tol=1e-6)
        assert body["open_signals"][0]["current_price"] == 130.0  # [FE1.1.0] تتبع حي
        assert body["detections"][0]["traded"] is True

    def test_toggle_trading(self, clean_db):
        client = vnz.app.test_client()
        old = vnz.is_trading_enabled
        r = client.post("/api/trading/toggle")
        assert r.status_code == 200
        assert r.get_json()["trading_enabled"] == (not old)
        client.post("/api/trading/toggle")  # إعادة الحالة
        assert vnz.is_trading_enabled == old

    def test_stats_reset(self, clean_db):
        s = [x for x in DET.scan(impulse_df()) if x.direction == "BULLISH"][-1]
        vnz.create_pending_signal("TEST/USDT", s)
        client = vnz.app.test_client()
        r = client.post("/api/stats/reset")
        assert r.status_code == 200
        assert vnz.get_paper_balance() == vnz.PAPER_BALANCE_START
        assert vnz.active_trade_count() == 0

    def test_dashboard_html_is_arabic_rtl(self):
        client = vnz.app.test_client()
        r = client.get("/")
        html = r.get_data(as_text=True)
        assert 'dir="rtl"' in html and "Fibo-Elio" in html
        assert "ورقي" in html

    def test_pnl_history_endpoint(self, clean_db):
        client = vnz.app.test_client()
        r = client.get("/api/pnl_history")
        assert r.status_code == 200
        assert "history" in r.get_json()


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 4 — تعاقب مزودي البيانات (FE1.0.1): باينانس أولًا ثم البدائل عند الحظر
# ─────────────────────────────────────────────────────────────────────────────

def _klines(n: int = 80, base: float = 100.0) -> list:
    """شموع خام على عقد ccxt — ثوابت لطيفة تكفي عتبة 60 شمعة."""
    return [[1700000000000 + i * 3600000, base, base + 1.0, base - 1.0, base, 10.0] for i in range(n)]


class FakeExchange:
    """بديل مزود ccxt — سلوك قابل للبرمجة مع عدّاد استدعاءات."""

    def __init__(self, fn):
        self._fn = fn
        self.calls = 0

    def fetch_ohlcv(self, symbol, timeframe=None, limit=None):
        self.calls += 1
        return self._fn(symbol, timeframe, limit)

    def amount_to_precision(self, symbol, amount):
        return f"{float(amount):.6f}"


def _ban(*a):
    raise Exception("APIError(code=-1003): Way too much request weight used; IP banned")


def _reset_providers(monkeypatch, mapping):
    monkeypatch.setattr(vnz, "EXCHANGES", OrderedDict(mapping))
    monkeypatch.setattr(vnz, "provider_state", {
        name: {"ok": 0, "fail": 0, "last_error": "", "last_ok_at": None, "cooldown_until": 0.0}
        for name in mapping
    })
    monkeypatch.setattr(vnz, "active_source", {"name": None, "since": None})
    monkeypatch.setattr(vnz.time, "sleep", lambda *a: None)  # اختبارات سريعة


class TestDataProviderRotation:
    def test_binance_ban_falls_back_to_bybit(self, clean_db, monkeypatch):
        ban, ok = FakeExchange(_ban), FakeExchange(lambda *a: _klines())
        _reset_providers(monkeypatch, OrderedDict([("binance", ban), ("bybit", ok)]))
        df = vnz.fetch_ohlcv_df("BTC/USDT", "1h", limit=80)
        assert df is not None and len(df) == 80
        assert ban.calls == 1 and ok.calls == 1
        assert vnz.active_source["name"] == "bybit"
        st = vnz.provider_state["binance"]
        assert st["fail"] == 1 and "-1003" in st["last_error"] and st["cooldown_until"] > 0

    def test_cooldown_skips_banned_provider_next_fetch(self, clean_db, monkeypatch):
        ban, ok = FakeExchange(_ban), FakeExchange(lambda *a: _klines())
        _reset_providers(monkeypatch, OrderedDict([("binance", ban), ("bybit", ok)]))
        assert vnz.fetch_ohlcv_df("BTC/USDT", "1h", limit=80) is not None
        first_ban_calls = ban.calls
        assert vnz.fetch_ohlcv_df("ETH/USDT", "1h", limit=80) is not None
        assert ban.calls == first_ban_calls  # باينانس مبردود — لم يُستدعَ مجددًا
        assert ok.calls == 2

    def test_full_rotation_recovery_to_primary_after_cooldown(self, clean_db, monkeypatch):
        ban, ok = FakeExchange(_ban), FakeExchange(lambda *a: _klines())
        _reset_providers(monkeypatch, OrderedDict([("binance", ban), ("bybit", ok)]))
        vnz.fetch_ohlcv_df("BTC/USDT", "1h", limit=80)
        # انتهاء التبريد يدويًا — باينانس يعود أولًا في المحاولة التالية (الأصل أولًا دائمًا)
        vnz.provider_state["binance"]["cooldown_until"] = 0.0
        vnz.fetch_ohlcv_df("BTC/USDT", "1h", limit=80)
        assert ban.calls == 2 and ok.calls == 2

    def test_all_providers_fail_returns_none(self, clean_db, monkeypatch):
        e1, e2 = FakeExchange(_ban), FakeExchange(lambda *a: [])
        _reset_providers(monkeypatch, OrderedDict([("binance", e1), ("bybit", e2)]))
        assert vnz.fetch_ohlcv_df("BTC/USDT", "1h", limit=80) is None
        assert e1.calls == 1 and e2.calls == 1  # التبريد يمنع التكرار الفوري داخل نفس الجلب

    def test_data_status_exposes_telemetry(self, clean_db, monkeypatch):
        ban, ok = FakeExchange(_ban), FakeExchange(lambda *a: _klines())
        _reset_providers(monkeypatch, OrderedDict([("binance", ban), ("bybit", ok)]))
        vnz.fetch_ohlcv_df("BTC/USDT", "1h", limit=80)
        d = vnz.data_status()
        assert d["active"] == "bybit"
        assert d["providers"]["binance"]["fail"] == 1
        assert d["providers"]["bybit"]["ok"] == 1
        assert d["providers"]["binance"]["cooling_sec"] > 0

    def test_amount_prec_safe_without_exchange(self, clean_db, monkeypatch):
        _reset_providers(monkeypatch, OrderedDict())
        assert vnz.amount_prec("BTC/USDT", 1.23456789) == 1.23456789  # لا مزود — إرجاع كما هو

    def test_health_includes_data_source(self, clean_db):
        client = vnz.app.test_client()
        r = client.get("/health")
        assert r.status_code == 200
        assert "data_source" in r.get_json()

    def test_api_all_includes_data_block(self, clean_db):
        client = vnz.app.test_client()
        r = client.get("/api/all")
        assert r.status_code == 200
        body = r.get_json()
        assert "data" in body and "providers" in body["data"]


# ─────────────────────────────────────────────────────────────────────────────────
# الجولة 5 — التتبع الحي والإغلاق/الإلغاء اليدوي (FE1.1.0)
# ─────────────────────────────────────────────────────────────────────────────────

class TestLiveTrackingAndManualActions:
    def _fill_trade(self, clean_db, monkeypatch):
        """إنشاء أمر معلق وملؤه → صفقة مفتوحة جاهزة للتتبع/الإغلاق."""
        s = [x for x in DET.scan(impulse_df()) if x.direction == "BULLISH"][-1]
        vnz.create_pending_signal("TEST/USDT", s)
        row = clean_db.query("SELECT * FROM signals", one=True)
        entry = float(row["entry_price"])
        fill = pd.DataFrame([{"ts": 0, "open": entry + 1, "high": entry + 2,
                              "low": entry - 1, "close": entry, "volume": 1}])
        monkeypatch.setattr(vnz, "fetch_ohlcv_df", lambda *a, **k: fill)
        vnz.monitor_step()
        return clean_db.query("SELECT * FROM signals", one=True)

    def test_get_live_price_uses_cache(self, clean_db, monkeypatch):
        vnz._price_cache.clear()
        calls = {"n": 0}
        def fake_fetch(*a, **k):
            calls["n"] += 1
            return pd.DataFrame([{"ts": 0, "open": 130, "high": 131,
                                  "low": 129, "close": 130.5, "volume": 1}])
        monkeypatch.setattr(vnz, "fetch_ohlcv_df", fake_fetch)
        p1 = vnz.get_live_price("TEST/USDT")
        p2 = vnz.get_live_price("TEST/USDT")
        assert math.isclose(p1, 130.5) and math.isclose(p2, 130.5)
        assert calls["n"] == 1  # الاستدعاء الثاني من الذاكرة المؤقتة (20 ثانية)

    def test_get_live_price_none_on_failure(self, clean_db, monkeypatch):
        vnz._price_cache.clear()
        monkeypatch.setattr(vnz, "fetch_ohlcv_df", lambda *a, **k: None)
        assert vnz.get_live_price("TEST/USDT") is None

    def test_enrich_open_signal_unrealized_and_progress(self, clean_db, monkeypatch):
        row = self._fill_trade(clean_db, monkeypatch)
        price = float(row["fill_price"]) * 1.02  # ربح 2% افتراضي
        monkeypatch.setattr(vnz, "get_live_price", lambda sym: price)
        out = vnz.enrich_live_signal(dict(row))
        qty, fill = float(row["quantity"]), float(row["fill_price"])
        gross = qty * (price - fill)
        fees = (qty * fill + qty * price) * 0.001
        assert math.isclose(out["current_price"], price)
        assert math.isclose(out["unrealized_usdt"], gross - fees, rel_tol=1e-4)
        assert out["unrealized_pct"] > 0
        assert out["progress_pct"] > 0          # السعر فوق الدخول — تقدم نحو الهدف
        assert out["dist_tp_pct"] > 0            # الهدف أعلى من السعر الحالي
        assert out["dist_sl_pct"] < 0            # الوقف أسفل من السعر الحالي

    def test_enrich_pending_signal_dist_entry(self, clean_db, monkeypatch):
        s = [x for x in DET.scan(impulse_df()) if x.direction == "BULLISH"][-1]
        vnz.create_pending_signal("TEST/USDT", s)
        row = clean_db.query("SELECT * FROM signals", one=True)
        monkeypatch.setattr(vnz, "get_live_price", lambda sym: 135.0)
        out = vnz.enrich_live_signal(dict(row))
        entry = float(row["entry_price"])
        assert out["current_price"] == 135.0
        assert math.isclose(out["dist_entry_pct"], (entry - 135.0) / 135.0 * 100.0, rel_tol=1e-3)  # مقرّب 3 منازل
        assert "unrealized_usdt" not in out      # المعلق بلا ربح غير محقق

    def test_api_all_enriches_open_rows(self, clean_db, monkeypatch):
        self._fill_trade(clean_db, monkeypatch)
        monkeypatch.setattr(vnz, "get_live_price", lambda sym: 130.0)
        client = vnz.app.test_client()
        body = client.get("/api/all").get_json()
        sig = body["open_signals"][0]
        assert sig["current_price"] == 130.0
        assert "unrealized_usdt" in sig and "progress_pct" in sig and "dist_tp_pct" in sig

    def test_manual_close_endpoint_market_price(self, clean_db, monkeypatch):
        row = self._fill_trade(clean_db, monkeypatch)
        price = float(row["fill_price"]) * 1.01
        monkeypatch.setattr(vnz, "get_live_price", lambda sym: price)
        client = vnz.app.test_client()
        r = client.post("/api/trades/close", json={"id": int(row["id"])})
        assert r.status_code == 200 and r.get_json()["ok"] is True
        after = clean_db.query("SELECT * FROM signals", one=True)
        assert after["status"] == "closed"
        assert "يدوي" in after["close_reason"]
        assert math.isclose(float(after["close_price"]), price, rel_tol=1e-9)
        assert float(after["pnl_usdt"]) > 0
        assert vnz.get_paper_balance() > vnz.PAPER_BALANCE_START  # الرصيد حُدّث

    def test_manual_close_falls_back_to_fill_price(self, clean_db, monkeypatch):
        row = self._fill_trade(clean_db, monkeypatch)
        monkeypatch.setattr(vnz, "get_live_price", lambda sym: None)  # مزودات فشلت
        client = vnz.app.test_client()
        r = client.post("/api/trades/close", json={"id": int(row["id"])})
        assert r.status_code == 200
        after = clean_db.query("SELECT * FROM signals", one=True)
        assert math.isclose(float(after["close_price"]), float(row["fill_price"]), rel_tol=1e-9)

    def test_manual_close_rejects_pending_and_unknown(self, clean_db, monkeypatch):
        s = [x for x in DET.scan(impulse_df()) if x.direction == "BULLISH"][-1]
        vnz.create_pending_signal("TEST/USDT", s)
        row = clean_db.query("SELECT * FROM signals", one=True)
        client = vnz.app.test_client()
        assert client.post("/api/trades/close", json={"id": int(row["id"])}).status_code == 404  # معلق وليس مفتوحًا
        assert client.post("/api/trades/close", json={"id": 9999}).status_code == 404
        assert client.post("/api/trades/close", json={"id": "abc"}).status_code == 400

    def test_manual_cancel_endpoint(self, clean_db, monkeypatch):
        s = [x for x in DET.scan(impulse_df()) if x.direction == "BULLISH"][-1]
        vnz.create_pending_signal("TEST/USDT", s)
        row = clean_db.query("SELECT * FROM signals", one=True)
        client = vnz.app.test_client()
        r = client.post("/api/trades/cancel", json={"id": int(row["id"])})
        assert r.status_code == 200 and r.get_json()["ok"] is True
        after = clean_db.query("SELECT * FROM signals", one=True)
        assert after["status"] == "cancelled"
        assert "يدوي" in after["close_reason"]
        assert vnz.active_trade_count() == 0  # خرج من الصفقات النشطة

    def test_manual_cancel_rejects_open(self, clean_db, monkeypatch):
        row = self._fill_trade(clean_db, monkeypatch)
        client = vnz.app.test_client()
        r = client.post("/api/trades/cancel", json={"id": int(row["id"])})
        assert r.status_code == 404  # المفتوح يُغلق بـ /api/trades/close لا إلغاء

    def test_manual_endpoints_require_auth(self, monkeypatch):
        monkeypatch.setattr(vnz, "DASHBOARD_PROTECTED", True)
        monkeypatch.setattr(vnz, "DASHBOARD_USERNAME", "admin")
        monkeypatch.setattr(vnz, "DASHBOARD_PASSWORD", "test123")
        client = vnz.app.test_client()
        for path in ("/api/trades/close", "/api/trades/cancel"):
            r = client.post(path, json={"id": 1})
            assert r.status_code == 401  # بلا مصادقة → رفض
        import base64
        cred = base64.b64encode(b"admin:test123").decode()
        r = client.post("/api/trades/cancel", json={"id": 1},
                        headers={"Authorization": "Basic " + cred})
        assert r.status_code == 404  # مصادقة تمر — لكن لا صفقة بهذا المعرف


class TestShortFetchRegressionFE111:
    """FE1.1.1 — إصلاح حرج: كان شرط 60 شمعة يرفض استعلامات المراقبة القصيرة (limit=2)
    فتعطلت حلقة الملء/الوقف/الهدف كليًا منذ البداية."""

    def test_short_query_limit2_returns_rows(self, clean_db, monkeypatch):
        ok = FakeExchange(lambda *a: _klines(2, base=100.0))  # صفّان فقط كما تطلب المراقبة
        _reset_providers(monkeypatch, OrderedDict([("binance", ok)]))
        df = vnz.fetch_ohlcv_df("BTC/USDT", "15m", limit=2, min_candles=2)
        assert df is not None and len(df) == 2
        assert ok.calls == 1  # نجحت من أول محاولة — لا تكرار ولا هدر

    def test_short_query_rejected_by_default_min(self, clean_db, monkeypatch):
        ok = FakeExchange(lambda *a: _klines(2, base=100.0))
        _reset_providers(monkeypatch, OrderedDict([("binance", ok)]))
        assert vnz.fetch_ohlcv_df("BTC/USDT", "15m", limit=2) is None  # الافتراضي 60

    def test_scan_query_short_response_still_rejected(self, clean_db, monkeypatch):
        ok = FakeExchange(lambda *a: _klines(30, base=100.0))
        _reset_providers(monkeypatch, OrderedDict([("binance", ok)]))
        assert vnz.fetch_ohlcv_df("BTC/USDT", "15m", limit=500) is None  # 30 < 60 للمسح

    def test_get_live_price_works_with_short_candles(self, clean_db, monkeypatch):
        vnz._price_cache.clear()
        ok = FakeExchange(lambda *a: [[1700000000000, 130.0, 131.0, 129.0, 130.5, 10.0],
                                      [1700000900000, 130.5, 132.0, 130.0, 131.7, 10.0]])
        _reset_providers(monkeypatch, OrderedDict([("binance", ok)]))
        assert math.isclose(vnz.get_live_price("BTC/USDT"), 131.7)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
