"""اختبارات FE1.10.2 «اقتباسات flowsurface»: التراجع الأُسّي لكتم التلغرام + ملحق التجميع
(نمط notify.rs) وشارة النضارة وعدّاد إغلاق الشمعة في اللوحة (نمط DataFreshness/kline.rs).
صفر مساس بالبوابات أو الحجز الذري أو منطق التداول."""
import time
import pytest

import vnz


@pytest.fixture()
def _clean_tg_dedup():
    """عزل خريطة الكتم بين الاختبارات + إرجاع الثوابت الافتراضية."""
    vnz._tg_dedup.clear()
    old = (vnz.TELEGRAM_DEDUP_SEC, vnz.TG_DEDUP_MAX_SEC, vnz.TG_BACKOFF_TRIGGER, vnz.TG_BACKOFF_LEVELS)
    vnz.TELEGRAM_DEDUP_SEC = 300
    vnz.TG_DEDUP_MAX_SEC = 1800
    vnz.TG_BACKOFF_TRIGGER = 3
    vnz.TG_BACKOFF_LEVELS = 3
    yield
    vnz._tg_dedup.clear()
    (vnz.TELEGRAM_DEDUP_SEC, vnz.TG_DEDUP_MAX_SEC, vnz.TG_BACKOFF_TRIGGER, vnz.TG_BACKOFF_LEVELS) = old


class TestTgExponentialBackoff:
    """التراجع الأُسّي: أول ظهور يمر، والتكرار المكبوت يُصعّد، والهدوء يخفّف."""

    def test_first_seen_passes(self, _clean_tg_dedup):
        assert vnz._tg_dedup_ok("خطأ تجريبي واحد") is True

    def test_repeat_within_window_suppressed(self, _clean_tg_dedup):
        msg = "رسالة مكررة داخل النافذة"
        assert vnz._tg_dedup_ok(msg) is True
        assert vnz._tg_dedup_ok(msg) is False
        assert vnz._tg_dedup_ok(msg) is False

    def test_suppression_counter_grows(self, _clean_tg_dedup):
        msg = "عدّاد الكتم"
        vnz._tg_dedup_ok(msg)
        vnz._tg_dedup_ok(msg)
        vnz._tg_dedup_ok(msg)
        st = vnz._tg_dedup[msg]
        assert st["suppressed"] == 2.0

    def test_escalation_after_trigger(self, _clean_tg_dedup):
        """3 كتمات ثم انتهاء النافذة → المستوى يصعد والنافذة تتضاعف."""
        msg = "نمط يتصاعد"
        vnz._tg_dedup_ok(msg)          # أول ظهور
        st = vnz._tg_dedup[msg]
        st["last"] -= 301              # إخراج النداء من النافذة يدويًا
        vnz._tg_dedup_ok(msg)          # مُسموح — بلا كتمات → لا تصعيد
        assert st["level"] == 0.0
        for _ in range(3):             # 3 كتمات داخل النافذة
            assert vnz._tg_dedup_ok(msg) is False
        st["last"] -= 301
        assert vnz._tg_dedup_ok(msg) is True
        assert st["level"] == 1.0      # صُعّد مرة واحدة
        assert st["note"] == 3.0       # ملحق التجميع مُثبت

    def test_escalation_window_doubles(self, _clean_tg_dedup):
        """المستوى 1 يعني نافذة 600ث (2× الأساس)."""
        msg = "نافذة متضاعفة"
        st = vnz._tg_dedup.setdefault(msg, {"last": time.time(), "level": 1.0,
                                            "suppressed": 0.0, "note": 0.0})
        # داخل 600ث لكن خارج 300 → يجب أن يُكتم (النافذة الفعلية تضاعفت)
        st["last"] -= 400
        assert vnz._tg_dedup_ok(msg) is False

    def test_escalation_cap(self, _clean_tg_dedup):
        """المستوى محصور بـ TG_BACKOFF_LEVELS والنافذة بـ TG_DEDUP_MAX_SEC."""
        msg = "السقف"
        vnz._tg_dedup[msg] = {"last": time.time() - 2000, "level": 3.0,
                              "suppressed": 10.0, "note": 0.0}
        assert vnz._tg_dedup_ok(msg) is True
        st = vnz._tg_dedup[msg]
        assert st["level"] == 3.0  # لا يتجاوز السقف

    def test_quiet_decay_downgrades(self, _clean_tg_dedup):
        """هدوء النمط (كتمات قليلة) يخفض المستوى تدريجيًا."""
        msg = "هدوء يخفف"
        vnz._tg_dedup[msg] = {"last": time.time() - 2000, "level": 2.0,
                              "suppressed": 0.0, "note": 0.0}
        assert vnz._tg_dedup_ok(msg) is True
        assert vnz._tg_dedup[msg]["level"] == 1.0

    def test_disabled_by_zero(self, _clean_tg_dedup):
        """TELEGRAM_DEDUP_SEC=0 يعطل الكتم كليًا كما كان."""
        vnz.TELEGRAM_DEDUP_SEC = 0
        msg = "تعطيل بالصفر"
        assert vnz._tg_dedup_ok(msg) is True
        assert vnz._tg_dedup_ok(msg) is True

    def test_distinct_messages_independent(self, _clean_tg_dedup):
        assert vnz._tg_dedup_ok("رسالة أ") is True
        assert vnz._tg_dedup_ok("رسالة ب") is True
        assert vnz._tg_dedup_ok("رسالة أ") is False

    def test_tg_note_appended_only_when_pattern(self, _clean_tg_dedup):
        msg = "ملحق التجميع"
        assert vnz._tg_note(msg) == ""  # بلا نمط
        vnz._tg_dedup[msg] = {"last": time.time(), "level": 1.0,
                              "suppressed": 0.0, "note": 5.0}
        out = vnz._tg_note(msg)
        assert "5" in out and "نمط متكرر" in out

    def test_full_chain_aggregation_note_reaches_telegram(self, _clean_tg_dedup, monkeypatch):
        """log_and_notify يرسل النص + الملحق إلى التلغرام فقط، والسجل خام."""
        sent = []
        monkeypatch.setattr(vnz, "send_telegram_message", lambda m: sent.append(m))
        monkeypatch.setattr(vnz, "telegram_gate", lambda t: True)
        monkeypatch.setattr(vnz, "tg_claim_once", lambda k: True)
        monkeypatch.setattr(vnz, "_panel_dedup_ok", lambda m: True)
        msg = "بلاغ متكرر يغرق المحادثة"
        vnz.log_and_notify("warning", msg, ntype="BINANCE_CONN")
        assert len(sent) == 1 and sent[0] == msg          # أول ظهور خام
        # نمط مكبوت: كتمات كثيرة ثم انتهاء النافذة
        for _ in range(4):
            vnz._tg_dedup_ok(msg)
        vnz._tg_dedup[msg]["last"] -= 301
        vnz.log_and_notify("warning", msg, ntype="BINANCE_CONN")
        assert len(sent) == 2
        assert "نمط متكرر" in sent[1] and sent[1].startswith(msg)


