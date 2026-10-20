"""اختبارات FE1.10.2 «اقتباسات flowmap» (Apache-2.0 — إعادة كتابة أصلية بإسناد):
مهلة لا-أحداث لتيك باينانس الخام + تصفير backoff بشرط الاستقرار + jitter كامل،
بوابة صحة الطوابع الزمنية _ts_sane_ms، كاش قمة الأسبوع SWR+single-flight،
تسجيل بطابور محدود بإسقاط مُعدّ، وتحقق إعدادات بنطاق مسمّى عند الإقلاع.
صفر مساس بالبوابات أو الحمايات أو منطق التداول."""
import threading
import time

import pytest

import vnz
from utils.logger import QUEUE_STATS, _BoundedQueueHandler

# [عزل conftest] العادة العامة تستبدل vnz.weekly_high بـ lambda None لكل الاختبارات —
# نلتقط الأصلية وقت الاستيراد (قبل تطبيق العادة) ونستعيدها لاختبارات SWR فقط
_REAL_WEEKLY_HIGH = vnz.weekly_high


@pytest.fixture(autouse=True)
def _real_weekly_high(monkeypatch):
    """استعادة weekly_high الأصلية لاختبارات هذا الملف حصرًا — الأخرى تبقى معزولة."""
    monkeypatch.setattr(vnz, "weekly_high", _REAL_WEEKLY_HIGH)
    yield


# ── بوابة صحة الطوابع الزمنية (نمط flowmap base.py ts_ns_sane) ────────────────

class TestTsSanityGate:
    def test_sane_now_passes(self):
        now_ms = int(time.time() * 1000)
        assert vnz._ts_sane_ms(now_ms) is True

    def test_floor_boundary_passes(self):
        assert vnz._ts_sane_ms(vnz._TS_FLOOR_MS) is True

    def test_1970_unit_mixup_rejected(self):
        """توقيع خلط الوحدات: طابع ثوانٍ/نصي مدفوع في حقل ms يسقط تحت أرضية 2010."""
        assert vnz._ts_sane_ms(1_000) is False
        assert vnz._ts_sane_ms(0) is False
        assert vnz._ts_sane_ms(-5) is False

    def test_future_beyond_horizon_rejected(self):
        now_ms = int(time.time() * 1000)
        assert vnz._ts_sane_ms(now_ms + vnz._TS_HORIZON_MS + 60_000) is False

    def test_future_within_horizon_tolerated(self):
        """ساعة مزود متقدمة حتى يوم واحد tolerated — بعده لا معنى."""
        now_ms = int(time.time() * 1000)
        assert vnz._ts_sane_ms(now_ms + 3600_000) is True

    def test_non_numeric_rejected(self):
        assert vnz._ts_sane_ms("not-a-ts") is False
        assert vnz._ts_sane_ms(None) is False

    def test_gate_drop_counts_and_warns_once(self, caplog):
        before = vnz._ts_gate_state["dropped"]
        with caplog.at_level("WARNING"):
            vnz._ts_gate_drop(999)
            vnz._ts_gate_drop(998)  # الثانية صامتة
        assert vnz._ts_gate_state["dropped"] == before + 2
        # تحذير واحد للحوادث الواحدة كحد أقصى في هذه الدفعة
        assert sum(1 for r in caplog.records if "بوابة الطوابع" in r.message) <= 1


class TestKlineCacheTsGate:
    def test_cache_write_filters_insane_rows(self, monkeypatch):
        """طابع فاسد لا يدخل الكاش الدائم أبدًا — لا يصل إلى db.execute إطلاقًا."""
        executed = []
        class _FakeDB:
            def execute(self, sql, params=None):
                executed.append(params)
        monkeypatch.setattr(vnz, "db", _FakeDB())
        monkeypatch.setattr(vnz, "_kline_cache_max_ts", {})
        now_ms = int(time.time() * 1000)
        good = [now_ms - 300_000, 1.0, 2.0, 0.5, 1.5, 10.0]
        bad1970 = [1_000, 1.0, 2.0, 0.5, 1.5, 10.0]           # خلط وحدات
        badfuture = [now_ms + 40 * 24 * 3600 * 1000, 1.0, 2.0, 0.5, 1.5, 10.0]
        vnz._kline_cache_write("TEST/USDT", "5m", [good, bad1970, badfuture])
        # الشمعة الصالحة وحدها وصلت القاعدة
        assert len(executed) == 1
        assert int(executed[0][2]) == good[0]
        assert vnz._kline_cache_max_ts[("TEST/USDT", "5m")] == good[0]


