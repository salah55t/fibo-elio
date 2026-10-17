#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_fe1914.py — اختبارات FE1.9.14 «درع الخسارة الكبيرة»

الخلفية (بلاغ المستخدم): «راجع لوحة التحكم والنتائج وحللها واصلح مايمكن تجنب الخسارة
الكبيرة في الصفقات». تحليل الصفقات الخمس المغلقة (صافي -42.67$ رغم فوز 60%) كشف:
  1) كل الصفقات دخلها R:R صافٍ دون 1R (0.43-0.77) — الأرضية 0.3 كانت تقبل مخاطرة
     أكبر من المكافأة، ومع أهداف دون 1R كانت حمايتا الجزئي/BE (تريغر +1R) ميتين
     بنيويًا — كل خاسر يأخذ -1R كاملًا بلا موازن.
  2) وقف بنيوي عريض: PROM وقفها 6.19% من الدخول على 15m → خسارة كاملة 1.03% من
     الرصيد لمكافأة قُصّها سقف الأسبوع إلى 0.65R.
  3) مخاطرة 1% لكل صفقة وحد يومي 5% ومتتاليات 3 — سقوف يوم كامل متساهلة.

الجولات:
  1) الثوابت الإنتاجية الجديدة (بعلامة production_gates — بلا تخفيف conftest)
  2) بوابة MAX_STOP_PCT: رفض بنية وقفها أعرض من السقف + عداد + سبب مسمّى + تمرير
     هندسة سكالبينج واقعية + الحد الحدي + التعطيل بالصفر
  3) التريغر التكيفي للحماية: خطة دون 1R تُحمى عند 0.7×مسافة TP1 (أرضية 0.3R)،
     الخطة فوق 1R تبقى عند +1R حرفيًا، تعطيل الكسر بالصفر
  4) حدود اليوم: متتاليتان → تبريد، حد يومي 3% يمنع الإشارات
  5) تزامن اللوحة والإصدار وrender.yaml

