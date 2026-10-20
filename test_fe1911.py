#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات FE1.9.16 «الشارت النظيف في نافذة عائمة — إزالة مؤشر LuxAlgo»
==========================================================================
الطلب: «قم بتنضيف الشارت من بيانات الموجات الذي يفسد الرؤية اترك المهم فقط
وازل المؤشر الذي اضفناه الذي يحسب الموجات بطريقة غير طريقة الاستراتيجية».

الجواب المنفَّذ: أُزيل مؤشر Elliott Wave [LuxAlgo] كليًا (كان يحسب الموجات
بأطوال pivothigh ثابتة 4/8/16 لا بطريقة الاستراتيجية): حُذف static/elliott-wave.js
ومسار /ew.js وزر الطبقة ومثيل علاماتها وسطر الإسناد من اللوحة.

ما يُغطيه الملف:
  1) /ew.js لم يعد يُقدَّم (404)
  2) ملف static/elliott-wave.js محذوف من المستودع
  3) اللوحة خالية من أي أثر: الزر/السكربت/الدوال/الأسطورة/الإسناد
  4) طبقة موجات المحرك (طريقة الاستراتيجية) باقية اختيارية عبر /api/ew_strategy
  5) تزامن الإصدار vnz/panel و/health
"""

import os
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
# 1) المسار /ew.js أُزيل
# ─────────────────────────────────────────────────────────────────────────────

def test_ew_js_route_removed(clean_db):
    r = client().get("/ew.js")
    assert r.status_code == 404, "مسار مؤشر LuxAlgo يجب أن يكون ميتًا"


def test_ew_js_route_removed_even_protected(monkeypatch):
    """حتى مع تفعيل حماية اللوحة: المسار غير موجود أصلًا (404 بلا مصادقة أيضًا
    لأن المسار حُذف — لو بقي محميًا لكان 401)."""
    monkeypatch.setattr(vnz, "DASHBOARD_PROTECTED", True)
    r = client().get("/ew.js")
    assert r.status_code == 404


def test_elliott_wave_file_deleted():
    p = os.path.join(os.path.dirname(os.path.abspath(panel.__file__)),
                     "static", "elliott-wave.js")
    assert not os.path.exists(p), "ملف الخوارزمية يجب أن يكون محذوفًا من المستودع"


# ─────────────────────────────────────────────────────────────────────────────
# 2) اللوحة خالية من أي أثر للمؤشر
# ─────────────────────────────────────────────────────────────────────────────

def test_panel_has_no_luxalgo_traces():
    html = panel.PANEL_HTML
    for bad in ("LuxAlgo", "elliott-wave", "/ew.js", "ElliottWaveLux",
                "__EW_FAILED", 'id="ew-toggle"', "ewToggle()", "ewRebuild",
                "ewMaybe", "ewStyleOf", "EW_SERIES", "EW_MARKS",
                'id="ew-note"', 'id="chart-legend-ew"', "CC BY-NC-SA",
                "ZigZag", "زيجزاج 4", "زيجزاج 8", "زيجزاج 16"):
        assert bad not in html, f"أثر متبقٍ لمؤشر LuxAlgo في اللوحة: {bad}"


def test_panel_still_serves_lwc_library():
    """مكتبة الشارت نفسها (Lightweight Charts) باقية — المحذوف مؤشر الموجات فقط."""
    html = panel.PANEL_HTML
    assert '/lwc.js' in html and "window.__LWC_FAILED" in html
    assert "TradingView Lightweight Charts" in html


def test_ew_strategy_endpoint_alive_for_engine_layer(clean_db):
    """طبقة موجات المحرك (طريقة الاستراتيجية) باقية — نقطة /api/ew_strategy تعمل."""
    r = client().get("/api/ew_strategy?symbol=BAD/USDT&tf=5m")
    assert r.status_code == 200
    body = r.get_json()
    assert body["symbol"] == "BAD/USDT" and "zigzag" in body and "setup" in body


# ─────────────────────────────────────────────────────────────────────────────
# 3) تزامن الإصدار
# ─────────────────────────────────────────────────────────────────────────────

def test_version_sync_vnz_panel():
    assert vnz.BOT_VERSION == "FE1.10.2"
    assert panel.BOT_VERSION == "FE1.10.2"
    assert panel.BOT_VERSION == vnz.BOT_VERSION
    h = client().get("/health").get_json()
    assert h["version"] == "FE1.10.2"