class TestWsApplyOhlcvTsGate:
    def test_live_candles_drop_insane_ts(self):
        """شمعة بطابع فاسد لا تسمّم شموع الحيّة التي تغذّي SuperTrend/ADX والمراقبة."""
        sym = "TS-TEST/USDT"
        now_ms = int(time.time() * 1000)
        good = [now_ms - 300_000, 1.0, 2.0, 0.5, 1.5, 10.0]
        bad = [1_000, 1.0, 2.0, 0.5, 1.5, 10.0]
        dropped_before = vnz._ts_gate_state["dropped"]
        ok = vnz.ws_apply_ohlcv(sym, [bad, good], "unit-test")
        assert ok is True
        with vnz._ws_lock:
            stored = [r[0] for r in vnz._ws_candles[sym]["candles"]]
        assert good[0] in stored
        assert bad[0] not in stored
        assert vnz._ts_gate_state["dropped"] == dropped_before + 1


# ── كاش قمة الأسبوع SWR + single-flight (نمط flowmap market_cache) ────────────

class TestWeeklyHighSwr:
    @pytest.fixture()
    def _fresh_state(self):
        vnz._tp_week_cache.clear()
        vnz._tp_week_inflight.clear()
        vnz._tp_week_stats.update({"swr_hits": 0, "singleflight_blocks": 0})
        yield
        vnz._tp_week_cache.clear()
        vnz._tp_week_inflight.clear()

    def test_fresh_hit_returns_without_fetch(self, _fresh_state, monkeypatch):
        vnz._tp_week_cache["AAA/USDT"] = (time.time(), 2.5)
        calls = []
        monkeypatch.setattr(vnz, "_tp_week_refresh", lambda s: calls.append(s) or 2.5)
        assert vnz.weekly_high("AAA/USDT") == 2.5
        assert calls == []

    def test_stale_serves_immediately_with_bg_refresh(self, _fresh_state, monkeypatch):
        """SWR: القديمة الصادقة تُعاد فورًا والتحديث خلفي وحيد ينعشها."""
        vnz._tp_week_cache["BBB/USDT"] = (time.time() - vnz.TP_WEEK_CAP_TTL_SEC - 5, 1.0)
        done = threading.Event()
        calls = []
        def _slow_refresh(sym):
            calls.append(sym)
            time.sleep(0.15)
            out = 9.9
            with vnz._tp_week_lock:
                vnz._tp_week_cache[sym] = (time.time(), out)
                vnz._tp_week_inflight.pop(sym, None)
            done.set()
            return out
        monkeypatch.setattr(vnz, "_tp_week_refresh", _slow_refresh)
        t0 = time.time()
        out = vnz.weekly_high("BBB/USDT")
        assert time.time() - t0 < 0.05      # لم ينتظر REST إطلاقًا
        assert out == 1.0                   # القديمة الصادقة
        assert done.wait(2.0)               # الخلفي أكمل وانعش
        assert calls == ["BBB/USDT"]        # جلب واحد لا اثنان
        assert vnz.weekly_high("BBB/USDT") == 9.9  # الجديد طازج

    def test_singleflight_collapses_concurrent_misses(self, _fresh_state, monkeypatch):
        """نداءات متسابقة على رمز بلا قيمة تنهار إلى جلب واحد."""
        calls = []
        started = threading.Event()
        release = threading.Event()
        def _blocking_refresh(sym):
            calls.append(sym)
            started.set()
            release.wait(3.0)
            with vnz._tp_week_lock:
                vnz._tp_week_cache[sym] = (time.time(), 7.7)
                vnz._tp_week_inflight.pop(sym, None)
            return 7.7
        monkeypatch.setattr(vnz, "_tp_week_refresh", _blocking_refresh)
        results = []
        def _first():
            results.append(vnz.weekly_high("CCC/USDT"))
        t1 = threading.Thread(target=_first)
        t1.start()
        assert started.wait(2.0)
        # نداء متسابق أثناء الجلب الأول: single-flight يعيده None fail-open
        assert vnz.weekly_high("CCC/USDT") is None
        release.set()
        t1.join(3.0)
        assert results == [7.7]
        assert calls == ["CCC/USDT"]        # جلب واحد فقط
        assert vnz._tp_week_stats["singleflight_blocks"] >= 1


