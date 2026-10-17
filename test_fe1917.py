# -*- coding: utf-8 -*-
"""[FE1.9.17] المعايرة الزمنية للفريم 5m — اختبارات الإصلاح الجذري لبلاغ «لا صفقات».

الجذر: الثابتان الشريطيان (سقف عمر البنية 36 شمعة / صلاحية المعلق 6 شموع) عُيّرا
زمنيًا على فريم 15m (9 ساعات / 1.5 ساعة) وتشغيل الكشف على 5m قطع الميزانيتين
ثلاث مرات بصمت (3 ساعات / 30 دقيقة) — فقتل البنى لحظة صلاحيتها بالضبط.
العقد الجديد: الميزانية بالساعات والاشتقاق زمني ديناميكي على الفريم الحي.
"""

import pytest

import vnz


@pytest.fixture()
def _restore_bars():
    """يحفظ الثوابت الشريطية والفريم ويعيدها بعد كل اختبار — عزل تام بين الاختبارات."""
    tf = vnz.SIGNAL_TIMEFRAME
    age, pend = vnz.MAX_STRUCTURE_AGE_BARS, vnz.PENDING_MAX_CANDLES
    hours, life = vnz.MAX_STRUCTURE_AGE_HOURS, vnz.PENDING_LIFETIME_HOURS
    yield
    vnz.SIGNAL_TIMEFRAME = tf
    vnz.MAX_STRUCTURE_AGE_HOURS, vnz.PENDING_LIFETIME_HOURS = hours, life
    vnz.MAX_STRUCTURE_AGE_BARS, vnz.PENDING_MAX_CANDLES = age, pend


class TestTimeBudgetDerivation:
    """الاشتقاق الزمني: الميزانية بالساعات تُترجم إلى شموع على الفريم الحي."""

    def test_default_15m_unchanged(self):
        # الإقلاع الافتراضي 15m = القيم التاريخية حرفيًا (36/6)
        assert vnz.SIGNAL_TIMEFRAME == "15m"
        assert vnz.MAX_STRUCTURE_AGE_BARS == 36
        assert vnz.PENDING_MAX_CANDLES == 6

    @pytest.mark.usefixtures("_restore_bars")
    def test_5m_rescale_preserves_time_budget(self, monkeypatch):
        # قلب الإصلاح: 5m يستعيد الميزانيتين الزمنيتين الأصليتين (9س/1.5س)
        monkeypatch.setattr(vnz, "SIGNAL_TIMEFRAME", "5m")
        vnz._recalibrate_tf_bars()
        assert vnz.MAX_STRUCTURE_AGE_BARS == 108   # 9 ساعات × 12 شمعة/ساعة
        assert vnz.PENDING_MAX_CANDLES == 18       # 1.5 ساعة × 12 شمعة/ساعة
        # الصيغة زمنية: صلاحية المعلق على 5m = 18×300 = 5400ث = 1.5س كما كان على 15m
        assert vnz.PENDING_MAX_CANDLES * vnz.TF_SECONDS["5m"] == 5400
        assert vnz.MAX_STRUCTURE_AGE_BARS * vnz.TF_SECONDS["5m"] == 9 * 3600

    @pytest.mark.usefixtures("_restore_bars")
    def test_hours_env_override(self, monkeypatch):
        # متغيرا الساعات بيئيتان يتجاوزان الميزانية الافتراضية
        monkeypatch.setattr(vnz, "MAX_STRUCTURE_AGE_HOURS", 4.0)
        monkeypatch.setattr(vnz, "PENDING_LIFETIME_HOURS", 0.5)
        vnz._recalibrate_tf_bars()
        assert vnz.MAX_STRUCTURE_AGE_BARS == 16    # 4س × 4 شموع/ساعة (15m)
        assert vnz.PENDING_MAX_CANDLES == 3        # 0.5س = 2 ← أرضية 3

    @pytest.mark.usefixtures("_restore_bars")
    def test_coarse_tf_floors(self, monkeypatch):
        # فريمات خشنة: الأرضيات تمنع الصفر (1h: 9 شمعة عمر / صلاحية 3)
        monkeypatch.setattr(vnz, "SIGNAL_TIMEFRAME", "1h")
        vnz._recalibrate_tf_bars()
        assert vnz.MAX_STRUCTURE_AGE_BARS == 9
        assert vnz.PENDING_MAX_CANDLES == 3
        monkeypatch.setattr(vnz, "SIGNAL_TIMEFRAME", "4h")
        vnz._recalibrate_tf_bars()
        # 9س/4س = 2.25 شمعة ← أرضية العمر 6 تمنع انكماش السقف عن معنى
        assert vnz.MAX_STRUCTURE_AGE_BARS == 6
        assert vnz.PENDING_MAX_CANDLES == 3

    @pytest.mark.usefixtures("_restore_bars")
    def test_structure_fresh_honors_derived_cap(self, monkeypatch):
        # بنية عمرها 50 شمعة: متقادمة على 15m (36) حية على 5m (108)
        df = [{"close": 1.0}] * 101
        p5_idx = 50  # العمر 100-50 = 50

        class _S:  # structure_fresh يقرأ pivot_indices[5] حصرًا
            pivot_indices = {5: p5_idx}

        monkeypatch.setattr(vnz, "SIGNAL_TIMEFRAME", "5m")
        vnz._recalibrate_tf_bars()
        assert vnz.structure_fresh(_S(), df) is True
        monkeypatch.setattr(vnz, "SIGNAL_TIMEFRAME", "15m")
        vnz._recalibrate_tf_bars()
        assert vnz.structure_fresh(_S(), df) is False


