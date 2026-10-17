# -*- coding: utf-8 -*-
"""مصائد مشتركة لكل الاختبارات — [FE1.9.9]
عزل weekly_high عن الشبكة: كل اختبار يجدها تعيد None (fail-open بالمسار التراثي)
ما لم يتجاوزها الاختبار صراحةً بـmonkeypatch الخاص به (يطغى على هذه المصيدة لأنه
يُنفَّذ بعدها بنفس كائن monkeypatch). كاش القمة يُصفَّر قبل وبعد كل اختبار.

[FE1.9.14] درع الخسارة الكبيرة: بوابتا MAX_STOP_PCT (3.5%) وRR_NET_MIN (0.6)
جديدتان على هندسة الفِكسترات التخليقية (دخول 109.27/وقف 89.9 = وقف 17.7% وrr_net
0.345 — صُممت لعهد الأرضية 0.3 وقبل بوابة العرض). لكل اختبار عادي تُخفَّضان هنا
قيمًا اختبارية (0 / 0.3) كي تختبر البوابات الأقدم بنفس هندستها، وأي اختبار يريد
القيم الإنتاجية الحقيقية (اختبارات الدرع نفسها وحدود الثوابت) يعلّم نفسه
@pytest.mark.production_gates فيتخطى هذه المصيدة."""

import pytest


@pytest.fixture(autouse=True)
def _isolate_weekly_high(monkeypatch):
    import vnz
    vnz._tp_week_cache.clear()
    monkeypatch.setattr(vnz, "weekly_high", lambda symbol: None)
    yield
    vnz._tp_week_cache.clear()


@pytest.fixture(autouse=True)
def _fe1914_test_gates(request, monkeypatch):
    """[FE1.9.14] تخفيف بوابتَي عرض الوقف وR:R الصافي للهندسة التخليقية —
    اختبارات production_gates وحدها ترى القيم الإنتاجية."""
    if request.node.get_closest_marker("production_gates"):
        return
    import vnz
    monkeypatch.setattr(vnz, "MAX_STOP_PCT", 0.0)
    monkeypatch.setattr(vnz, "RR_NET_MIN", 0.3)


@pytest.fixture(autouse=True)
def _isolate_kline_fill(monkeypatch):
    """[FE1.9.16] عزل مسار جلب الشموع عند الطلب عن الشبكة: كل اختبار يجد الملء
    معطّلًا والتحديث الخلفي مطفأ — اختبارات FE1.9.16 تتجاوزه صراحة بـmonkeypatch
    الخاص بها (يُنفَّذ بعد هذه المصيدة فتطغى عليها بنفس كائن monkeypatch)."""
    import vnz
    monkeypatch.setattr(vnz, "KLINE_BG_REFRESH", False)
    monkeypatch.setattr(vnz, "_klines_fetch_fill",
                        lambda symbol, tf, limit, wait=True: (None, None, "cooldown"))
    yield