# ── تحقق الإعدادات بنطاق مسمّى (نمط flowmap config.py) ────────────────────────

class TestBootConfigValidation:
    def test_defaults_pass(self):
        vnz._validate_boot_config()  # لا استثناء بالقيم الافتراضية

    def test_out_of_range_raises_named_error(self, monkeypatch):
        monkeypatch.setattr(vnz, "WS_STALE_SEC", 0.5)
        with pytest.raises(ValueError) as ei:
            vnz._validate_boot_config()
        msg = str(ei.value)
        assert "WS_STALE_SEC" in msg and "[10, 3600]" in msg

    def test_nan_rejected(self, monkeypatch):
        monkeypatch.setattr(vnz, "RR_NET_MIN_TP1", float("nan"))
        with pytest.raises(ValueError) as ei:
            vnz._validate_boot_config()
        assert "RR_NET_MIN_TP1" in str(ei.value)

    def test_zero_allowed_for_opt_out(self, monkeypatch):
        monkeypatch.setattr(vnz, "MAX_STOP_PCT", 0.0)   # 0 = تعطيل البوابة
        monkeypatch.setattr(vnz, "RR_NET_MIN_TP1", 0.0)
        vnz._validate_boot_config()  # لا استثناء


# ── اللوجر بطابور محدود (نمط flowmap logging_setup) ───────────────────────────

class TestBoundedLogging:
    def test_overflow_drops_counted_not_raises(self):
        import queue as _q
        h = _BoundedQueueHandler(_q.Queue(maxsize=2))
        import logging as _lg
        recs = [_lg.LogRecord("t", _lg.INFO, "p", 1, f"m{i}", None, None) for i in range(5)]
        dropped0 = QUEUE_STATS["dropped"]
        for r in recs:
            h.handle(r)  # امتلاء الطابور يعني إسقاطًا مُعدًّا — لا استثناء للمسار الساخن
        assert QUEUE_STATS["dropped"] >= dropped0 + 3

    def test_vnz_imports_queue_stats(self):
        assert isinstance(vnz.QUEUE_STATS, dict) and "dropped" in vnz.QUEUE_STATS


# ── تيك باينانس الخام: الثوابت والعدادات (مهلة الصمت + الاستقرار) ─────────────

class TestRawTickResilience:
    def test_constants_exist(self):
        assert vnz.RAW_EVENT_TIMEOUT_SEC >= 15.0    # مهلة لا-أحداث معقولة
        assert 0 < vnz.RAW_STABLE_SEC < 60.0        # إثبات استقرار قبل التصفير
        assert vnz.RAW_BACKOFF_BASE == 5.0

    def test_resilience_counters_exist(self):
        assert "silence_timeouts" in vnz._raw_resilience
        assert "stability_resets" in vnz._raw_resilience


# ── /health قسم resilience مرئي ───────────────────────────────────────────────

class TestHealthResilienceSection:
    def test_health_exposes_resilience_counters(self, monkeypatch):
        monkeypatch.setattr(vnz.db, "check", lambda: True)
        client = vnz.app.test_client()
        body = client.get("/health").get_json()
        res = body.get("resilience") or {}
        for key in ("ts_gate_dropped", "raw_silence_timeouts", "raw_stability_resets",
                    "tp_week_swr_hits", "tp_week_singleflight", "log_queue_dropped"):
            assert key in res, f"/health resilience يفتقد {key}"
