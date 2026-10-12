#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
 FIBO-ELIO — بوت موجة إليوت + مستويات فيبوناتشي  (FE1.0.1)
═══════════════════════════════════════════════════════════════════════════════
 مشروع منفصل طلب المستخدم: «امسح جميع الاستراتيجيات واترك فقط استراتيجية اليوت
 ومستويات فيبوناتشي، وضع المشروع في مستودع منفصل، ولتكن الاستراتيجية مثل
 الاستراتيجية الأصلية الموجودة في المشروع الأصلي قبل الاقتباس».

 المصدر الأصلي (منقول حرفيًا — رخصة MIT):
     github.com/dtwijesekara/Elliott_Waves_Algo_TradingBot
   • engine/pattern_detector.py  — كاشف المحاور ZigZag (آلة حالة 3 أطوار) + نوافذ P0–P5
   • engine/wave_validator.py    — القواعد الصارمة الثلاث (W2 لا تكسر أصل W1 /
                                    W3 ليست الأقصر وتكسر قمة W1 / W4 لا تتداخل مع W1)
   • engine/fibonacci.py         — مستويات فيبوناتشي الكانونية (تصحيح 0.236–0.886
                                    وامتداد 1.0–3.414) ومفحص التقارب ±0.5%
   لا تعديل جوهري على المنطق الأصلي — الاستراتيجية كما هي قبل الاقتباس.

 منطق التداول الأصلي كما في المشروع المصدر:
   • الإشارة: فريم 1h (SIGNAL_TIMEFRAME) — زيجزاج بنسبة انعكاس قابلة للضبط
     (افتراضي 0.6% وفق جدول معايرة المؤلف لفريم 1h: 0.3–0.6%) + مصدر السعر Close
   • الدخول: أمر معلّق عند حد 0.382 لتراجع الموجة 3 (entry_zone_low)
   • الوقف: بنيوي خلف أصل الموجة 1 (P0 − 0.1%)
   • الهدف: امتداد فيبوناتشي 1.618 للموجة 1 من قاع الموجة 2
   • الإلغاء: إغلاق خلف P0 يبطل العدّ، أو انتهاء صلاحية الأمر المعلق بعد 3 شموع
   • التقييم الأفضل: +1 إن كان تراجع W2 في منطقته المثالية (0.382–0.886)
     و+1 لتراجع W4 (0.236–0.5)، وللموكلفات المتساوية الأحدث زمنيًا

 الوضع الورقي الدائم: هذا البوت لا يرسل أي أمر حقيقي إلى المنصة إطلاقًا —
 كل الصفقات محاكاة ورقية برصيد وهمي (PAPER_BALANCE) ورسوم واقعية 0.1% للاتجاهين.
 مفتاح التداول يتحكم في توليد إشارات ورقية جديدة فقط.

 FE1.0.1: طبقة مزودي بيانات متعددة — باينانس أولًا كما في الأصل، ثم Bybit → OKX
 → Gate.io تلقائيًا عند الحظر/الفشل. الدرس المستفاد من المشروع السابق: عنوان
 الخروج المشترك لخدمات Render يتعرض لحظر وزن باينانس (-1003) المتجدد بسبب
 استهلاك الخدمات الأخرى على نفس العنوان، فالبدائل العامة بحدود سخية تضمن استمرار
 الرؤية للسوق دون أي تغيير على المنطق الأصلي أو الوضع الورقي.

 متغيرات البيئة (نفس عقد المشروع السابق + إعدادات الاستراتيجية):
   BINANCE_API_KEY / BINANCE_API_SECRET  (اختياريان — الشموع العامة تكفي للورقي)
   DATABASE_URL          اختياري (PostgreSQL) — وإلا SQLite محلي
   TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID اختياريان
   DASHBOARD_USERNAME / DASHBOARD_PASSWORD اختياريان (حماية اللوحة)
   DEVIATION_THRESHOLD   نسبة انعكاس الزيجزاج (افتراضي 0.006 = 0.6% لفريم 1h)
   SIGNAL_TIMEFRAME      فريم الكشف (افتراضي 1h)   ENTRY_TIMEFRAME فريم التنفيذ (15m)
   MAX_OPEN_TRADES       أقصى صفقات متزامنة (3)     RISK_PCT_PER_TRADE مخاطرة الصفقة (1%)
   PENDING_MAX_CANDLES   صلاحية الأمر المعلق بشموع الكشف (3)
   PAPER_BALANCE         الرصيد الورقي (10000)
