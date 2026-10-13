#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
 FIBO-ELIO — بوت موجة إليوت + مستويات فيبوناتشي  (FE1.0.2)
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

 الوضع الافتراضي ورقي آمن: محاكاة برصيد وهمي (PAPER_BALANCE) ورسوم واقعية 0.1%
 للاتجاهين، ومفتاح التوليد يتحكم في إنتاج إشارات جديدة فقط.

 FE1.4.0: التداول الحقيقي بزر مثل نسخة V9 + لوحة سبرانية نيون:
 • زر «التداول الحقيقي» في اللوحة (مثل V9): تفعيله يحول الإشارات الجديدة إلى
   أوامر فعلية على باينانس — LIMIT BUY عند فيبو 0.382 (أمر معلق حقيقي على
   المنصة) → بيع سوق فعلي عند الوقف/الهدف/الإبطال.
 • شروط التفعيل الصارمة: مفاتيح باينانس مضبوطة + فحص اتصال حي ناجح + رصيد USDT
   مقروء — وإلا يرفض الزر التفعيل برسالة واضحة. الإيقاف يعيد الوضع الورقي فورًا
   (الصفقات الحقيقية المفتوحة تستمر بالإدارة حتى إغلاقها).
 • قواعد باينانس كاملة (بدون نسيان): دقة الكمية/السعر (LOT_SIZE/PRICE_FILTER
   عبر amount_to_precision/price_to_precision)، أدنى قيمة الأمر (NOTIONAL/
   MIN_NOTIONAL من قواعد السوق)، أدنى كمية، كفاية رصيد USDT الحر، سقف أمان
   REAL_MAX_NOTIONAL_USDT لكل أمر، وضع TESTNET اختياري (BINANCE_TESTNET).
 • بطاقة «اتصال باينانس» حية في اللوحة: الاتصال، زمن الاستجابة، رصيد USDT،
   صلاحية التداول — مع نقطة /api/binance/status مستقلة وكاش 60 ثانية.
 • المحاسبة: الصفقة الحقيقية تُسجل مثل الورقية (أرباح/نسب/إشعارات) لكن دون أي
   مساس بالرصيد الورقي — وعمود «الوضع» في اللوحة يفرز حقيقية/ورقية.

 FE1.0.1: طبقة مزودي بيانات متعددة — باينانس أولًا كما في الأصل، ثم Bybit → OKX
 → Gate.io تلقائيًا عند الحظر/الفشل. الدرس المستفاد من المشروع السابق: عنوان
 الخروج المشترك لخدمات Render يتعرض لحظر وزن باينانس (-1003) المتجدد بسبب
 استهلاك الخدمات الأخرى على نفس العنوان، فالبدائل العامة بحدود سخية تضمن استمرار
 الرؤية للسوق دون أي تغيير على المنطق الأصلي أو الوضع الورقي.

 FE1.0.2: فريم الكشف 15m (طلب المستخدم + جدول معايرة المؤلف: نطاق 15m
 0.004–0.008 «Primary entry TF» والانعكاس 0.006 في منتصفه) + حماية افتراضية
 للوحة (admin/test123) حتى بلا متغيرات بيئة — النشر اليدوي كان يتركها مكشوفة.

 FE1.1.0: تتبع حي لكل صفقة + تحكم يدوي من اللوحة:
 • السعر الحي لكل صفقة مفتوحة/معلقة (ذاكرة مؤقتة 20 ثانية لتخفيف ضغط المزودين)
 • الربح/الخسارة غير المحقق لكل صفقة (صافي بعد رسوم الاتجاهين) ونسبة التقدم نحو الهدف
 • إغلاق يدوي بسعر السوق للصفقات المفتوحة (POST /api/trades/close)
 • إلغاء يدوي للأوامر المعلقة (POST /api/trades/cancel)
 الحلقة الآلية للوقف/الهدف لم تتغير — اليدوي بديل متاح في أي لحظة.

 FE1.1.1: إصلاح حرج اكتشفه التتبع الحي — fetch_ohlcv_df كانت ترفض أي استجابة
 أقل من 60 شمعة، بينما حلقة المراقبة (ملء المعلق + وقف/هدف المفتوح) تجلب شمعتين
 فقط limit=2 فكانت تُهدر النتيجة وتتجاهل الصفقات: لا ملء ولا إغلاق آلي أبدًا.
 الحل: معامل min_candles — المسح 60+ كما هو، والمراقبة/السعر الحي 2.

 FE1.2.0: الأسعار الحية من ويب سوكت لا REST (طلب المستخدم «اريد جلب الاسعار
 الحية من ويب سوكت وليس كطلبات api»):
 • خيط مستقل بحلقة asyncio دائمة يشترك عبر ccxt.pro في تيارين لكل رمز نشط:
    watch_ohlcv (شموع 15m حية — للملء/الوقف/الهدف والسعر الاحتياطي)
    watch_ticker (آخر سعر — الأحدث زمنيًا يفوز في العرض)
 • الاشتراك فقط للرموز ذات صفقات نشطة (معلق/مفتوح) — مزامنة كل 10 ثوانٍ
 • تعاقب مزودين للويب سوكت أيضًا: باينانس ← Bybit ← OKX ← Gate عند الفشل
 • لا REST للأسعار الحية ما دام تيار ويب سوكت حيًا (حداثة ≤ WS_STALE_SEC)؛
   REST يبقى احتياطًا تلقائيًا عند تعطل/غياب التيار — بلا أي تغيير على المنطق
 • /api/ws/status تشخيص كامل + شارة مصدر السعر (WS/REST) في اللوحة

 متغيرات البيئة (نفس عقد المشروع السابق + إعدادات الاستراتيجية):
   BINANCE_API_KEY / BINANCE_API_SECRET  (اختياريان — الشموع العامة تكفي للورقي،
                                         والمفتاحان مطلوبان لزر التداول الحقيقي فقط)
   BINANCE_TESTNET       "1" لتنفيذ الأوامر الحقيقية على تيستنت باينانس (اختباري)
   REAL_MAX_NOTIONAL_USDT سقف قيمة أمر الشراء الحقيقي الواحد (افتراضي 50$)
   DATABASE_URL          اختياري (PostgreSQL) — وإلا SQLite محلي
   TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID اختياريان
   DASHBOARD_USERNAME / DASHBOARD_PASSWORD حماية اللوحة — الافتراضي admin/test123
   (يُنصح بضبطهما من متغيرات البيئة في Render لرفع الافتراضي)
   DEVIATION_THRESHOLD   نسبة انعكاس الزيجزاج (افتراضي 0.006 = 0.6% لفريم 1h)
   SIGNAL_TIMEFRAME      فريم الكشف (افتراضي 1h)   ENTRY_TIMEFRAME فريم التنفيذ (15m)
   MAX_OPEN_TRADES       أقصى صفقات متزامنة (معلقة + مفتوحة) — الافتراضي 3، الإنتاج 5 عبر render.yaml     RISK_PCT_PER_TRADE مخاطرة الصفقة (1%)
   PENDING_MAX_CANDLES   صلاحية الأمر المعلق بشموع الكشف (3)
   PAPER_BALANCE         الرصيد الورقي (10000)
