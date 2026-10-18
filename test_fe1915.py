#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات FE1.9.16 «الشارت النظيف في نافذة عائمة»
====================================================
الطلب: «شارت العملات لا يضهر اي بيانات سوى العملات التي دخلت طابور الانتضار
لسعر الدخول او المفتوحة وكذلك قم بتنضيف الشارت من بيانات الموجات الذي يفسد
الرؤية اترك المهم فقط ... وكذلك اجعل الشارت يفتح في نافذة عائمة عند الطلب
مع زر اغلاق للنافذة».

ما يُغطيه الملف:
  1) /api/all يكشف watchlist كاملة — قائمة رموز الشارت تُعبأ منها فتظهر
     بيانات كل عملات المراقبة لا الصفقات وحدها
  2) النافذة العائمة: markup كامل + openChartModal/closeChartModal + زر ✕
     + Esc + الخلفية + زر 🕯 في الهيدر + chartFocus يفتح النافذة
  3) تنضيف الشارت: EWX مطفأة افتراضيًا + صفر مفاتيح فيبو في JS العرض
  4) بوابة النبض: chartTick لا يعمل والنافذة مغلقة
  5) تزامن الإصدار
"""

import sqlite3

import pytest

import vnz
vnz.DASHBOARD_PROTECTED = False  # بيئة الاختبار: بلا مصادقة
import panel


# ─────────────────────────────────────────────────────────────────────────────
# أدوات
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def clean_db(monkeypatch):
    """قاعدة SQLite مؤقتة لكل اختبار — عزل كامل (نفس نمط test_fe1912)."""
    monkeypatch.setattr(vnz, "USE_POSTGRES", False)
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    old = vnz.db.conn
    vnz.db.conn = conn
    vnz.init_db()
    yield
    vnz.db.conn = old


def client():
    return vnz.app.test_client()


# ─────────────────────────────────────────────────────────────────────────────
# 1) watchlist في /api/all — «الشارت لا يعرض بيانات» يُحل من المصدر
# ─────────────────────────────────────────────────────────────────────────────

def test_api_all_exposes_watchlist(clean_db, monkeypatch):
    monkeypatch.setattr(vnz, "watchlist", ["AAA/USDT", "BBB/USDT", "CCC/USDT"])
    body = client().get("/api/all").get_json()
    assert body["watchlist"] == ["AAA/USDT", "BBB/USDT", "CCC/USDT"]


def test_api_all_watchlist_is_list_of_strings(clean_db, monkeypatch):
    monkeypatch.setattr(vnz, "watchlist", ["X/USDT"])
    body = client().get("/api/all").get_json()
    assert isinstance(body["watchlist"], list)
    assert all(isinstance(s, str) for s in body["watchlist"])


def test_panel_chart_populate_uses_watchlist_first():
    """قائمة الرموز تُعبأ من watchlist أولًا ثم الصفقات — كل عملات المراقبة ظاهرة."""
    html = panel.PANEL_HTML
    fn_pos = html.find("function chartPopulate(")
    assert fn_pos != -1, "chartPopulate موجودة"
    body = html[fn_pos:html.find("}", html.find("if(!chartSym) chartSym = syms[0];"))]
    watch_pos = body.find("(s.watchlist||[])")
    open_pos = body.find("(s.open_signals||[])")
    assert watch_pos != -1, "chartPopulate يقرأ watchlist"
    assert open_pos != -1 and watch_pos < open_pos, "watchlist قبل الصفقات في الترتيب"


# ─────────────────────────────────────────────────────────────────────────────
# 2) النافذة العائمة — تفتح عند الطلب وتغلق بزر ✕/Esc/الخلفية
# ─────────────────────────────────────────────────────────────────────────────

def test_panel_has_floating_chart_modal_markup():
    html = panel.PANEL_HTML
    assert 'id="chart-modal"' in html, "حاوية النافذة العائمة"
    assert 'role="dialog"' in html and 'aria-modal="true"' in html
    assert 'class="cmodal-backdrop" onclick="closeChartModal()"' in html, "نقر الخلفية يغلق"
    assert 'class="cmodal-close" onclick="closeChartModal()"' in html, "زر الإغلاق ✕"
    assert 'id="lwc-chart"' in html and 'id="chart-sym"' in html, "الشارت والقائمة داخل النافذة"
    assert html.count('id="chart-sym"') == 1, "قائمة واحدة داخل النافذة (لا نسخة مضمّنة قديمة)"


def test_panel_modal_open_close_functions():
    html = panel.PANEL_HTML
    assert "function openChartModal(" in html and "function closeChartModal(" in html
    assert "CHART_OPEN = true" in html and "CHART_OPEN = false" in html
    assert "document.body.style.overflow" in html, "قفل تمرير الصفحة خلف النافذة"
    assert "(e.key==='Escape'||e.key==='Esc')" in html, "Esc يغلق النافذة"


def test_panel_header_chart_button_and_focus():
    html = panel.PANEL_HTML
    assert 'onclick="openChartModal()"' in html, "زر 🕯 الشارت في الهيدر"
    assert "function chartFocus(sym){\n  openChartModal(sym);\n}" in html, \
        "نقر رمز أي صفقة يفتح النافذة على الرمز"


def test_chart_tick_gated_when_modal_closed():
    """بوابة النبض: لا جلب شموع والنافذة مغلقة (صفر طلبات)."""
    html = panel.PANEL_HTML
    tick_pos = html.find("async function chartTick(")
    assert tick_pos != -1
    body = html[tick_pos:tick_pos + 400]
    assert "if(!CHART_OPEN) return;" in body, "chartTick محبوَس داخل النافذة المفتوحة"
    init_pos = html.find("function chartInit(")
    assert "if(CHART || window.__LWC_FAILED || !CHART_OPEN) return;" in \
        html[init_pos:init_pos + 200], "chartInit داخل النافذة المفتوحة فقط"


def test_chart_height_follows_viewport():
    """الشارت داخل النافذة أكبر: حتى 58% من ارتفاع الشاشة (300..520px)."""
    html = panel.PANEL_HTML
    assert "function chartH()" in html
    assert "window.innerHeight" in html
    assert "height: chartH()" in html, "chartInit وapplyOptions يستخدمان chartH"


# ─────────────────────────────────────────────────────────────────────────────
# 3) تنضيف الشارت — طبقة المحرك اختيارية مطفأة وبلا مفاتيح فيبو مزعجة
# ─────────────────────────────────────────────────────────────────────────────

def test_engine_wave_layer_optional_default_off():
    html = panel.PANEL_HTML
    assert 'id="ewx-toggle"' in html, "زر موجات المحرك باقٍ (طريقة الاستراتيجية)"
    seg = html.split('id="ewx-toggle"')[1][:120]
    assert "checked" not in seg, "مطفأة افتراضيًا — الشارت نظيف عند الفتح"
    assert "let EWX_ON = false" in html
    assert "ewxToggle()" in html and "/api/ew_strategy" in html
    assert 'id="ewx-note"' in html and "EWX_MARKS" in html


def test_no_fib_keys_in_chart_rendering():
    """مفاتيح فيبو W2/W4/W3 المنقّطة (8 خطوط) حُذفت من JS العرض — كانت تفسد الرؤية."""
    html = panel.PANEL_HTML
    for bad in ("w2_zone", "w4_zone", "w3_ext", "fib_overlays",
                "#c792ea", "#64d8cb", "#8a6bb8", "مفاتيح W4", "مفاتيح فيبو W2/W3"):
        assert bad not in html, f"بقايا مفاتيح فيبو في العرض: {bad}"


def test_trade_lines_still_drawn_the_essential():
    """«اترك المهم فقط»: خطوط الصفقة (دخول/وقف/أهداف/سقف) وعلامات الملء/الغلق باقية."""
    html = panel.PANEL_HTML
    assert "function chartApplyOverlays()" in html
    assert "دخول" in html and "وقف" in html and "هدف " in html and "سقف أسبوع" in html
    assert "'ملء'" in html and "'ربح':'خسارة'" in html


# ─────────────────────────────────────────────────────────────────────────────
# 4) تزامن الإصدار
# ─────────────────────────────────────────────────────────────────────────────

def test_version_sync_vnz_panel():
    assert vnz.BOT_VERSION == "FE1.9.18"
    assert panel.BOT_VERSION == "FE1.9.18"
    assert panel.BOT_VERSION == vnz.BOT_VERSION