class TestPanelFreshnessBadge:
    """شارة النضارة وعدّاد الشمعة في اللوحة — عناصر ووظيفة العدّاد."""

    @pytest.fixture()
    def panel_src(self):
        with open("panel.py", "r", encoding="utf-8") as f:
            return f.read()

    def test_fresh_badge_function_exists(self, panel_src):
        assert "function chartFreshTick()" in panel_src
        assert "setInterval(chartFreshTick, 1000)" in panel_src

    def test_fresh_badge_states(self, panel_src):
        assert "حية ·" in panel_src and "مؤقت · حدّثت" in panel_src

    def test_countdown_present(self, panel_src):
        assert "إغلاق الشمعة خلال" in panel_src

    def test_fresh_span_injected_in_chart_note(self, panel_src):
        assert 'id="chart-fresh"' in panel_src

    def test_tf_seconds_map(self, panel_src):
        assert "TFSEC_MAP" in panel_src and "'5m':300" in panel_src and "'1h':3600" in panel_src

    def test_zero_requests_added(self, panel_src):
        """العدّاد قراءة من الذاكرة حصرًا — لا fetch جديدة داخل chartFreshTick."""
        seg = panel_src.split("function chartFreshTick()")[1].split("setInterval")[0]
        assert "api(" not in seg and "fetch(" not in seg

    def test_gate_on_closed_modal(self, panel_src):
        """العدّاد صامت والنافذة مغلقة (بوابة CHART_OPEN)."""
        seg = panel_src.split("function chartFreshTick()")[1].split("setInterval")[0]
        assert "CHART_OPEN" in seg

    def test_version_synced(self, panel_src):
        assert 'BOT_VERSION = "FE1.10.2"' in panel_src


class TestVersionSync:
    def test_vnz_version(self):
        assert vnz.BOT_VERSION == "FE1.10.2"

    def test_env_defaults_exist(self):
        assert vnz.TG_DEDUP_MAX_SEC == 1800
        assert vnz.TG_BACKOFF_TRIGGER == 3
        assert vnz.TG_BACKOFF_LEVELS == 3