تشغيل: pytest test_fe1914.py -v   (من داخل مجلد المشروع)
"""

import json
import math
import os
import sqlite3

import pandas as pd
import pytest

import vnz
import panel
vnz.DASHBOARD_PROTECTED = False  # بيئة الاختبار: بلا مصادقة (نفس عقد test_fe100)


# ─────────────────────────────────────────────────────────────────────────────
# تجهيزات (نفس عقد test_fe180)
# ─────────────────────────────────────────────────────────────────────────────

class _StubFib:
    def __init__(self):
        self.wave2_retrace_pct = 0.5
        self.wave4_retrace_pct = 0.3
        self.wave2_in_zone = True
        self.wave4_in_zone = True


class _StubValidation:
    def __init__(self):
        self.fib = _StubFib()


def make_setup(prices=None, direction: str = "BULLISH"):
    """نافذة صاعدة قياسية (هندسة test_fe180): وقفها 17.7% وrr_net 0.345 —
    تُستخدم هنا حصرًا لاختبار رفض بوابة العرض (وقفة أعرض من أي سقف واقعي)."""
    from engine.pattern_detector import DetectedSetup
    P = prices or [90.0, 100.0, 100.0, 115.0, 104.0, 108.0]
    return DetectedSetup(
        symbol="TEST/USDT", timeframe="15m", direction=direction,
        pivot_indices=[0, 10, 20, 30, 40, 95],
        pivot_timestamps=[pd.Timestamp("2026-01-01", tz="UTC")] * 6,
        pivot_prices=P,
        validation_result=_StubValidation(),
        detected_at=pd.Timestamp("2026-01-01", tz="UTC"),
    )


def make_scalp_setup():
    """هندسة سكالبينج واقعية (بُنيت لـFE1.9.16): دخول ≈100.0، وقف ≈97.2 (2.8% —
    تحت سقف 3.5%)، درجة W5 = P4+W1 = 102.203 → rr_net ≈ 0.71 (فوق أرضية 0.6)،
    P5=101.0 وlast_close=100.3 (مطاردة 0.3%، الهدف فوق max(close,P5))."""
    from engine.pattern_detector import DetectedSetup
    P = [97.297, 101.0, 98.6, 100.865, 98.5, 101.0]
    return DetectedSetup(
        symbol="TEST/USDT", timeframe="15m", direction="BULLISH",
        pivot_indices=[0, 10, 20, 30, 40, 95],
        pivot_timestamps=[pd.Timestamp("2026-01-01", tz="UTC")] * 6,
        pivot_prices=P,
        validation_result=_StubValidation(),
        detected_at=pd.Timestamp("2026-01-01", tz="UTC"),
    )


def insert_sig(status="open", is_real=0, fill=100.0, sl=95.0, tp=120.0, qty=10.0,
               entry=106.0, order_id=None, meta_json=None, symbol="TEST/USDT"):
    vnz.db.execute(
        "INSERT INTO signals (symbol, direction, strategy_name, status, entry_price, stop_loss,"
        " take_profit, quantity, notional_usdt, fill_price, created_at, is_real, order_id, meta_json, pivots_json)"
        " VALUES (%s,%s,'Elliott_Fibonacci',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (symbol, "BULLISH", status, entry, sl, tp, qty, qty * fill, fill,
         vnz.utc_now_iso(), is_real, order_id, meta_json, '{"P0": 90.0}'),
    )
    return vnz.db.query("SELECT * FROM signals ORDER BY id DESC LIMIT 1", one=True)


def set_tp1(sig_id: int, tp1: float):
    vnz.db.execute("UPDATE signals SET tp1=%s WHERE id=%s", (tp1, sig_id))
    return vnz.db.query("SELECT * FROM signals WHERE id=%s", (sig_id,), one=True)


@pytest.fixture()
def clean_db(tmp_path, monkeypatch):
    """قاعدة SQLite مؤقتة لكل اختبار — نفس عقد test_fe100."""
    monkeypatch.setattr(vnz, "USE_POSTGRES", False)
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    old = vnz.db.conn
    vnz.db.conn = conn
    vnz.init_db()
    vnz.set_paper_balance(vnz.PAPER_BALANCE_START)
    yield vnz.db
    vnz.db.conn = old


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 1 — الثوابت الإنتاجية الجديدة (بلا تخفيف conftest)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.production_gates
class TestProductionDefaults:

    def test_big_loss_shield_constants(self):
        # [FE1.9.14] درع الخسارة الكبيرة — القيم الإنتاجية الحقيقية
        assert vnz.RR_NET_MIN == 0.6, "أرضية R:R الصافي 0.6"
        assert vnz.MAX_STOP_PCT == 3.5, "سقف عرض الوقف البنيوي 3.5%"
        assert vnz.BE_TP1_FRACTION == 0.7, "التريغر التكيفي 0.7 من مسافة TP1"
        assert vnz.RISK_PCT_PER_TRADE == 0.7, "مخاطرة الصفقة 0.7% بدل 1%"
        assert vnz.DAILY_LOSS_LIMIT_PCT == 3.0, "حد الخسارة اليومي 3% بدل 5%"
        assert vnz.MAX_CONSEC_LOSSES == 2, "متتاليتان تكفيان للتبريد"

    def test_untouched_core_constants(self):
        # كشف الموجات والبوابات الأقدم لم تُمس
        assert vnz.BE_TRIGGER_R == 1.0
        assert vnz.TP_MIN_RR == 0.5
        assert vnz.MAX_ENTRY_DISTANCE_PCT == 1.5
        assert vnz.MAX_STRUCTURE_AGE_BARS == 36
        assert vnz.SYMBOL_COOLDOWN_SEC == 5400
        assert vnz.CLUSTER_MAX_SAME_DIRECTION == 3
        assert vnz.PENDING_MAX_CANDLES == 6
        assert vnz.PAPER_MAX_POSITION_PCT == 30.0


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 2 — بوابة سقف عرض الوقف البنيوي
# ─────────────────────────────────────────────────────────────────────────────

class TestWideStopGate:
    """بدون علامة production_gates: conftest يخفض MAX_STOP_PCT=0 — نثبت أن
    التعطيل يُبقي السلوك القديم حرفيًا، ثم نختبر البوابة بقيم إنتاجية صريحة."""

    def test_gate_disabled_keeps_legacy_behavior(self, clean_db):
        # MAX_STOP_PCT=0 (تخفيف conftest) + أرضية 0.3 → هندسة test_fe180 تمر كما كانت
        assert vnz.create_pending_signal("TEST/USDT", make_setup(), last_close=110.0) is True

    @pytest.mark.production_gates
    def test_wide_stop_rejected_with_counter_and_reason(self, clean_db, monkeypatch):
        monkeypatch.setattr(vnz, "MAX_STOP_PCT", 3.5)
        before = vnz.scan_stats["rejected_wide_stop"]
        # وقف 17.7% من الدخول — بنية إليوتية سليمة لكنها ليست سكالبينج
        assert vnz.create_pending_signal("TEST/USDT", make_setup(), last_close=110.0) is False
        assert vnz.scan_stats["rejected_wide_stop"] == before + 1
        reason = vnz._reject_reason.get("TEST/USDT", "")
        assert "سقف السكالبينج" in reason
        assert "أعرض" in reason

    @pytest.mark.production_gates
    def test_scalp_geometry_passes_production_gates(self, clean_db):
        # وقف 2.8% + rr_net 0.75 — هندسة سكالبينج حقيقية تعبر كل بوابات الدرع
        before_ws = vnz.scan_stats["rejected_wide_stop"]
        before_rr = vnz.scan_stats["rejected_rr_net"]
        assert vnz.create_pending_signal("TEST/USDT", make_scalp_setup(), last_close=100.3) is True
        assert vnz.scan_stats["rejected_wide_stop"] == before_ws
        assert vnz.scan_stats["rejected_rr_net"] == before_rr
        row = vnz.db.query("SELECT * FROM signals ORDER BY id DESC LIMIT 1", one=True)
        assert row["status"] == "pending"
        entry = float(row["entry_price"])
        sl = float(row["stop_loss"])
        tp = float(row["take_profit"])
        assert (entry - sl) / entry <= 0.035, "الوقف داخل سقف السكالبينج"
        assert vnz.rr_net_value(entry, sl, tp) >= 0.6, "المكافأة الصافية فوق الأرضية"

    @pytest.mark.production_gates
    def test_stop_cap_boundary_lowered(self, clean_db, monkeypatch):
        # نفس هندسة السكالبينج (وقف 2.8%) مع سقف أدنى 2.0% → تُرفض
        monkeypatch.setattr(vnz, "MAX_STOP_PCT", 2.0)
        before = vnz.scan_stats["rejected_wide_stop"]
        assert vnz.create_pending_signal("TEST/USDT", make_scalp_setup(), last_close=100.3) is False
        assert vnz.scan_stats["rejected_wide_stop"] == before + 1

    @pytest.mark.production_gates
    def test_gate_disabled_via_zero_even_in_production(self, clean_db, monkeypatch):
        monkeypatch.setattr(vnz, "MAX_STOP_PCT", 0.0)
        monkeypatch.setattr(vnz, "RR_NET_MIN", 0.3)  # نعزل بوابة R:R — نختبر عرض الوقف وحده
        assert vnz.create_pending_signal("TEST/USDT", make_setup(), last_close=110.0) is True


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 3 — التريغر التكيفي للحماية (أهداف دون 1R)
# ─────────────────────────────────────────────────────────────────────────────

class TestAdaptiveProtection:

    def test_sub_1r_plan_protected_at_tp1_fraction(self, clean_db):
        # tp1 = 104 (0.8R) → eff = 0.7×0.8 = 0.56 → التريغر = 100 + 5×0.56 = 102.8
        sig = set_tp1(insert_sig(fill=100.0, sl=95.0, tp=104.0, qty=10.0)["id"], 104.0)
        bal0 = vnz.get_paper_balance()
        vnz._protection_step(sig, 102.9)  # الشمعة لمست 102.9 > التريغر 102.8
        row = vnz.db.query("SELECT * FROM signals WHERE id=%s", (sig["id"],), one=True)
        meta = json.loads(row["meta_json"] or "{}")
        assert float(row["stop_loss"]) == 100.0, "BE نُقل للدخول عند التريغر التكيفي"
        assert meta.get("be_done") is True and meta.get("partial_done") is True
        assert float(row["quantity"]) == 5.0
        # ربح الرجل: 5×(102.8−100) − رسوم (500+514)×0.001 = 14 − 1.014 = 12.986
        assert abs(float(row["realized_pnl_usdt"]) - 12.986) < 1e-6
        assert abs(vnz.get_paper_balance() - bal0 - 12.986) < 1e-6

    def test_sub_1r_no_fire_below_trigger(self, clean_db):
        sig = set_tp1(insert_sig(fill=100.0, sl=95.0, tp=104.0, qty=10.0)["id"], 104.0)
        vnz._protection_step(sig, 102.7)  # تحت التريغر 102.8
        row = vnz.db.query("SELECT * FROM signals WHERE id=%s", (sig["id"],), one=True)
        meta = json.loads(row["meta_json"] or "{}")
        assert float(row["stop_loss"]) == 95.0, "لا حماية قبل التريغر التكيفي"
        assert not meta.get("be_done") and not meta.get("partial_done")
        assert float(row["quantity"]) == 10.0

    def test_above_1r_plan_stays_at_1R(self, clean_db):
        # tp1 = 120 (4R) → eff يبقى 1.0 — التريغر 105 كما في FE1.8.0 حرفيًا
        sig = set_tp1(insert_sig(fill=100.0, sl=95.0, tp=120.0, qty=10.0)["id"], 120.0)
        vnz._protection_step(sig, 104.9)  # تحت 105 — لا شيء
        row = vnz.db.query("SELECT * FROM signals WHERE id=%s", (sig["id"],), one=True)
        assert float(row["stop_loss"]) == 95.0 and float(row["quantity"]) == 10.0
        vnz._protection_step(sig, 105.5)  # لمست +1R
        row = vnz.db.query("SELECT * FROM signals WHERE id=%s", (sig["id"],), one=True)
        meta = json.loads(row["meta_json"] or "{}")
        assert float(row["stop_loss"]) == 100.0
        assert meta.get("be_done") is True
        # جزئي عند 105: 5×5 − (500+525)×0.001 = 23.975 (نفس رقم FE1.8.0)
        assert abs(float(row["realized_pnl_usdt"]) - 23.975) < 1e-6

    def test_floor_03r_for_very_tight_plans(self, clean_db):
        # tp1 = 101.75 (0.35R) → 0.7×0.35 = 0.245 < أرضية 0.3 → eff = 0.3 → تريغر 101.5
        sig = set_tp1(insert_sig(fill=100.0, sl=95.0, tp=101.75, qty=10.0)["id"], 101.75)
        vnz._protection_step(sig, 101.55)
        row = vnz.db.query("SELECT * FROM signals WHERE id=%s", (sig["id"],), one=True)
        meta = json.loads(row["meta_json"] or "{}")
        assert float(row["stop_loss"]) == 100.0 and meta.get("be_done") is True
        assert float(row["quantity"]) == 5.0
        # 5×1.5 − (500+507.5)×0.001 = 7.5 − 1.0075 = 6.4925
        assert abs(float(row["realized_pnl_usdt"]) - 6.4925) < 1e-6

    def test_fraction_zero_disables_adaptation(self, clean_db, monkeypatch):
        # BE_TP1_FRACTION=0 → التريغر يعود +1R حرفيًا حتى مع هدف دون 1R
        monkeypatch.setattr(vnz, "BE_TP1_FRACTION", 0.0)
        sig = set_tp1(insert_sig(fill=100.0, sl=95.0, tp=104.0, qty=10.0)["id"], 104.0)
        vnz._protection_step(sig, 103.0)  # فوق التريغر التكيفي لكن تحت +1R
        row = vnz.db.query("SELECT * FROM signals WHERE id=%s", (sig["id"],), one=True)
        meta = json.loads(row["meta_json"] or "{}")
        assert float(row["stop_loss"]) == 95.0
        assert not meta.get("be_done") and not meta.get("partial_done")

    def test_missing_tp1_falls_back_to_take_profit(self, clean_db):
        # صفقات قبل FE1.9.9 بلا عمود tp1 → take_profit هو المرجع
        sig = insert_sig(fill=100.0, sl=95.0, tp=102.8, qty=10.0)  # 0.56R
        vnz._protection_step(sig, 102.9)  # 0.7×0.56 = 0.392 → تريغر 101.96
        row = vnz.db.query("SELECT * FROM signals WHERE id=%s", (sig["id"],), one=True)
        meta = json.loads(row["meta_json"] or "{}")
        assert meta.get("be_done") is True, "الرجوع لtake_profit حيّ الحماية"


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 4 — حدود اليوم المشددة
# ─────────────────────────────────────────────────────────────────────────────

class TestTightenedDayLimits:

    def test_two_consecutive_losses_pause_entries(self, clean_db):
        # سقف افتراضي 2 [FE1.9.14]: وقفان كاملان → تبريد فوري
        for _ in range(2):
            sig = insert_sig(fill=100.0, sl=95.0, tp=120.0, qty=10.0)
            vnz.close_signal_row(sig, 95.0, "وقف اختباري")
        snap = vnz.risk_snapshot()
        assert snap["loss_streak"] == 2
        assert snap["pause_until"], "وقفان متتاليان يجب أن يفعّلا التبريد"

    def test_daily_limit_3pct_blocks(self, clean_db):
        # -310$ على أساس 10000 = 3.1% > السقف 3% → منع الإشارات الجديدة
        vnz.db_set_state("risk_day", vnz._utc_day())
        vnz.db_set_state("risk_realized", "-310.0")
        vnz.db_set_state("risk_day_base", "10000.0")
        vnz.db_set_state("risk_streak", "0")
        vnz.db_set_state("risk_pause_until", "")
        before = vnz.scan_stats["rejected_daily_loss"]
        assert vnz.create_pending_signal("TEST/USDT", make_setup(), last_close=110.0) is False
        assert vnz.scan_stats["rejected_daily_loss"] == before + 1

    def test_daily_below_3pct_allows(self, clean_db):
        vnz.db_set_state("risk_day", vnz._utc_day())
        vnz.db_set_state("risk_realized", "-290.0")  # 2.9% < 3%
        vnz.db_set_state("risk_day_base", "10000.0")
        vnz.db_set_state("risk_streak", "0")
        vnz.db_set_state("risk_pause_until", "")
        assert vnz.create_pending_signal("TEST/USDT", make_setup(), last_close=110.0) is True


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 5 — تزامن اللوحة والإصدار وrender.yaml
# ─────────────────────────────────────────────────────────────────────────────

class TestPanelAndDeploymentSync:

    def test_version_sync(self):
        assert vnz.BOT_VERSION == "FE1.9.17"
        assert panel.BOT_VERSION == "FE1.9.17"

    def test_panel_gate_chip_present(self):
        src = panel.PANEL_HTML
        assert "rejected_wide_stop" in src
        assert "وقف أعرض من السقف" in src

    def test_render_yaml_pins_shield_values(self):
        with open("render.yaml", encoding="utf-8") as f:
            content = f.read()
        for key, val in [("RISK_PCT_PER_TRADE", '"0.7"'), ("RR_NET_MIN", '"0.6"'),
                         ("MAX_STOP_PCT", '"3.5"'), ("BE_TP1_FRACTION", '"0.7"'),
                         ("DAILY_LOSS_LIMIT_PCT", '"3.0"'), ("MAX_CONSEC_LOSSES", '"2"')]:
            assert f'{key}\n        value: {val}' in content, f"تثبيت {key}={val} مفقود"

    @pytest.mark.production_gates
    def test_api_all_exposes_protection_echo(self, clean_db):
        client = vnz.app.test_client()
        body = client.get("/api/all").get_json()
        prot = body["protection"]
        assert prot["max_stop_pct"] == 3.5
        assert prot["be_trigger_r"] == 1.0
        assert prot["be_tp1_fraction"] == 0.7
        assert prot["rr_net_min"] == 0.6
        # العداد الجديد ضمن الإحصاءات
        assert "rejected_wide_stop" in body["stats"]