"""

import asyncio
import json
import logging
import math
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import gc
import pandas as pd
import requests

try:  # تحميل اختياري لملف .env محليًا
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from flask import Flask, Response, jsonify, request

import ccxt
try:  # [FE1.2.0] تفعيل مساحة ccxt.pro (ويب سوكت) — متوفرة ضمن حزمة ccxt الحديثة
    import ccxt.pro  # noqa: F401
    _HAS_CCXT_PRO = True
except Exception:
    _HAS_CCXT_PRO = False

from engine.pattern_detector import DetectorConfig, DetectedSetup, PivotDetector
from engine.wave_validator import validate_impulse
from engine.fibonacci import FibonacciLevels
from utils.logger import get_logger, fmt_price

# ══════════════════════════════════════════════════════════════════════════════
# الإعدادات — البيئة هي مصدر الحقيقة
# ══════════════════════════════════════════════════════════════════════════════

BOT_VERSION = "FE1.4.0"  # FE1.4.0: زر التداول الحقيقي مثل V9 + قواعد باينانس الكاملة + بطاقة اتصال باينانس + لوحة سبرانية نيون
STRATEGY_NAME = "Elliott_Fibonacci"
REPO_URL = "https://github.com/salah55t/fibo-elio"

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")     # [FE1.0.2] افتراضي عهد المشروع — يُرفع من متغيرات البيئة
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "test123")   # [FE1.0.2] اللوحة تبقى محمية حتى بلا متغيرات بيئة (نشر يدوي)

# [FE1.0.2] فريم الكشف 15m — بطلب المستخدم («اريد تغيير الفريم الفحص الى 15 دقيقة بدل الساعة»)
# وبجدول معايرة المؤلف (engine/pattern_detector.py): نطاق 15m = 0.004–0.008 «Primary entry TF»
# والانعكاس 0.006 يقع في منتصف نطاق 15م — القيمة القديمة 1h تبقى متاحة عبر متغير البيئة SIGNAL_TIMEFRAME
SIGNAL_TIMEFRAME = os.getenv("SIGNAL_TIMEFRAME", "15m")
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

# [FE1.2.0] تغذية الأسعار الحية عبر ويب سوكت (ccxt.pro) — REST احتياطًا فقط
WS_ENABLED = os.getenv("WS_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
WS_STALE_SEC = float(os.getenv("WS_STALE_SEC", "90"))     # أقدم عمر مقبول لبيانات الويب سوكت قبل الرجوع لـ REST
WS_SYNC_INTERVAL = float(os.getenv("WS_SYNC_INTERVAL", "10"))  # إيقاع مزامنة الاشتراكات مع الصفقات النشطة
WS_RECV_TIMEOUT_SEC = float(os.getenv("WS_RECV_TIMEOUT_SEC", "60"))  # مهلة انتظار رسالة قبل اعتبار المزود ميتًا

# [FE1.3.0] البقاء الحي — نبضة ذاتية إلى /health العام (بلا مصادقة) تمنع نوم Render المجاني
# (الخطة المجانية تُخمد الخدمة بعد 15 دقيقة بلا طلبات خارجية، والاستيقاظ يأخذ نحو دقيقة)
# القديم FE1.2.0: نبضة كل 14 دقيقة بلا إعادة محاولة — أي فشل عابر واحد كان يسمح بالنوم
KEEP_ALIVE_ENABLED = os.getenv("KEEP_ALIVE_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
KEEP_ALIVE_INTERVAL_SEC = float(os.getenv("KEEP_ALIVE_INTERVAL_SEC", "600"))  # نبضة كل 10 دقائق — هامش أمان مزدوج تحت سقف 15 دقيقة
KEEP_ALIVE_URL = os.getenv("KEEP_ALIVE_URL", "")  # تجاوز يدوي اختياري (مثال: https://fibo-elio.onrender.com)
PANEL_URL = os.getenv("PANEL_URL", "")            # بديل اشتقاق ثانٍ إن لم يُحقن RENDER_EXTERNAL_URL (نشر خارج Render)

# [FE1.3.1] حمية الذاكرة — الخطة المجانية 512MB وأعطال OOM («Instance failed: ran out of memory»)
# كانت تعيد إقلاع الخدمة كل دقائق = «الخمول» الظاهري. السبب: تحميل أسواق 4 منصات كاملة (~40-80MB لكل واحدة)
MEM_LAZY_MARKETS = os.getenv("MEM_LAZY_MARKETS", "1").strip().lower() not in ("0", "false", "no", "off")
MEM_PRUNE_MARKETS = int(os.getenv("MEM_PRUNE_MARKETS", "400"))    # لا يُقلَّم مزود أسواقه أقل من هذا العدد
MEM_GC_THRESHOLD_MB = float(os.getenv("MEM_GC_THRESHOLD_MB", "380"))  # تجميع قسري فوق هذا
MEM_CRITICAL_MB = float(os.getenv("MEM_CRITICAL_MB", "450"))          # سجل حرج فوق هذا

# [FE1.4.0] التداول الحقيقي — زر مثل V9: تفعيله يحول الإشارات الجديدة إلى أوامر
# فعلية على باينانس (LIMIT عند فيبو 0.382 ← بيع سوق عند الوقف/الهدف). الورقي يبقى
# الوضع الافتراضي الآمن، والتفعيل يتطلب مفاتيح + فحص اتصال ناجح من الزر نفسه.
BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "0").strip().lower() in ("1", "true", "yes", "on")
REAL_MAX_NOTIONAL_USDT = float(os.getenv("REAL_MAX_NOTIONAL_USDT", "50.0"))  # سقف قيمة أمر الشراء الحقيقي الواحد (حماية)
BIN_STATUS_TTL_SEC = float(os.getenv("BIN_STATUS_TTL_SEC", "60"))  # كاش بطاقة اتصال باينانس

DASHBOARD_PROTECTED = bool(DASHBOARD_USERNAME and DASHBOARD_PASSWORD)
USE_POSTGRES = DATABASE_URL.startswith("postgres")

TF_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600,
    "2h": 7200, "4h": 14400, "6h": 21600, "8h": 28800, "12h": 43200, "1d": 86400,
}

logger = get_logger("fibo-elio")


# [FE1.3.1] أدوات قياس وتنظيف الذاكرة — بلا تبعيات خارجية (قراءة /proc مباشرة)
def rss_mb() -> float:
    """الذاكرة المقيمة الحالية بالميجابايت — 0.0 إن لم تتوفر /proc (بيئات غير لينكس)."""
    try:
        with open("/proc/self/status", "r") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return float(int(line.split()[1])) / 1024.0
    except Exception:
        pass
    return 0.0


def mem_check(reason: str = "") -> float:
    """قياس + تنظيف ذكي: gc.collect() فوق عتبة التحذير، وسجل حرج فوق الحد الأخير.
    تُستدعى دوريًا من حلقات المسح/المراقبة — قراءة /proc رخيصة والتنظيف عند الحاجة فقط.
    تعيد RSS الحالية بالميجابايت."""
    m = rss_mb()
    if m >= MEM_GC_THRESHOLD_MB:
        gc.collect()
        m2 = rss_mb()
        tag = f" ({reason})" if reason else ""
        if m2 >= MEM_CRITICAL_MB:
            logger.critical("الذاكرة حرجة %.0fMB بعد التنظيف (كانت %.0fMB)%s — اقتراب من سقف 512MB", m2, m, tag)
        else:
            logger.info("تنظيف ذاكرة%s: %.0fMB ← %.0fMB", tag, m, m2)
        return m2
    return m


def prune_markets(ex: Any, keep: Optional[List[str]] = None) -> int:
    """[FE1.3.1] تقليم أسواق مزود محمّل: الاحتفاظ بالأزواج المطلوبة فقط (قائمة المراقبة).
    أسواق ccxt الكاملة (آلاف الأزواج بفلاترها ودقتها) تلتهم عشرات الميجابايت لكل مزود.
    يعيد عدد الأزواج المتبقية، أو -1 عند أي فشل (يبقى الوضع الكامل — آمن دائمًا)."""
    try:
        keep_set = set(keep or watchlist)
        markets = getattr(ex, "markets", None)
        if not isinstance(markets, dict):
            return -1
        if len(markets) <= MEM_PRUNE_MARKETS:
            return len(markets)  # صغير أصلًا — لا فائدة من التقليم
        slim: Dict[str, Any] = {}
        for k, m in markets.items():
            if k in keep_set:
                slim[k] = m
            elif isinstance(m, dict) and (m.get("symbol") in keep_set or m.get("id") in keep_set):
                slim[k] = m
        if len(slim) >= len(markets):
            return len(markets)
        ex.markets = slim
        mbid = getattr(ex, "markets_by_id", None)
        if isinstance(mbid, dict) and mbid:
            ex.markets_by_id = {
                i: m for i, m in mbid.items()
                if i in keep_set or (isinstance(m, dict) and (m.get("symbol") in keep_set or m.get("id") in keep_set))
            }
        return len(slim)
    except Exception as exc:
        logger.debug("تقليم الأسواق لم يُكمل: %s", exc)
        return -1

# حالة التشغيل — [FE1.4.0] مفتاحان مثل V9: التوليد (ورقي/إيقاف) + التداول الحقيقي
is_trading_enabled: bool = False
trading_status_lock = threading.Lock()
is_real_mode: bool = False            # زر التداول الحقيقي — افتراضيًا متوقف (ورقي آمن)
real_mode_lock = threading.Lock()

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
  is_real INTEGER DEFAULT 0,
  order_id TEXT,
  exit_order_id TEXT,
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


def migrate_db() -> None:
    """[FE1.4.0] أعمدة التداول الحقيقي لقواعد بيانات قديمة (ALTER بلا أذى إن وُجدت)."""
    for col, ddl in (("is_real", "INTEGER DEFAULT 0"), ("order_id", "TEXT"), ("exit_order_id", "TEXT")):
        try:
            db.execute(f"ALTER TABLE signals ADD COLUMN {col} {ddl}")
        except Exception:
            pass


def init_db() -> None:
    ddl = _SIGNALS_DDL_PG if USE_POSTGRES else _SIGNALS_DDL_SQLITE
    for attempt in range(5):
        try:
            for stmt in [s.strip() for s in ddl.split(";") if s.strip()]:
                db.execute(stmt)
            migrate_db()
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
        # [FE1.3.2] spot فقط: bybit/okx يحمّلان افتراضيًا عقودًا مستقبلية وخيارات = ذروة 100-200MB عند التحميل
        "options": {"defaultType": "spot", "fetchMarkets": ["spot"]},
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
            if not st.get("markets_pruned"):  # [FE1.3.1] تقليم لمرة واحدة بعد أول جلب ناجح
                st["markets_pruned"] = True
                n = prune_markets(EXCHANGES[name])
                if n >= 0:
                    logger.info("تقليم أسواق %s بعد أول جلب — بقي %d زوج فقط (حمية الذاكرة)", name, n)
            return raw, name
        except Exception as exc:
            with provider_lock:
                st = provider_state[name]
                st["fail"] += 1
                st["last_error"] = str(exc)[:280]
                st["cooldown_until"] = time.time() + PROVIDER_COOLDOWN_SEC
            if not st.get("markets_pruned"):  # [FE1.3.2] تقليم عند الفشل أيضًا — ccxt حمّل الأسواق قبل الطلب (حظر جغرافي مثلاً)
                st["markets_pruned"] = True
                n = prune_markets(EXCHANGES[name])
                if n >= 0:
                    logger.info("تقليم أسواق %s بعد فشل جلب (حُمّلت ضمن المحاولة) — بقي %d زوج فقط", name, n)
            errors.append(f"{name}: {str(exc)[:120]}")
    if errors:
        logger.warning("فشل جلب %s %s من المزودين المتاحين — %s", symbol, timeframe, " | ".join(errors))
    return None, None


def fetch_ohlcv_df(symbol: str, timeframe: str, limit: int = OHLCV_LIMIT,
                   min_candles: int = 60) -> Optional[pd.DataFrame]:
    """شموع OHLCV كإطار pandas بعقد الطبقة الأولى (timestamp/open/high/low/close/volume).
    [FE1.0.1] عبر تعاقب المزودين — باينانس أولًا كما في الأصل ثم البدائل آليًا.
    [FE1.1.1] min_candles: الحد الأدنى المطلوب — المسح يحتاج 60+، والمراقبة/السعر الحي
    تجلب شمعتين فقط (limit=2) فتمرر min_candles=2 وإلا رُفضت استجاباتها القصيرة
    وهُدرت (هذا كان يعطل حلقة المراقبة كاملة قبل FE1.1.1)."""
    for attempt in range(3):
        raw, _src = fetch_ohlcv_raw(symbol, timeframe, limit)
        if raw:
            if len(raw) < min_candles:
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
# [FE1.4.0] طبقة التداول الحقيقي — باينانس مباشرة بقواعد المنصة الكاملة
# المبدأ: الورقي يبقى الافتراضي، والزر يفعّل تنفيذ الإشارات الجديدة فعليًا.
# كل أمر يمر عبر قواعد باينانس: دقة الكمية/السعر، أدنى قيمة/كمية، كفاية الرصيد.
# ══════════════════════════════════════════════════════════════════════════════

_trade_ex_lock = threading.Lock()
_trade_ex: Any = None            # نسخة التداول (مفاتيح خاصة) — تُبنى مرة واحدة كسولًا
_trade_pruned = False            # تقليم أسواق نسخة التداول لمرة واحدة (حمية الذاكرة)
_bin_probe: Any = None           # نسخة عامة بلا مفاتيح لفحص الاتصال عندما لا توجد مفاتيح
_bin_status_lock = threading.Lock()
_bin_status_cache: Dict[str, Any] = {"ts": 0.0, "data": None}


def binance_trade_exchange():
    """نسخة تداول باينانس بالمفاتيح (spot) — بلا مفاتيح ترجع None فلا تداول حقيقي إطلاقًا."""
    global _trade_ex
    if not (API_KEY and API_SECRET):
        return None
    with _trade_ex_lock:
        if _trade_ex is None:
            ex = ccxt.binance({
                "apiKey": API_KEY, "secret": API_SECRET,
                "enableRateLimit": True,
                "options": {"defaultType": "spot", "fetchMarkets": ["spot"],
                            "adjustForTimeDifference": True},
            })
            if BINANCE_TESTNET:
                ex.set_sandbox_mode(True)
                logger.info("التداول الحقيقي: وضع TESTNET مفعّل (BINANCE_TESTNET=1)")
            _trade_ex = ex
        return _trade_ex


def _binance_public_probe():
    """نسخة عامة رخيصة لفحص الاتصال فقط عندما لا توجد مفاتيح — لا أسواق ولا ذاكرة تُذكر."""
    global _bin_probe
    if _bin_probe is None:
        _bin_probe = ccxt.binance({
            "enableRateLimit": True,
            "options": {"defaultType": "spot", "fetchMarkets": ["spot"]},
        })
    return _bin_probe


def binance_status_snapshot(force: bool = False) -> Dict[str, Any]:
    """[FE1.4.0] حالة اتصال باينانس للوحة: ping حي + زمن استجابة + (بمفاتيح)
    رصيد USDT وصلاحية التداول. كاش BIN_STATUS_TTL_SEC — لا ضغط على باينانس
    مهما تكرر تحديث اللوحة، وبلا استثناءات أبدًا."""
    now = time.time()
    with _bin_status_lock:
        if not force and _bin_status_cache["data"] is not None and now - _bin_status_cache["ts"] < BIN_STATUS_TTL_SEC:
            return dict(_bin_status_cache["data"])
    keys_ok = bool(API_KEY and API_SECRET)
    data: Dict[str, Any] = {
        "connected": False, "keys_present": keys_ok, "testnet": BINANCE_TESTNET,
        "latency_ms": None, "usdt_free": None, "usdt_total": None, "can_trade": None,
        "error": None, "checked_at": utc_now_iso(),
    }
    try:
        ex = binance_trade_exchange() if keys_ok else _binance_public_probe()
        if ex is None:
            raise RuntimeError("تعذر إنشاء اتصال باينانس")
        t0 = time.time()
        ex.fetch_time()  # نقطة عامة خفيفة — مقياس الاتصال وزمن الاستجابة
        data["connected"] = True
        data["latency_ms"] = round((time.time() - t0) * 1000.0)
        if keys_ok:
            bal = ex.fetch_balance()
            usdt = (bal or {}).get("USDT") or {}
            data["usdt_free"] = float(usdt.get("free") or 0.0)
            data["usdt_total"] = float(usdt.get("total") or 0.0)
            info = (bal or {}).get("info") or {}
            ct = info.get("canTrade")
            data["can_trade"] = bool(ct) if ct is not None else None
    except Exception as exc:
        data["error"] = str(exc)[:220]
    with _bin_status_lock:
        _bin_status_cache["ts"] = now
        _bin_status_cache["data"] = dict(data)
    return data


def real_market(ex, symbol: str) -> Dict[str, Any]:
    """قواعد السوق من باينانس (فلاتر الدقة/الكمية/القيمة) — بلا استثناءات أبدًا."""
    try:
        if not ex.markets:
            ex.load_markets()
            global _trade_pruned
            if not _trade_pruned:
                _trade_pruned = True
                n = prune_markets(ex, list(dict.fromkeys(list(watchlist) + [symbol])))
                if n >= 0:
                    logger.info("تقليم أسواق نسخة التداول — بقي %d زوج فقط (حمية الذاكرة)", n)
        return ex.markets.get(symbol) or {}
    except Exception as exc:
        logger.warning("تعذر جلب قواعد السوق %s: %s", symbol, exc)
        return {}


def real_min_cost(mkt: Dict[str, Any]) -> float:
    """أدنى قيمة أمر (NOTIONAL/MIN_NOTIONAL) — من قواعد باينانس، وإلا الافتراضي المحلي."""
    try:
        c = ((mkt or {}).get("limits") or {}).get("cost") or {}
        v = c.get("min")
        if v:
            return float(v)
    except Exception:
        pass
    return MIN_NOTIONAL_USDT


def real_min_amount(mkt: Dict[str, Any]) -> float:
    """أدنى كمية (LOT_SIZE.minQty) — 0 إن غابت القاعدة."""
    try:
        a = ((mkt or {}).get("limits") or {}).get("amount") or {}
        v = a.get("min")
        if v is not None:
            return float(v)
    except Exception:
        pass
    return 0.0


def real_adjust_amount(ex, symbol: str, qty: float) -> float:
    """أرضية الكمية على خطوة LOT_SIZE (amount_to_precision) — بأمان تام بلا استثناءات."""
    try:
        v = float(ex.amount_to_precision(symbol, qty))
        return v if v > 0 else 0.0
    except Exception:
        return math.floor(qty * 1e6) / 1e6


def real_adjust_price(ex, symbol: str, price: float) -> float:
    """دقة السعر على tickSize (price_to_precision) — بأمان تام بلا استثناءات."""
    try:
        return float(ex.price_to_precision(symbol, price))
    except Exception:
        return price


def compute_quantity_real(symbol: str, entry: float, sl: float, free_usdt: float,
                          ex=None) -> Optional[float]:
    """حجم المركز الحقيقي: مخاطرة RISK_PCT_PER_TRADE من رصيد USDT الفعلي الحر
    + سقف أمان REAL_MAX_NOTIONAL_USDT + قواعد باينانس (LOT_SIZE، أدنى كمية،
    أدنى قيمة NOTIONAL، كفاية الرصيد). يرفض بأمان عند أي قاعدة غير محققة."""
    if free_usdt is None or free_usdt <= 0:
        log_and_notify("error", f"❌ رفض أمر حقيقي {symbol}: رصيد USDT الحر صفر أو غير مقروء", "REAL_TRADE_ERROR")
        return None
    ex = ex or binance_trade_exchange()
    risk_amount = free_usdt * (RISK_PCT_PER_TRADE / 100.0)
    risk_per_coin = abs(entry - sl)
    if risk_per_coin <= 0 or risk_amount <= 0:
        return None
    qty = risk_amount / risk_per_coin
    if ex is not None:
        qty = real_adjust_amount(ex, symbol, qty)
    if qty <= 0:
        return None
    notional = qty * entry
    if notional > REAL_MAX_NOTIONAL_USDT:
        cap_qty = REAL_MAX_NOTIONAL_USDT / entry
        qty = real_adjust_amount(ex, symbol, cap_qty) if ex else math.floor(cap_qty * 1e6) / 1e6
        notional = qty * entry
    mkt = real_market(ex, symbol)
    min_amt = real_min_amount(mkt)
    min_cost = real_min_cost(mkt)
    if min_amt and qty < min_amt:
        log_and_notify("error", f"❌ رفض أمر حقيقي {symbol}: الكمية {qty} تحت أدنى كمية باينانس {min_amt}", "REAL_TRADE_ERROR")
        return None
    if notional < min_cost:
        # ارفع لأدنى قيمة تداول فقط إن بقيت المخاطرة ضمن 3× المخططة (نفس مبدأ الورقي)
        qty_min = min_cost / entry
        if qty_min * risk_per_coin <= risk_amount * 3.0:
            qty = real_adjust_amount(ex, symbol, qty_min) if ex else math.floor(qty_min * 1e6) / 1e6
            notional = qty * entry
        else:
            log_and_notify("error",
                           f"❌ رفض أمر حقيقي {symbol}: مسافة الوقف أوسع من أن تتحمل أدنى قيمة "
                           f"باينانس ({min_cost:.2f}$) ضمن حد المخاطرة", "REAL_TRADE_ERROR")
            return None
    if notional > free_usdt:
        log_and_notify("error",
                       f"❌ رفض أمر حقيقي {symbol}: القيمة {notional:.2f}$ تتجاوز رصيد USDT الحر {free_usdt:.2f}$",
                       "REAL_TRADE_ERROR")
        return None
    return qty


def place_real_limit_buy(symbol: str, price: float, qty: float) -> Optional[Dict[str, Any]]:
    """أمر LIMIT BUY حقيقي عند فيبو 0.382 — يبقى معلقًا على المنصة كأمر حقيقي."""
    ex = binance_trade_exchange()
    if ex is None:
        return None
    try:
        order = ex.create_order(symbol, "limit", "buy", qty, price, {"newOrderRespType": "FULL"})
        log_and_notify("info",
                       f"🟢 أمر حقيقي على باينانس: شراء LIMIT {symbol} — كمية {qty} عند {fmt_price(price)} "
                       f"(id={order.get('id')})", "REAL_ORDER")
        return order
    except Exception as exc:
        log_and_notify("error", f"❌ فشل أمر الشراء الحقيقي {symbol}: {exc}", "REAL_TRADE_ERROR")
        return None


def place_real_market_sell(symbol: str, qty: float) -> Optional[Dict[str, Any]]:
    """أمر بيع سوق حقيقي — للإغلاق عند الوقف/الهدف/يدويًا."""
    ex = binance_trade_exchange()
    if ex is None:
        return None
    try:
        order = ex.create_order(symbol, "market", "sell", qty, None, {"newOrderRespType": "FULL"})
        log_and_notify("info",
                       f"🔴 أمر حقيقي على باينانس: بيع سوق {symbol} — كمية {qty} (id={order.get('id')})",
                       "REAL_ORDER")
        return order
    except Exception as exc:
        log_and_notify("error", f"❌ فشل أمر البيع الحقيقي {symbol}: {exc}", "REAL_TRADE_ERROR")
        return None


def fetch_real_order(ex, symbol: str, order_id: Any) -> Optional[Dict[str, Any]]:
    """حالة الأمر الحقيقي من المنصة — None عند فشل عابر (تُعاد المحاولة في الدورة القادمة)."""
    try:
        return ex.fetch_order(order_id, symbol)
    except Exception as exc:
        logger.warning("تعذر جلب حالة الأمر الحقيقي %s/%s: %s", symbol, order_id, exc)
        return None


def cancel_real_order(ex, symbol: str, order_id: Any) -> bool:
    """إلغاء أمر معلق حقيقي — False يعني إعادة الفحص/المحاولة في الدورة القادمة."""
    try:
        ex.cancel_order(order_id, symbol)
        return True
    except Exception as exc:
        logger.warning("تعذر إلغاء الأمر الحقيقي %s/%s: %s", symbol, order_id, exc)
        return False


def fetch_free_base(ex, base: str) -> float:
    """الرصيد الحر للعملة الأساسية — للتحقق قبل البيع (نفس منطق V9)."""
    try:
        bal = ex.fetch_balance()
        cur = (bal or {}).get(base) or {}
        return float(cur.get("free") or 0.0)
    except Exception as exc:
        logger.warning("تعذر جلب رصيد %s الحر: %s", base, exc)
        return 0.0


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


# ── FE1.2.0: تغذية أسعار حية عبر ويب سوكت (ccxt.pro) — REST احتياطًا فقط ──────
# المبدأ: تياران لكل رمز نشط (شموع 15m + ticker) يغذيان الذاكرة أدناه، وكل
# مستخدمي السعر (اللوحة/المراقبة/الإحصاء) يقرؤون من الذاكرة أولًا — REST لا
# يُستدعى إلا عند غياب التيار أو تقادمه (فشل شبكة مثلاً) فلا انقطاع للخدمة.

_ws_lock = threading.Lock()
_ws_price: Dict[str, Dict[str, Any]] = {}    # symbol -> {price, ts(epoch), source}
_ws_candles: Dict[str, Dict[str, Any]] = {}  # symbol -> {candles: [[ts,o,h,l,c,v]...], ts, source}
_ws_subs: Dict[str, Dict[str, Any]] = {}     # symbol -> {provider, state, last_error, updates, last_msg_at, started_at}
_ws_tasks: Dict[str, Dict[str, Any]] = {}    # symbol -> {"ohlcv": Task, "ticker": Task}
_ws_exchanges: Dict[str, Any] = {}           # اسم المزود -> نسخة ccxt.pro (اتصالات عامة بلا مفاتيح)
_ws_loop: Any = None
_ws_thread_started = False
WS_CANDLE_KEEP = 5                 # نحتفظ بآخر 5 شموع (الأخيرة قيد التكوين كما في REST)
WS_PRICE_FROM_CANDLE_TTL = 30.0    # املا السعر من إغلاق الشمعة إن غاب الـ ticker أطول من ذلك


def _ws_mark(symbol: str, provider: str, state: str, error: str = "") -> None:
    """تحديث حالة اشتراك رمز للتشخيص (/api/ws/status واللوحة)."""
    with _ws_lock:
        sub = _ws_subs.setdefault(symbol, {
            "provider": provider, "state": state, "last_error": "",
            "updates": 0, "last_msg_at": None, "started_at": utc_now_iso(),
        })
        sub["provider"] = provider
        sub["state"] = state
        sub["last_error"] = error[:200]


def ws_apply_price(symbol: str, price: Any, source: str) -> bool:
    """تحديث السعر الحي من تيار ticker — دالة متزامنة قابلة للاختبار مباشرة."""
    try:
        p = float(price)
    except (TypeError, ValueError):
        return False
    if not (p > 0) or math.isnan(p) or math.isinf(p):
        return False
    now = time.time()
    with _ws_lock:
        _ws_price[symbol] = {"price": p, "ts": now, "source": source}
        sub = _ws_subs.get(symbol)
        if sub is not None:
            sub["updates"] += 1
            sub["last_msg_at"] = utc_now_iso()
            sub["state"] = "live"
            sub["last_error"] = ""
    return True


def ws_apply_ohlcv(symbol: str, candles: Any, source: str) -> bool:
    """تحديث شموع فريم التنفيذ من تيار watch_ohlcv — الأخيرة قيد التكوين كما في REST.
    الدمج حسب الطابع الزمني: بعض المزودين يرسلون الشمعة الجارية وحدها فلا يجوز
    أن يمحو التيار تاريخ البذرة المغلق، والنافذة تُقص لآخر WS_CANDLE_KEEP شموع.
    تُنظّف الصفوف الناقصة، ويُملأ السعر من إغلاق الشمعة الجارية إن غاب الـ ticker."""
    if not isinstance(candles, (list, tuple)) or not candles:
        return False
    clean: List[List[float]] = []
    for c in candles:
        try:
            if len(c) < 6:
                continue
            ts, o, h, lo, cl = c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4])
            if not (ts and o > 0 and h > 0 and lo > 0 and cl > 0):
                continue
            clean.append([int(ts), o, h, lo, cl, float(c[5])])
        except (TypeError, ValueError, IndexError):
            continue
    if not clean:
        return False
    with _ws_lock:
        existing = _ws_candles.get(symbol)
    if existing and existing["candles"]:
        by_ts = {int(row[0]): row for row in existing["candles"]}
        for row in clean:
            by_ts[int(row[0])] = row  # الشمعة الجارية تُحدّث، المغلقة تبقى
        clean = [by_ts[k] for k in sorted(by_ts)][-WS_CANDLE_KEEP:]
    else:
        clean = clean[-WS_CANDLE_KEEP:]
    now = time.time()
    with _ws_lock:
        _ws_candles[symbol] = {"candles": clean, "ts": now, "source": source}
        sub = _ws_subs.get(symbol)
        if sub is not None:
            sub["updates"] += 1
            sub["last_msg_at"] = utc_now_iso()
            sub["state"] = "live"
            sub["last_error"] = ""
    with _ws_lock:
        cur = _ws_price.get(symbol)
    if not cur or now - cur["ts"] >= WS_PRICE_FROM_CANDLE_TTL:
        ws_apply_price(symbol, clean[-1][4], source)  # إغلاق الشمعة الجارية = آخر سعر
    return True


def ws_feed_snapshot() -> Dict[str, Any]:
    """لقطة حالة تغذية الويب سوكت للوحة والتشخيص — بلا استثناءات أبدًا."""
    now = time.time()
    with _ws_lock:
        subs = {s: dict(v) for s, v in _ws_subs.items()}
        prices = {s: {"price": v["price"], "age_sec": round(now - v["ts"], 1), "source": v["source"]}
                  for s, v in _ws_price.items()}
        candles = {s: {"n": len(v["candles"]), "age_sec": round(now - v["ts"], 1), "source": v["source"]}
                   for s, v in _ws_candles.items()}
        symbols = sorted(_ws_tasks.keys())
    live_n = sum(1 for v in subs.values() if v.get("state") == "live")
    return {
        "enabled": WS_ENABLED,
        "thread_started": _ws_thread_started,
        "loop_alive": bool(_ws_loop is not None and _ws_loop.is_running()),
        "live_streams": live_n,
        "symbols": symbols,
        "subscriptions": subs,
        "prices": prices,
        "candles": candles,
    }


# ── FE1.1.0: تتبع حي — سعر لكل صفقة مع ذاكرة مؤقتة قصيرة ─────────────────────

_price_cache: Dict[str, Tuple[float, float]] = {}  # symbol -> (price, ts)
_price_cache_lock = threading.Lock()
PRICE_CACHE_TTL = float(os.getenv("PRICE_CACHE_TTL", "20"))


def get_live_price(symbol: str) -> Optional[float]:
    """السعر الحي — [FE1.2.0] ويب سوكت أولًا ثم ذاكرة 20 ث، ويُختار الأحدث زمنيًا
    بينهما، وREST (فريم التنفيذ 15m) أخيرًا عند غياب/تقادم الكل.
    الذاكرة القصيرة تمنع ضرب المزودين عند كل تحديث للوحة ما دام لا تيارًا حيًا."""
    now = time.time()
    ws_hit: Optional[Dict[str, Any]] = None
    if WS_ENABLED:
        with _ws_lock:
            h = _ws_price.get(symbol)
        if h and now - h["ts"] < WS_STALE_SEC:
            ws_hit = h
    with _price_cache_lock:
        rest_hit = _price_cache.get(symbol)
        if rest_hit and now - rest_hit[1] >= PRICE_CACHE_TTL:
            rest_hit = None
    if ws_hit or rest_hit:
        if ws_hit and (not rest_hit or ws_hit["ts"] >= rest_hit[1]):
            return float(ws_hit["price"])
        return float(rest_hit[0])
    try:
        df = fetch_ohlcv_df(symbol, ENTRY_TIMEFRAME, limit=2, min_candles=2)
        price = float(df["close"].iloc[-1]) if df is not None and not df.empty else None
    except Exception:
        price = None
    if price:
        with _price_cache_lock:
            _price_cache[symbol] = (price, now)
    return price


def get_recent_candles(symbol: str, timeframe: str, limit: int,
                       min_candles: int = 2) -> Optional[pd.DataFrame]:
    """[FE1.2.0] شموع فريم التنفيذ — أولوية لتيار ويب سوكت والاحتياط REST كما في FE1.1.1.
    نفس بُنية fetch_ohlcv_df بالضبط (ts/open/high/low/close/volume + timestamp/symbol/timeframe)
    فتنتقل حلقة المراقبة إلى التيار الحي بلا أي تغيير في منطق الملء/الوقف/الهدف."""
    if timeframe == ENTRY_TIMEFRAME and WS_ENABLED:
        with _ws_lock:
            entry = _ws_candles.get(symbol)
        if entry and time.time() - entry["ts"] < WS_STALE_SEC:
            rows = entry["candles"][-limit:] if (limit and limit > 0) else list(entry["candles"])
            if len(rows) >= min_candles:
                df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
                df["symbol"] = symbol
                df["timeframe"] = timeframe
                df = df[REQUIRED_COLS + ["symbol", "timeframe"]]
                df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
                return df
    return fetch_ohlcv_df(symbol, timeframe, limit=limit, min_candles=min_candles)


def _ws_exchange(name: str):
    """نسخة ccxt.pro للمزود — اتصالات عامة بلا مفاتيح (الشموع العامة تكفي للورقي)."""
    ex = _ws_exchanges.get(name)
    if ex is None:
        cls = getattr(ccxt.pro, name, None)
        if cls is None:
            raise ValueError(f"المزود {name} غير مدعوم في ccxt.pro")
        ex = cls({"enableRateLimit": False, "options": {"defaultType": "spot", "fetchMarkets": ["spot"]}})  # [FE1.3.2]
        _ws_exchanges[name] = ex
    return ex


async def _ws_watch_stream(symbol: str, stream: str) -> None:
    """حلقة اشتراك دائمة لرمز واحد: stream='ohlcv' شموع التنفيذ أو 'ticker' آخر سعر.
    تعاقب المزودين عند الفشل — نفس فلسفة طبقة REST (باينانس ← Bybit ← OKX ← Gate).
    ccxt.pro يعيد الاتصال تلقائيًا؛ أي استثناء يديرنا للمزود التالي بعد 3 ثوانٍ."""
    order = [p for p in DATA_PROVIDERS if p] or ["binance"]
    idx = 0
    while True:
        name = order[idx % len(order)]
        idx += 1
        try:
            ex = _ws_exchange(name)
            if not ex.markets:
                await ex.load_markets()
                # [FE1.3.1] تقليم فوري — نسخ pro تحمّل الأسواق كاملة أيضًا (الرمز نفسه مشمول أمانًا)
                n = prune_markets(ex, list(dict.fromkeys(list(watchlist) + [symbol])))
                if n >= 0:
                    logger.info("تقليم أسواق ويب سوكت %s — بقي %d زوج فقط (حمية الذاكرة)", name, n)
            _ws_mark(symbol, name, "connecting")
            if stream == "ohlcv":
                # بذرة REST واحدة عند بدء الاشتراك: التيار قد يبدأ بالشمعة الجارية
                # وحدها، والبذرة تضمن شمعة مغلقة + جارية فورًا (نفس نافذة REST limit=2)
                try:
                    seed = await asyncio.to_thread(
                        fetch_ohlcv_df, symbol, ENTRY_TIMEFRAME, WS_CANDLE_KEEP, 2)
                    if seed is not None and not seed.empty:
                        # fetch_ohlcv_df يُسقط عمود ts ويحتفظ بـ timestamp — نرجع للمللي ثانية
                        rows = [[int(r.timestamp.timestamp() * 1000), float(r.open), float(r.high),
                                 float(r.low), float(r.close), float(r.volume)]
                                for r in seed.itertuples(index=False)]
                        ws_apply_ohlcv(symbol, rows, name)
                except Exception as exc:
                    logger.debug("بذرة شموع %s من %s فشلت (سيكملها التيار): %s", symbol, name, exc)
            while True:
                if stream == "ohlcv":
                    data = await asyncio.wait_for(
                        ex.watch_ohlcv(symbol, ENTRY_TIMEFRAME), timeout=WS_RECV_TIMEOUT_SEC)
                    if not ws_apply_ohlcv(symbol, data, name):
                        await asyncio.sleep(1.0)
                else:
                    t = await asyncio.wait_for(ex.watch_ticker(symbol), timeout=WS_RECV_TIMEOUT_SEC)
                    t = t or {}
                    if not ws_apply_price(symbol, t.get("last") or t.get("close"), name):
                        await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _ws_mark(symbol, name, "error", f"{type(exc).__name__}: {exc}")
            await asyncio.sleep(3.0)


async def _ws_cancel_task(task: Any) -> None:
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


def _ws_spawn(symbol: str) -> None:
    """إنشاء مهمتي الاشتراك (شموع + سعر) داخل حلقة asyncio — بأمان من خيط آخر."""
    def _create() -> None:
        if _ws_loop is None or not _ws_loop.is_running():
            return
        t1 = _ws_loop.create_task(_ws_watch_stream(symbol, "ohlcv"))
        t2 = _ws_loop.create_task(_ws_watch_stream(symbol, "ticker"))
        with _ws_lock:
            _ws_tasks[symbol] = {"ohlcv": t1, "ticker": t2}
    _ws_loop.call_soon_threadsafe(_create)


def ws_sync_subscriptions() -> Dict[str, int]:
    """مزامنة اشتراكات ويب سوكت مع الرموز ذات الصفقات النشطة (معلق/مفتوح) —
    تُستدعى دوريًا من مشرف حلقة الويب سوكت ومن حلقة المراقبة احتياطًا.
    الرمز دون نشاط يُلغى اشتراكه فورًا فلا اتصالات زائدة على المزودين."""
    if not WS_ENABLED or _ws_loop is None or not _ws_loop.is_running():
        return {"added": 0, "removed": 0}
    try:
        rows = db.query("SELECT DISTINCT symbol FROM signals WHERE status IN ('pending','open')")
    except Exception:
        return {"added": 0, "removed": 0}
    wanted = {r["symbol"] for r in rows} if rows else set()
    with _ws_lock:
        current = set(_ws_tasks.keys())
    added = removed = 0
    for sym in wanted - current:
        _ws_spawn(sym)
        added += 1
    for sym in current - wanted:
        with _ws_lock:
            tasks = _ws_tasks.pop(sym, None)
        if tasks:
            for t in tasks.values():
                asyncio.run_coroutine_threadsafe(_ws_cancel_task(t), _ws_loop)
            _ws_subs.pop(sym, None)
            removed += 1
    # تنظيف مهام ماتت كليًا (خطأ غير متوقع) — المزامنة القادمة تعيد إقلاعها إن لزم
    with _ws_lock:
        dead = [s for s, tt in _ws_tasks.items() if all(t.done() for t in tt.values())]
        for s in dead:
            _ws_tasks.pop(s, None)
    if added or removed:
        logger.info("ويب سوكت: اشتراكات الرموز النشطة — أضيف %d وأُلغي %d (الحالي: %s)",
                    added, removed, ",".join(sorted(wanted)) or "لا شيء")
    return {"added": added, "removed": removed}


def start_ws_price_feed() -> None:
    """[FE1.2.0] إقلاع خيط ويب سوكت مستقل: حلقة asyncio دائمة + مشرف مزامنة.
    بلا تعطيل أبدًا: أي فشل (ccxt.pro غائب مثلًا) يُسجل ويبقى النظام على REST."""
    global _ws_loop, _ws_thread_started
    if _ws_thread_started or not WS_ENABLED:
        return
    if not _HAS_CCXT_PRO:
        logger.warning("ccxt.pro غير متوفر في هذه النسخة — الأسعار الحية تبقى REST كما في FE1.1.1")
        return
    _ws_thread_started = True

    async def _supervisor() -> None:
        while True:
            try:
                ws_sync_subscriptions()
            except Exception as exc:
                logger.debug("مشرف ويب سوكت: %s", exc)
            await asyncio.sleep(WS_SYNC_INTERVAL)

    def _run() -> None:
        global _ws_loop
        _ws_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_ws_loop)
        _ws_loop.call_soon_threadsafe(lambda: _ws_loop.create_task(_supervisor()))
        try:
            _ws_loop.run_forever()
        finally:
            _ws_loop.close()

    threading.Thread(target=_run, daemon=True, name="ws-price-feed").start()
    logger.info("خيط ويب سوكت للأسعار الحية أُقلع (ccxt.pro) — المزودون: %s | REST احتياطًا عند التقادم",
                ",".join(DATA_PROVIDERS))


def enrich_live_signal(sig: Dict[str, Any]) -> Dict[str, Any]:
    """تتبع حي لكل صفقة: السعر الآن، غير المحقق (صافي بعد الرسوم)،
    نسبة التقدم نحو الهدف، وبُعد الوقف — للمعلق: بُعد السعر عن منطقة الدخول."""
    out = dict(sig)
    price = get_live_price(sig["symbol"])
    out["current_price"] = price
    status = sig.get("status")
    try:
        if status == "open":
            fill = float(sig.get("fill_price") or 0)
            qty = float(sig.get("quantity") or 0)
            tp = float(sig.get("take_profit") or 0)
            sl = float(sig.get("stop_loss") or 0)
            peak = float(sig.get("peak_price") or 0)
            if price and fill > 0 and qty > 0:
                gross = qty * (price - fill)
                fees = (qty * fill + qty * price) * FEE_RATE
                net = gross - fees
                out["unrealized_usdt"] = round(net, 6)
                out["unrealized_pct"] = round(net / (qty * fill) * 100.0, 4) if qty * fill > 0 else 0.0
            if price and fill > 0 and tp != fill:
                out["progress_pct"] = round((price - fill) / (tp - fill) * 100.0, 1)
            if price and tp > 0:
                out["dist_tp_pct"] = round((tp - price) / price * 100.0, 3)
            if price and sl > 0:
                out["dist_sl_pct"] = round((sl - price) / price * 100.0, 3)
            if peak > 0:
                out["peak_price"] = peak  # القمة المتتبعة من حلقة المراقبة
        elif status == "pending":
            entry = float(sig.get("entry_price") or 0)
            if price and entry > 0:
                # موجب = السعر تحت الدخول (اللمس أقرب) — سلبي = السعر فوق الدخول
                out["dist_entry_pct"] = round((entry - price) / price * 100.0, 3)
    except (TypeError, ValueError):
        pass
    return out


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
    """أمر معلّق عند 0.382 لتراجع الموجة 3 — كما ينفذ الأصل _determine_entry_price.
    [FE1.4.0] وضع التداول الحقيقي: أمر LIMIT BUY فعلي على باينانس بنفس السعر
    وبقواعد المنصة الكاملة (دقة السعر/الكمية، أدنى قيمة، كفاية الرصيد).
    فشل الأمر الحقيقي = لا إشارة (لا سقوط صامت للورقي)."""
    entry = float(setup.entry_zone_low)
    sl = float(setup.stop_loss_price)
    tp = compute_take_profit(setup)
    if not (entry > 0 and sl > 0 and tp > entry > sl):
        logger.info("[%s] أسعار الإعداد غير منطقية (entry=%s sl=%s tp=%s) — تجاهل",
                    symbol, fmt_price(entry), fmt_price(sl), fmt_price(tp))
        return False
    real = is_real_mode
    order_id: Optional[str] = None
    if real:
        ex = binance_trade_exchange()
        if ex is None:
            log_and_notify("error", f"❌ رفض أمر حقيقي {symbol}: مفاتيح باينانس غير مضبوطة", "REAL_TRADE_ERROR")
            return False
        st = binance_status_snapshot()
        if not st.get("connected") or st.get("usdt_free") is None:
            log_and_notify("error",
                           f"❌ رفض أمر حقيقي {symbol}: اتصال باينانس غير جاهز ({st.get('error') or 'لا رصيد'})",
                           "REAL_TRADE_ERROR")
            return False
        qty = compute_quantity_real(symbol, entry, sl, float(st["usdt_free"]), ex)
        if qty is None:
            return False
        price_p = real_adjust_price(ex, symbol, entry)
        qty = real_adjust_amount(ex, symbol, qty)
        mkt = real_market(ex, symbol)
        if qty <= 0 or qty * price_p < real_min_cost(mkt):
            log_and_notify("error",
                           f"❌ رفض أمر حقيقي {symbol}: الكمية تحت حدود باينانس بعد تطبيق الدقة",
                           "REAL_TRADE_ERROR")
            return False
        order = place_real_limit_buy(symbol, price_p, qty)
        if order is None:
            return False
        order_id = str(order.get("id") or "") or None
    else:
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
        " peak_price, expires_at, is_real, order_id) VALUES (%s,%s,%s,'pending',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (symbol, "BULLISH", STRATEGY_NAME, entry, sl, tp, qty, qty * entry, round(rr, 2),
         pivots_json, fib_json, utc_now_iso(), entry, expires_at, 1 if real else 0, order_id),
    )
    with scan_stats_lock:
        scan_stats["setups_bull_traded"] += 1
    mode_tag = "حقيقية 🔴" if real else "ورقية"
    if fib:
        signal_msg = (
            f"🌊 إشارة إليوت+فيبو جديدة ({mode_tag}): {symbol}\n"
            f"دخول معلّق: {fmt_price(entry)} | وقف بنيوي: {fmt_price(sl)} | هدف 1.618: {fmt_price(tp)}\n"
            f"R:R = {rr:.2f} | W2={fib.wave2_retrace_pct*100:.1f}% W4={fib.wave4_retrace_pct*100:.1f}%"
        )
    else:
        signal_msg = f"🌊 إشارة إليوت+فيبو جديدة ({mode_tag}): {symbol} — دخول {fmt_price(entry)}"
    log_and_notify("info", signal_msg, "NEW_SIGNAL")
    return True


def close_signal_row(sig: Dict[str, Any], exit_price: float, reason: str,
                     exit_order_id: Optional[str] = None) -> None:
    """محاسبة الإغلاق: رسوم 0.1% × اتجاهين — نفس عقد المشروع السابق.
    [FE1.4.0] الصفقة الحقيقية: نفس المحاسبة للعرض والإحصاء لكن دون أي مساس
    بالرصيد الورقي (الأرباح/الخسائر الحقيقية على الحساب الفعلي في باينانس)."""
    entry = float(sig["fill_price"])
    qty = float(sig["quantity"])
    gross = qty * (exit_price - entry)
    fees = (qty * entry + qty * exit_price) * FEE_RATE
    pnl_usdt = gross - fees
    pnl_pct = (pnl_usdt / (qty * entry)) * 100.0 if qty * entry > 0 else 0.0
    is_real = bool(sig.get("is_real"))
    db.execute(
        "UPDATE signals SET status='closed', close_price=%s, close_reason=%s, closed_at=%s,"
        " pnl_usdt=%s, pnl_pct=%s, exit_order_id=%s WHERE id=%s",
        (exit_price, reason, utc_now_iso(), round(pnl_usdt, 6), round(pnl_pct, 4), exit_order_id, sig["id"]),
    )
    tag = "حقيقية 🔴" if is_real else "ورقية"
    if not is_real:
        set_paper_balance(get_paper_balance() + pnl_usdt)
    emoji = "✅" if pnl_usdt >= 0 else "🛑"
    balance_line = (f"النتيجة: {pnl_usdt:+.2f}$ ({pnl_pct:+.2f}%)"
                    + ("" if is_real else f" | الرصيد الورقي: {get_paper_balance():.2f}$"))
    log_and_notify(
        "info" if pnl_usdt >= 0 else "warning",
        f"{emoji} إغلاق {tag}: {sig['symbol']} — {reason}\n"
        f"دخول {fmt_price(entry)} → خروج {fmt_price(exit_price)}\n{balance_line}",
        "TRADE_CLOSED",
    )


def close_real_trade(sig: Dict[str, Any], trigger_price: float, reason: str) -> None:
    """[FE1.4.0] إغلاق صفقة حقيقية: بيع سوق فعلي للكمية المفتوحة (بقواعد باينانس)
    ثم المحاسبة دون مساس بالرصيد الورقي.
    • الغبار (أقل من حدود بيع باينانس): يُغلق محاسبيًا دون أمر بيع مع توثيق السبب.
    • فشل البيع: تبقى الصفقة مفتوحة وتُعاد المحاولة في الدورة القادمة — لا فقدان.
    • الكمية الفعلية للبيع = الحد الأدنى بين كمية الصفقة والرصيد الحر (كما في V9) —
      لا نبيع أرصدة نفس العملة المملوكة خارج البوت."""
    symbol = sig["symbol"]
    ex = binance_trade_exchange()
    if ex is None:
        log_and_notify("error", f"❌ تعذر إغلاق {symbol} حقيقيًا: مفاتيح باينانس غائبة", "REAL_TRADE_ERROR")
        return
    try:
        base = symbol.split("/")[0]
        free = fetch_free_base(ex, base)
        sell_qty = min(float(sig["quantity"]), free if free and free > 0 else 0.0)
        sell_qty = real_adjust_amount(ex, symbol, sell_qty)
        mkt = real_market(ex, symbol)
        if sell_qty <= 0 or sell_qty < real_min_amount(mkt) or sell_qty * trigger_price < real_min_cost(mkt):
            close_signal_row(sig, trigger_price,
                             reason + " — كمية غبار أقل من حدود بيع باينانس (محاسبة بلا أمر بيع)")
            return
        order = place_real_market_sell(symbol, sell_qty)
        if order is None:
            return  # تبقى مفتوحة — إعادة محاولة في الدورة القادمة
        exit_price = float(order.get("average") or order.get("price") or 0) or trigger_price
        close_signal_row(sig, exit_price, reason, exit_order_id=str(order.get("id") or "") or None)
    except Exception as exc:
        log_and_notify("error", f"❌ استثناء إغلاق حقيقي {symbol}: {exc}", "REAL_TRADE_ERROR")


def _resync_after_cancel_attempt(sig: Dict[str, Any], ex, reason_terminal: str) -> None:
    """بعد محاولة إلغاء أمر حقيقي: هل ملئ؟ ملئ جزئيًا؟ أُلغي فعلًا؟ — الحكم من المنصة."""
    order = fetch_real_order(ex, sig["symbol"], sig["order_id"])
    status = ((order or {}).get("status") or "").lower()
    filled = float((order or {}).get("filled") or 0)
    avg = float((order or {}).get("average") or 0) or float(sig["entry_price"])
    if filled > 0:
        db.execute("UPDATE signals SET status='open', fill_price=%s, quantity=%s, filled_at=%s WHERE id=%s",
                   (avg, filled, utc_now_iso(), sig["id"]))
        log_and_notify("info",
                       f"🎯 [حقيقي] مُلئ أمر الشراء (جزئيًا على الأقل): {sig['symbol']} — كمية {filled} عند {fmt_price(avg)}",
                       "REAL_FILLED")
    elif status in ("canceled", "expired", "rejected"):
        db.execute("UPDATE signals SET status='cancelled', close_reason=%s, closed_at=%s WHERE id=%s",
                   (reason_terminal + f" (حالة المنصة: {status})", utc_now_iso(), sig["id"]))
    else:
        logger.warning("[%s] أمر حقيقي ما زال حيًا بعد محاولة الإلغاء — إعادة المحاولة في الدورة القادمة", sig["symbol"])


def handle_real_pending(sig: Dict[str, Any], close_now: float, p0: float) -> None:
    """[FE1.4.0] إدارة الأمر المعلق الحقيقي من المنصة مباشرة (حقيقة الملء من باينانس
    لا من الشموع): FILLED ← فتح بأسعار التنفيذ الفعلية | ملغى/منتهي ← محاسبة،
    مع أي ملء جزئي يُفتح صفقة مفتوحة بكميته الفعلية.
    الأوامر الحية: نفس قواعد الورقي (إبطال بنيوي خلف P0 + انتهاء الصلاحية)."""
    ex = binance_trade_exchange()
    if ex is None or not sig.get("order_id"):
        logger.warning("[%s] صفقة حقيقية معلقة بلا منصة/معرف أمر — تجاهل الدورة", sig["symbol"])
        return
    order = fetch_real_order(ex, sig["symbol"], sig["order_id"])
    if order is None:
        return  # فشل عابر — الدورة القادمة
    status = (order.get("status") or "").lower()
    filled = float(order.get("filled") or 0)
    avg = float(order.get("average") or 0)
    qty_target = float(sig["quantity"])
    if status == "closed" or (filled > 0 and filled >= qty_target - 1e-12):
        fill_price = avg or float(sig["entry_price"])
        db.execute("UPDATE signals SET status='open', fill_price=%s, quantity=%s, filled_at=%s WHERE id=%s",
                   (fill_price, filled or qty_target, utc_now_iso(), sig["id"]))
        log_and_notify("info",
                       f"🎯 [حقيقي] مُلئ أمر الشراء: {sig['symbol']} — كمية {filled or qty_target} عند {fmt_price(fill_price)}\n"
                       f"وقف: {fmt_price(sig['stop_loss'])} | هدف 1.618: {fmt_price(sig['take_profit'])}",
                       "REAL_FILLED")
        return
    if status in ("canceled", "expired", "rejected"):
        if filled > 0:
            db.execute("UPDATE signals SET status='open', fill_price=%s, quantity=%s, filled_at=%s WHERE id=%s",
                       (avg or float(sig["entry_price"]), filled, utc_now_iso(), sig["id"]))
            log_and_notify("info",
                           f"🎯 [حقيقي] ملء جزئي قبل الإلغاء: {sig['symbol']} — كمية {filled} عند {fmt_price(avg or float(sig['entry_price']))}",
                           "REAL_FILLED")
        else:
            db.execute("UPDATE signals SET status='cancelled', close_reason=%s, closed_at=%s WHERE id=%s",
                       (f"أُلغي الأمر الحقيقي على المنصة (حالة: {status})", utc_now_iso(), sig["id"]))
        return
    # ما زال حيًا على المنصة — نفس قواعد الإبطال/الصلاحية كما في الورقي
    if close_now < p0:
        cancel_real_order(ex, sig["symbol"], sig["order_id"])
        _resync_after_cancel_attempt(sig, ex,
                                     f"إبطال بنيوي: إغلاق {fmt_price(close_now)} خلف أصل الموجة 1 (P0={fmt_price(p0)})")
    elif sig.get("expires_at") and utc_now_iso() > sig["expires_at"]:
        cancel_real_order(ex, sig["symbol"], sig["order_id"])
        _resync_after_cancel_attempt(sig, ex, "انتهت صلاحية الأمر المعلق (3 شموع) دون ملء كامل")


def monitor_step() -> None:
    """نفّذ أوامر الإغلاق/الملء الورقية — كل 60 ثانية على شموع فريم التنفيذ (15m)."""
    pend = db.query("SELECT * FROM signals WHERE status='pending' ORDER BY id ASC")
    for sig in pend:
        symbol = sig["symbol"]
        try:
            df = get_recent_candles(symbol, ENTRY_TIMEFRAME, limit=2, min_candles=2)  # [FE1.2.0] ويب سوكت أولًا
        except Exception as exc:
            logger.warning("[مراقبة] فشل جلب %s: %s", symbol, exc)
            continue
        if df is None or df.empty:
            continue
        last = df.iloc[-1]
        close_now = float(last["close"])
        p0 = float(json.loads(sig["pivots_json"])["P0"])

        # [FE1.4.0] الأمر الحقيقي يُدار من المنصة مباشرة (حقيقة الملء من باينانس)
        if sig.get("is_real"):
            handle_real_pending(sig, close_now, p0)
            continue

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
            df = get_recent_candles(symbol, ENTRY_TIMEFRAME, limit=2, min_candles=2)  # [FE1.2.0] ويب سوكت أولًا
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
        # [FE1.4.0] الصفقة الحقيقية: الإغلاق بأمر بيع سوق فعلي على باينانس
        if sig.get("is_real"):
            if low_now <= float(sig["stop_loss"]):
                close_real_trade(sig, float(sig["stop_loss"]), "وقف خسارة بنيوي (خلف أصل الموجة 1)")
            elif high_now >= float(sig["take_profit"]):
                close_real_trade(sig, float(sig["take_profit"]), "هدف فيبوناتشي 1.618 تحقق")
            continue
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
    for i_sym, symbol in enumerate(watchlist):
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
            if i_sym % 5 == 4:  # [FE1.3.2] فحص ذاكرة خفيف كل 5 أزواج — gc فوق العتبة فقط
                mem_check("أثناء دورة المسح")
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
        mem_check("بعد دورة مسح")  # [FE1.3.1] حمية الذاكرة
        nap = seconds_until_next_candle(SIGNAL_TIMEFRAME)
        logger.info("الدورة اكتملت — النوم %.0f ثانية حتى إغلاق شمعة %s القادمة", nap, SIGNAL_TIMEFRAME)
        time.sleep(nap)


def monitor_loop() -> None:
    """مراقبة تنفيذية على فريم الدخول (15m): ملء المعلق + وقف/هدف المفتوح.
    [FE1.1.0] الإغلاق اليدوي من اللوحة يخدم نفس مسار close_signal_row فتظل المحاسبة موحدة."""
    time.sleep(20)
    while True:
        try:
            db.ensure()
            monitor_step()
            ws_sync_subscriptions()  # [FE1.2.0] احتياط موازٍ للمشرف — مزامنة الاشتراكات كل دقيقة
            mem_check("دورة مراقبة")  # [FE1.3.1] حمية الذاكرة كل دقيقة
        except Exception as exc:
            logger.exception("استثناء في حلقة المراقبة: %s", exc)
        time.sleep(60)


# [FE1.3.0] حالة البقاء الحي — تُعرض في /health و/api/all لتشخيص حي من اللوحة أو curl
keep_alive_lock = threading.Lock()
keep_alive_stop = threading.Event()
keep_alive_state: Dict[str, Any] = {
    "enabled": False, "target": "", "interval_sec": 0.0,
    "last_ping_at": "", "last_ok": None, "ok_count": 0, "fail_count": 0,
}


def keep_alive_snapshot() -> Dict[str, Any]:
    with keep_alive_lock:
        return dict(keep_alive_state)


def resolve_keep_alive_url() -> str:
    """هدف النبضة: KEEP_ALIVE_URL ← RENDER_EXTERNAL_URL (يحقنه Render تلقائيًا) ← PANEL_URL."""
    base = KEEP_ALIVE_URL or RENDER_EXTERNAL_URL or PANEL_URL
    return base.rstrip("/") + "/health" if base else ""


def keep_alive_ping(url: str) -> bool:
    """نبضة واحدة إلى /health (عام بلا مصادقة) مع تحديث عدادات التشخيص."""
    ok = False
    try:
        resp = requests.get(url, timeout=15)
        ok = (resp.status_code == 200)
        if not ok:
            logger.warning("نبضة البقاء أعادت HTTP %s من %s", resp.status_code, url)
    except Exception as exc:
        logger.warning("فشلت نبضة البقاء إلى %s: %s", url, exc)
    with keep_alive_lock:
        keep_alive_state["last_ping_at"] = utc_now_iso()
        keep_alive_state["last_ok"] = ok
        if ok:
            keep_alive_state["ok_count"] += 1
        else:
            keep_alive_state["fail_count"] += 1
    return ok


def keep_alive_loop() -> None:
    """[FE1.3.0] نبضة ذاتية ضد نوم Render المجاني — محصّنة ضد الفشل العابر.
    - الهدف /health العام (بلا مصادقة) — يصلح أيضًا هدفًا لكرون خارجي (cron-job.org)
    - نجاح ← سكون KEEP_ALIVE_INTERVAL_SEC (افتراضي 600ث) | فشل ← إعادة محاولة كل 60ث حتى النجاح
      فلا تبقى فجوة صمت تسمح بالنوم (القديم: نبضة واحدة كل 14 دقيقة بلا إعادة محاولة)
    - أوقفه بـ KEEP_ALIVE_ENABLED=0 إن اعتمدت كليًا على كرون خارجي يضرب /health"""
    url = resolve_keep_alive_url()
    with keep_alive_lock:
        keep_alive_state.update({
            "enabled": bool(KEEP_ALIVE_ENABLED and url),
            "target": url,
            "interval_sec": KEEP_ALIVE_INTERVAL_SEC,
        })
    if not KEEP_ALIVE_ENABLED:
        logger.info("البقاء الحي معطّل (KEEP_ALIVE_ENABLED=0) — اعتمد على كرون خارجي يضرب /health كل 10 دقائق")
        return
    if not url:
        logger.warning("البقاء الحي معطّل: لا KEEP_ALIVE_URL ولا RENDER_EXTERNAL_URL ولا PANEL_URL — اضبط KEEP_ALIVE_URL يدويًا")
        return
    logger.info("البقاء الحي نشط — نبضة /health كل %.0f ثانية إلى %s (إعادة محاولة كل 60 ثانية عند الفشل)",
                KEEP_ALIVE_INTERVAL_SEC, url)
    if keep_alive_stop.wait(60):   # نبضة تأكيد مبكرة بعد دقيقة من الإقلاع
        return
    while True:
        keep_alive_ping(url)
        nap = KEEP_ALIVE_INTERVAL_SEC if keep_alive_state["last_ok"] else 60.0
        if keep_alive_stop.wait(nap):
            return


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
            df = get_recent_candles(r["symbol"], ENTRY_TIMEFRAME, limit=2, min_candles=2)  # [FE1.2.0]
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
        "mode": ("real" if is_real_mode else "paper"),  # [FE1.4.0] real = أوامر فعلية على باينانس
        "real_trading": is_real_mode,
        "db": "postgres" if USE_POSTGRES else "sqlite",
        "trading_enabled": is_trading_enabled,
        "data_source": (active_source.get("name") or "boot"),
        "live_feed": ("websocket" if (WS_ENABLED and _ws_thread_started) else "rest"),
        "pairs": len(watchlist),
        "memory": {  # [FE1.3.1] تشخيص الذاكرة — سبب أعطال OOM الحقيقية
            "rss_mb": round(rss_mb(), 1),
            "gc_threshold_mb": MEM_GC_THRESHOLD_MB,
            "critical_mb": MEM_CRITICAL_MB,
        },
        "keep_alive": keep_alive_snapshot(),  # [FE1.3.0] تشخيص النبضة — عام بلا مصادقة لكرون جوب
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
    live_rows = [enrich_live_signal(_parse_sig_row(r)) for r in open_rows]  # [FE1.1.0] تتبع حي
    return jsonify({
        "version": BOT_VERSION,
        "strategy": STRATEGY_NAME,
        "mode": ("real" if is_real_mode else "paper"),
        "real_mode": is_real_mode,               # [FE1.4.0] زر التداول الحقيقي
        "binance": binance_status_snapshot(),    # [FE1.4.0] بطاقة اتصال باينانس
        "trading_enabled": is_trading_enabled,
        "paper_balance": get_paper_balance(),
        "stats": compute_stats(),
        "open_signals": live_rows,
        "closed_signals": [_parse_sig_row(r) for r in closed_rows],
        "detections": dets,
        "notifications": notif_rows,
        "data": data_status(),  # [FE1.0.1] تشخيص مزودي البيانات للوحة
        "memory": {  # [FE1.3.1] بطاقة الذاكرة في اللوحة
            "rss_mb": round(rss_mb(), 1),
            "gc_threshold_mb": MEM_GC_THRESHOLD_MB,
            "critical_mb": MEM_CRITICAL_MB,
        },
        "keep_alive": keep_alive_snapshot(),  # [FE1.3.0] بطاقة النبضة في اللوحة
    })


@app.route("/api/trades/close", methods=["POST"])
def api_trades_close():
    """[FE1.1.0] إغلاق يدوي لصفقة مفتوحة بسعر السوق الحالي (ورقي) — الوضع الآلي يبقى يعمل."""
    resp = require_dashboard_auth()
    if resp:
        return resp
    body = request.get_json(silent=True) or {}
    try:
        sig_id = int(body.get("id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "معرف صفقة غير صالح"}), 400
    rows = db.query("SELECT * FROM signals WHERE id = %s AND status = 'open'", (sig_id,))
    if not rows:
        return jsonify({"ok": False, "error": "لا توجد صفقة مفتوحة بهذا المعرف"}), 404
    sig = _parse_sig_row(rows[0])
    price = get_live_price(sig["symbol"]) or float(sig["fill_price"])
    if sig.get("is_real"):  # [FE1.4.0] بيع سوق فعلي على باينانس
        close_real_trade(sig, price, "إغلاق يدوي من اللوحة (بسعر السوق)")
        return jsonify({
            "ok": True,
            "message": f"جارٍ تنفيذ البيع الحقيقي لإغلاق {sig['symbol']} — راقب الإشعارات للتأكيد",
            "close_price": price,
        })
    close_signal_row(sig, price, "إغلاق يدوي من اللوحة (بسعر السوق)")
    return jsonify({
        "ok": True,
        "message": f"أُغلقت صفقة {sig['symbol']} عند {fmt_price(price)} — الرصيد حُدّث",
        "close_price": price,
    })


@app.route("/api/trades/cancel", methods=["POST"])
def api_trades_cancel():
    """[FE1.1.0] إلغاء يدوي لأمر معلق لم يُملأ بعد."""
    resp = require_dashboard_auth()
    if resp:
        return resp
    body = request.get_json(silent=True) or {}
    try:
        sig_id = int(body.get("id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "معرف أمر غير صالح"}), 400
    rows = db.query("SELECT * FROM signals WHERE id = %s AND status = 'pending'", (sig_id,))
    if not rows:
        return jsonify({"ok": False, "error": "لا يوجد أمر معلق بهذا المعرف"}), 404
    sig = rows[0]
    db.execute(
        "UPDATE signals SET status='cancelled', close_reason=%s, closed_at=%s WHERE id=%s",
        ("إلغاء يدوي من اللوحة", utc_now_iso(), sig_id),
    )
    log_and_notify(
        "info",
        f"🚫 أُلغي الأمر المعلق (ورقي): {sig['symbol']} — دخول {fmt_price(float(sig['entry_price']))} (إلغاء يدوي)",
        "ORDER_CANCELLED",
    )
    return jsonify({"ok": True, "message": f"أُلغي الأمر المعلق لـ {sig['symbol']}"})


@app.route("/api/ws/status")
def api_ws_status():
    """[FE1.2.0] تشخيص تغذية الأسعار الحية: الاشتراكات، المصادر، أعمار آخر تحديث."""
    resp = require_dashboard_auth()
    if resp:
        return resp
    snap = ws_feed_snapshot()
    snap["version"] = BOT_VERSION
    snap["entry_timeframe"] = ENTRY_TIMEFRAME
    return jsonify(snap)


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


@app.route("/api/binance/status")
def api_binance_status():
    """[FE1.4.0] حالة اتصال باينانس للوحة (محمية) — ping حي + رصيد وصلاحيات بمفاتيح."""
    resp = require_dashboard_auth()
    if resp:
        return resp
    snap = binance_status_snapshot()
    snap["version"] = BOT_VERSION
    snap["real_mode"] = is_real_mode
    return jsonify(snap)


@app.route("/api/trading/real", methods=["POST"])
def api_trading_real():
    """[FE1.4.0] زر التداول الحقيقي مثل V9: تفعيل/إيقاف تنفيذ الإشارات الجديدة
    بأوامر فعلية على باينانس. شروط التفعيل الصارمة: مفاتيح باينانس موجودة +
    فحص اتصال حي ناجح + رصيد USDT مقروء — وإلا رفض برسالة واضحة.
    الإيقاف يعيد الوضع الورقي فورًا (الصفقات الحقيقية المفتوحة تستمر بالإدارة)."""
    global is_real_mode
    resp = require_dashboard_auth()
    if resp:
        return resp
    body = request.get_json(silent=True) or {}
    enable = body.get("enable")
    with real_mode_lock:
        target = (not is_real_mode) if enable is None else bool(enable)
        if target == is_real_mode:
            return jsonify({
                "ok": True, "real_mode": is_real_mode,
                "message": ("التداول الحقيقي مُفعّل أصلًا" if is_real_mode else "التداول الحقيقي متوقف أصلًا"),
                "binance": binance_status_snapshot(),
            })
        if target:
            if not (API_KEY and API_SECRET):
                return jsonify({"ok": False,
                                "error": "مفاتيح باينانس غير مضبوطة — أضف BINANCE_API_KEY و BINANCE_API_SECRET في متغيرات بيئة Render أولًا"}), 400
            st = binance_status_snapshot(force=True)
            if not st.get("connected") or st.get("usdt_free") is None:
                return jsonify({"ok": False,
                                "error": f"فحص باينانس قبل التفعيل فشل: {st.get('error') or 'لا استجابة'}"}), 400
            is_real_mode = True
            db_set_state("real_mode", "1")
            msg = ("🔴 التداول الحقيقي مُفعّل — الإشارات الجديدة ستُنفذ بأوامر فعلية على باينانس "
                   f"(USDT الحر: {float(st['usdt_free']):.2f}$ | سقف الأمر: {REAL_MAX_NOTIONAL_USDT:.0f}$)")
            bin_snap = st
        else:
            is_real_mode = False
            db_set_state("real_mode", "0")
            msg = "⚪ التداول الحقيقي أُوقف — العودة للوضع الورقي (الصفقات الحقيقية المفتوحة تُدار حتى إغلاقها)"
            bin_snap = binance_status_snapshot()
    log_and_notify("info", msg, "REAL_MODE_CHANGE")
    return jsonify({"ok": True, "real_mode": is_real_mode, "message": msg, "binance": bin_snap})


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


def restore_real_mode_flag() -> None:
    """[FE1.4.0] استعادة زر التداول الحقيقي — مع حارس أمان: بلا مفاتيح يُفرض الإيقاف."""
    global is_real_mode
    flag = db_get_state("real_mode", "0")
    if flag == "1" and not (API_KEY and API_SECRET):
        is_real_mode = False
        db_set_state("real_mode", "0")
        log_and_notify("warning", "⚠ أُوقف التداول الحقيقي عند الإقلاع: مفاتيح باينانس غير مضبوطة", "REAL_MODE_OFF")
        return
    is_real_mode = (flag == "1")
    logger.info("حالة التداول الحقيقي المستعادة: %s", "مفعّلة ⚠ (أوامر فعلية)" if is_real_mode else "متوقفة (ورقي)")


def load_markets_async() -> None:
    """[FE1.3.1] لم يعد يُحمّل أسواق المزودين مسبقًا — التحميل كسول عند أول استخدام:
    ccxt يستدعي load_markets داخليًا في أول fetch_ohlcv لكل مزود، وprune_markets
    يقلّم الأسواق فور أول نجاح. كان التحميل المسبق لكل المزودين يستهلك 150-300MB
    دفعة واحدة عند الإقلاع = السبب الرئيسي لأعطال OOM على خطة 512MB."""
    if not MEM_LAZY_MARKETS:
        def _load():
            for name, ex in EXCHANGES.items():
                try:
                    ex.load_markets()
                    logger.info("تحميل أسواق المزود %s اكتمل (الوضع القديم المسبق)", name)
                except Exception as exc:
                    logger.warning("تعذر تحميل أسواق المزود %s — يُعاد تلقائيًا عند أول جلب: %s", name, exc)
        threading.Thread(target=_load, daemon=True).start()
        return
    logger.info("حمية الذاكرة: الأسواق تُحمّل كسولًا عند أول استخدام لكل مزود، وتُقلّم فور نجاح أول جلب")


def initialize_bot_services() -> None:
    init_db()
    restore_trading_flag()
    restore_real_mode_flag()
    load_markets_async()
    start_ws_price_feed()  # [FE1.2.0] الأسعار الحية من ويب سوكت — REST احتياطًا فقط
    threading.Thread(target=scan_loop, daemon=True, name="scan-loop").start()
    threading.Thread(target=monitor_loop, daemon=True, name="monitor-loop").start()
    threading.Thread(target=keep_alive_loop, daemon=True, name="keep-alive").start()
    ka_target = resolve_keep_alive_url()
    ka_txt = (f"نشط — نبضة كل {int(KEEP_ALIVE_INTERVAL_SEC)} ثانية إلى {ka_target}"
              if (KEEP_ALIVE_ENABLED and ka_target) else "معطل ⚠ (خطر نوم الخدمة على الخطة المجانية)")
    mem_txt = (f"كسول + تقليم + gc عند {int(MEM_GC_THRESHOLD_MB)}MB" if MEM_LAZY_MARKETS
               else "مسبق (الوضع القديم) — خطر OOM")
    real_txt = ("🔴 نشط — الإشارات الجديدة أوامر فعلية على باينانس ⚠" if is_real_mode
                else "⚪ متوقف — وضع ورقي آمن (فعّله من زر اللوحة)")
    log_and_notify(
        "info",
        f"🚀 Fibo-Elio {BOT_VERSION} أقلع — استراتيجية واحدة: Elliott_Fibonacci (المنطق الأصلي)\n"
        f"الوضع: {'حقيقي 🔴' if is_real_mode else 'ورقي'} | أزواج: {len(watchlist)} | فريم الكشف {SIGNAL_TIMEFRAME} | التنفيذ {ENTRY_TIMEFRAME}\n"
        f"الأسعار الحية: {'ويب سوكت (ccxt.pro) — REST احتياطًا' if WS_ENABLED else 'REST'} | "
        f"انعكاس الزيجزاج {DEVIATION_THRESHOLD*100:.2f}% | أقصى صفقات {MAX_OPEN_TRADES} | مخاطرة {RISK_PCT_PER_TRADE}%\n"
        f"البقاء الحي: {ka_txt}\n"
        f"التداول الحقيقي: {real_txt} | سقف الأمر {REAL_MAX_NOTIONAL_USDT:.0f}$ | تيستنت {'نعم' if BINANCE_TESTNET else 'لا'}\n"
        f"الذاكرة: {mem_txt} — الحد 512MB",
        "BOOT",
    )


if __name__ == "__main__":
    initialize_bot_services()
    app.run(host="0.0.0.0", port=PORT, threaded=True)
