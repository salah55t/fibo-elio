#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_fe140.py — اختبارات التداول الحقيقي + قواعد باينانس + بطاقة الاتصال FE1.4.0

سبع جولات:
  1) قواعد باينانس: دقة الكمية/السعر، أدنى قيمة/كمية، سقف الأمان، رفض الوقف الواسع
  2) بطاقة اتصال باينانس: بلا مفاتيح (فحص عام) / بمفاتيح (رصيد) / فشل / الكاش
  3) زر التداول الحقيقي: رفض بلا مفاتيح / تفعيل بمفاتيح + اتصال / استمرار الحالة / إيقاف
  4) إنشاء إشارة حقيقية: أمر LIMIT وهمي ناجح → is_real=1 + order_id + الرصيد الورقي سليم
  5) مراقبة المعلق الحقيقي: ملء من المنصة (بأسعار التنفيذ) / إبطال بنيوي يلغي الأمر
  6) إغلاق حقيقي: بيع سوق + محاسبة بلا مساس بالرصيد الورقي / الغبار يُغلق محاسبيًا
  7) نقاط API واللوحة: /api/binance/status، /health mode، /api/all يحمل binance،
     الهيكل السبراني (زر حقيقي + بطاقة اتصال + خلفية متحركة) في PANEL_HTML