"""

import json
import logging
import math
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

try:  # تحميل اختياري لملف .env محليًا
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from flask import Flask, Response, jsonify, request

import ccxt

from engine.pattern_detector import DetectorConfig, DetectedSetup, PivotDetector
from engine.wave_validator import validate_impulse
from engine.fibonacci import FibonacciLevels
from utils.logger import get_logger, fmt_price

# ══════════════════════════════════════════════════════════════════════════════
# الإعدادات — البيئة هي مصدر الحقيقة
# ══════════════════════════════════════════════════════════════════════════════

BOT_VERSION = "FE1.0.1"  # FE1.0.1: تعاقب مزودي البيانات ضد حظر باينانس المشترك بين خدمات Render
STRATEGY_NAME = "Elliott_Fibonacci"
REPO_URL = "https://github.com/salah55t/fibo-elio"

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")

SIGNAL_TIMEFRAME = os.getenv("SIGNAL_TIMEFRAME", "1h")
ENTRY_TIMEFRAME = os.getenv("ENTRY_TIMEFRAME", "15m")
OHLCV_LIMIT = int(os.getenv("OHLCV_LIMIT", "500"))
DEVIATION_THRESHOLD = float(os.getenv("DEVIATION_THRESHOLD", "0.006"))
MIN_WAVE_BARS = int(os.getenv("MIN_WAVE_BARS", "2"))
FIB_TOLERANCE_PCT = float(os.getenv("FIB_TOLERANCE_PCT", "0.5"))
MAX_OPEN_TRADES = int(os.getenv("MAX_OPEN_TRADES", "3"))
RISK_PCT_PER_TRADE = float(os.getenv("RISK_PCT_PER_TRADE", "1.0"))
PENDING_MAX_CANDLES = int(os.getenv("PENDING_MAX_CANDLES", "3"))
PAPER_BALANCE_START = float(os.getenv("PAPER_BALANCE", "10000.0"))
FEE_RATE = float(os.getenv("FEE_RATE", "0.001"))          # 0.1% تيكر لكل اتجاه
INTER_SYMBOL_SLEEP = float(os.getenv("INTER_SYMBOL_SLEEP", "1.0"))
MIN_NOTIONAL_USDT = float(os.getenv("MIN_NOTIONAL_USDT", "10.0"))
CANDLE_CLOSE_BUFFER_SECS = 5
PORT = int(os.getenv("PORT", "10000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")
# [FE1.0.1] سلسلة مزودي البيانات: باينانس أولًا كما في الأصل، ثم بدائل عامة بحدود سخية
DATA_PROVIDERS: List[str] = [
    p.strip().lower() for p in os.getenv("DATA_PROVIDERS", "binance,bybit,okx,gate").split(",") if p.strip()
]
PROVIDER_COOLDOWN_SEC = float(os.getenv("PROVIDER_COOLDOWN_SEC", "900"))  # تبريد المزود الفاشل 15 دقيقة

DASHBOARD_PROTECTED = bool(DASHBOARD_USERNAME and DASHBOARD_PASSWORD)
USE_POSTGRES = DATABASE_URL.startswith("postgres")

TF_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600,
    "2h": 7200, "4h": 14400, "6h": 21600, "8h": 28800, "12h": 43200, "1d": 86400,
}

logger = get_logger("fibo-elio")

# حالة التشغيل (ورقي دائمًا — المفتاح يتحكم بتوليد إشارات جديدة فقط)
is_trading_enabled: bool = False
trading_status_lock = threading.Lock()

scan_stats_lock = threading.Lock()
scan_stats: Dict[str, Any] = {
    "cycles": 0, "scanned": 0, "setups_valid": 0, "setups_bull_traded": 0,
    "setups_bear_seen": 0, "rejected_active_limit": 0, "rejected_symbol_busy": 0,
    "last_scan_at": "", "last_scan_fetched": 0,  # [FE1.0.1] تشخيص دورة المسح
}

# آخر الالتقاطات (صاعدة/هابطة) للوحة — حلقة ذاكرة خفيفة
detections_lock = threading.Lock()
recent_detections: List[Dict[str, Any]] = []
DETECTIONS_MAX = 60


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ══════════════════════════════════════════════════════════════════════════════
# طبقة قاعدة البيانات — PostgreSQL (DATABASE_URL) أو SQLite محلي
# ══════════════════════════════════════════════════════════════════════════════

class Database:
    """غلاف موحد: مؤشرات %s في Postgres و ? في SQLite، صفوف كقواميس."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.conn = None
        self._connect()

    def _connect(self) -> None:
        if USE_POSTGRES:
            import psycopg2
            import psycopg2.extras
            url = DATABASE_URL
            if "sslmode=" not in url:
                url += ("&" if "?" in url else "?") + "sslmode=require"
            self.conn = psycopg2.connect(url)
            self.conn.autocommit = True
        else:
            import sqlite3
            os.makedirs("data", exist_ok=True)
            self.conn = sqlite3.connect("data/fibo_elio.db", check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        logger.info("قاعدة البيانات: %s", "PostgreSQL" if USE_POSTGRES else "SQLite المحلية")

    def _ph(self, sql: str) -> str:
        return sql if USE_POSTGRES else sql.replace("%s", "?")

    def check(self) -> bool:
        try:
            if USE_POSTGRES and (self.conn.closed or self.conn.status != 1):
                return False
            self.query("SELECT 1 AS ok", one=True)
            return True
        except Exception:
            return False

    def ensure(self) -> None:
        if not self.check():
            with self.lock:
                try:
                    self.conn.close()
                except Exception:
                    pass
                for attempt in range(5):
                    try:
                        time.sleep(3 * (attempt + 1))
                        self._connect()
                        logger.info("إعادة اتصال قاعدة البيانات نجحت (محاولة %d)", attempt + 1)
                        return
                    except Exception as exc:
                        logger.warning("فشل إعادة اتصال DB (%d): %s", attempt + 1, exc)
                logger.critical("تعذر استعادة قاعدة البيانات بعد 5 محاولات")

    def query(self, sql: str, params: Tuple = (), one: bool = False):
        with self.lock:
            cur = self.conn.cursor()
            try:
                cur.execute(self._ph(sql), params)
                rows = cur.fetchall()
                if USE_POSTGRES:
                    cols = [d[0] for d in cur.description] if cur.description else []
                    result = [dict(zip(cols, r)) for r in rows]
                else:
                    result = [dict(r) for r in rows]
                return (result[0] if result else None) if one else result
            finally:
                cur.close()

    def execute(self, sql: str, params: Tuple = ()) -> None:
        with self.lock:
            cur = self.conn.cursor()
            try:
                cur.execute(self._ph(sql), params)
                if not USE_POSTGRES:
                    self.conn.commit()
            finally:
                cur.close()


db = Database()

_SIGNALS_DDL_PG = """
CREATE TABLE IF NOT EXISTS signals (
  id BIGSERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  direction TEXT NOT NULL,
  strategy_name TEXT NOT NULL,
  status TEXT NOT NULL,
  entry_price NUMERIC,
  fill_price NUMERIC,
  stop_loss NUMERIC,
  take_profit NUMERIC,
  quantity NUMERIC,
  notional_usdt NUMERIC,
  rr_ratio NUMERIC,
  pivots_json TEXT,
  fib_json TEXT,
  created_at TEXT,
  filled_at TEXT,
  closed_at TEXT,
  close_price NUMERIC,
  close_reason TEXT,
  pnl_usdt NUMERIC,
  pnl_pct NUMERIC,
  peak_price NUMERIC,
  expires_at TEXT,
  meta_json TEXT
);
CREATE TABLE IF NOT EXISTS notifications (
  id BIGSERIAL PRIMARY KEY,
  level TEXT, message TEXT, ntype TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS bot_state (
  key TEXT PRIMARY KEY, value TEXT
);
"""

_SIGNALS_DDL_SQLITE = _SIGNALS_DDL_PG.replace("BIGSERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT").replace("NUMERIC", "REAL")


def init_db() -> None:
    ddl = _SIGNALS_DDL_PG if USE_POSTGRES else _SIGNALS_DDL_SQLITE
    for attempt in range(5):
        try:
            for stmt in [s.strip() for s in ddl.split(";") if s.strip()]:
                db.execute(stmt)
            if db_get_state("paper_balance") is None:
                db_set_state("paper_balance", repr(PAPER_BALANCE_START))
            logger.info("تهيئة قاعدة البيانات اكتملت — الإصدار %s", BOT_VERSION)
            return
        except Exception as exc:
            logger.warning("init_db محاولة %d فشلت: %s", attempt + 1, exc)
            time.sleep(5)
    raise RuntimeError("فشل تهيئة قاعدة البيانات")


def _state_get_raw(key: str) -> Optional[str]:
    row = db.query("SELECT value FROM bot_state WHERE key = %s", (key,), one=True)
    return row["value"] if row else None


def db_get_state(key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        v = _state_get_raw(key)
        return v if v is not None else default
    except Exception as exc:
        logger.warning("db_get_state(%s): %s", key, exc)
        return default


def db_set_state(key: str, value: str) -> None:
    try:
        db.execute(
            "INSERT INTO bot_state (key, value) VALUES (%s, %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (key, value),
        )
    except Exception as exc:
        logger.warning("db_set_state(%s): %s", key, exc)


def get_paper_balance() -> float:
    try:
        return float(db_get_state("paper_balance", repr(PAPER_BALANCE_START)) or PAPER_BALANCE_START)
    except Exception:
        return PAPER_BALANCE_START


def set_paper_balance(value: float) -> None:
    db_set_state("paper_balance", repr(float(value)))


def log_and_notify(level: str, message: str, ntype: str = "INFO") -> None:
    """سجّل محليًا + أخزن للوحة + أرسل تلجرام إن توفرت المفاتيح."""
    getattr(logger, level if level in ("info", "warning", "error") else "info", logger.info)(message)
    try:
        db.execute(
            "INSERT INTO notifications (level, message, ntype, created_at) VALUES (%s, %s, %s, %s)",
            (level, message, ntype, utc_now_iso()),
        )
    except Exception:
        pass
    send_telegram_message(message)


def send_telegram_message(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except Exception as exc:
        logger.warning("تعذر إرسال تلجرام: %s", exc)


# ══════════════════════════════════════════════════════════════════════════════
# طبقة بيانات السوق — ccxt (كما في المشروع الأصلي)
# ══════════════════════════════════════════════════════════════════════════════

def _build_exchange(name: str):
    """تهيئة مزود ccxt — مفاتيح باينانس تُمرر لباينانس فقط (البدائل عامة بلا مفاتيح)."""
    cls = getattr(ccxt, name, None)
    if cls is None and name == "gate":
        cls = getattr(ccxt, "gateio", None)  # الاسم القديم في إصدارات ccxt الأقدم
    if cls is None:
        raise ValueError(f"مزود غير معروف في ccxt: {name}")
    opts: Dict[str, Any] = {
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    }
    if name == "binance":
        opts["apiKey"] = API_KEY or None
        opts["secret"] = API_SECRET or None
    return cls(opts)


provider_lock = threading.Lock()
EXCHANGES: "OrderedDict[str, Any]" = OrderedDict()
for _pname in DATA_PROVIDERS:
    try:
        EXCHANGES[_pname] = _build_exchange(_pname)
    except Exception as _exc:
        logger.warning("تعذر تهيئة مزود البيانات %s: %s", _pname, _exc)

# حالة كل مزود: عدادات + آخر خطأ + تبريد زمني بعد الفشل (حظر -1003 المشترك مثالًا)
provider_state: Dict[str, Dict[str, Any]] = {
    name: {"ok": 0, "fail": 0, "last_error": "", "last_ok_at": None, "cooldown_until": 0.0}
    for name in EXCHANGES
}
active_source: Dict[str, Any] = {"name": None, "since": None}


def current_exchange():
    """المزود الفعّال الحالي (لأدوات دقة الكميات) — باينانس احتياطًا."""
    with provider_lock:
        name = active_source["name"]
    if name and name in EXCHANGES:
        return EXCHANGES[name]
    return EXCHANGES.get("binance") or (next(iter(EXCHANGES.values())) if EXCHANGES else None)


def amount_prec(symbol: str, qty: float) -> float:
    """تقريب الكمية حسب قواعد المزود الفعّال — بأمان تام بلا استثناءات."""
    ex = current_exchange()
    if ex is None:
        return qty
    try:
        return float(ex.amount_to_precision(symbol, qty))
    except Exception:
        return qty


def data_status() -> Dict[str, Any]:
    """تشخيص مزودي البيانات للوحة وواجهات API — بلا كتمان لأي فشل."""
    now = time.time()
    with provider_lock:
        provs: Dict[str, Any] = {}
        for name, st in provider_state.items():
            provs[name] = {
                "ok": st["ok"],
                "fail": st["fail"],
                "last_error": st["last_error"] or None,
                "last_ok_at": st["last_ok_at"],
                "cooling_sec": max(0, int(st["cooldown_until"] - now)),
            }
        active = dict(active_source)
    return {"active": active.get("name"), "active_since": active.get("since"), "providers": provs}

REQUIRED_COLS = ["timestamp", "open", "high", "low", "close", "volume"]


def normalize_symbol(base: str) -> str:
    """BTC → BTC/USDT (إدخال القائمة أساسي فقط، التسعير USDT دائمًا)."""
    base = base.strip().upper()
    if "/" in base:
        return base
    return f"{base}/USDT"


def load_watchlist() -> List[str]:
    """القائمة من crypto_list.txt أو SYMBOLS بيئيًا — بالترتيب وبلا تكرار."""
    raw_env = os.getenv("SYMBOLS", "")
    symbols: List[str] = []
    if raw_env.strip():
        symbols = [normalize_symbol(s) for s in raw_env.split(",") if s.strip()]
    elif os.path.exists("crypto_list.txt"):
        with open("crypto_list.txt", "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    symbols.append(normalize_symbol(line))
    if not symbols:
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    seen, uniq = set(), []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


watchlist: List[str] = load_watchlist()


def fetch_ohlcv_raw(symbol: str, timeframe: str, limit: int) -> Tuple[Optional[list], Optional[str]]:
    """تجربة المزودين بالترتيب: باينانس أولًا (الأصل) ثم البدائل عند الحظر/الفشل.
    المزود الفاشل يدخل تبريدًا مؤقتًا حتى لا تُهدر زمن كل دورة عليه."""
    now = time.time()
    with provider_lock:
        order = [n for n in EXCHANGES if provider_state[n]["cooldown_until"] <= now]
    errors: List[str] = []
    for name in order:
        try:
            raw = EXCHANGES[name].fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if not raw:
                raise ValueError("قائمة شموع فارغة")
            with provider_lock:
                st = provider_state[name]
                st["ok"] += 1
                st["last_ok_at"] = utc_now_iso()
                if active_source["name"] != name:
                    active_source["name"] = name
                    active_source["since"] = utc_now_iso()
                    logger.info("مزود البيانات الفعّال الآن: %s", name)
            return raw, name
        except Exception as exc:
            with provider_lock:
                st = provider_state[name]
                st["fail"] += 1
                st["last_error"] = str(exc)[:280]
                st["cooldown_until"] = time.time() + PROVIDER_COOLDOWN_SEC
            errors.append(f"{name}: {str(exc)[:120]}")
    if errors:
        logger.warning("فشل جلب %s %s من المزودين المتاحين — %s", symbol, timeframe, " | ".join(errors))
    return None, None


def fetch_ohlcv_df(symbol: str, timeframe: str, limit: int = OHLCV_LIMIT) -> Optional[pd.DataFrame]:
    """شموع OHLCV كإطار pandas بعقد الطبقة الأولى (timestamp/open/high/low/close/volume).
    [FE1.0.1] عبر تعاقب المزودين — باينانس أولًا كما في الأصل ثم البدائل آليًا."""
    for attempt in range(3):
        raw, _src = fetch_ohlcv_raw(symbol, timeframe, limit)
        if raw:
            if len(raw) < 60:
                return None
            df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
            df["symbol"] = symbol
            df["timeframe"] = timeframe
            df = df[REQUIRED_COLS + ["symbol", "timeframe"]]
            df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
            return df
        time.sleep(2.0 * (attempt + 1))
    return None


# كاشف المحاور — إعداد المؤلف الافتراضي (zigzag + close + min_wave_bars=2)
detector = PivotDetector(DetectorConfig(
    method="zigzag",
    deviation_threshold=DEVIATION_THRESHOLD,
    price_source="close",
    min_wave_bars=MIN_WAVE_BARS,
    require_fib_confluence=False,
    fib_tolerance_pct=FIB_TOLERANCE_PCT,
))


# ══════════════════════════════════════════════════════════════════════════════
# محرك الصفقات الورقي — نفس تدفق execute_wave_setup الأصلي
# ══════════════════════════════════════════════════════════════════════════════

def compute_take_profit(setup: DetectedSetup) -> float:
    """الهدف = امتداد 1.618 للموجة 1 من قاع الموجة 2 (منطق الأصل حرفيًا)."""
    p0, p1, p2 = setup.pivot_prices[0], setup.pivot_prices[1], setup.pivot_prices[2]
    fib = FibonacciLevels(swing_start=p0, swing_end=p1)
    targets = fib.extension_levels(ratios=(1.618, 1.272), base_price=p2)
    tp = next((lv for lv in targets if lv.ratio == 1.618), targets[-1])
    return float(tp.price)


def compute_quantity(symbol: str, entry: float, sl: float) -> Optional[float]:
    """حجم المركز على مسافة المخاطرة الحقيقية (1% من الرصيد الورقي)."""
    balance = get_paper_balance()
    risk_amount = balance * (RISK_PCT_PER_TRADE / 100.0)
    risk_per_coin = abs(entry - sl)
    if risk_per_coin <= 0 or risk_amount <= 0:
        return None
    qty_raw = risk_amount / risk_per_coin
    qty = amount_prec(symbol, qty_raw)
    if qty == qty_raw:
        # لا طبقة دقة متاحة (بلا مزود أو فشل التقريب) — تقريب بسيط كما في الأصل
        qty = math.floor(qty * 1e6) / 1e6
    if qty <= 0:
        return None
    notional = qty * entry
    if notional < MIN_NOTIONAL_USDT:
        # ورقي: اسمح بأدنى حجم تداول لكن ارفض إن تجاوزت المخاطرة 3× الميزانية المخططة
        qty_min = MIN_NOTIONAL_USDT / entry
        if qty_min * risk_per_coin <= risk_amount * 3.0:
            qty = amount_prec(symbol, qty_min)
            if qty <= 0:
                qty = math.floor(qty_min * 1e6) / 1e6
        else:
            logger.info("[%s] رفض الحجم: مسافة الوقف واسعة جدًا لأدنى حجم (%.2f USDT مخاطرة)", symbol, qty_min * risk_per_coin)
            return None
    return qty


def active_trade_count() -> int:
    rows = db.query(
        "SELECT COUNT(*) AS n FROM signals WHERE status IN ('pending', 'open')"
    )
    return int(rows[0]["n"]) if rows else 0


def symbol_has_active(symbol: str) -> bool:
    rows = db.query(
        "SELECT COUNT(*) AS n FROM signals WHERE symbol = %s AND status IN ('pending', 'open')",
        (symbol,),
    )
    return bool(rows and int(rows[0]["n"]) > 0)


def register_detection(symbol: str, setup: DetectedSetup, traded: bool) -> None:
    """حلقة الالتقاطات للوحة: صاعدة (قابلة للتنفيذ) وهابطة (للمتابعة فقط — سبوت)."""
    fib = setup.validation_result.fib
    entry = {
        "symbol": symbol,
        "timeframe": setup.timeframe,
        "direction": setup.direction,
        "pivots": [round(p, 8) for p in setup.pivot_prices],
        "w2_retrace": round(fib.wave2_retrace_pct, 4) if fib else None,
        "w4_retrace": round(fib.wave4_retrace_pct, 4) if fib else None,
        "w2_in_zone": bool(fib.wave2_in_zone) if fib else False,
        "w4_in_zone": bool(fib.wave4_in_zone) if fib else False,
        "entry_zone_low": round(setup.entry_zone_low, 8),
        "entry_zone_high": round(setup.entry_zone_high, 8),
        "stop_loss": round(setup.stop_loss_price, 8),
        "take_profit": round(compute_take_profit(setup), 8),
        "traded": traded,
        "detected_at": utc_now_iso(),
    }
    with detections_lock:
        recent_detections.insert(0, entry)
        del recent_detections[DETECTIONS_MAX:]


def create_pending_signal(symbol: str, setup: DetectedSetup) -> bool:
    """أمر معلّق عند 0.382 لتراجع الموجة 3 — كما ينفذ الأصل _determine_entry_price."""
    entry = float(setup.entry_zone_low)
    sl = float(setup.stop_loss_price)
    tp = compute_take_profit(setup)
    if not (entry > 0 and sl > 0 and tp > entry > sl):
        logger.info("[%s] أسعار الإعداد غير منطقية (entry=%s sl=%s tp=%s) — تجاهل",
                    symbol, fmt_price(entry), fmt_price(sl), fmt_price(tp))
        return False
    qty = compute_quantity(symbol, entry, sl)
    if qty is None:
        return False
    risk_per_coin = entry - sl
    rr = (tp - entry) / risk_per_coin if risk_per_coin > 0 else 0.0
    fib = setup.validation_result.fib
    expires_at = datetime.fromtimestamp(
        time.time() + PENDING_MAX_CANDLES * TF_SECONDS.get(SIGNAL_TIMEFRAME, 3600),
        tz=timezone.utc,
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    pivots_json = json.dumps({"P0": setup.pivot_prices[0], "P1": setup.pivot_prices[1],
                              "P2": setup.pivot_prices[2], "P3": setup.pivot_prices[3],
                              "P4": setup.pivot_prices[4], "P5": setup.pivot_prices[5]})
    fib_json = json.dumps({
        "w2_retrace": round(fib.wave2_retrace_pct, 4) if fib else None,
        "w4_retrace": round(fib.wave4_retrace_pct, 4) if fib else None,
        "w2_in_zone": bool(fib.wave2_in_zone) if fib else False,
        "w4_in_zone": bool(fib.wave4_in_zone) if fib else False,
        "entry_zone_low": round(setup.entry_zone_low, 8),
        "entry_zone_high": round(setup.entry_zone_high, 8),
        "tp_note": "امتداد 1.618 للموجة 1 من قاع الموجة 2 (الأصل)",
    })
    db.execute(
        "INSERT INTO signals (symbol, direction, strategy_name, status, entry_price, stop_loss,"
        " take_profit, quantity, notional_usdt, rr_ratio, pivots_json, fib_json, created_at,"
        " peak_price, expires_at) VALUES (%s,%s,%s,'pending',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (symbol, "BULLISH", STRATEGY_NAME, entry, sl, tp, qty, qty * entry, round(rr, 2),
         pivots_json, fib_json, utc_now_iso(), entry, expires_at),
    )
    with scan_stats_lock:
        scan_stats["setups_bull_traded"] += 1
    if fib:
        signal_msg = (
            f"🌊 إشارة إليوت+فيبو جديدة (ورقية): {symbol}\n"
            f"دخول معلّق: {fmt_price(entry)} | وقف بنيوي: {fmt_price(sl)} | هدف 1.618: {fmt_price(tp)}\n"
            f"R:R = {rr:.2f} | W2={fib.wave2_retrace_pct*100:.1f}% W4={fib.wave4_retrace_pct*100:.1f}%"
        )
    else:
        signal_msg = f"🌊 إشارة إليوت+فيبو جديدة (ورقية): {symbol} — دخول {fmt_price(entry)}"
    log_and_notify("info", signal_msg, "NEW_SIGNAL")
    return True


def close_signal_row(sig: Dict[str, Any], exit_price: float, reason: str) -> None:
    """محاسبة الإغلاق: رسوم 0.1% × اتجاهين على الورقي — نفس عقد المشروع السابق."""
    entry = float(sig["fill_price"])
    qty = float(sig["quantity"])
    gross = qty * (exit_price - entry)
    fees = (qty * entry + qty * exit_price) * FEE_RATE
    pnl_usdt = gross - fees
    pnl_pct = (pnl_usdt / (qty * entry)) * 100.0 if qty * entry > 0 else 0.0
    db.execute(
        "UPDATE signals SET status='closed', close_price=%s, close_reason=%s, closed_at=%s,"
        " pnl_usdt=%s, pnl_pct=%s WHERE id=%s",
        (exit_price, reason, utc_now_iso(), round(pnl_usdt, 6), round(pnl_pct, 4), sig["id"]),
    )
    set_paper_balance(get_paper_balance() + pnl_usdt)
    emoji = "✅" if pnl_usdt >= 0 else "🛑"
    log_and_notify(
        "info" if pnl_usdt >= 0 else "warning",
        f"{emoji} إغلاق ورقي: {sig['symbol']} — {reason}\n"
        f"دخول {fmt_price(entry)} → خروج {fmt_price(exit_price)}\n"
        f"النتيجة: {pnl_usdt:+.2f}$ ({pnl_pct:+.2f}%) | الرصيد الورقي: {get_paper_balance():.2f}$",
        "TRADE_CLOSED",
    )


def monitor_step() -> None:
    """نفّذ أوامر الإغلاق/الملء الورقية — كل 60 ثانية على شموع فريم التنفيذ (15m)."""
    pend = db.query("SELECT * FROM signals WHERE status='pending' ORDER BY id ASC")
    for sig in pend:
        symbol = sig["symbol"]
        try:
            df = fetch_ohlcv_df(symbol, ENTRY_TIMEFRAME, limit=2)
        except Exception as exc:
            logger.warning("[مراقبة] فشل جلب %s: %s", symbol, exc)
            continue
        if df is None or df.empty:
            continue
        last = df.iloc[-1]
        close_now = float(last["close"])
        p0 = float(json.loads(sig["pivots_json"])["P0"])

        # 1) الإبطال البنيوي (منطق الأصل is_wave_invalidated): إغلاق خلف P0 يبطل العدّ
        if close_now < p0:
            db.execute("UPDATE signals SET status='cancelled', close_reason=%s, closed_at=%s WHERE id=%s",
                       (f"إبطال بنيوي: إغلاق {fmt_price(close_now)} خلف أصل الموجة 1 (P0={fmt_price(p0)})",
                        utc_now_iso(), sig["id"]))
            logger.info("[%s] أمر معلق أُبطل بنيويًا (إغلاق خلف P0)", symbol)
            continue

        # 2) انتهاء الصلاحية — MAX_CANDLES_PENDING شمعة كشف (الأصل)
        if sig.get("expires_at") and utc_now_iso() > sig["expires_at"]:
            db.execute("UPDATE signals SET status='expired', close_reason=%s, closed_at=%s WHERE id=%s",
                       ("انتهت صلاحية الأمر المعلق (3 شموع) دون لمس منطقة الدخول", utc_now_iso(), sig["id"]))
            logger.info("[%s] أمر معلق انتهت صلاحيته دون ملء", symbol)
            continue

        # 3) الملء: لمس الشمعة لسعر الأمر المعلق (منخفض ≤ الدخول) — كما يفعل حد حقيقي
        entry = float(sig["entry_price"])
        low_now = float(last["low"])
        if low_now <= entry:
            fill_price = entry if close_now >= entry else close_now  # ملء بسعر أفضل إن نزل السوق تحته
            db.execute("UPDATE signals SET status='open', fill_price=%s, filled_at=%s WHERE id=%s",
                       (fill_price, utc_now_iso(), sig["id"]))
            log_and_notify("info",
                           f"🎯 مُلئ الأمر المعلق (ورقي): {symbol} عند {fmt_price(fill_price)}\n"
                           f"وقف: {fmt_price(sig['stop_loss'])} | هدف 1.618: {fmt_price(sig['take_profit'])}",
                           "ORDER_FILLED")

    opened = db.query("SELECT * FROM signals WHERE status='open' ORDER BY id ASC")
    for sig in opened:
        symbol = sig["symbol"]
        try:
            df = fetch_ohlcv_df(symbol, ENTRY_TIMEFRAME, limit=2)
        except Exception as exc:
            logger.warning("[مراقبة] فشل جلب %s: %s", symbol, exc)
            continue
        if df is None or df.empty:
            continue
        last = df.iloc[-1]
        high_now, low_now = float(last["high"]), float(last["low"])
        # تتبع القمة لعرضه في اللوحة
        peak = max(float(sig.get("peak_price") or sig["fill_price"]), high_now)
        if abs(peak - float(sig.get("peak_price") or 0)) > 1e-12:
            db.execute("UPDATE signals SET peak_price=%s WHERE id=%s", (peak, sig["id"]))
        # الوقف أولًا (متحفظ) — الوقف بنيوي خلف P0، الهدف امتداد 1.618
        if low_now <= float(sig["stop_loss"]):
            close_signal_row(sig, float(sig["stop_loss"]), "وقف خسارة بنيوي (خلف أصل الموجة 1)")
        elif high_now >= float(sig["take_profit"]):
            close_signal_row(sig, float(sig["take_profit"]), "هدف فيبوناتشي 1.618 تحقق")


# ══════════════════════════════════════════════════════════════════════════════
# حلقة المسح — إيقاع المشروع الأصلي: بعد إغلاق كل شمعة كشف (1h)
# ══════════════════════════════════════════════════════════════════════════════

def select_best_setup(setups: List[DetectedSetup]) -> Optional[DetectedSetup]:
    """تقييم الأصل حرفيًا: +1 لمنطقة W2 المثالية، +1 لمنطقة W4، وللمتساويين الأحدث."""
    if not setups:
        return None
    if len(setups) == 1:
        return setups[0]

    def score(s: DetectedSetup) -> Tuple[int, float]:
        fib = s.validation_result.fib
        pts = 0
        if fib:
            if fib.wave2_in_zone:
                pts += 1
            if fib.wave4_in_zone:
                pts += 1
        recency = s.detected_at.timestamp() if s.detected_at else 0.0
        return (pts, recency)

    return max(setups, key=score)


_last_outage_notify = {"at": 0.0}


def maybe_notify_outage() -> None:
    """إشعار لوحة واحد كل 6 ساعات كحد أقصى عند فشل كل مزودي البيانات — بلا ضجيج."""
    now = time.time()
    if now - _last_outage_notify["at"] < 6 * 3600:
        return
    _last_outage_notify["at"] = now
    log_and_notify(
        "warn",
        "تعذّر جلب الشموع من كل مزودي البيانات (باينانس والبدائل) — البوت يراقب وسيحاول مع الدورة القادمة تلقائيًا",
        "DATA_OUTAGE",
    )


def scan_cycle() -> None:
    """دورة كشف كاملة على القائمة — الكشف الصاعد يُنفذ ورقيًا والهابط يُعرض فقط."""
    db.ensure()
    with scan_stats_lock:
        scan_stats["cycles"] += 1
        scan_stats["last_scan_at"] = utc_now_iso()
    scanned_before = scan_stats["scanned"]
    trading_on = is_trading_enabled
    for symbol in watchlist:
        try:
            df = fetch_ohlcv_df(symbol, SIGNAL_TIMEFRAME, limit=OHLCV_LIMIT)
            if df is None:
                continue
            with scan_stats_lock:
                scan_stats["scanned"] += 1
            setups = detector.scan(df)
            if not setups:
                time.sleep(INTER_SYMBOL_SLEEP)
                continue
            with scan_stats_lock:
                scan_stats["setups_valid"] += len(setups)
            bulls = [s for s in setups if s.direction == "BULLISH"]
            bears = [s for s in setups if s.direction == "BEARISH"]
            with scan_stats_lock:
                scan_stats["setups_bear_seen"] += len(bears)
            for b in bears:
                register_detection(symbol, b, traded=False)

            if bulls:
                best = select_best_setup(bulls)
                if best is not None:
                    already = symbol_has_active(symbol)
                    full = active_trade_count() >= MAX_OPEN_TRADES
                    traded = False
                    if already:
                        with scan_stats_lock:
                            scan_stats["rejected_symbol_busy"] += 1
                    elif full:
                        with scan_stats_lock:
                            scan_stats["rejected_active_limit"] += 1
                    elif not trading_on:
                        logger.info("[%s] إعداد صاعد صالح لكن توليد الإشارات معطل (ورقي متوقف)", symbol)
                    else:
                        traded = create_pending_signal(symbol, best)
                    register_detection(symbol, best, traded=traded)
        except Exception as exc:
            logger.exception("[%s] استثناء في دورة المسح: %s", symbol, exc)
        finally:
            time.sleep(INTER_SYMBOL_SLEEP)
    with scan_stats_lock:
        scan_stats["last_scan_fetched"] = scan_stats["scanned"] - scanned_before
    if scan_stats["last_scan_fetched"] == 0:
        maybe_notify_outage()


def seconds_until_next_candle(timeframe: str) -> float:
    """نوم حتى إغلاق الشمعة القادمة + هامش أمان — كما في main.py الأصلي."""
    candle_secs = TF_SECONDS.get(timeframe, 3600)
    offset = time.time() % candle_secs
    remaining = candle_secs - offset
    return remaining + CANDLE_CLOSE_BUFFER_SECS


def scan_loop() -> None:
    logger.info("حلقة المسح بدأت — فريم الكشف %s | انعكاس الزيجزاج %.2f%% | %d أزواج",
                SIGNAL_TIMEFRAME, DEVIATION_THRESHOLD * 100, len(watchlist))
    while True:
        try:
            scan_cycle()
        except Exception as exc:
            logger.exception("استثناء في حلقة المسح: %s", exc)
        nap = seconds_until_next_candle(SIGNAL_TIMEFRAME)
        logger.info("الدورة اكتملت — النوم %.0f ثانية حتى إغلاق شمعة %s القادمة", nap, SIGNAL_TIMEFRAME)
        time.sleep(nap)


def monitor_loop() -> None:
    """مراقبة تنفيذية على فريم الدخول (15m): ملء المعلق + وقف/هدف المفتوح."""
    time.sleep(20)
    while True:
        try:
            db.ensure()
            monitor_step()
        except Exception as exc:
            logger.exception("استثناء في حلقة المراقبة: %s", exc)
        time.sleep(60)


def keep_alive_loop() -> None:
    """نبضة ذاتية ضد نوم Render المجاني — كما في المشروع السابق."""
    if not RENDER_EXTERNAL_URL:
        return
    url = RENDER_EXTERNAL_URL.rstrip("/") + "/health"
    while True:
        time.sleep(14 * 60)
        try:
            requests.get(url, timeout=10)
            logger.info("نبضة البقاء أُرسلت إلى %s", url)
        except Exception as exc:
            logger.warning("فشلت نبضة البقاء: %s", exc)


# ══════════════════════════════════════════════════════════════════════════════
# لوحة التحكم وواجهات API
# ══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)


def require_dashboard_auth():
    if not DASHBOARD_PROTECTED:
        return
    auth = request.authorization
    if not (auth and auth.username == DASHBOARD_USERNAME and auth.password == DASHBOARD_PASSWORD):
        return Response(
            "لوحة Fibo-Elio محمية — أدخل اسم المستخدم وكلمة المرور\n",
            401, {"WWW-Authenticate": "Basic realm='Fibo-Elio Dashboard'"},
        )


def _parse_sig_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    for key in ("pivots_json", "fib_json", "meta_json"):
        raw = out.pop(key, None)
        if raw:
            try:
                out[key.replace("_json", "")] = json.loads(raw)
            except Exception:
                out[key.replace("_json", "")] = None
    return out


def compute_stats() -> Dict[str, Any]:
    closed = db.query("SELECT pnl_usdt, fill_price, close_price, quantity FROM signals WHERE status='closed'")
    open_rows = db.query("SELECT fill_price, quantity, take_profit, symbol FROM signals WHERE status='open'")
    pend_rows = db.query("SELECT COUNT(*) AS n FROM signals WHERE status='pending'")
    wins = [r for r in closed if float(r["pnl_usdt"] or 0) > 0]
    losses = [r for r in closed if float(r["pnl_usdt"] or 0) <= 0]
    gross_win = sum(float(r["pnl_usdt"] or 0) for r in wins)
    gross_loss = abs(sum(float(r["pnl_usdt"] or 0) for r in losses))
    unrealized = 0.0
    for r in open_rows:
        try:
            df = fetch_ohlcv_df(r["symbol"], ENTRY_TIMEFRAME, limit=2)
            price = float(df["close"].iloc[-1]) if df is not None and not df.empty else float(r["fill_price"])
            unrealized += float(r["quantity"]) * (price - float(r["fill_price"]))
        except Exception:
            pass
    with scan_stats_lock:
        cyc = dict(scan_stats)
    return {
        "closed_n": len(closed),
        "open_n": len(open_rows),
        "pending_n": int(pend_rows[0]["n"]) if pend_rows else 0,
        "wins_n": len(wins),
        "losses_n": len(losses),
        "win_rate": (len(wins) / len(closed) * 100.0) if closed else None,
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else (None if gross_win == 0 else 99.0),
        "total_pnl": sum(float(r["pnl_usdt"] or 0) for r in closed),
        "unrealized": unrealized,
        **cyc,
    }


@app.route("/")
def home():
    resp = require_dashboard_auth()
    if resp:
        return resp
    return Response(get_dashboard_html(), mimetype="text/html")


@app.route("/health")
def health():
    db_ok = db.check()
    return jsonify({
        "status": "ok" if db_ok else "degraded",
        "version": BOT_VERSION,
        "strategy": STRATEGY_NAME,
        "mode": "paper",
        "db": "postgres" if USE_POSTGRES else "sqlite",
        "trading_enabled": is_trading_enabled,
        "data_source": (active_source.get("name") or "boot"),
        "pairs": len(watchlist),
        "time": utc_now_iso(),
    })


@app.route("/api/all")
def api_all():
    resp = require_dashboard_auth()
    if resp:
        return resp
    open_rows = db.query(
        "SELECT * FROM signals WHERE status IN ('pending','open') ORDER BY id DESC LIMIT 50"
    )
    closed_rows = db.query(
        "SELECT * FROM signals WHERE status='closed' ORDER BY id DESC LIMIT 25"
    )
    notif_rows = db.query("SELECT * FROM notifications ORDER BY id DESC LIMIT 15")
    with detections_lock:
        dets = list(recent_detections)
    return jsonify({
        "version": BOT_VERSION,
        "strategy": STRATEGY_NAME,
        "mode": "paper",
        "trading_enabled": is_trading_enabled,
        "paper_balance": get_paper_balance(),
        "stats": compute_stats(),
        "open_signals": [_parse_sig_row(r) for r in open_rows],
        "closed_signals": [_parse_sig_row(r) for r in closed_rows],
        "detections": dets,
        "notifications": notif_rows,
        "data": data_status(),  # [FE1.0.1] تشخيص مزودي البيانات للوحة
    })


@app.route("/api/signals")
def api_signals():
    rows = db.query("SELECT * FROM signals ORDER BY id DESC LIMIT 100")
    return jsonify({"signals": [_parse_sig_row(r) for r in rows], "version": BOT_VERSION})


@app.route("/api/pnl_history")
def api_pnl_history():
    rows = db.query(
        "SELECT id, symbol, pnl_usdt, pnl_pct, closed_at FROM signals"
        " WHERE status='closed' ORDER BY id ASC LIMIT 500"
    )
    return jsonify({"history": rows, "version": BOT_VERSION})


@app.route("/api/trading/toggle", methods=["POST"])
def toggle_trading_status():
    global is_trading_enabled
    with trading_status_lock:
        is_trading_enabled = not is_trading_enabled
        db_set_state("trading_enabled", "1" if is_trading_enabled else "0")
    msg = "🌊 توليد الإشارات الورقية: مفعّل" if is_trading_enabled else "⏸ توليد الإشارات الورقية: معطّل (المراقبة مستمرة)"
    log_and_notify("info", msg, "TRADING_STATUS_CHANGE")
    return jsonify({"trading_enabled": is_trading_enabled, "message": msg})


@app.route("/api/stats/reset", methods=["POST"])
def api_stats_reset():
    resp = require_dashboard_auth()
    if resp:
        return resp
    db.execute("DELETE FROM signals")
    db.execute("DELETE FROM notifications")
    set_paper_balance(PAPER_BALANCE_START)
    with detections_lock:
        recent_detections.clear()
    with scan_stats_lock:
        for k in scan_stats:
            scan_stats[k] = 0
    msg = "🧹 تم تصفير الإحصائيات والصفقات وإرجاع الرصيد الورقي إلى البداية"
    log_and_notify("info", msg, "STATS_RESET")
    return jsonify({"ok": True, "message": msg})


def get_dashboard_html():
    from panel import PANEL_HTML
    return PANEL_HTML


# ══════════════════════════════════════════════════════════════════════════════
# التشغيل الرئيسي
# ══════════════════════════════════════════════════════════════════════════════

def restore_trading_flag() -> None:
    global is_trading_enabled
    flag = db_get_state("trading_enabled", "0")
    is_trading_enabled = (flag == "1")
    logger.info("حالة توليد الإشارات الورقية المستعادة: %s", "مفعّلة" if is_trading_enabled else "معطلة")


def load_markets_async() -> None:
    def _load():
        for name, ex in EXCHANGES.items():
            try:
                ex.load_markets()
                logger.info("تحميل أسواق المزود %s اكتمل (دقة الكميات جاهزة)", name)
            except Exception as exc:
                logger.warning("تعذر تحميل أسواق المزود %s — يُعاد تلقائيًا عند أول جلب: %s", name, exc)
    t = threading.Thread(target=_load, daemon=True)
    t.start()


def initialize_bot_services() -> None:
    init_db()
    restore_trading_flag()
    load_markets_async()
    threading.Thread(target=scan_loop, daemon=True, name="scan-loop").start()
    threading.Thread(target=monitor_loop, daemon=True, name="monitor-loop").start()
    threading.Thread(target=keep_alive_loop, daemon=True, name="keep-alive").start()
    log_and_notify(
        "info",
        f"🚀 Fibo-Elio {BOT_VERSION} أقلع — استراتيجية واحدة: Elliott_Fibonacci (المنطق الأصلي)\n"
        f"وضع ورقي دائم | أزواج: {len(watchlist)} | فريم الكشف {SIGNAL_TIMEFRAME} | التنفيذ {ENTRY_TIMEFRAME}\n"
        f"انعكاس الزيجزاج {DEVIATION_THRESHOLD*100:.2f}% | أقصى صفقات {MAX_OPEN_TRADES} | مخاطرة {RISK_PCT_PER_TRADE}%",
        "BOOT",
    )


if __name__ == "__main__":
    initialize_bot_services()
    app.run(host="0.0.0.0", port=PORT, threaded=True)