class TestRecalibrationWiring:
    """الربط: الاشتقاق يعمل عند الإقلاع والتبديل الحي والاستعادة من قاعدة الحالة."""

    def test_source_calls_at_all_three_sites(self):
        src = open("vnz.py", encoding="utf-8").read()
        # تعريف الدالة + النداء عند الإقلاع (module level)
        assert "def _recalibrate_tf_bars()" in src
        assert "_recalibrate_tf_bars()  # [FE1.9.17] المعايرة عند الإقلاع" in src
        # التبديل الحي من اللوحة (set_signal_timeframe)
        assert "_recalibrate_tf_bars()  # [FE1.9.17] الثوابت الشريطية" in src
        # الاستعادة من قاعدة الحالة (restore_timeframe_flags)
        assert "_recalibrate_tf_bars()  # [FE1.9.17] المعايرة الزمنية على الفريم المستعاد" in src

    def test_old_bar_env_vars_deprecated(self):
        # قيم الشموع القديمة أُهملت عمدًا — قراءة env لها أُزيلت كي لا تُخنق
        # الاشتقاق على 5m إن بقي تثبيت قديم في لوحة Render
        src = open("vnz.py", encoding="utf-8").read()
        assert 'os.getenv("MAX_STRUCTURE_AGE_BARS"' not in src
        assert 'os.getenv("PENDING_MAX_CANDLES"' not in src

    def test_api_all_protection_carries_budgets(self):
        src = open("vnz.py", encoding="utf-8").read()
        for key in ("structure_age_hours", "structure_age_bars",
                    "pending_lifetime_hours", "pending_window_bars"):
            assert f'"{key}"' in src

    def test_expiry_message_uses_derived_value(self):
        # نص انتهاء الصلاحية يعرض عدد الشموع المشتق الفعلي لا رقمًا قديمًا
        src = open("vnz.py", encoding="utf-8").read()
        assert "PENDING_MAX_CANDLES} شموع" in src

    def test_render_yaml_new_semantics(self):
        import pathlib
        y = pathlib.Path("render.yaml").read_text(encoding="utf-8")
        assert "MAX_STRUCTURE_AGE_HOURS" in y and 'value: "9"' in y
        assert "PENDING_LIFETIME_HOURS" in y and 'value: "1.5"' in y
        # التثبيتات الشريطية القديمة أزيلت من مصدر الحقيقة
        assert "- key: MAX_STRUCTURE_AGE_BARS" not in y
        assert "- key: PENDING_MAX_CANDLES" not in y


@pytest.mark.production_gates
class TestProtectedGatesUntouched:
    """صفر مساس بالحمايات التداولية — المعايرة زمنية لا تخفيف جودة."""

    def test_entry_and_cooldown_gates(self):
        assert vnz.MAX_ENTRY_DISTANCE_PCT == 1.5       # لا مطاردة
        assert vnz.SYMBOL_COOLDOWN_SEC == 5400         # لا إعادة إنشاء حرفية
        assert vnz.CLUSTER_MAX_SAME_DIRECTION == 3     # سقف العنقود
        assert vnz.DEEP_RETRACE_BLOCK_PCT == 0.786     # عمق التصحيح

    def test_geometry_gates(self):
        assert vnz.RR_NET_MIN == 0.6                   # أرضية R:R الصافي [FE1.9.14]
        assert vnz.MAX_STOP_PCT == 3.5                 # سقف عرض الوقف [FE1.9.14]
        assert vnz.TP_WEEK_CAP_DAYS == 7               # سقف الأسبوع [FE1.9.9]
        assert vnz.TP_MIN_RR == 0.5                    # تأهيل درجات السلّم

    def test_time_budgets_values(self):
        assert vnz.MAX_STRUCTURE_AGE_HOURS == 9.0      # النية الأصلية لـ36 شمعة
        assert vnz.PENDING_LIFETIME_HOURS == 1.5       # النية الأصلية لـ6 شموع

    def test_premise_alive_untouched(self):
        # بوابة الفرضية الحية دلالتها كما هي: الإغلاق تحت P0 = ميتة
        class _S:
            pivot_prices = {0: 100.0}
        assert vnz.premise_alive(_S(), 100.0) is True
        assert vnz.premise_alive(_S(), 99.9) is False