تشغيل: pytest test_fe140.py -v   (من داخل مجلد المشروع)
"""

import json
import math
import threading

import pytest

import vnz
vnz.DASHBOARD_PROTECTED = False  # بيئة الاختبار: بلا مصادقة (الإنتاج admin/test123)


# ─────────────────────────────────────────────────────────────────────────────
# تجهيزات
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def clean_db(tmp_path, monkeypatch):
    """قاعدة SQLite مؤقتة لكل اختبار — عزل كامل (نمط test_fe100/130)."""
    monkeypatch.setattr(vnz, "USE_POSTGRES", False)
    import sqlite3
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    old = vnz.db.conn
    vnz.db.conn = conn
    vnz.init_db()  # يشمل migrate_db — الأعمدة الحقيقية موجودة
    vnz.set_paper_balance(vnz.PAPER_BALANCE_START)
    yield vnz.db
    vnz.db.conn = old


@pytest.fixture()
def real_reset():
    """حالة التداول الحقيقي وكاش الاتصال نظيفان قبل وبعد كل اختبار."""
    vnz.is_real_mode = False
    with vnz._bin_status_lock:
        vnz._bin_status_cache["ts"] = 0.0
        vnz._bin_status_cache["data"] = None
    yield
    vnz.is_real_mode = False
    with vnz._bin_status_lock:
        vnz._bin_status_cache["ts"] = 0.0
        vnz._bin_status_cache["data"] = None


@pytest.fixture()
def client(clean_db, real_reset):
    return vnz.app.test_client()


class FakeBinance:
    """نسخة تداول وهمية بقواعد باينانس مبسطة (خطوة 0.00001 للكمية و0.01 للسعر).

    markets: BTC/USDT بحدود واقعية (minQty=0.0001، minNotional=10.0)
    سلوك قابل للبرمجة: fill_immediately، sell_fail، cancel_ok...
    """

    def __init__(self, usdt_free=1000.0, base_free=0.0):
        self.usdt_free = usdt_free
        self.base_free = base_free
        self.orders = []
        self.canceled = []
        self._oid = 9000
        self.sell_fail = False
        self.create_fail = False
        self.markets = {
            "BTC/USDT": {
                "symbol": "BTC/USDT", "active": True,
                "precision": {"amount": 5, "price": 2},
                "limits": {
                    "amount": {"min": 0.0001, "max": 1000.0},
                    "cost": {"min": 10.0, "max": None},
                },
            },
        }

    # قواعد الدقة
    def amount_to_precision(self, symbol, amount):
        return f"{math.floor(float(amount) * 1e5) / 1e5:.5f}"

    def price_to_precision(self, symbol, price):
        return f"{math.floor(float(price) * 100) / 100:.2f}"

    # فحص الاتصال
    def fetch_time(self):
        return 1700000000000

    def fetch_balance(self):
        return {
            "USDT": {"free": self.usdt_free, "total": self.usdt_free},
            "BTC": {"free": self.base_free, "total": self.base_free},
            "info": {"canTrade": True},
        }

    # الأوامر
    def create_order(self, symbol, type_, side, amount, price=None, params=None):
        if self.create_fail:
            raise RuntimeError("binance reject: insufficient balance")
        self._oid += 1
        order = {
            "id": str(self._oid), "symbol": symbol, "type": type_, "side": side,
            "amount": float(amount), "price": float(price) if price else None,
            "filled": 0.0, "average": None, "status": "open", "fee": None,
        }
        if type_ == "limit":
            self.orders.append(order)
        else:  # سوق يُنفذ فورًا
            order["status"] = "closed"
            order["filled"] = float(amount)
            order["average"] = 102.0  # سعر تنفيذ وهمي ثابت للاختبار
            self.orders.append(order)
        return order

    def fetch_order(self, order_id, symbol):
        for o in self.orders:
            if str(o["id"]) == str(order_id):
                return dict(o)
        return {"id": str(order_id), "status": "canceled", "filled": 0.0, "average": None}

    def cancel_order(self, order_id, symbol):
        self.canceled.append(str(order_id))
        for o in self.orders:
            if str(o["id"]) == str(order_id) and o["filled"] == 0.0:
                o["status"] = "canceled"


class FakeSetup:
    """بديل خفيف عن DetectedSetup للاختبار — نفس الحقول المستخدمة في create_pending_signal."""
    class _V:
        pass

    def __init__(self, entry=100.0, sl=95.0):
        self.entry_zone_low = entry
        self.entry_zone_high = entry + 1.0
        self.stop_loss_price = sl
        self.pivot_prices = [90.0, 105.0, 97.0, 115.0, 108.0, 130.0]
        self.timeframe = "15m"
        self.direction = "BULLISH"
        self.detected_at = None
        self.validation_result = FakeSetup._V()
        self.validation_result.fib = None


def real_setup(monkeypatch, ex, real=True):
    """ربط بيئة حقيقية وهمية: مفاتيح + نسخة تداول + حالة اتصال."""
    monkeypatch.setattr(vnz, "API_KEY", "k_test", raising=False)
    monkeypatch.setattr(vnz, "API_SECRET", "s_test", raising=False)
    monkeypatch.setattr(vnz, "binance_trade_exchange", lambda: ex, raising=False)
    st = {"connected": True, "keys_present": True, "testnet": False,
          "latency_ms": 42, "usdt_free": ex.usdt_free, "usdt_total": ex.usdt_free,
          "can_trade": True, "error": None, "checked_at": vnz.utc_now_iso()}
    with vnz._bin_status_lock:
        vnz._bin_status_cache["ts"] = __import__("time").time()
        vnz._bin_status_cache["data"] = st
    vnz.is_real_mode = real
    return st


def row_by_id(db, sig_id):
    return db.query("SELECT * FROM signals WHERE id = %s", (sig_id,), one=True)


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 1 — قواعد باينانس (دقة + حدود + سقف)
# ─────────────────────────────────────────────────────────────────────────────

def test_rules_amount_price_precision():
    ex = FakeBinance()
    assert vnz.real_adjust_amount(ex, "BTC/USDT", 0.123456789) == 0.12345  # أرضية على 1e-5
    assert vnz.real_adjust_price(ex, "BTC/USDT", 100.9999) == 100.99       # أرضية على 0.01
    # بلا نسخة (None) → سقوط آمن بلا استثناءات
    assert vnz.real_adjust_amount(None, "BTC/USDT", 1.5) == 1.5
    assert vnz.real_adjust_price(None, "BTC/USDT", 7.777) == 7.777


def test_rules_market_limits():
    ex = FakeBinance()
    mkt = vnz.real_market(ex, "BTC/USDT")
    assert vnz.real_min_cost(mkt) == 10.0        # NOTIONAL من قواعد باينانس
    assert vnz.real_min_amount(mkt) == 0.0001    # LOT_SIZE.minQty
    # سوق مفقود/فاسد → الافتراضي المحلي بلا انهيار
    assert vnz.real_min_cost({}) == vnz.MIN_NOTIONAL_USDT
    assert vnz.real_min_amount(None) == 0.0
    assert vnz.real_min_cost(vnz.real_market(ex, "NOPE/USDT")) == vnz.MIN_NOTIONAL_USDT


def test_rules_quantity_normal_and_cap():
    ex = FakeBinance()
    # 1000$ × 1% مخاطرة / مسافة 5$ = 2 عملة → القيمة 200$ > سقف 50$ → تُقص
    monkey_cap = 50.0
    old_cap = vnz.REAL_MAX_NOTIONAL_USDT
    try:
        vnz.REAL_MAX_NOTIONAL_USDT = monkey_cap
        qty = vnz.compute_quantity_real("BTC/USDT", 100.0, 95.0, 1000.0, ex)
        assert qty is not None
        assert qty * 100.0 <= monkey_cap + 1e-9       # السقف محترم
        assert abs(qty * 100.0 - monkey_cap) < 0.01   # ملاصق للسقف (بعد الدقة)
    finally:
        vnz.REAL_MAX_NOTIONAL_USDT = old_cap


def test_rules_quantity_rejections():
    ex = FakeBinance()
    old_cap = vnz.REAL_MAX_NOTIONAL_USDT
    try:
        vnz.REAL_MAX_NOTIONAL_USDT = 50.0
        # رصيد صفر → رفض صريح
        assert vnz.compute_quantity_real("BTC/USDT", 100.0, 95.0, 0.0, ex) is None
        # أدنى كمية: قيمة صغيرة على سعر مرتفع جدًا؟ — نستخدم مسافة ضيقة جدًا لأدنى حجم
        # مسافة وقف 0.00001$ → كمية مطلوبة ضخمة → السقف يقص إلى 50$/سعر — هنا عكسها:
        # اختبار الرفض بسبب تجاوز الرصيد: سقف أعلى من الرصيد الحر
        vnz.REAL_MAX_NOTIONAL_USDT = 5000.0
        assert vnz.compute_quantity_real("BTC/USDT", 100.0, 99.99999, 10.0, ex) is None
    finally:
        vnz.REAL_MAX_NOTIONAL_USDT = old_cap


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 2 — بطاقة اتصال باينانس
# ─────────────────────────────────────────────────────────────────────────────

def test_binance_status_public_no_keys(clean_db, real_reset, monkeypatch):
    monkeypatch.setattr(vnz, "API_KEY", "", raising=False)
    monkeypatch.setattr(vnz, "API_SECRET", "", raising=False)

    class Probe:
        def fetch_time(self):
            return 1

    monkeypatch.setattr(vnz, "_binance_public_probe", lambda: Probe(), raising=False)
    st = vnz.binance_status_snapshot(force=True)
    assert st["connected"] is True
    assert st["keys_present"] is False
    assert st["usdt_free"] is None
    assert st["error"] is None


def test_binance_status_with_keys_and_cache(clean_db, real_reset, monkeypatch):
    ex = FakeBinance(usdt_free=123.45)
    real_setup(monkeypatch, ex, real=False)
    st = vnz.binance_status_snapshot(force=True)
    assert st["connected"] is True
    assert st["usdt_free"] == 123.45
    assert st["can_trade"] is True
    # الكاش: تعديل الرصيد لا يظهر قبل انتهاء TTL
    ex.usdt_free = 999.0
    st2 = vnz.binance_status_snapshot()
    assert st2["usdt_free"] == 123.45


def test_binance_status_error_path(clean_db, real_reset, monkeypatch):
    monkeypatch.setattr(vnz, "API_KEY", "k", raising=False)
    monkeypatch.setattr(vnz, "API_SECRET", "s", raising=False)

    class Dead:
        def fetch_time(self):
            raise RuntimeError("network down")

    monkeypatch.setattr(vnz, "binance_trade_exchange", lambda: Dead(), raising=False)
    st = vnz.binance_status_snapshot(force=True)
    assert st["connected"] is False
    assert "network down" in (st["error"] or "")
    assert st["usdt_free"] is None


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 3 — زر التداول الحقيقي (نقطة /api/trading/real)
# ─────────────────────────────────────────────────────────────────────────────

def test_real_toggle_rejected_without_keys(client, clean_db, real_reset, monkeypatch):
    monkeypatch.setattr(vnz, "API_KEY", "", raising=False)
    monkeypatch.setattr(vnz, "API_SECRET", "", raising=False)
    r = client.post("/api/trading/real", json={"enable": True})
    assert r.status_code == 400
    body = r.get_json()
    assert body["ok"] is False
    assert "مفاتيح" in body["error"]
    assert vnz.is_real_mode is False


def test_real_toggle_enable_and_persist(client, clean_db, real_reset, monkeypatch):
    ex = FakeBinance(usdt_free=250.0)
    real_setup(monkeypatch, ex, real=False)
    r = client.post("/api/trading/real", json={"enable": True})
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True and body["real_mode"] is True
    assert vnz.is_real_mode is True
    assert vnz.db_get_state("real_mode") == "1"
    # استدعاء متطابق (مفعّل أصلًا) لا يكسر شيئًا
    r2 = client.post("/api/trading/real", json={"enable": True})
    assert r2.get_json()["real_mode"] is True


def test_real_toggle_disable(client, clean_db, real_reset, monkeypatch):
    ex = FakeBinance(usdt_free=250.0)
    real_setup(monkeypatch, ex, real=True)
    r = client.post("/api/trading/real", json={"enable": False})
    assert r.status_code == 200
    assert r.get_json()["real_mode"] is False
    assert vnz.is_real_mode is False
    assert vnz.db_get_state("real_mode") == "0"


def test_real_toggle_enable_fails_when_binance_down(client, clean_db, real_reset, monkeypatch):
    monkeypatch.setattr(vnz, "API_KEY", "k", raising=False)
    monkeypatch.setattr(vnz, "API_SECRET", "s", raising=False)

    class Dead:
        def fetch_time(self):
            raise RuntimeError("down")

    monkeypatch.setattr(vnz, "binance_trade_exchange", lambda: Dead(), raising=False)
    with vnz._bin_status_lock:
        vnz._bin_status_cache["ts"] = 0.0
        vnz._bin_status_cache["data"] = None
    r = client.post("/api/trading/real", json={"enable": True})
    assert r.status_code == 400
    assert vnz.is_real_mode is False


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 4 — إنشاء إشارة حقيقية (أمر LIMIT فعلي)
# ─────────────────────────────────────────────────────────────────────────────

def test_create_real_signal_places_limit_order(clean_db, real_reset, monkeypatch):
    ex = FakeBinance(usdt_free=1000.0)
    real_setup(monkeypatch, ex, real=True)
    old_cap = vnz.REAL_MAX_NOTIONAL_USDT
    try:
        vnz.REAL_MAX_NOTIONAL_USDT = 50.0
        ok = vnz.create_pending_signal("BTC/USDT", FakeSetup(entry=100.0, sl=95.0))
    finally:
        vnz.REAL_MAX_NOTIONAL_USDT = old_cap
    assert ok is True
    assert len(ex.orders) == 1
    order = ex.orders[0]
    assert order["side"] == "buy" and order["type"] == "limit"
    assert order["price"] == 100.0                       # دقة السعر مطبقة
    row = vnz.db.query("SELECT * FROM signals ORDER BY id DESC", one=True)
    assert row["is_real"] == 1
    assert row["order_id"] == order["id"]
    assert 0 < row["quantity"] <= 0.5                    # سقف 50$ عند سعر 100
    # الرصيد الورقي لم يُمس بإنشاء إشارة حقيقية
    assert vnz.get_paper_balance() == vnz.PAPER_BALANCE_START


def test_create_real_signal_fails_without_exchange(clean_db, real_reset, monkeypatch):
    real_setup(monkeypatch, FakeBinance(), real=True)
    monkeypatch.setattr(vnz, "binance_trade_exchange", lambda: None, raising=False)
    ok = vnz.create_pending_signal("BTC/USDT", FakeSetup())
    assert ok is False
    assert vnz.db.query("SELECT COUNT(*) AS n FROM signals")[0]["n"] == 0


def test_create_real_signal_fails_when_order_rejected(clean_db, real_reset, monkeypatch):
    ex = FakeBinance(usdt_free=1000.0)
    ex.create_fail = True
    real_setup(monkeypatch, ex, real=True)
    ok = vnz.create_pending_signal("BTC/USDT", FakeSetup())
    assert ok is False
    assert vnz.db.query("SELECT COUNT(*) AS n FROM signals")[0]["n"] == 0


def test_create_paper_signal_when_real_off(clean_db, real_reset, monkeypatch):
    real_setup(monkeypatch, FakeBinance(), real=False)
    vnz.is_real_mode = False
    ok = vnz.create_pending_signal("BTC/USDT", FakeSetup())
    assert ok is True
    row = vnz.db.query("SELECT * FROM signals ORDER BY id DESC", one=True)
    assert row["is_real"] == 0 and row["order_id"] is None
    assert len(row_by_id(vnz.db, row["id"]).keys()) >= 0  # الأعمدة موجودة


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 5 — مراقبة المعلق الحقيقي
# ─────────────────────────────────────────────────────────────────────────────

def _insert_real_pending(order_id="77", qty=0.5):
    import datetime as _dt
    vnz.db.execute(
        "INSERT INTO signals (symbol, direction, strategy_name, status, entry_price, stop_loss,"
        " take_profit, quantity, notional_usdt, rr_ratio, pivots_json, fib_json, created_at,"
        " peak_price, expires_at, is_real, order_id)"
        " VALUES ('BTC/USDT','BULLISH','Elliott_Fibonacci','pending',100.0,95.0,120.0,%s,%s,4.0,"
        " '{\"P0\": 90.0}', NULL, %s, 100.0, %s, 1, %s)",
        (qty, qty * 100.0, vnz.utc_now_iso(),
         (vnz.utc_now_iso() and
          (_dt.datetime.fromtimestamp(__import__("time").time() + 3600, tz=_dt.timezone.utc)
           .strftime("%Y-%m-%dT%H:%M:%SZ"))), order_id),
    )
    return vnz.db.query("SELECT * FROM signals ORDER BY id DESC", one=True)


def test_real_pending_filled_from_exchange(clean_db, real_reset, monkeypatch):
    ex = FakeBinance()
    real_setup(monkeypatch, ex, real=True)
    sig = _insert_real_pending(order_id="77")
    ex.orders.append({"id": "77", "status": "closed", "filled": 0.5, "average": 100.02,
                      "price": 100.0, "side": "buy", "type": "limit", "amount": 0.5})
    vnz.handle_real_pending(sig, close_now=99.0, p0=90.0)
    row = row_by_id(vnz.db, sig["id"])
    assert row["status"] == "open"
    assert float(row["fill_price"]) == 100.02     # سعر التنفيذ الفعلي من المنصة
    assert float(row["quantity"]) == 0.5


def test_real_pending_structural_invalidation_cancels(clean_db, real_reset, monkeypatch):
    ex = FakeBinance()
    real_setup(monkeypatch, ex, real=True)
    sig = _insert_real_pending(order_id="78")
    ex.orders.append({"id": "78", "status": "open", "filled": 0.0, "average": None,
                      "price": 100.0, "side": "buy", "type": "limit", "amount": 0.5})
    vnz.handle_real_pending(sig, close_now=88.0, p0=90.0)  # إغلاق خلف P0 → إبطال
    assert "78" in ex.canceled
    row = row_by_id(vnz.db, sig["id"])
    assert row["status"] == "cancelled"
    assert "إبطال بنيوي" in (row["close_reason"] or "")


def test_real_pending_cancelled_on_exchange_no_fill(clean_db, real_reset, monkeypatch):
    ex = FakeBinance()
    real_setup(monkeypatch, ex, real=True)
    sig = _insert_real_pending(order_id="79")
    # الأمر غير موجود في قائمة الوهمي → fetch يعيد canceled بلا ملء
    vnz.handle_real_pending(sig, close_now=99.0, p0=90.0)
    row = row_by_id(vnz.db, sig["id"])
    assert row["status"] == "cancelled"
    assert "أُلغي الأمر الحقيقي على المنصة" in (row["close_reason"] or "")


def test_real_pending_partial_fill_opens_partial(clean_db, real_reset, monkeypatch):
    ex = FakeBinance()
    real_setup(monkeypatch, ex, real=True)
    sig = _insert_real_pending(order_id="80", qty=0.5)
    # المنصة: ألغيت بعد ملء 0.2 فقط
    ex.orders.append({"id": "80", "status": "canceled", "filled": 0.2, "average": 100.0,
                      "price": 100.0, "side": "buy", "type": "limit", "amount": 0.5})
    vnz.handle_real_pending(sig, close_now=99.0, p0=90.0)
    row = row_by_id(vnz.db, sig["id"])
    assert row["status"] == "open"
    assert float(row["quantity"]) == 0.2


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 6 — الإغلاق الحقيقي (بيع سوق + محاسبة)
# ─────────────────────────────────────────────────────────────────────────────

def _insert_real_open(qty=0.5, fill=100.0):
    vnz.db.execute(
        "INSERT INTO signals (symbol, direction, strategy_name, status, entry_price, fill_price,"
        " stop_loss, take_profit, quantity, notional_usdt, rr_ratio, pivots_json, fib_json, created_at,"
        " filled_at, peak_price, is_real, order_id)"
        " VALUES ('BTC/USDT','BULLISH','Elliott_Fibonacci','open',100.0,%s,95.0,120.0,%s,%s,4.0,"
        " '{\"P0\": 90.0}', NULL, %s, %s, %s, 1, '77')",
        (fill, qty, qty * 100.0, vnz.utc_now_iso(), vnz.utc_now_iso(), fill),
    )
    return vnz.db.query("SELECT * FROM signals ORDER BY id DESC", one=True)


def test_real_close_market_sell_and_accounting(clean_db, real_reset, monkeypatch):
    ex = FakeBinance(usdt_free=1000.0, base_free=0.5)
    real_setup(monkeypatch, ex, real=True)
    sig = _insert_real_open(qty=0.5, fill=100.0)
    bal_before = vnz.get_paper_balance()
    vnz.close_real_trade(sig, 120.0, "هدف فيبوناتشي 1.618 تحقق")
    # بيع سوق تم
    sells = [o for o in ex.orders if o["side"] == "sell"]
    assert len(sells) == 1 and sells[0]["type"] == "market"
    row = row_by_id(vnz.db, sig["id"])
    assert row["status"] == "closed"
    assert float(row["close_price"]) == 102.0      # سعر التنفيذ من أمر السوق الوهمي
    assert row["exit_order_id"] == sells[0]["id"]
    # PnL محسوب (ربح) لكن الرصيد الورقي بلا مساس
    assert float(row["pnl_usdt"]) > 0
    assert vnz.get_paper_balance() == bal_before


def test_real_close_sell_failure_keeps_open(clean_db, real_reset, monkeypatch):
    ex = FakeBinance(usdt_free=1000.0, base_free=0.5)
    ex.sell_fail = True
    # نحقن فشل البيع عبر create_fail مؤقتًا (نفس نقطة الفشل الفعلية)
    ex.create_fail = True
    real_setup(monkeypatch, ex, real=True)
    sig = _insert_real_open(qty=0.5, fill=100.0)
    bal_before = vnz.get_paper_balance()
    vnz.close_real_trade(sig, 120.0, "هدف فيبوناتشي 1.618 تحقق")
    row = row_by_id(vnz.db, sig["id"])
    assert row["status"] == "open"                  # تبقى مفتوحة — إعادة محاولة لاحقًا
    assert vnz.get_paper_balance() == bal_before


def test_real_close_dust_accounting_only(clean_db, real_reset, monkeypatch):
    ex = FakeBinance(usdt_free=1000.0, base_free=0.00001)  # رصيد حر أقل من minQty
    real_setup(monkeypatch, ex, real=True)
    sig = _insert_real_open(qty=0.5, fill=100.0)
    vnz.close_real_trade(sig, 120.0, "هدف فيبوناتشي 1.618 تحقق")
    assert len([o for o in ex.orders if o["side"] == "sell"]) == 0  # لا أمر بيع
    row = row_by_id(vnz.db, sig["id"])
    assert row["status"] == "closed"
    assert "غبار" in (row["close_reason"] or "")


def test_close_signal_row_real_does_not_touch_paper_balance(clean_db, real_reset, monkeypatch):
    sig = _insert_real_open(qty=0.5, fill=100.0)
    bal_before = vnz.get_paper_balance()
    vnz.close_signal_row(sig, 95.0, "وقف خسارة بنيوي (خلف أصل الموجة 1)")
    row = row_by_id(vnz.db, sig["id"])
    assert float(row["pnl_usdt"]) < 0
    assert vnz.get_paper_balance() == bal_before     # الحقيقية لا تغير الورقي
    # الورقية العادية كما في العقد القديم
    vnz.is_real_mode = False
    ok = vnz.create_pending_signal("ETH/USDT", FakeSetup(entry=100.0, sl=95.0))
    assert ok is True


# ─────────────────────────────────────────────────────────────────────────────
# الجولة 7 — نقاط API واللوحة السبرانية
# ─────────────────────────────────────────────────────────────────────────────

def test_api_binance_status_endpoint(client, clean_db, real_reset, monkeypatch):
    ex = FakeBinance(usdt_free=321.0)
    real_setup(monkeypatch, ex, real=False)
    r = client.get("/api/binance/status")
    body = r.get_json()
    assert body["connected"] is True
    assert body["usdt_free"] == 321.0
    assert body["real_mode"] is False
    assert body["version"] == "FE1.4.0"


def test_health_mode_paper_and_real(client, clean_db, real_reset, monkeypatch):
    r = client.get("/health")
    assert r.get_json()["mode"] == "paper"
    vnz.is_real_mode = True
    r2 = client.get("/health")
    b = r2.get_json()
    assert b["mode"] == "real"
    assert b["real_trading"] is True
    vnz.is_real_mode = False


def test_api_all_carries_real_and_binance(client, clean_db, real_reset, monkeypatch):
    ex = FakeBinance(usdt_free=55.0)
    real_setup(monkeypatch, ex, real=True)
    r = client.get("/api/all")
    body = r.get_json()
    assert body["real_mode"] is True
    assert body["mode"] == "real"
    assert body["binance"]["connected"] is True
    assert body["binance"]["usdt_free"] == 55.0


def test_panel_cyber_structure():
    """اللوحة السبرانية: زر حقيقي + بطاقة اتصال + خلفية متحركة + تصميم نيون."""
    html = vnz.get_dashboard_html()
    # زر التداول الحقيقي مثل V9
    assert "real-toggle" in html and "toggleReal" in html
    assert "التداول الحقيقي" in html
    # بطاقة اتصال باينانس
    assert "اتصال باينانس" in html and "رصيد USDT الحقيقي" in html
    # خلفية سوداء متحركة (شبكة + هالات + مسح)
    assert "bg-grid" in html and "gridmove" in html
    assert "orb1" in html and "scanlines" in html and "scanbar" in html
    # ألوان نيون مشعة
    for color in ("#00ff9c", "#00e5ff", "#ff2bd6", "#ff3355"):
        assert color in html
    # توهج نيون وخط سبراني
    assert "text-shadow" in html and "Orbitron" in html
    # لافتتا الوضع (ورقي/حقيقي) + عمود الوضع في الجداول
    assert "banner-real" in html and "banner-paper" in html
    assert "p-real" in html and "modePill" in html
    import panel as panel_mod
    assert panel_mod.BOT_VERSION == "FE1.4.0"


def test_ddl_migration_adds_real_columns(clean_db):
    cols = {r["name"] for r in vnz.db.query("PRAGMA table_info(signals)")}
    assert {"is_real", "order_id", "exit_order_id"} <= cols
    # ترحيل بلا أذى عند الاستدعاء المتكرر
    vnz.migrate_db()
    vnz.migrate_db()
    cols2 = {r["name"] for r in vnz.db.query("PRAGMA table_info(signals)")}
    assert cols == cols2
