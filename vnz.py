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

 FE1.4.1: علاج أعطال OOM (نفاد الذاكرة 512MB) التي رافقت FE1.4.0:
 • السبب الجذري: نداءات ccxt الموحدة على نسخة التداول (fetch_balance/create_order/
   fetch_order/cancel_order/amount_to_precision) تستدعي load_markets() داخليًا
   فتحمّل كون أسواق باينانس الكامل (~1600+ سوق ببياناتها الخام) = نتوء +150-300MB
   فوق أساس الخدمة ← قتل فوق سقف 512MB ← إعادة إقلاع ← تكرار كل دقيقتين.
   prune_markets لم يكن ينفع لأنه يقلّم «بعد» اكتمال التحميل (النتوء حدث أصلًا).
 • الحل الجذري: طبقة تداول «بلا أسواق نهائيًا» عبر نقاط باينانس الخام (implicit API
   في ccxt — لا تلمس load_markets إطلاقًا):
     الحساب/الرصيد  ← privateGetAccount      (GET /api/v3/account)
     قواعد السوق    ← publicGetExchangeInfo?symbol= (كيلوبايتات بدل كون الأسواق + كاش 6 ساعات)
     الأمر          ← privatePostOrder       (POST /api/v3/order)
     حالة الأمر     ← privateGetOrder        (GET /api/v3/order)
     الإلغاء        ← privateDeleteOrder     (DELETE /api/v3/order)
   والدقة (LOT_SIZE/PRICE_FILTER) تُطبق يدويًا بأرضية Decimal على stepSize/tickSize
   بدل amount_to_precision/price_to_precision — نفس القواعد بلا أي كون أسواق.
 • حمية إضافية: malloc_trim بعد gc لإرجاع الذاكرة المحررة فعليًا للنظام (المُوزّع
   في CPython يحتجزها)، وخفض عتبات التنظيف (gc عند 360MB، حرج عند 440MB).
 • القواعد لم تُنسَ: نفس فلاتر باينانس (دقة/أدنى كمية/أدنى قيمة) وسقف الأمر و
   TESTNET — لا تغيير على أي منطق تداول، فقط مصدر القواعد أرحم ذاكرةً.

 FE1.4.2: إغلاق بقية ثغرات load_markets التي أسقطت النشر الأول لـ FE1.4.1:
 • المسح REST (أول نشاط عند الإقلاع): fetch_ohlcv الموحدة تحمّل كون الأسواق
   داخليًا ← استُبدلت لباينانس بـ publicGetKlines الخام (بلا أسواق نهائيًا).
   البدائل (Bybit/OKX/Gate) تبقى موحدة — لا تُستخدم إلا عند فشل باينانس.
 • الويب سوكت: watch_ohlcv/watch_ticker داخليا يطلبان market() ← تُحقن نسخ
   ccxt.pro بأسواق مصنوعة مصغّرة (قائمة المراقبة فقط، بمعرفات صيغة كل منصة)
   فلا load_markets عند أول اشتراك بأي صفقة نشطة.
 • دقة الورقي: amount_to_precision كانت عبر market() تحمّل الأسواق عند أول
   إشارة ورقية ← لباينانس تمر عبر exchangeInfo الخام والخطوة اليدوية.
 • render.yaml: عتبتا الذاكرة حُدّثتا 380←360 و450←440 (البيئة تتجاوز الافتراضيات).
 • النتيجة: لا يوجد في المشروع بأكمله أي مسار ساخن يستدعي load_markets —
   كون الأسواق (~+150-300MB) لم يعد يُلمس إطلاقًا في التشغيل الطبيعي.

 FE1.5.0: ماسح الكون الكامل + إصلاحات مراجعة اللوحة (طلب «راجع لوحة التحكم واصلح
 المشاكل الضاهرة اريد اضافة الية فحص اولي لكل ازواج باينانس الملائمة لهذه
 الاستراتيجية»):
 • ماسح كون باينانس: بدل قائمة يدوية ثابتة (crypto_list.txt) يفحص الماسح كامل
   أسواق USDT عبر نقاط خام رخيصة الوزن (لا load_markets إطلاقًا — درس FE1.4.x):
   1) publicGetTicker24hr (وزن 80) ← ترشيح: سيولة ≥ SCAN_MIN_VOLUME_USDT،
      سبريد ≤ SCAN_MAX_SPREAD_PCT، مدى 24h ≥ SCAN_MIN_RANGE_PCT (الموجات تحتاج
      حركة)، استبعاد العملات المستقرة/الورقية والرموز المرفوعة (UP/DOWN/BULL/BEAR).
   2) أعلى SCAN_CANDIDATES مرشحًا ← شموع 15m خام لكل مرشح ← عدّاد زيجزاج بنفس
      عتبة الانعكاس DEVIATION_THRESHOLD + ATR% + سعة الموجات + كفاءة الاتجاه
      ← درجة ملاءمة 0-100 موجهة لاستراتيجية إليوت+فيبو (0.70 تقني + 0.30 سيولة).
   3) أعلى SCAN_TOP_N يُطبق تلقائيًا على قائمة المراقبة (مع الحفاظ الإجباري على
      الرموز ذات الصفقات النشطة) وتُحدّث أسواق الويب سوكت المصنوعة للرموز الجديدة.
 • حماية IP (418/429): وزن منخفض جدًا (~160 لكل فحص كل 6 ساعات) + إيقاع مهذب
   + إجهاض فوري وحفظ النتائج القديمة عند أي قيد من باينانس.
 • زر «فحص الآن» في اللوحة (POST /api/scan/run محمي) + جدول النتائج + بطاقة حالة.
 • إصلاحات مراجعة اللوحة الحية: حالة WS كانت عالقة «connecting» وlive_streams=0
   رغم التدفق (إعادة اتصال تيار الشموع كانت تُنزل حالة الرمز رغم تدفق السعر —
   الآن التدفق الحديث يحمي الحالة)، بقايا أسعار/شموع متقادمة للرموز الملغاة
   تُنظّف ولا تُعرض (كانت تظهر أعمار ساعات!)، HEAD / يرجع 200 بلا مصادقة
   لفاحصات الصحة (GET / يبقى محميًا)، /api/signals و/api/pnl_history أصبحتا
   محميتين (كانتا تكشفان بيانات الصفقات للعامة).

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
from decimal import Decimal, ROUND_FLOOR
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

BOT_VERSION = "FE1.8.0"  # FE1.8.0: حماية الموضع — وقف راكن STOP_LOSS_LIMIT على المنصة + مصالقة دورية، BE@1R (وقف عند التعادل)، إغلاق جزئي 50% عند +1R، حد خسارة يومي + قاطع متتاليات الخسارة، بوابة R:R صافية بعد الرسوم
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

# [FE1.5.0] ماسح الكون الكامل — فحص أولي ديناميكي لكل أزواج باينانس USDT الملائمة
# للاستراتيجية (موجات إليوت + فيبوناتشي) بدل قائمة يدوية ثابتة. درس حرب الذاكرة:
# لا load_markets إطلاقًا — نقاط خام فقط (ticker/24hr + klines) بوزن منخفض جدًا.
SCAN_UNIVERSE_ENABLED = os.getenv("SCAN_UNIVERSE_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
SCAN_INTERVAL_SEC = float(os.getenv("SCAN_INTERVAL_SEC", "21600"))    # فحص كامل كل 6 ساعات
SCAN_TOP_N = int(os.getenv("SCAN_TOP_N", "20"))                       # عدد الأزواج المطبقة على قائمة المراقبة
SCAN_CANDIDATES = int(os.getenv("SCAN_CANDIDATES", "40"))             # كم مرشحًا يُحلَّل بشموع 15m
SCAN_MIN_VOLUME_USDT = float(os.getenv("SCAN_MIN_VOLUME_USDT", "5000000"))  # سيولة 24h أدنى (5 مليون $)
SCAN_MAX_SPREAD_PCT = float(os.getenv("SCAN_MAX_SPREAD_PCT", "0.15"))  # أقصى فرق bid/ask %
SCAN_MIN_RANGE_PCT = float(os.getenv("SCAN_MIN_RANGE_PCT", "2.0"))     # أدنى مدى 24h % — الموجات تحتاج حركة
SCAN_KLINES_LIMIT = int(os.getenv("SCAN_KLINES_LIMIT", "200"))         # شموع 15m لكل مرشح (وزن 2 فقط)
SCANNER_BAN_RETRY_SEC = float(os.getenv("SCANNER_BAN_RETRY_SEC", "1800"))  # [FE1.5.1] إعادة محاولة بعد إجهاض 418/429 (30 دقيقة)

# [FE1.6.0] اقتباسات ElliottWavesEngine (github.com/SmarterSystems/ElliottWavesEngine)
# فحص ذيل شامل للقواعد + أرضية تناسبية للأمواج الدافعة + سلّم أهداف احتمالي
# + بوابة تحيز الاتجاه من فريم أعلى — كلها متغيرات بيئة قابلة للضبط الحي
WAVE_MIN_PROPORTION = float(os.getenv("WAVE_MIN_PROPORTION", "0.15"))  # أرضية الموجة الدافعة من الحركة الأمومية (0 يعطل القاعدة الرابعة)
TP_LADDER_ENABLED = os.getenv("TP_LADDER_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
TP_MIN_RR = float(os.getenv("TP_MIN_RR", "0.5"))          # أدنى مخاطرة/عائد يقبل به هدف من السلّم — وإلا بقي 1.618 الأصلي (الوقف البنيوي يجعل R:R النموذجي 0.5-0.8)
HTF_BIAS_ENABLED = os.getenv("HTF_BIAS_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
HTF_BIAS_TIMEFRAME = os.getenv("HTF_BIAS_TIMEFRAME", "1d")  # فريم التحيز الأعلى (يوجّه فريم الكشف 15m)
HTF_BIAS_CACHE_SEC = float(os.getenv("HTF_BIAS_CACHE_SEC", "14400"))  # كاش التحيز 4 ساعات (وزن REST مهمل)

# [FE1.7.0] بوابات جودة القبول — دروس أول صفقات حية: 8/9 إشارات كانت مطاردة فوق منطقة
# الدخول (+1.1% إلى +4.3%) و5 منها انتهت دون لمس، 3/9 إعادة حرفية لنفس المحاور،
# وإشارة UNI بهدف أقل من السعر الحي (نمط حقق هدفه والبوت يشتري بعده).
MAX_ENTRY_DISTANCE_PCT = float(os.getenv("MAX_ENTRY_DISTANCE_PCT", "1.5"))      # أقصى ارتفاع للسوق فوق منطقة الدخول % — لا مطاردة (0 يعطل)
MAX_STRUCTURE_AGE_BARS = int(os.getenv("MAX_STRUCTURE_AGE_BARS", "12"))        # أقصى عمر بنية P5 بالشموع — لا بنى أتمت قبل ساعات (0 يعطل)
SYMBOL_COOLDOWN_SEC = float(os.getenv("SYMBOL_COOLDOWN_SEC", "5400"))          # تبريد الرمز بعد انتهاء/إلغاء أمر معلق — لا إعادة إنشاء حرفية (0 يعطل)
CLUSTER_MAX_SAME_DIRECTION = int(os.getenv("CLUSTER_MAX_SAME_DIRECTION", "3")) # سقف الإشارات الصاعدة النشطة معًا — لا 5 لونجات مترابطة (0 يعطل)
# [FE1.7.0] سقوف التعرض الورقي — كانت الورقي يفتح مركزًا بقيمة 2.5× الرصيد (مخاطرة 1%
# على وقف ضيق = رافعة ضمنية) بينما الحقيقي مقيد بـ REAL_MAX_NOTIONAL_USDT — الإحصاءات
# الورقية لن تكون تنبؤية للحقيقي دون سقوف مماثلة.
PAPER_MAX_POSITION_PCT = float(os.getenv("PAPER_MAX_POSITION_PCT", "30"))      # سقف قيمة المركز الواحد % من الرصيد الورقي (0 يعطل)
PAPER_MAX_TOTAL_PCT = float(os.getenv("PAPER_MAX_TOTAL_PCT", "100"))           # سقف مجموع قيم المراكز الورقية النشطة % من الرصيد (0 يعطل)
# [FE1.7.0] حارس انقطاع التغذية مع مواضع مفتوحة — كان فشل الجلب يُتخطى صامتًا
# فيمضي الوقف/الهدف بلا فحص طوال الانقطاع (إعادة نشر/حظر 418/سقوط المزودين)
OUTAGE_ALERT_AFTER_CYCLES = int(os.getenv("OUTAGE_ALERT_AFTER_CYCLES", "3"))   # تنبيه بعد N دورات مراقبة فاشلة متتالية (60ث لكل دورة)
OUTAGE_RENOTIFY_SEC = float(os.getenv("OUTAGE_RENOTIFY_SEC", "900"))           # تكرار التنبيه كل 15 دقيقة طوال الانقطاع

# [FE1.8.0] حماية الموضع — درس التشغيل الحي: الوقف كان في الذاكرة فقط (لا أمر STOP راكن
# على المنصة) فأي انقطاع/نشر يترك الموضع مكشوفًا، ولا توجد آلية لقفل الربح أو تقليص
# التعرض بعد تحقق جزء من الفرضية.
REAL_STANDING_STOP = os.getenv("REAL_STANDING_STOP", "1").strip().lower() not in ("0", "false", "no", "off")
STOP_LIMIT_OFFSET_PCT = float(os.getenv("STOP_LIMIT_OFFSET_PCT", "0.5"))       # سعر LIMIT لأمر الوقف الراكن أسفل التريغر % — ضمان الملء في الومضة (0 = LIMIT عند التريغر نفسه)
RECONCILE_REAL_SEC = float(os.getenv("RECONCILE_REAL_SEC", "600"))             # مصالقة حماية المواضع الحقيقية كل N ثانية (منصة هي مصدر الحقيقة)
BE_AT_R_ENABLED = os.getenv("BE_AT_R_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
BE_TRIGGER_R = float(os.getenv("BE_TRIGGER_R", "1.0"))                         # نقل الوقف إلى الدخول عند +N×R (الورقي والحقيقي) — 0 يعطل عبر BE_AT_R_ENABLED
PARTIAL_AT_R_ENABLED = os.getenv("PARTIAL_AT_R_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
PARTIAL_CLOSE_PCT = float(os.getenv("PARTIAL_CLOSE_PCT", "50.0"))              # نسبة الإغلاق الجزئي عند +N×R — تحقيق ربح جزئي وتقليص التعرض (1-99)
DAILY_LOSS_LIMIT_PCT = float(os.getenv("DAILY_LOSS_LIMIT_PCT", "5.0"))         # إيقاف الإشارات الجديدة بعد خسارة يومية % من أساس اليوم (0 يعطل)
MAX_CONSEC_LOSSES = int(os.getenv("MAX_CONSEC_LOSSES", "3"))                   # قاطع المتتاليات: N خسائر متتالية → تبريد تداول (0 يعطل)
LOSS_STREAK_COOLDOWN_SEC = float(os.getenv("LOSS_STREAK_COOLDOWN_SEC", "14400"))  # تبريد 4 ساعات بعد المتتالية — المراقبة تستمر بلا انقطاع
RR_NET_MIN = float(os.getenv("RR_NET_MIN", "0.3"))                             # أرضية R:R صافية بعد رسوم الاتجاهين — الإشارات تحت الأرضية تُرفض (0 يعطل)

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
MEM_GC_THRESHOLD_MB = float(os.getenv("MEM_GC_THRESHOLD_MB", "360"))  # تجميع قسري فوق هذا ([FE1.4.1] 380←360)
MEM_CRITICAL_MB = float(os.getenv("MEM_CRITICAL_MB", "440"))          # سجل حرج فوق هذا ([FE1.4.1] 450←440)

# [FE1.4.0] التداول الحقيقي — زر مثل V9: تفعيله يحول الإشارات الجديدة إلى أوامر
# فعلية على باينانس (LIMIT عند فيبو 0.382 ← بيع سوق عند الوقف/الهدف). الورقي يبقى
# الوضع الافتراضي الآمن، والتفعيل يتطلب مفاتيح + فحص اتصال ناجح من الزر نفسه.
BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "0").strip().lower() in ("1", "true", "yes", "on")
REAL_MAX_NOTIONAL_USDT = float(os.getenv("REAL_MAX_NOTIONAL_USDT", "50.0"))  # سقف قيمة أمر الشراء الحقيقي الواحد (حماية)
BIN_STATUS_TTL_SEC = float(os.getenv("BIN_STATUS_TTL_SEC", "60"))  # كاش بطاقة اتصال باينانس
REAL_RULES_TTL_SEC = float(os.getenv("REAL_RULES_TTL_SEC", "21600"))  # [FE1.4.1] كاش قواعد السوق الواحد (6 ساعات)

DASHBOARD_PROTECTED = bool(DASHBOARD_USERNAME and DASHBOARD_PASSWORD)
USE_POSTGRES = DATABASE_URL.startswith("postgres")

TF_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600,
    "2h": 7200, "4h": 14400, "6h": 21600, "8h": 28800, "12h": 43200, "1d": 86400,
}

logger = get_logger("fibo-elio")


# [FE1.3.1] أدوات قياس وتنظيف الذاكرة — بلا تبعيات خارجية (قراءة /proc مباشرة)
def _malloc_trim() -> None:
    """[FE1.4.1] إرجاع الذاكرة المحررة فعليًا لنظام التشغيل عبر glibc malloc_trim.
    gc.collect() يحرر الكائنات لكن مُوزّع CPython يحتجز الصفحات (تجزئة الـ heap)
    فلا تنخفض RSS — وmalloc_trim هو ما يعيدها للنظام فعلًا. بلا أثر إن فشلت."""
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


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
    """قياس + تنظيف ذكي: malloc_trim دائمًا (رخيص)، وgc.collect() فوق عتبة التحذير،
    وسجل حرج فوق الحد الأخير. تُستدعى دوريًا من حلقات المسح/المراقبة —
    قراءة /proc ونداء trim رخيصان والتنظيف الثقيل عند الحاجة فقط.
    تعيد RSS الحالية بالميجابايت."""
    _malloc_trim()  # [FE1.4.1] إرجاع الصفحات المحررة سابقًا للنظام — يقاوم زحف RSS المزمن
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
            # [FE1.6.1] قيم الفهرس أصبحت قوائم أسواق (اصطلاح ccxt 4.4+) — نفحص
            # أول سوق داخل القائمة نفسه لنقرر الإبقاء على المعرف أو حذفه
            kept: Dict[str, Any] = {}
            for i, m in mbid.items():
                m0 = m[0] if (isinstance(m, list) and m) else m
                if i in keep_set or (isinstance(m0, dict) and (m0.get("symbol") in keep_set or m0.get("id") in keep_set)):
                    kept[i] = m
            ex.markets_by_id = kept
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
    "rejected_htf_bias": 0,  # [FE1.6.0] إشارات صاعدة مرفوضة لانحياز هابط قوي على الفريم الأعلى
    "rejected_stale_premise": 0,  # [FE1.6.2] إشارات من محاور تاريخية: الإغلاق الحالي دون P0 (فرضية ماتت)
    "rejected_far_entry": 0,      # [FE1.7.0] مطاردة: السوق أعلى من منطقة الدخول بفارق كبير
    "rejected_target_invalid": 0, # [FE1.7.0] الهدف تحت السعر الحي أو تحت P5 — نمط حقق هدفه بالفعل
    "rejected_old_structure": 0,  # [FE1.7.0] بنية P0-P5 تجاوزت سقف العمر
    "rejected_cooldown": 0,       # [FE1.7.0] تبريد الرمز بعد انتهاء/إلغاء حديث
    "rejected_cluster": 0,        # [FE1.7.0] سقف العنقود الاتجاهي
    "rejected_exposure_cap": 0,   # [FE1.7.0] سقوف التعرض الورقي (مركز/إجمالي)
    "rejected_rr_net": 0,         # [FE1.8.0] R:R صافي بعد الرسوم تحت الأرضية
    "rejected_risk_pause": 0,     # [FE1.8.0] تبريد متتاليات الخسارة جارٍ
    "rejected_daily_loss": 0,     # [FE1.8.0] حد الخسارة اليومي ملامس
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
  meta_json TEXT,
  initial_quantity NUMERIC,
  realized_pnl_usdt NUMERIC DEFAULT 0
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
    for col, ddl in (("is_real", "INTEGER DEFAULT 0"), ("order_id", "TEXT"), ("exit_order_id", "TEXT"),
                     ("initial_quantity", "NUMERIC"), ("realized_pnl_usdt", "NUMERIC DEFAULT 0")):  # [FE1.8.0] محاسبة الجزئي
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
    """تقريب الكمية حسب قواعد المزود الفعّال — بأمان تام بلا استثناءات.
    [FE1.4.2] بلا load_markets: لباينانس عبر exchangeInfo?symbol= الخام (نفس
    فلسفة طبقة التداول بلا أسواق) — amount_to_precision الموحدة كانت تستدعي
    market() التي تحمّل كون الأسواق عند أول إشارة ورقية (نتوء OOM)."""
    try:
        ex = current_exchange()
        if ex is None:
            return qty
        name = active_source.get("name") or "binance"
        if name == "binance" and not getattr(ex, "markets", None):
            r = real_market_rules(symbol, ex=_binance_public_probe())
            if r:
                v = _floor_step(float(qty), r.get("step") or 0.0)
                return v if v > 0 else 0.0
            return qty
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


def _binance_raw_klines(ex, symbol: str, timeframe: str, limit: int) -> list:
    """[FE1.4.2] شموع باينانس الخام عبر publicGetKlines — بلا load_markets نهائيًا.
    أول مسح عند الإقلاع كان عبر fetch_ohlcv الموحدة التي تحمّل كون الأسواق داخليًا
    (نتوء +100-250MB) فيقتل الخدمة فوق سقف 512MB مباشرة بعد الإقلاع — وهو ما
    فجّر النشر الأول لـ FE1.4.1. الصيغة الخام: [openTime, o, h, l, c, v, ...]."""
    raw = ex.publicGetKlines({"symbol": _bin_sym(symbol), "interval": timeframe,
                              "limit": int(limit)})
    return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])]
            for k in (raw or [])]


def fetch_ohlcv_raw(symbol: str, timeframe: str, limit: int) -> Tuple[Optional[list], Optional[str]]:
    """تجربة المزودين بالترتيب: باينانس أولًا (الأصل) ثم البدائل عند الحظر/الفشل.
    المزود الفاشل يدخل تبريدًا مؤقتًا حتى لا تُهدر زمن كل دورة عليه."""
    now = time.time()
    with provider_lock:
        order = [n for n in EXCHANGES if provider_state[n]["cooldown_until"] <= now]
    errors: List[str] = []
    for name in order:
        try:
            if name == "binance":
                # [FE1.4.2] نقاط خام بلا أسواق — المسح هو أول نشاط عند الإقلاع
                # وكان أكبر مصدر نتوء ذاكرة (fetch_ohlcv الموحدة تحمّل كون الأسواق).
                # غياب publicGetKlines (نسخ قديمة/بدائل اختبار) ← سقوط آمن للموحدة.
                try:
                    raw = _binance_raw_klines(EXCHANGES[name], symbol, timeframe, limit)
                except AttributeError:
                    raw = EXCHANGES[name].fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            else:
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
# [FE1.6.0] + أرضية التناسب WAVE_MIN_PROPORTION والفحص الواعي بالذيل يعملان
# تلقائيًا داخل كاشف المحاور (محاور مُنقّاة بالويك + قيم قصى مطلقة بين المحاور)
detector = PivotDetector(DetectorConfig(
    method="zigzag",
    deviation_threshold=DEVIATION_THRESHOLD,
    price_source="close",
    min_wave_bars=MIN_WAVE_BARS,
    require_fib_confluence=False,
    fib_tolerance_pct=FIB_TOLERANCE_PCT,
    min_wave_proportion=WAVE_MIN_PROPORTION,
))


# ══════════════════════════════════════════════════════════════════════════════
# [FE1.4.0] طبقة التداول الحقيقي — باينانس مباشرة بقواعد المنصة الكاملة
# المبدأ: الورقي يبقى الافتراضي، والزر يفعّل تنفيذ الإشارات الجديدة فعليًا.
# كل أمر يمر عبر قواعد باينانس: دقة الكمية/السعر، أدنى قيمة/كمية، كفاية الرصيد.
# ══════════════════════════════════════════════════════════════════════════════

_trade_ex_lock = threading.Lock()
_trade_ex: Any = None            # نسخة التداول (مفاتيح خاصة) — تُبنى مرة واحدة كسولًا
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
            # [FE1.4.1] privateGetAccount بدل fetch_balance — fetch_balance كانت
            # تستدعي load_markets داخليًا فتحمّل كون أسواق باينانس كاملًا (سبب OOM)!
            acc = _real_account(ex)
            usdt = next((b for b in (acc.get("balances") or [])
                         if isinstance(b, dict) and b.get("asset") == "USDT"), {})
            data["usdt_free"] = float(usdt.get("free") or 0.0)
            data["usdt_total"] = float(usdt.get("free") or 0.0) + float(usdt.get("locked") or 0.0)
            ct = acc.get("canTrade")
            data["can_trade"] = bool(ct) if ct is not None else None
    except Exception as exc:
        data["error"] = str(exc)[:220]
    with _bin_status_lock:
        _bin_status_cache["ts"] = now
        _bin_status_cache["data"] = dict(data)
    return data


def _real_account(ex) -> Dict[str, Any]:
    """[FE1.4.1] حساب باينانس الخام (GET /api/v3/account عبر privateGetAccount) —
    نقطة implicit لا تستدعي load_markets إطلاقًا (بديل fetch_balance الذي كان يحمّل
    كون الأسواق كاملًا ويسبب أعطال OOM)."""
    return ex.privateGetAccount() or {}


# ── [FE1.4.1] أدوات الطبقة بلا أسواق — قواعد السوق الواحد + الدقة اليدوية ──────
_REAL_RULES_LOCK = threading.Lock()
_REAL_RULES_CACHE: Dict[str, Dict[str, Any]] = {}  # symbol -> {"ts": float, "rules": dict}


def _bin_sym(symbol: str) -> str:
    """صيغة باينانس الخام: BTC/USDT ← BTCUSDT."""
    return str(symbol).replace("/", "").replace(":", "").upper()


def _fmt_dec(v: float) -> str:
    """نص عشري بلا أُس علمي (باينانس ترفض 1e-05) — عبر Decimal لتفادي انحراف العوامات."""
    return format(Decimal(str(v)).normalize(), "f")


def _floor_step(value: float, step: float) -> float:
    """أرضية القيمة على مضاعفات الخطوة (stepSize للكمية/tickSize للسعر) بدقة Decimal
    — بديل amount_to_precision/price_to_precision التي تتطلب كون الأسواق كاملًا."""
    try:
        if not step or step <= 0:
            return value
        q = (Decimal(str(value)) / Decimal(str(step))).to_integral_value(rounding=ROUND_FLOOR)
        return float(q * Decimal(str(step)))
    except Exception:
        return value


def _norm_real_order(raw: Any) -> Dict[str, Any]:
    """توحيد استجابة باينانس الخام على نفس شكل ccxt الذي تستهلكه بقية الشيفرة:
    {id, status(open/closed/canceled/expired/rejected), filled, average, price} —
    فلا يتغير أي منطق أعلى الطبقة (handle_real_pending/close_real_trade...)."""
    raw = raw or {}
    st = str(raw.get("status") or "").upper()
    st_map = {"NEW": "open", "PENDING_CANCEL": "open", "PARTIALLY_FILLED": "open",
              "FILLED": "closed", "CANCELED": "canceled", "CANCELLED": "canceled",
              "REJECTED": "rejected", "EXPIRED": "expired"}
    filled = float(raw.get("executedQty") or 0.0)
    quote = float(raw.get("cummulativeQuoteQty") or 0.0)
    avg = (quote / filled) if (filled > 0 and quote > 0) else None
    price = float(raw.get("price") or 0.0)
    return {
        "id": str(raw.get("orderId") or raw.get("clientOrderId") or ""),
        "status": st_map.get(st, st.lower() or "open"),
        "filled": filled,
        "average": avg,
        "price": price or None,
        "raw": raw,
    }


def real_market_rules(symbol: str, ex=None, force: bool = False) -> Dict[str, Any]:
    """[FE1.4.1] قواعد سوق واحد من باينانس عبر exchangeInfo?symbol=… — استجابة كيلوبايتات
    بدل كون الأسواق الكامل (آلاف الميجابايتات)، مع كاش REAL_RULES_TTL_SEC.
    بلا load_markets نهائيًا. يعيد {tick, step, min_qty, min_cost, status} أو {} بأمان."""
    now = time.time()
    with _REAL_RULES_LOCK:
        c = _REAL_RULES_CACHE.get(symbol)
        if c and not force and now - c["ts"] < REAL_RULES_TTL_SEC:
            return c["rules"]
    ex = ex or binance_trade_exchange()
    if ex is None:
        return {}
    try:
        raw = ex.publicGetExchangeInfo({"symbol": _bin_sym(symbol)}) or {}
        syms = raw.get("symbols") or []
        s = syms[0] if syms else {}
        flt = {f.get("filterType"): f for f in (s.get("filters") or []) if isinstance(f, dict)}
        notion = flt.get("NOTIONAL") or flt.get("MIN_NOTIONAL") or {}
        rules = {
            "tick": float((flt.get("PRICE_FILTER") or {}).get("tickSize") or 0.0),
            "step": float((flt.get("LOT_SIZE") or {}).get("stepSize") or 0.0),
            "min_qty": float((flt.get("LOT_SIZE") or {}).get("minQty") or 0.0),
            "min_cost": float(notion.get("minNotional") or 0.0),
            "status": s.get("status") or "",
        }
        with _REAL_RULES_LOCK:
            _REAL_RULES_CACHE[symbol] = {"ts": now, "rules": rules}
        return rules
    except Exception as exc:
        logger.warning("تعذر جلب قواعد السوق %s من باينانس: %s", symbol, exc)
        with _REAL_RULES_LOCK:
            c = _REAL_RULES_CACHE.get(symbol)
        return dict(c["rules"]) if c else {}


def real_market(ex, symbol: str) -> Dict[str, Any]:
    """قواعد السوق بصيغة موحدة خفيفة (بلا أسواق — [FE1.4.1]):
    {limits:{cost:{min},amount:{min}}, step, tick} من كاش exchangeInfo?symbol=.
    الفلاتر نفسها التي كانت من كون الأسواق (NOTIONAL/LOT_SIZE) لكن بمصدر رخيم."""
    r = real_market_rules(symbol, ex)
    if not r:
        return {}
    return {
        "symbol": symbol,
        "limits": {"cost": {"min": r.get("min_cost") or None},
                   "amount": {"min": r.get("min_qty") or None}},
        "precision_step": r.get("step") or 0.0,
        "precision_tick": r.get("tick") or 0.0,
    }


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
    """أرضية الكمية على خطوة LOT_SIZE (stepSize من قواعد السوق عبر Decimal) —
    بلا استثناءات وبلا أسواق ([FE1.4.1] بدل amount_to_precision)."""
    if ex is None and binance_trade_exchange() is None:
        return qty  # بلا طبقة دقة متاحة — سقوط آمن كما في الأصل
    try:
        r = real_market_rules(symbol, ex)
        v = _floor_step(float(qty), r.get("step") or 0.0)
        return v if v > 0 else 0.0
    except Exception:
        return math.floor(qty * 1e6) / 1e6


def real_adjust_price(ex, symbol: str, price: float) -> float:
    """دقة السعر على tickSize (أرضية Decimal) — بلا استثناءات وبلا أسواق
    ([FE1.4.1] بدل price_to_precision). الأرضية آمنة لأمر الشراء (سعر أدنى يملأ)."""
    if ex is None and binance_trade_exchange() is None:
        return price  # بلا طبقة دقة متاحة — سقوط آمن كما في الأصل
    try:
        r = real_market_rules(symbol, ex)
        return _floor_step(float(price), r.get("tick") or 0.0)
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
    """أمر LIMIT BUY حقيقي عند فيبو 0.382 — يبقى معلقًا على المنصة كأمر حقيقي.
    [FE1.4.1] عبر نقطة باينانس الخام privatePostOrder — بلا أسواق إطلاقًا."""
    ex = binance_trade_exchange()
    if ex is None:
        return None
    try:
        raw = ex.privatePostOrder({
            "symbol": _bin_sym(symbol), "side": "BUY", "type": "LIMIT",
            "timeInForce": "GTC", "quantity": _fmt_dec(qty), "price": _fmt_dec(price),
            "newOrderRespType": "FULL",
        })
        order = _norm_real_order(raw)
        log_and_notify("info",
                       f"🟢 أمر حقيقي على باينانس: شراء LIMIT {symbol} — كمية {qty} عند {fmt_price(price)} "
                       f"(id={order.get('id')})", "REAL_ORDER")
        return order
    except Exception as exc:
        log_and_notify("error", f"❌ فشل أمر الشراء الحقيقي {symbol}: {exc}", "REAL_TRADE_ERROR")
        return None


def place_real_market_sell(symbol: str, qty: float) -> Optional[Dict[str, Any]]:
    """أمر بيع سوق حقيقي — للإغلاق عند الوقف/الهدف/يدويًا.
    [FE1.4.1] عبر نقطة باينانس الخام privatePostOrder — بلا أسواق إطلاقًا."""
    ex = binance_trade_exchange()
    if ex is None:
        return None
    try:
        raw = ex.privatePostOrder({
            "symbol": _bin_sym(symbol), "side": "SELL", "type": "MARKET",
            "quantity": _fmt_dec(qty), "newOrderRespType": "FULL",
        })
        order = _norm_real_order(raw)
        log_and_notify("info",
                       f"🔴 أمر حقيقي على باينانس: بيع سوق {symbol} — كمية {qty} (id={order.get('id')})",
                       "REAL_ORDER")
        return order
    except Exception as exc:
        log_and_notify("error", f"❌ فشل أمر البيع الحقيقي {symbol}: {exc}", "REAL_TRADE_ERROR")
        return None


def fetch_real_order(ex, symbol: str, order_id: Any) -> Optional[Dict[str, Any]]:
    """حالة الأمر الحقيقي من المنصة — [FE1.4.1] privateGetOrder موحّد بـ _norm_real_order.
    None عند فشل عابر (تُعاد المحاولة في الدورة القادمة)."""
    try:
        raw = ex.privateGetOrder({"symbol": _bin_sym(symbol), "orderId": int(str(order_id))})
        return _norm_real_order(raw)
    except Exception as exc:
        logger.warning("تعذر جلب حالة الأمر الحقيقي %s/%s: %s", symbol, order_id, exc)
        return None


def cancel_real_order(ex, symbol: str, order_id: Any) -> bool:
    """إلغاء أمر معلق حقيقي — [FE1.4.1] privateDeleteOrder.
    False يعني إعادة الفحص/المحاولة في الدورة القادمة."""
    try:
        ex.privateDeleteOrder({"symbol": _bin_sym(symbol), "orderId": int(str(order_id))})
        return True
    except Exception as exc:
        logger.warning("تعذر إلغاء الأمر الحقيقي %s/%s: %s", symbol, order_id, exc)
        return False


def fetch_free_base(ex, base: str) -> float:
    """الرصيد الحر للعملة الأساسية — للتحقق قبل البيع (نفس منطق V9).
    [FE1.4.1] من الحساب الخام بلا أسواق."""
    try:
        acc = _real_account(ex)
        for b in (acc.get("balances") or []):
            if isinstance(b, dict) and b.get("asset") == base:
                return float(b.get("free") or 0.0)
        return 0.0
    except Exception as exc:
        logger.warning("تعذر جلب رصيد %s الحر: %s", base, exc)
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
# محرك الصفقات الورقي — نفس تدفق execute_wave_setup الأصلي
# ══════════════════════════════════════════════════════════════════════════════

def compute_take_profit(setup: DetectedSetup) -> float:
    """الهدف = امتداد 1.618 للموجة 1 من قاع الموجة 2 (منطق الأصل حرفيًا).
    [FE1.6.0] صار الهدف الاحتياطي لسلّم compute_tp_ladder."""
    p0, p1, p2 = setup.pivot_prices[0], setup.pivot_prices[1], setup.pivot_prices[2]
    fib = FibonacciLevels(swing_start=p0, swing_end=p1)
    targets = fib.extension_levels(ratios=(1.618, 1.272), base_price=p2)
    tp = next((lv for lv in targets if lv.ratio == 1.618), targets[-1])
    return float(tp.price)


def compute_tp_ladder(setup: DetectedSetup) -> List[Tuple[float, str]]:
    """[FE1.6.0] سلّم أهداف الموجة 5 باحتمالاتها (اقتباس ElliottWavesEngine:
    سلّم أهداف باحتمالاتهم + تصعيد عند تجاوز الأهداف):
      1) W5 = W1 من قاع/قمة W4 — أشهر علاقة بين الموجتين (الأكثر حدوثًا)
      2) W5 = 0.618 × W3 من قاع/قمة W4 — امتداد متوسط
      3) امتداد 1.618 للموجة 1 من قاع W2 — هدف الأصل الأصلي (الأبعد)
    مرتبة: الصاعد تصاعديًا (الأقرب أولًا) والهابط تنازليًا.
    الاختيار في create_pending_signal: أقرب هدف يحقق TP_MIN_RR — يرفع نسبة
    الإصابة بدل مطاردة الهدف البعيد دائمًا، مع أرضية R:R صارمة."""
    P = setup.pivot_prices
    p0, p1, p2, p3, p4 = P[0], P[1], P[2], P[3], P[4]
    w1 = abs(p1 - p0)
    w3 = abs(p3 - p2)
    if setup.direction == "BULLISH":
        cands = [
            (p4 + w1, "w5_eq_w1"),            # W5 = W1 (مساواة)
            (p4 + 0.618 * w3, "w5_0618_w3"),  # W5 = 0.618 × W3
            (p2 + 1.618 * w1, "ext_1618"),    # امتداد 1.618 (الأصل)
        ]
        return sorted(cands, key=lambda t: t[0])
    cands = [
        (p4 - w1, "w5_eq_w1"),
        (p4 - 0.618 * w3, "w5_0618_w3"),
        (p2 - 1.618 * w1, "ext_1618"),
    ]
    return sorted(cands, key=lambda t: t[0], reverse=True)


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
    # [FE1.7.0] سقف المركز الواحد — كبح الرافعة الضمنية للورقي (القيمة فوق السقف تُقلّص لا تُرفض)
    if PAPER_MAX_POSITION_PCT > 0:
        max_pos = balance * (PAPER_MAX_POSITION_PCT / 100.0)
        if notional > max_pos:
            qty = amount_prec(symbol, max_pos / entry)
            if qty <= 0:
                qty = math.floor(max_pos / entry * 1e6) / 1e6
            notional = qty * entry
            logger.info("[%s] قُلّص الحجم بسقف المركز الورقي (%.0f%% من الرصيد = %.2f$)",
                        symbol, PAPER_MAX_POSITION_PCT, notional)
    # [FE1.7.0] سقف التعرض الإجمالي للمراكز النشطة — الباقي من السقف هو الأقصى المسموح
    if PAPER_MAX_TOTAL_PCT > 0:
        max_total = balance * (PAPER_MAX_TOTAL_PCT / 100.0)
        remaining = max_total - active_paper_notional()
        if remaining < MIN_NOTIONAL_USDT:
            with scan_stats_lock:
                scan_stats["rejected_exposure_cap"] += 1
            logger.info("[%s] رفض: التعرض الورقي النشط بلغ سقف %.0f%% من الرصيد (%.2f$/%.2f$)",
                        symbol, PAPER_MAX_TOTAL_PCT, max_total - remaining, max_total)
            return None
        if notional > remaining:
            qty = amount_prec(symbol, remaining / entry)
            if qty <= 0:
                qty = math.floor(remaining / entry * 1e6) / 1e6
            notional = qty * entry
            logger.info("[%s] قُلّص الحجم بسقف التعرض الإجمالي إلى %.2f$ (المتبقي %.2f$)",
                        symbol, notional, remaining)
    if notional < MIN_NOTIONAL_USDT:
        # [FE1.7.0] بعد التقليص صار أدنى من قيمة التداول — لا صفقة
        with scan_stats_lock:
            scan_stats["rejected_exposure_cap"] += 1
        logger.info("[%s] رفض: الحجم بعد سقوف التعرض دون أدنى قيمة (%.2f$)", symbol, notional)
        return None
    return qty


def active_trade_count() -> int:
    rows = db.query(
        "SELECT COUNT(*) AS n FROM signals WHERE status IN ('pending', 'open')"
    )
    return int(rows[0]["n"]) if rows else 0


def active_paper_notional() -> float:
    """[FE1.7.0] مجموع قيمة المراكز الورقية النشطة (معلقة + مفتوحة) — لسقف التعرض الإجمالي.
    كانت الورقي يفتح مركزًا بقيمة 2.5× الرصيد (AVAX: وقف 0.4% × مخاطرة 1% = 24,920$)
    فيصبح سقف 5 صفقات رافعة ضمنية 12×+ لا تمثل اقتصاد الحقيقي المقيّد بـ 50$/أمر."""
    rows = db.query(
        "SELECT COALESCE(SUM(notional_usdt), 0) AS s FROM signals"
        " WHERE status IN ('pending', 'open') AND COALESCE(is_real, 0) = 0"
    )
    try:
        return float(rows[0]["s"] or 0.0) if rows else 0.0
    except Exception:
        return 0.0


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
WS_SNAPSHOT_MAX_AGE_SEC = 1800.0   # [FE1.5.0] ما فوق هذا العمر لا يُعرض في اللوحة (بقايا رموز ملغاة)


def _ws_mark(symbol: str, provider: str, state: str, error: str = "") -> None:
    """تحديث حالة اشتراك رمز للتشخيص (/api/ws/status واللوحة).
    [FE1.5.0] إصلاح «connecting العالقة»: إعادة اتصال تيار واحد (شموع مثلًا) لا
    تُنزل حالة الرمز من «live» طالما تدفق حديث من التيار الآخر — كانت إعادة
    اتصال الشموع تُعاد الحالة «connecting» باستمرار رغم تدفق السعر (579 تحديثًا)
    فتبدو live_streams=0 كذبًا في اللوحة."""
    with _ws_lock:
        sub = _ws_subs.setdefault(symbol, {
            "provider": provider, "state": state, "last_error": "",
            "updates": 0, "last_msg_at": None, "last_msg_ts": 0.0,
            "started_at": utc_now_iso(),
        })
        sub["provider"] = provider
        if state in ("connecting", "error") and sub.get("state") == "live":
            fresh = bool(sub.get("last_msg_ts")) and (time.time() - float(sub["last_msg_ts"])) <= WS_STALE_SEC
            if fresh:
                sub["last_error"] = error[:200]
                return
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
            sub["last_msg_ts"] = now      # [FE1.5.0] لحماية الحالة من إعادة اتصال التيار الآخر
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
            sub["last_msg_ts"] = now      # [FE1.5.0] لحماية الحالة من إعادة اتصال التيار الآخر
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
        # [FE1.5.0] لا بقايا متقادمة في اللوحة — كانت أعمار ساعات (1.8h!) تظهر للرموز الملغاة
        prices = {s: {"price": v["price"], "age_sec": round(now - v["ts"], 1), "source": v["source"]}
                  for s, v in _ws_price.items() if now - v["ts"] <= WS_SNAPSHOT_MAX_AGE_SEC}
        candles = {s: {"n": len(v["candles"]), "age_sec": round(now - v["ts"], 1), "source": v["source"]}
                   for s, v in _ws_candles.items() if now - v["ts"] <= WS_SNAPSHOT_MAX_AGE_SEC}
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


def _index_markets_by_id(fab: Dict[str, Any]) -> Dict[str, Any]:
    """[FE1.6.1] فهرس markets_by_id باصطلاح ccxt الحديث: المعرف الخام → [قائمة أسواق].
    safe_market في ccxt 4.4+ يقرأ markets_by_id[id] كقائمة (len()==1 → [0]) —
    قيمة dict مفردة تُفسَّر بعدد مفاتيحها وتنكسر في markets[0] بـ KeyError: 0
    لكل رسالة miniTicker/kline (سبب استثناء handle_tickers في السجلات).
    set_markets الداخلية لـ ccxt تبني هذا الاصطلاح — ونحن نتجاوزها بالحقن.
    ملاحظة: القيم المزدوجة في fab (رمز موحد + معرف) تشير لنفس السوق — الفهرسة
    بالمعرف الخام فقط وتزال الازدواجية تلقائيًا."""
    by_id: Dict[str, Any] = {}
    for m in fab.values():
        if not isinstance(m, dict):
            continue
        mid = m.get("id")
        if not mid:
            continue
        lst = by_id.get(mid)
        if lst is None:
            by_id[mid] = [m]
        elif all(x.get("symbol") != m.get("symbol") for x in lst):
            lst.append(m)
    return by_id


def _fabricate_ws_markets(name: str, symbols: List[str]) -> Dict[str, Any]:
    """[FE1.4.2] أسواق مصغّرة مصنوعة يدويًا لنسخة الويب سوكت — حتى لا يستدعي
    watch_ohlcv/watch_ticker الداخليان load_markets (كون الأسواق = نتوء OOM).
    معرف السوق بصيغة كل منصة: باينانس/بايبيت BTCUSDT · OKX BTC-USDT · Gate BTC_USDT.
    أي حقل إضافي يطلبه المزود يُدار بتعاقب المزودين + REST الخام احتياطًا."""
    def mk(sym: str) -> Dict[str, Any]:
        b, q = sym.split("/", 1)
        if name == "okx":
            mid = f"{b}-{q}"
        elif name == "gate":
            mid = f"{b}_{q}"
        else:  # binance/bybit وغيرهما: ملتصق
            mid = f"{b}{q}"
        return {"id": mid, "lowercaseId": mid.lower(), "symbol": sym,
                "base": b, "quote": q, "baseId": b, "quoteId": q,
                "type": "spot", "spot": True, "active": True,
                "swap": False, "future": False, "contract": False, "option": False,
                "linear": False, "inverse": False,
                "precision": {}, "limits": {}}
    markets: Dict[str, Any] = {}
    for s in symbols:
        if "/" in s:
            m = mk(s)
            markets[s] = m
            markets[m["id"]] = m  # بالمعرف أيضًا لـ safe_symbol على بيانات التيار
    return markets


def _ws_exchange(name: str):
    """نسخة ccxt.pro للمزود — اتصالات عامة بلا مفاتيح (الشموع العامة تكفي للورقي).
    [FE1.4.2] الأسواق تُحقن مصنوعة مصغّرة (قائمة المراقبة فقط) — لا load_markets
    إطلاقًا على نسخ الويب سوكت (أول اشتراك كان يحمّل كون الأسواق = نتوء OOM)."""
    ex = _ws_exchanges.get(name)
    if ex is None:
        cls = getattr(ccxt.pro, name, None)
        if cls is None:
            raise ValueError(f"المزود {name} غير مدعوم في ccxt.pro")
        ex = cls({"enableRateLimit": False, "options": {"defaultType": "spot", "fetchMarkets": ["spot"]}})  # [FE1.3.2]
        if not getattr(ex, "markets", None):
            fab = _fabricate_ws_markets(name, watchlist)
            ex.markets = fab
            # [FE1.6.1] المعرف → [قائمة] باصطلاح ccxt 4.4+ (القيمة dict مفردة كانت
            # تكسر safe_market بـ KeyError: 0 على كل رسالة تيار — سبب فشل باينانس WS)
            ex.markets_by_id = _index_markets_by_id(fab)
            logger.info("أسواق مصنوعة مصغّرة لويب سوكت %s — %d رمز (بلا load_markets)", name, len(watchlist))
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
            # [FE1.4.2] الأسواق مصنوعة مصغّرة داخل _ws_exchange — لا load_markets إطلاقًا
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
            _ws_candles.pop(sym, None)   # [FE1.5.0] لا بقايا أسعار/شموع متقادمة للرمز الملغى
            _ws_price.pop(sym, None)
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
            # [FE1.8.0] حالة الحماية للوحة: BE/جزئي/الوقف الراكن + محاسبة الجزئي
            meta = sig.get("meta") if isinstance(sig.get("meta"), dict) else None
            if meta is None and sig.get("meta_json"):
                try:
                    meta = json.loads(sig["meta_json"])
                except Exception:
                    meta = {}
            meta = meta if isinstance(meta, dict) else {}
            out["be_done"] = bool(meta.get("be_done"))
            out["partial_done"] = bool(meta.get("partial_done"))
            out["stop_order_id"] = meta.get("stop_order_id") or None
            out["realized_pnl_usdt"] = round(float(sig.get("realized_pnl_usdt") or 0), 6)
            out["initial_quantity"] = float(sig.get("initial_quantity") or qty)
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


def create_pending_signal(symbol: str, setup: DetectedSetup, last_close: float = 0.0) -> bool:
    """أمر معلّق عند 0.382 لتراجع الموجة 3 — كما ينفذ الأصل _determine_entry_price.
    [FE1.4.0] وضع التداول الحقيقي: أمر LIMIT BUY فعلي على باينانس بنفس السعر
    وبقواعد المنصة الكاملة (دقة السعر/الكمية، أدنى قيمة، كفاية الرصيد).
    فشل الأمر الحقيقي = لا إشارة (لا سقوط صامت للورقي).
    [FE1.7.0] بوابتا المطاردة وصلاحية الهدف لحظة الإنشاء (last_close=0 يعطّلهما
    — توافق نداءات الاختبارات القديمة): لا أمر معلق بعيدًا عن السوق (زومبي يقطس
    خانة 45 دقيقة ثم يُعاد حرفيًا)، ولا شراء نمطٍ حقق هدفه بالفعل.
    [FE1.8.0] قاطع المخاطر قبل أي أمر (تبريد متتاليات الخسارة/حد الخسارة اليومي
    — الإشارات تتوقف والمراقبة مستمرة) + أرضية R:R صافية بعد رسوم الاتجاهين."""
    # [FE1.8.0] قاطع المخاطر — قبل أي حساب أو أمر (ورقي أو حقيقي)
    block = risk_entry_block_reason()
    if block:
        key = "rejected_risk_pause" if "تبريد" in block else "rejected_daily_loss"
        with scan_stats_lock:
            scan_stats[key] += 1
        logger.info("[%s] رفض قاطع المخاطر: %s — لا إشارة جديدة", symbol, block)
        return False
    entry = float(setup.entry_zone_low)
    sl = float(setup.stop_loss_price)
    tp = compute_take_profit(setup)
    # [FE1.6.0] سلّم الأهداف: أقرب هدف احتمالي يحقق أرضية R:R — وإلا بقي 1.618
    tp_basis = "ext_1618"
    risk_per_coin_pre = entry - sl
    if TP_LADDER_ENABLED and risk_per_coin_pre > 0:
        for cand, basis in compute_tp_ladder(setup):
            if (cand - entry) / risk_per_coin_pre >= TP_MIN_RR:
                tp, tp_basis = float(cand), basis
                break
    if not (entry > 0 and sl > 0 and tp > entry > sl):
        logger.info("[%s] أسعار الإعداد غير منطقية (entry=%s sl=%s tp=%s) — تجاهل",
                    symbol, fmt_price(entry), fmt_price(sl), fmt_price(tp))
        return False
    # [FE1.7.0] بوابة المطاردة: من بيانات أول صفقات حية — 8/9 إشارات مُنشأة كانت
    # بسعر سوق أعلى من منطقة الدخول (+1.1% إلى +4.3%) و5 منها انتهت دون لمس:
    # المعلق البعيد يقطس خانة 45 دقيقة ثم يُعاد حرفيًا كل دورة. الشراء فقط حين
    # يكون السعر قرب منطقة الدخول فعلًا (تراجع W4 بدأ) — عندها الملء له معنى.
    if last_close > 0 and MAX_ENTRY_DISTANCE_PCT > 0:
        distance_pct = (float(last_close) / entry - 1.0) * 100.0
        if distance_pct > MAX_ENTRY_DISTANCE_PCT:
            with scan_stats_lock:
                scan_stats["rejected_far_entry"] += 1
            logger.info("[%s] رفض مطاردة: السعر الحي %s أعلى من منطقة الدخول %s بـ%.2f%% (السقف %.1f%%) — لا إشارة",
                        symbol, fmt_price(float(last_close)), fmt_price(entry),
                        distance_pct, MAX_ENTRY_DISTANCE_PCT)
            return False
    # [FE1.7.0] صلاحية الهدف: هدف تحت السعر الحي أو تحت P5 = الموجة 5 وصلت السقف
    # (حالة حية UNI: TP=7.592 والإغلاق 7.6 وP5=7.713 — الشراء بعد تحقق الهدف)
    if last_close > 0 and setup.direction == "BULLISH":
        try:
            p5 = float(setup.pivot_prices[5])
        except (TypeError, ValueError, IndexError):
            p5 = 0.0
        ceiling = max(float(last_close), p5) if p5 > 0 else float(last_close)
        if tp <= ceiling:
            with scan_stats_lock:
                scan_stats["rejected_target_invalid"] += 1
            logger.info("[%s] رفض هدف مُحقق: TP %s ≤ max(الإغلاق %s, P5 %s) — لا إشارة",
                        symbol, fmt_price(tp), fmt_price(float(last_close)),
                        fmt_price(p5) if p5 > 0 else "—")
            return False
    # [FE1.8.0] أرضية R:R صافية بعد رسوم الاتجاهين — الورقي كان يقبل أهدافًا إجمالية
    # تأكل الرسوم (0.2% من قيمة الصفقة) نسبة معتبرة من العائد على الأهداف الضيقة
    rr_net = rr_net_value(entry, sl, tp)
    if RR_NET_MIN > 0 and risk_per_coin_pre > 0 and rr_net < RR_NET_MIN:
        with scan_stats_lock:
            scan_stats["rejected_rr_net"] += 1
        logger.info("[%s] رفض R:R صافٍ منخفض: %.3f < %.3f (دخول %s → هدف %s، وقف %s، رسوم الاتجاهين %.2f%%)",
                    symbol, rr_net, RR_NET_MIN, fmt_price(entry), fmt_price(tp), fmt_price(sl),
                    FEE_RATE * 200.0)
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
        "tp_note": "سلّم أهداف FE1.6.0 (W5=W1، 0.618×W3، امتداد 1.618) — الأصل 1.618 احتياطًا",
        "tp_basis": tp_basis,
        "tp_ladder": [round(c, 8) for c, _ in compute_tp_ladder(setup)] if TP_LADDER_ENABLED else [],
        "rr_net": round(rr_net, 4),  # [FE1.8.0] R:R صافي بعد رسوم الاتجاهين
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
    basis_txt = {
        "w5_eq_w1": "W5=W1", "w5_0618_w3": "W5=0.618×W3", "ext_1618": "امتداد 1.618",
    }.get(tp_basis, tp_basis)
    if fib:
        signal_msg = (
            f"🌊 إشارة إليوت+فيبو جديدة ({mode_tag}): {symbol}\n"
            f"دخول معلّق: {fmt_price(entry)} | وقف بنيوي: {fmt_price(sl)} | هدف {basis_txt}: {fmt_price(tp)}\n"
            f"R:R = {rr:.2f} (صافٍ بعد الرسوم {rr_net:.2f}) | W2={fib.wave2_retrace_pct*100:.1f}% W4={fib.wave4_retrace_pct*100:.1f}%"
        )
    else:
        signal_msg = f"🌊 إشارة إليوت+فيبو جديدة ({mode_tag}): {symbol} — دخول {fmt_price(entry)}"
    log_and_notify("info", signal_msg, "NEW_SIGNAL")
    return True


def close_signal_row(sig: Dict[str, Any], exit_price: float, reason: str,
                     exit_order_id: Optional[str] = None) -> None:
    """محاسبة الإغلاق: رسوم 0.1% × اتجاهين — نفس عقد المشروع السابق.
    [FE1.4.0] الصفقة الحقيقية: نفس المحاسبة للعرض والإحصاء لكن دون أي مساس
    بالرصيد الورقي (الأرباح/الخسائر الحقيقية على الحساب الفعلي في باينانس).
    [FE1.8.0] تدخل أرباح الأرجل الجزئية المحققة (realized_pnl_usdt) في الإجمالي
    مرة واحدة عند الإغلاق النهائي — ونسبة الربح على الحجم الأصلي لا المتبقي."""
    entry = float(sig["fill_price"])
    qty = float(sig["quantity"])
    realized_prev = float(sig.get("realized_pnl_usdt") or 0)   # [FE1.8.0] أرباح الجزئي السابقة
    base_qty = float(sig.get("initial_quantity") or qty)       # [FE1.8.0] الأساس الأصلي للنسبة
    gross = qty * (exit_price - entry)
    fees = (qty * entry + qty * exit_price) * FEE_RATE
    pnl_usdt = gross - fees + realized_prev
    pnl_pct = (pnl_usdt / (base_qty * entry)) * 100.0 if base_qty * entry > 0 else 0.0
    is_real = bool(sig.get("is_real"))
    db.execute(
        "UPDATE signals SET status='closed', close_price=%s, close_reason=%s, closed_at=%s,"
        " pnl_usdt=%s, pnl_pct=%s, exit_order_id=%s WHERE id=%s",
        (exit_price, reason, utc_now_iso(), round(pnl_usdt, 6), round(pnl_pct, 4), exit_order_id, sig["id"]),
    )
    _risk_on_close(pnl_usdt)  # [FE1.8.0] قاطع المخاطر: حد يومي + متتاليات
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
    # [FE1.8.0] ألغِ الوقف الراكن أولًا — وإلا بقي أمر STOP حي يبيع رصيدًا لا نملك بعده.
    # إن تبيّن أنه نُفذ على المنصة (ملء قبل الإلغاء) فالمحاسبة من سعر تنفيذه بلا بيع مزدوج.
    stop_oid = _sig_meta(sig).get("stop_order_id")
    if stop_oid:
        if not cancel_real_order(ex, symbol, stop_oid):
            so = fetch_real_order(ex, symbol, stop_oid)
            st = (so or {}).get("status")
            if st == "closed":
                close_signal_row(sig, float(so.get("average") or trigger_price),
                                 reason + " — الوقف الراكن نُفذ على المنصة أثناء الإغلاق",
                                 exit_order_id=str(so.get("id") or "") or None)
                return
            if st in ("open", None):
                # حي ولا يُلغى (أو الحالة غير قابلة للقراءة) — لا نبيع خوفًا من ازدواج
                log_and_notify("warning",
                               f"⚠ تعذر إلغاء الوقف الراكن لـ{symbol} — أُجّل الإغلاق للدورة القادمة تفاديًا لازدواج البيع",
                               "REAL_TRADE_ERROR")
                return
            # canceled/expired/rejected → الأمر ميت على المنصة — أمضِ للبيع عادي
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


# ══════════════════════════════════════════════════════════════════════════════
# [FE1.8.0] حماية الموضع — الوقف الراكن على المنصة + BE@1R + جزئي أول درج + قاطع مخاطر
# ══════════════════════════════════════════════════════════════════════════════

def _sig_meta(sig: Dict[str, Any]) -> Dict[str, Any]:
    """قراءة meta_json كقاموس — يقبل الصف الخام (meta_json نص) أو صف اللوحة المُحلل (meta)."""
    if isinstance(sig.get("meta"), dict):
        return dict(sig["meta"])
    raw = sig.get("meta_json")
    if raw:
        try:
            m = json.loads(raw)
            return m if isinstance(m, dict) else {}
        except Exception:
            return {}
    return {}


def _save_sig_meta(sig_id: Any, meta: Dict[str, Any]) -> None:
    """كتابة meta_json — حالة الحماية (stop_order_id/be_done/partial_done) تعيش مع الصف فتعبر النشر."""
    try:
        db.execute("UPDATE signals SET meta_json=%s WHERE id=%s",
                   (json.dumps(meta, ensure_ascii=False), sig_id))
    except Exception as exc:
        logger.warning("كتابة meta_json للصف %s فشلت: %s", sig_id, exc)


def rr_net_value(entry: float, sl: float, tp: float) -> float:
    """[FE1.8.0] R:R صافي بعد رسوم الاتجاهين: الرسوم تُدفع على الدخول والخروج
    (FEE_RATE × القيمة في كل اتجاه) فتُخصم من العائد قبل القسمة على المخاطرة.
    الورقي كان يعرض أرقامًا إجمالية تتحول حقيقية أضعف — الصافي هو الحاكم الآن."""
    risk = float(entry) - float(sl)
    if risk <= 0 or entry <= 0:
        return 0.0
    reward = (float(tp) - entry) - FEE_RATE * (entry + float(tp))
    return reward / risk


# ── قاطع المخاطر — حد خسارة يومي + تبريد متتاليات الخسارة (bot_state يعبر النشر) ──

def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _risk_base_now() -> float:
    """أساس نسبة الخسارة اليومية: رصيد الورقي — وفي الحقيقي رصيد USDT الحر من لقطة الاتصال."""
    if is_real_mode:
        try:
            v = float(binance_status_snapshot().get("usdt_free") or 0)
            if v > 0:
                return v
        except Exception:
            pass
    return get_paper_balance()


def _risk_on_close(pnl_usdt: float) -> None:
    """تحديث عدادات المخاطر بعد كل إغلاق: ترحيل اليوم، تراكم الخسارة اليومية، عدّ
    المتتاليات، وتفعيل تبريد الإشارات الجديدة عند N خسائر متتالية (المراقبة مستمرة)."""
    try:
        today = _utc_day()
        if db_get_state("risk_day") != today:
            db_set_state("risk_day", today)
            db_set_state("risk_realized", "0.0")
            db_set_state("risk_day_base", repr(_risk_base_now()))
            db_set_state("risk_streak", "0")
        realized = float(db_get_state("risk_realized", "0.0") or 0) + float(pnl_usdt or 0)
        db_set_state("risk_realized", repr(realized))
        if pnl_usdt < 0:
            streak = int(float(db_get_state("risk_streak", "0") or 0)) + 1
            db_set_state("risk_streak", str(streak))
            prev_pause = db_get_state("risk_pause_until")
            paused_now = bool(prev_pause and utc_now_iso() < prev_pause)
            if MAX_CONSEC_LOSSES > 0 and streak >= MAX_CONSEC_LOSSES and not paused_now:
                until = datetime.fromtimestamp(
                    time.time() + LOSS_STREAK_COOLDOWN_SEC, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
                db_set_state("risk_pause_until", until)
                log_and_notify(
                    "warning",
                    f"⛔ قاطع المخاطر: {streak} خسائر متتالية — إيقاف الإشارات الجديدة حتى {until} "
                    f"(المراقبة وإدارة المواضع القائمة تستمران بلا انقطاع)",
                    "RISK_PAUSE",
                )
        else:
            db_set_state("risk_streak", "0")
    except Exception as exc:
        logger.warning("تحديث عدادات المخاطر فشل: %s", exc)


def risk_snapshot() -> Dict[str, Any]:
    """بطاقة المخاطر للوحة (/api/all → risk): خسارة اليوم، الأساس، المتتالية، التبريد."""
    today = _utc_day()
    same_day = (db_get_state("risk_day") or today) == today
    realized = float(db_get_state("risk_realized", "0.0") or 0) if same_day else 0.0
    base = float(db_get_state("risk_day_base", "0") or 0) if same_day else 0.0
    streak = int(float(db_get_state("risk_streak", "0") or 0)) if same_day else 0
    pause_until = db_get_state("risk_pause_until") or ""
    paused = bool(pause_until and utc_now_iso() < pause_until)
    return {
        "daily_realized": round(realized, 4),
        "daily_base": round(base, 2),
        "daily_limit_pct": DAILY_LOSS_LIMIT_PCT,
        "daily_hit": bool(DAILY_LOSS_LIMIT_PCT > 0 and base > 0
                          and realized <= -base * DAILY_LOSS_LIMIT_PCT / 100.0),
        "loss_streak": streak,
        "max_consec_losses": MAX_CONSEC_LOSSES,
        "pause_until": pause_until if paused else "",
    }


def risk_entry_block_reason() -> Optional[str]:
    """سبب حجب الإشارات الجديدة إن وُجد — None يعني القبول مسموح.
    يُستدعى من create_pending_signal قبل أي أمر (ورقي أو حقيقي)."""
    snap = risk_snapshot()
    if snap["pause_until"]:
        return f"تبريد متتاليات الخسارة جارٍ حتى {snap['pause_until']}"
    if snap["daily_hit"]:
        return (f"حد الخسارة اليومي ملامس: {snap['daily_realized']:+.2f}$ من أساس "
                f"{snap['daily_base']:.2f}$ بسقف {DAILY_LOSS_LIMIT_PCT}%")
    return None


# ── الوقف الراكن على المنصة (STOP_LOSS_LIMIT) + المصالقة الدورية ──

def place_real_stop_loss(symbol: str, qty: float, stop_price: float,
                         ex=None) -> Optional[Dict[str, Any]]:
    """[FE1.8.0] وقف راكن STOP_LOSS_LIMIT SELL على باينانس — الحماية تعيش على المنصة
    لا في ذاكرة البوت: انقطاع/نشر/سقوط لا يترك الموضع مكشوفًا (ثغرة FE1.4–1.7).
    سعر LIMIT أسفل التريغر بـ STOP_LIMIT_OFFSET_PCT لضمان الملء في الومضة الهابطة.
    الغبار (تحت حدود باينانس) لا يرفع أمرًا — المراقبة المحلية تبقى خط الدفاع."""
    ex = ex or binance_trade_exchange()
    if ex is None or qty <= 0 or stop_price <= 0:
        return None
    try:
        limit_price = real_adjust_price(ex, symbol,
                                        stop_price * (1.0 - max(STOP_LIMIT_OFFSET_PCT, 0.0) / 100.0))
        qty = real_adjust_amount(ex, symbol, qty)
        mkt = real_market(ex, symbol)
        if qty <= 0 or qty < real_min_amount(mkt) or qty * stop_price < real_min_cost(mkt):
            logger.info("[%s] كمية الوقف الراكن غبار تحت حدود باينانس (%s) — بلا أمر راكن والمراقبة المحلية خط الدفاع",
                        symbol, qty)
            return None
        raw = ex.privatePostOrder({
            "symbol": _bin_sym(symbol), "side": "SELL", "type": "STOP_LOSS_LIMIT",
            "quantity": _fmt_dec(qty), "stopPrice": _fmt_dec(stop_price),
            "price": _fmt_dec(limit_price), "timeInForce": "GTC", "newOrderRespType": "FULL",
        })
        order = _norm_real_order(raw)
        log_and_notify("info",
                       f"🛡 وقف راكن على المنصة: {symbol} — بيع STOP_LOSS_LIMIT كمية {qty} "
                       f"تريغر {fmt_price(stop_price)} / حد {fmt_price(limit_price)} (id={order.get('id')})",
                       "REAL_STOP_PLACED")
        return order
    except Exception as exc:
        log_and_notify("error", f"❌ فشل وضع الوقف الراكن {symbol}: {exc}", "REAL_TRADE_ERROR")
        return None


def _ensure_real_stop(sig: Dict[str, Any], ex=None) -> None:
    """ضمان وجود وقف راكن لموضع حقيقي مفتوح — بعد الملء مباشرة ومن المصالقة الدورية.
    المعرف في meta_json (stop_order_id) — غيابه = ضعه (فشل سابق/غبار عابر)."""
    if not REAL_STANDING_STOP or not sig.get("is_real"):
        return
    meta = _sig_meta(sig)
    if meta.get("stop_order_id"):
        return
    ex = ex or binance_trade_exchange()
    if ex is None:
        return
    try:
        order = place_real_stop_loss(sig["symbol"], float(sig["quantity"]),
                                     float(sig["stop_loss"]), ex)
    except Exception as exc:
        logger.warning("وضع الوقف الراكن %s استثناء: %s", sig.get("symbol"), exc)
        return
    if order:
        meta.update({"stop_order_id": str(order.get("id") or ""),
                     "stop_price": float(sig["stop_loss"]), "stop_placed_at": utc_now_iso()})
        _save_sig_meta(sig["id"], meta)


def _replace_real_stop(sig: Dict[str, Any], new_stop: float, ex=None) -> bool:
    """استبدال الوقف الراكن (BE@1R أو كمية جديدة بعد جزئي): إلغاء القديم ثم وضع الجديد.
    إن تبيّن أن القديم نُفذ على المنصة → المحاسبة تغلق الموضع وتُعيد False."""
    ex = ex or binance_trade_exchange()
    if ex is None:
        return False
    meta = _sig_meta(sig)
    old_id = meta.get("stop_order_id")
    if old_id:
        if not cancel_real_order(ex, sig["symbol"], old_id):
            so = fetch_real_order(ex, sig["symbol"], old_id)
            st = (so or {}).get("status")
            if st == "closed":
                close_signal_row(sig, float(so.get("average") or new_stop),
                                 "الوقف الراكن نُفذ على المنصة أثناء تحديث الوقف",
                                 exit_order_id=str(so.get("id") or "") or None)
                return False
            if st in ("open", None):
                logger.warning("[%s] الوقف الراكن ما زال حيًا — إعادة محاولة الاستبدال في الدورة القادمة",
                               sig["symbol"])
                return False
        # ملغى فعليًا → أزل المعرف القديم وضع الجديد
    order = place_real_stop_loss(sig["symbol"], float(sig["quantity"]), new_stop, ex)
    if not order:
        return False
    meta.update({"stop_order_id": str(order.get("id") or ""),
                 "stop_price": float(new_stop), "stop_placed_at": utc_now_iso()})
    _save_sig_meta(sig["id"], meta)
    return True


def reconcile_real_protection() -> None:
    """[FE1.8.0] المصالقة الدورية — المنصة مصدر الحقيقة (مصالقة openOrders الخفيفة):
      • موضع حقيقي بلا وقف راكن (فشل وضع سابق) ← ضعه الآن.
      • الوقف الراكن نُفذ على المنصة (البوت كان ساقطًا لحظة التريغر) ← أغلق المحاسبة من سعر التنفيذ.
      • الوقف ملغى/مات على المنصة ← أعده فورًا.
      • الوقف المحلي تحرك (BE) دون الراكن ← استبدله.
    الوزن: صفقة مفتوحة = 1–2 نداء خام فقط، كل RECONCILE_REAL_SEC — لا أسواق إطلاقًا."""
    if not (is_real_mode and REAL_STANDING_STOP):
        return
    try:
        rows = db.query("SELECT * FROM signals WHERE status='open' AND is_real=1 ORDER BY id ASC")
    except Exception as exc:
        logger.warning("مصالقة الحماية: فشل قراءة المواضع: %s", exc)
        return
    ex = binance_trade_exchange()
    if ex is None:
        return
    for sig in rows:
        try:
            meta = _sig_meta(sig)
            stop_oid = meta.get("stop_order_id")
            if not stop_oid:
                _ensure_real_stop(sig, ex)
                continue
            so = fetch_real_order(ex, sig["symbol"], stop_oid)
            if so is None:
                continue  # فشل عابر — الدورة القادمة
            st = so.get("status")
            if st == "closed":
                exit_price = float(so.get("average") or meta.get("stop_price") or sig["stop_loss"])
                close_signal_row(sig, exit_price,
                                 "الوقف الراكن نُفذ على المنصة (مصالقة) — الحماية صمدت رغم غياب البوت",
                                 exit_order_id=str(so.get("id") or "") or None)
            elif st in ("canceled", "expired", "rejected"):
                meta.pop("stop_order_id", None)
                _save_sig_meta(sig["id"], meta)
                _ensure_real_stop({**sig, "meta_json": None}, ex)
            elif st == "open" and abs(float(meta.get("stop_price") or 0) - float(sig["stop_loss"] or 0)) > 1e-12:
                _replace_real_stop(sig, float(sig["stop_loss"]), ex)
        except Exception as exc:
            logger.warning("مصالقة حماية %s فشلت: %s", sig.get("symbol"), exc)


_last_reconcile_at = {"at": 0.0}


def _reconcile_maybe() -> None:
    """مصالقة الحماية كل RECONCILE_REAL_SEC داخل حلقة المراقبة — لا حلقة جديدة ولا ذاكرة إضافية."""
    if not (is_real_mode and REAL_STANDING_STOP):
        return
    if time.time() - _last_reconcile_at["at"] < max(RECONCILE_REAL_SEC, 60):
        return
    _last_reconcile_at["at"] = time.time()
    reconcile_real_protection()


# ── محاسبة الرجل الجزئية + خطوة الحماية عند +1R ──

def _account_partial_close(sig: Dict[str, Any], leg_qty: float, leg_price: float, reason: str) -> float:
    """[FE1.8.0] محاسبة رجل جزئية: تحقيق ربحها، تخفيض الكمية، تثبيت initial_quantity.
    الورقي: الرصيد يتحدث فورًا بالرجل — الإغلاق النهائي يجمع realized_pnl_usdt مرة
    واحدة فلا ازدواج. الحقيقي: البيع الفعلي تم قبل الاستدعاء وهذه المحاسبة العرضية.
    تُحدّث نسخة الصفقة في الذاكرة كي لا يغلق ما بعدها بكمية قديمة."""
    entry = float(sig.get("fill_price") or 0)
    qty_before = float(sig.get("quantity") or 0)
    leg_qty = min(float(leg_qty), qty_before)
    if leg_qty <= 0 or entry <= 0 or leg_price <= 0:
        return 0.0
    gross = leg_qty * (leg_price - entry)
    fees = (leg_qty * entry + leg_qty * leg_price) * FEE_RATE
    leg_pnl = gross - fees
    realized_new = float(sig.get("realized_pnl_usdt") or 0) + leg_pnl
    qty_after = qty_before - leg_qty
    init_qty = float(sig.get("initial_quantity") or qty_before)  # صفوف ما قبل FE1.8.0
    is_real = bool(sig.get("is_real"))
    db.execute(
        "UPDATE signals SET quantity=%s, notional_usdt=%s, realized_pnl_usdt=%s, initial_quantity=%s WHERE id=%s",
        (qty_after, qty_after * entry, round(realized_new, 6), init_qty, sig["id"]),
    )
    if not is_real:
        set_paper_balance(get_paper_balance() + leg_pnl)
    sig["quantity"] = qty_after
    sig["realized_pnl_usdt"] = realized_new
    sig["initial_quantity"] = init_qty
    tag = "حقيقية 🔴" if is_real else "ورقية"
    log_and_notify("info",
                   f"💰 إغلاق جزئي {tag}: {sig['symbol']} — بيع {leg_qty} عند {fmt_price(leg_price)} "
                   f"({reason}) | ربح الرجل {leg_pnl:+.4f}$ | المتبقي {qty_after}",
                   "PARTIAL_CLOSE")
    return leg_pnl


def _protection_step(sig: Dict[str, Any], high_now: float) -> None:
    """[FE1.8.0] خطوة حماية الموضع عند بلوغ +BE_TRIGGER_R×R (البوت شرائي BULLISH):
      1) جزئي أول درج: إغلاق PARTIAL_CLOSE_PCT% من الكمية — ربح مُحقق وتعرض أقل.
      2) BE@1R: الوقف ينتقل إلى الدخول — الموضع صار بلا مخاطرة.
    الورقي: تعديل وقف ومحاسبة. الحقيقي: بيع سوق جزئي + استبدال أمر الوقف الراكن
    بالكمية المتبقية وعند سعر الدخول. كل حدث مرة واحدة (أعلام meta_json تعبر النشر).
    monitor_step يستدعيها بعد حارس الوقف-أولًا داخل الشمعة — إن لمست الشمعة الوقف
    الأصلي فالحماية تُتخطى (لا نفترض ترتيبًا داخل الشمعة لم نره)."""
    if not (BE_AT_R_ENABLED or PARTIAL_AT_R_ENABLED):
        return
    try:
        entry = float(sig.get("fill_price") or 0)
        sl = float(sig.get("stop_loss") or 0)
        qty = float(sig.get("quantity") or 0)
    except (TypeError, ValueError):
        return
    if entry <= 0 or sl <= 0 or qty <= 0 or entry <= sl:
        return
    if BE_TRIGGER_R <= 0:
        return
    trigger = entry + (entry - sl) * BE_TRIGGER_R
    if high_now < trigger:
        return
    meta = _sig_meta(sig)
    is_real = bool(sig.get("is_real"))
    ex = binance_trade_exchange() if is_real else None
    if is_real and ex is None:
        return
    # 1) الإغلاق الجزئي أولًا — الكمية تقل قبل إعادة ضبط الوقف الراكن بالمتبقي
    if PARTIAL_AT_R_ENABLED and not meta.get("partial_done") and PARTIAL_CLOSE_PCT > 0:
        leg_qty = qty * min(max(PARTIAL_CLOSE_PCT, 1.0), 99.0) / 100.0
        if is_real:
            leg_qty = real_adjust_amount(ex, sig["symbol"], leg_qty)
            mkt = real_market(ex, sig["symbol"])
            if leg_qty <= 0 or leg_qty < real_min_amount(mkt) or leg_qty * trigger < real_min_cost(mkt):
                meta["partial_done"] = True  # غبار — سيُغلق كاملًا مع النهائي بلا تكرار إشعارات
                logger.info("[%s] الرجل الجزئية غبار تحت حدود باينانس — تخطٍّ نهائي", sig["symbol"])
            else:
                order = place_real_market_sell(sig["symbol"], leg_qty)
                if order:
                    meta["partial_done"] = True
                    _account_partial_close(sig, leg_qty,
                                           float(order.get("average") or trigger), "تحقق +1R")
                # فشل البيع → بلا علم — تعاد المحاولة في الدورة القادمة
        else:
            meta["partial_done"] = True
            _account_partial_close(sig, leg_qty, trigger, "تحقق +1R")
    # 2) BE@1R — نقل الوقف إلى الدخول (بعد الجزئي كي يحمل الراكن الكمية المتبقية)
    if BE_AT_R_ENABLED and not meta.get("be_done") and float(sig["stop_loss"]) < entry:
        be_msg = (f"🔒 وقف عند التعادل (BE@1R): {sig['symbol']} — الوقف انتقل إلى الدخول "
                  f"{fmt_price(entry)} والموضع بلا مخاطرة")
        if is_real and REAL_STANDING_STOP:
            if _replace_real_stop(sig, entry, ex):
                db.execute("UPDATE signals SET stop_loss=%s WHERE id=%s", (entry, sig["id"]))
                sig["stop_loss"] = entry
                meta["be_done"] = True
                log_and_notify("info", be_msg, "BREAK_EVEN")
            # فشل الاستبدال (راكن حي/فشل عابر) → بلا علم — تعاد المحاولة في الدورة القادمة
        else:
            db.execute("UPDATE signals SET stop_loss=%s WHERE id=%s", (entry, sig["id"]))
            sig["stop_loss"] = entry
            meta["be_done"] = True
            log_and_notify("info", be_msg, "BREAK_EVEN")
    _save_sig_meta(sig["id"], meta)


def _resync_after_cancel_attempt(sig: Dict[str, Any], ex, reason_terminal: str) -> None:
    """بعد محاولة إلغاء أمر حقيقي: هل ملئ؟ ملئ جزئيًا؟ أُلغي فعلًا؟ — الحكم من المنصة."""
    order = fetch_real_order(ex, sig["symbol"], sig["order_id"])
    status = ((order or {}).get("status") or "").lower()
    filled = float((order or {}).get("filled") or 0)
    avg = float((order or {}).get("average") or 0) or float(sig["entry_price"])
    if filled > 0:
        db.execute("UPDATE signals SET status='open', fill_price=%s, quantity=%s, filled_at=%s, initial_quantity=%s WHERE id=%s",
                   (avg, filled, utc_now_iso(), filled, sig["id"]))
        _ensure_real_stop({**sig, "status": "open", "fill_price": avg, "quantity": filled}, ex)  # [FE1.8.0]
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
        db.execute("UPDATE signals SET status='open', fill_price=%s, quantity=%s, filled_at=%s, initial_quantity=%s WHERE id=%s",
                   (fill_price, filled or qty_target, utc_now_iso(), filled or qty_target, sig["id"]))
        # [FE1.8.0] بعد الملء: ارفع الوقف الراكن على المنصة فورًا — الحماية لا تعيش في الذاكرة
        _ensure_real_stop({**sig, "status": "open", "fill_price": fill_price,
                           "quantity": filled or qty_target})
        log_and_notify("info",
                       f"🎯 [حقيقي] مُلئ أمر الشراء: {sig['symbol']} — كمية {filled or qty_target} عند {fmt_price(fill_price)}\n"
                       f"وقف: {fmt_price(sig['stop_loss'])} | هدف 1.618: {fmt_price(sig['take_profit'])}",
                       "REAL_FILLED")
        return
    if status in ("canceled", "expired", "rejected"):
        if filled > 0:
            db.execute("UPDATE signals SET status='open', fill_price=%s, quantity=%s, filled_at=%s, initial_quantity=%s WHERE id=%s",
                       (avg or float(sig["entry_price"]), filled, utc_now_iso(), filled, sig["id"]))
            _ensure_real_stop({**sig, "status": "open",
                               "fill_price": avg or float(sig["entry_price"]), "quantity": filled})  # [FE1.8.0]
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
            db.execute("UPDATE signals SET status='open', fill_price=%s, filled_at=%s, initial_quantity=%s WHERE id=%s",
                       (fill_price, utc_now_iso(), float(sig["quantity"]), sig["id"]))  # [FE1.8.0] أساس محاسبة الجزئي
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
            _open_outage_step(symbol, True)   # [FE1.7.0] موضع حي بلا تغذية — لا صمت
            continue
        if df is None or df.empty:
            _open_outage_step(symbol, True)   # [FE1.7.0]
            continue
        _open_outage_step(symbol, False)      # [FE1.7.0] نجاح — صفّر عداد الانقطاع
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
            else:
                # [FE1.8.0] حماية +1R (جزئي + BE) — لن تُستدعى إن لمست الشمعة الوقف (وقف-أولًا محفوظ)
                _protection_step(sig, high_now)
                if high_now >= float(sig["take_profit"]):
                    close_real_trade(sig, float(sig["take_profit"]), "هدف فيبوناتشي 1.618 تحقق")
            continue
        # الوقف أولًا (متحفظ) — الوقف بنيوي خلف P0، الهدف امتداد 1.618
        if low_now <= float(sig["stop_loss"]):
            close_signal_row(sig, float(sig["stop_loss"]), "وقف خسارة بنيوي (خلف أصل الموجة 1)")
        else:
            # [FE1.8.0] BE@1R + جزئي أول درج — بعد حارس الوقف-أولًا داخل الشمعة
            _protection_step(sig, high_now)
            if high_now >= float(sig["take_profit"]):
                close_signal_row(sig, float(sig["take_profit"]), "هدف فيبوناتشي 1.618 تحقق")


# ══════════════════════════════════════════════════════════════════════════════
# حلقة المسح — إيقاع المشروع الأصلي: بعد إغلاق كل شمعة كشف (1h)
# ══════════════════════════════════════════════════════════════════════════════

def select_best_setup(setups: List[DetectedSetup]) -> Optional[DetectedSetup]:
    """[FE1.6.0] تقييم مركب (اقتباس ElliottWavesEngine §5-8: التقييم الإرشادي
    وبدل +1/+1 الحرفي):
      • مناطق W2/W4 المثالية (كالسابق لكن بنقاط عائمة)
      • تناوب العمق: W2 عميق مع W4 أضح منه (بنية إليوت صحية)
      • امتداد W3 قرب 1.618 من W1 (الموجة الأقوى إحصائيًا)
      • مساواة W5≈W1 (أشهر علاقة بين الموجتين)
      • الأحدث يحسم التعادل (كما كان) — النتيجة تقرب 4 منازل لثبات المقارنة"""
    if not setups:
        return None
    if len(setups) == 1:
        return setups[0]

    def score(s: DetectedSetup) -> Tuple[float, float]:
        fib = s.validation_result.fib
        pts = 0.0
        if fib:
            if fib.wave2_in_zone:
                pts += 1.0
            if fib.wave4_in_zone:
                pts += 1.0
            # تناوب العمق: W2 في منطقته ويبلع W4 بوضوح — تناوب صحي بديل +1/+1
            w2r, w4r = fib.wave2_retrace_pct, fib.wave4_retrace_pct
            if 0.382 <= w2r <= 0.886 and 0.0 < w4r <= 0.5 and w2r > w4r + 0.1:
                pts += 0.5
        P = s.pivot_prices
        try:
            w1 = abs(math.log(P[1]) - math.log(P[0]))
            w3 = abs(math.log(P[3]) - math.log(P[2]))
            w5 = abs(math.log(P[5]) - math.log(P[4]))
            if w1 > 0:
                # امتداد W3/W1 قرب 1.618 (1.618 ← 1.0 نقطة، البعد يتناقص خطيًا)
                ext = w3 / w1
                pts += max(0.0, 1.0 - abs(ext - 1.618) / 1.618)
            if min(w1, w5) > 0:
                # مساواة W5≈W1 حتى نصف نقطة (0.5 × تشابه نسبي)
                pts += 0.5 * (1.0 - abs(w5 - w1) / max(w1, w5))
        except (ValueError, ZeroDivisionError, IndexError):
            pass
        recency = s.detected_at.timestamp() if s.detected_at else 0.0
        return (round(pts, 4), recency)

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


# [FE1.7.0] حارس انقطاع التغذية مع مواضع مفتوحة — كان فشل الجلب يُتخطى صامتًا
# (df=None → continue) فيمضي الوقف/الهدف بلا فحص طوال الانقطاع: إعادة نشر،
# حظر 418 على العنوان المشترك مع تبريد مزودين متتالين، أو سقوط السلسلة كلها.
_open_outage_lock = threading.Lock()
_open_outage: Dict[str, Dict[str, Any]] = {}   # symbol → {n: دورات فاشلة متتالية, last: آخر تنبيه}


def _open_outage_step(symbol: str, failed: bool) -> None:
    """تتبع فشل جلب الشموع لرمز عليه موضع مفتوح: تنبيه بعد OUTAGE_ALERT_AFTER_CYCLES
    دورات فاشلة متتالية (≈3 دقائق) ثم تكرار كل OUTAGE_RENOTIFY_SEC طوال الانقطاع.
    النجاح يصفّر العداد. صفر حلقات جديدة — يركب حلقة المراقبة القائمة."""
    if not failed:
        with _open_outage_lock:
            _open_outage.pop(symbol, None)
        return
    notify = False
    n = 0
    with _open_outage_lock:
        st = _open_outage.setdefault(symbol, {"n": 0, "last": 0.0})
        st["n"] += 1
        n = st["n"]
        if n == OUTAGE_ALERT_AFTER_CYCLES or (
            n > OUTAGE_ALERT_AFTER_CYCLES and time.time() - st["last"] >= OUTAGE_RENOTIFY_SEC
        ):
            st["last"] = time.time()
            notify = True
    if notify:
        log_and_notify(
            "error",
            f"⚠ انقطاع تغذية أسعار {symbol} وعليه موضع مفتوح — فشل الجلب {n} دورة متتالية، "
            f"الوقف/الهدف لا يُفحصان طوال الانقطاع. راقب المركز يدويًا إن استمر.",
            "DATA_OUTAGE_OPEN",
        )


# ══════════════════════════════════════════════════════════════════════════════
# [FE1.5.0] ماسح الكون الكامل — فحص أولي لكل أزواج باينانس الملائمة للاستراتيجية
# ══════════════════════════════════════════════════════════════════════════════
# المبدأ: بدل قائمة يدوية ثابتة (crypto_list.txt)، يفحص الماسح كامل أسواق باينانس
# USDT عبر نقاط خام رخيصة الوزن (لا load_markets إطلاقًا — درس FE1.4.x):
#   المرحلة 1: publicGetTicker24hr (وزن 80) ← ترشيح سيولة/سبريد/مدى + استبعاد
#              العملات المستقرة والرموز المرفوعة.
#   المرحلة 2: أفضل SCAN_CANDIDATES ← شموع 15m خام ← زيجزاج بعتبة الاستراتيجية
#              نفسها + ATR% + سعة الموجات + كفاءة الاتجاه ← درجة ملاءمة 0-100.
#   المرحلة 3: أعلى SCAN_TOP_N يُطبق على قائمة المراقبة (الرموز النشطة محفوظة
#              إجباريًا) وتُحدّث أسواق الويب سوكت المصنوعة للرموز الجديدة.
# حماية IP (418/429): وزن إجمالي ~160 لكل فحص كل 6 ساعات + إيقاع مهذب + إجهاض
# فوري مع حفظ النتائج السابقة عند أي قيد — الفحص لا يضرب التغذية الحية أبدًا.

_scanner_lock = threading.RLock()  # RLock: scanner_state_snapshot قد تُستدعى داخل الحصار نفسه (Lock كان يُحدث Deadlock)
_scanner_state: Dict[str, Any] = {
    "enabled": SCAN_UNIVERSE_ENABLED, "running": False, "last_scan_at": None,
    "next_scan_at": None, "duration_ms": None, "universe": None, "passed": None,
    "candidates": None, "applied": False, "error": None, "retry_after_sec": None,
}
_scanner_results: List[Dict[str, Any]] = []   # أعلى النتائج (قواميس صغيرة — ≤ 20 صفًا)
_scanner_boot_restored = False

# أصول أساس مستقرة/ورقية — بلا موجات إليوت ذات معنى (بيزوج USDT شبه ثابت أو ورقي)
_SCAN_STABLE_BASES = {
    "USDC", "FDUSD", "TUSD", "BUSD", "DAI", "USDP", "PYUSD", "USDS", "USDE",
    "USD1", "XUSD", "AEUR", "EURI", "EUR", "GBP", "TRY", "BRL", "ARS", "JPY",
    "RUB", "UAH", "ZAR", "USDT",
}


def _scanner_ban_hint(msg: str) -> bool:
    """هل الرسالة قيد باينانس (418/429/-1003)؟ — تُستخدم لجدولة إعادة محاولة قريبة."""
    m = str(msg)
    return "418" in m or "429" in m or "banned" in m.lower() or "-1003" in m


def scanner_state_snapshot() -> Dict[str, Any]:
    """لقطة حالة الماسح + النتائج الحالية — للوحة (/api/all) والتشخيص."""
    with _scanner_lock:
        out = dict(_scanner_state)
        out["results"] = list(_scanner_results)
        return out


def _liq_norm(quote_volume: float) -> float:
    """تطبيع لوغاريتمي للسيولة: 5M$ ← 0.0 ، 1B$ وأكثر ← 1.0."""
    if quote_volume <= 0:
        return 0.0
    return max(0.0, min(1.0, (math.log10(quote_volume) - 6.7) / (9.0 - 6.7)))


def zigzag_pivots(closes: List[float], deviation: float) -> List[Tuple[int, float]]:
    """نقاط انعكاس الزيجزاج بنفس دلالة عتبة الانعكاس الخاصة بالاستراتيجية:
    في الصعود يُتتبع القمة الجارية، وهبوط ≥ deviation عنها يؤكد القمة نقطة انعكاس
    ويقلب التتبع للقاع الجاري (والعكس). آخر قصوى غير مؤكدة تُضاف للنهاية.
    (مستقل عن كاشف المحاور الكامل — الفحص الأولي يريد ثراء الموجات لا نماذج P0-P5)."""
    if len(closes) < 3:
        return []
    piv: List[Tuple[int, float]] = []
    ext_i, ext_p = 0, closes[0]
    trend = 1  # +1: تتبّع القمة الجارية / -1: تتبّع القاع الجاري
    for i in range(1, len(closes)):
        p = closes[i]
        if trend == 1:
            if p >= ext_p:
                ext_i, ext_p = i, p
            elif ext_p > 0 and p <= ext_p * (1.0 - deviation):
                piv.append((ext_i, ext_p))       # قمة مؤكدة
                trend = -1
                ext_i, ext_p = i, p
        else:
            if p <= ext_p:
                ext_i, ext_p = i, p
            elif ext_p > 0 and p >= ext_p * (1.0 + deviation):
                piv.append((ext_i, ext_p))       # قاع مؤكد
                trend = 1
                ext_i, ext_p = i, p
    piv.append((ext_i, ext_p))                    # آخر قصوى (غير مؤكدة) — مفيدة للعدّ
    return piv


def _scanner_score_candidate(symbol: str, klines: list) -> Optional[Dict[str, Any]]:
    """درجة ملاءمة زوج لاستراتيجية الموجات (0-100) من شموع 15m خام:
    ثراء الانعكاسات + كفاءة الاتجاه + سعة الموجات + تذبذب صحي (ATR% بلا فوضى)."""
    if not klines or len(klines) < 60:
        return None
    try:
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
    except (TypeError, ValueError, IndexError):
        return None
    n = len(closes)
    if closes[0] <= 0:
        return None
    piv = zigzag_pivots(closes, DEVIATION_THRESHOLD)
    n_piv = len(piv)
    trs = []
    for i in range(1, n):
        if closes[i - 1] > 0:
            trs.append((highs[i] - lows[i]) / closes[i - 1])
    atr_pct = (sum(trs) / len(trs) * 100.0) if trs else 0.0
    # ثراء الموجات: 4 انعكاسات ← 0 ، 20+ ← 1 (نافذة 200 شمعة 15m)
    wave_score = max(0.0, min(1.0, (n_piv - 4) / 16.0))
    # سعة الموجات: متوسط الحركة بين الانعكاسات نسبةً للسعر (0.6% ← 0 ، 3%+ ← 1)
    amps = []
    for a in range(1, len(piv)):
        if piv[a - 1][1] > 0:
            amps.append(abs(piv[a][1] - piv[a - 1][1]) / piv[a - 1][1] * 100.0)
    avg_amp = (sum(amps) / len(amps)) if amps else 0.0
    amp_score = max(0.0, min(1.0, (avg_amp - 0.6) / 2.4))
    # كفاءة الاتجاه: صافي الحركة ÷ مجموع مسارات الانعكاسات (توجّه يحتضن دافع إليوت)
    path = sum(amps)
    net = abs(closes[-1] - closes[0]) / closes[0] * 100.0
    trend_eff = (net / path) if path > 0 else 0.0
    trend_score = max(0.0, min(1.0, trend_eff / 0.35))
    # ATR صحي: حركة كافية بلا فوضى — 0.15% أدنى، 0.6-1.8% مثالي، فوق 4.8% يصفر تدريجيًا
    if atr_pct < 0.15:
        atr_score = atr_pct / 0.15 * 0.5
    elif atr_pct <= 1.8:
        atr_score = 1.0
    else:
        atr_score = max(0.0, 1.0 - (atr_pct - 1.8) / 3.0)
    total = (0.35 * wave_score + 0.25 * trend_score + 0.20 * amp_score + 0.20 * atr_score) * 100.0
    return {
        "symbol": symbol, "pivots": n_piv,
        "atr_pct": round(atr_pct, 3), "avg_wave_pct": round(avg_amp, 3),
        "trend_eff": round(trend_eff, 3), "score": round(total, 1),
    }


def _scanner_filter_tickers(tickers: list) -> Tuple[List[Dict[str, Any]], int]:
    """المرحلة 1: ترشيح كل أسواق USDT — سيولة، سبريد، مدى، استبعاد المستقر/المرفوع.
    ترجع (المرشحون مرتبون بالسيولة تنازليًا، حجم الكون الكلي لأزواج USDT)."""
    universe = 0
    out: List[Dict[str, Any]] = []
    for t in (tickers or []):
        if not isinstance(t, dict):
            continue
        sym = str(t.get("symbol") or "")
        if not sym.endswith("USDT"):
            continue
        universe += 1
        base = sym[:-4]
        if not base or base.upper() in _SCAN_STABLE_BASES:
            continue
        if base.upper().endswith(("UP", "DOWN", "BULL", "BEAR")):  # رموز مرفوعة (leveraged tokens)
            continue
        try:
            last = float(t.get("lastPrice") or 0)
            qv = float(t.get("quoteVolume") or 0)
            bid = float(t.get("bidPrice") or 0)
            ask = float(t.get("askPrice") or 0)
            high = float(t.get("highPrice") or 0)
            low = float(t.get("lowPrice") or 0)
        except (TypeError, ValueError):
            continue
        if last <= 0 or qv < SCAN_MIN_VOLUME_USDT:
            continue
        mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else last
        spread = ((ask - bid) / mid * 100.0) if (mid > 0 and ask >= bid > 0) else 0.0
        if spread > SCAN_MAX_SPREAD_PCT:
            continue
        rng = ((high - low) / low * 100.0) if (low > 0 and high >= low) else 0.0
        if rng < SCAN_MIN_RANGE_PCT:
            continue
        out.append({"symbol": sym, "base": base, "last": last, "qv": qv,
                    "spread_pct": round(spread, 4), "range_pct": round(rng, 2)})
    out.sort(key=lambda x: x["qv"], reverse=True)
    return out, universe


def ws_refresh_fabricated_markets() -> None:
    """[FE1.5.0] بعد تغيّر قائمة المراقبة: حقن أسواق مصنوعة للرموز الجديدة داخل
    نسخ الويب سوكت الجاهزة — وإلا فشل market() للرمز الجديد عند أول اشتراك
    (الأسواق المصنوعة تُبنى من قائمة المراقبة لحظة إنشاء النسخة فقط)."""
    if not _ws_exchanges:
        return
    n = 0
    for name, ex in list(_ws_exchanges.items()):
        try:
            if getattr(ex, "markets", None) is None:
                continue
            fab = _fabricate_ws_markets(name, watchlist)
            ex.markets.update(fab)
            # [FE1.6.1] فهرس بالمعرف → [قائمة] لا dict مفردة (اصطلاح ccxt 4.4+)
            ex.markets_by_id.update(_index_markets_by_id(fab))
            n += 1
        except Exception as exc:
            logger.debug("تحديث أسواق WS المصنوعة لـ %s فشل: %s", name, exc)
    if n:
        logger.info("أسواق ويب سوكت المصنوعة حُدّثت لـ %d مزود بعد تغيير قائمة المراقبة", n)


def _apply_scan_watchlist(results: List[Dict[str, Any]]) -> bool:
    """تطبيق نتائج الفحص على قائمة المراقبة — مع الحفاظ الإجباري على كل رمز لديه
    صفقة نشطة (معلق/مفتوح) فلا يُهجر مركز مفتوح أبدًا، ثم تحديث أسواق WS."""
    top = [f"{r.get('base')}/USDT" for r in results if r.get("base")]
    if not top:
        return False
    try:
        rows = db.query("SELECT DISTINCT symbol FROM signals WHERE status IN ('pending','open')")
        active = {r["symbol"] for r in (rows or [])}
    except Exception:
        active = set()
    merged = list(top)
    for sym in sorted(active):
        if sym not in merged:
            merged.append(sym)
    watchlist[:] = merged
    ws_refresh_fabricated_markets()
    return True


def run_universe_scan(force: bool = False, trigger: str = "auto") -> Dict[str, Any]:
    """فحص كامل لكون باينانس: ترشيح + تحليل شموع + تطبيق أعلى N على قائمة المراقبة.
    آمن على الذاكرة (نقاط خام، تحرير فوري للنتوء الكبير) وآمن على IP (إجهاض عند 418/429).
    force=True يتجاوز فحص «الجارٍ الآن» للاستخدام اليدوي — الحارس نفسه يبقى ساريًا."""
    with _scanner_lock:
        if _scanner_state["running"] and not force:
            return {"ok": False, "error": "فحص جارٍ بالفعل", "scanner": scanner_state_snapshot()}
        _scanner_state["running"] = True
        _scanner_state["error"] = None
    t0 = time.time()
    ok = False
    try:
        ex = _binance_public_probe()
        tickers = ex.publicGetTicker24hr()          # كل الأسواق دفعة واحدة — وزن 80
        passed, universe = _scanner_filter_tickers(tickers)
        del tickers                                  # تحرير فوري للنتوء المُحلَّل
        mem_check("بعد ترشيح كون باينانس")
        cand = passed[:max(SCAN_CANDIDATES, SCAN_TOP_N)]
        results: List[Dict[str, Any]] = []
        aborted: Optional[str] = None
        for i, c in enumerate(cand):
            try:
                raw = ex.publicGetKlines({"symbol": c["symbol"], "interval": SIGNAL_TIMEFRAME,
                                          "limit": SCAN_KLINES_LIMIT})
                sc = _scanner_score_candidate(c["symbol"], raw or [])
            except Exception as exc:
                msg = str(exc)
                if "418" in msg or "429" in msg or "banned" in msg.lower() or "-1003" in msg:
                    aborted = f"باينانس قيّد الطلبات ({msg[:140]})"
                    break
                sc = None
            if sc:
                liq = _liq_norm(c["qv"])
                sc["final"] = round(0.70 * sc["score"] + 0.30 * liq * 100.0, 1)
                sc["base"] = c["base"]
                sc["qv"] = c["qv"]
                sc["range_pct"] = c["range_pct"]
                sc["last"] = c["last"]
                results.append(sc)
            if (i + 1) % 10 == 0:
                mem_check("أثناء تحليل مرشحي الكون")
            time.sleep(0.25)   # إيقاع مهذب (enableRateLimit يعمل أيضًا)
        if aborted:
            with _scanner_lock:
                _scanner_state["running"] = False
                _scanner_state["error"] = f"أُجهض الفحص: {aborted} — النتائج السابقة محفوظة"
                _scanner_state["duration_ms"] = int((time.time() - t0) * 1000)
                _scanner_state["universe"] = universe
                _scanner_state["passed"] = len(passed)
                _scanner_state["candidates"] = len(results)
                _scanner_state["retry_after_sec"] = SCANNER_BAN_RETRY_SEC  # [FE1.5.1] إعادة محاولة قريبة بعد انتهاء الحظر
            log_and_notify("warning", f"🛰 ماسح الكون: {_scanner_state['error']}", "UNIVERSE_SCAN")
            return {"ok": False, "error": _scanner_state["error"]}
        results.sort(key=lambda r: r["final"], reverse=True)
        results = results[:max(SCAN_TOP_N, 1)]
        applied = False
        if results and SCAN_UNIVERSE_ENABLED:
            applied = _apply_scan_watchlist(results)
        now_iso = utc_now_iso()
        with _scanner_lock:
            _scanner_state.update({
                "running": False, "last_scan_at": now_iso,
                "duration_ms": int((time.time() - t0) * 1000),
                "universe": universe, "passed": len(passed),
                "candidates": len(cand), "applied": applied, "error": None,
                "retry_after_sec": None,   # [FE1.5.1] نجاح — عودة للإيقاع الكامل
            })
            _scanner_results[:] = results
        try:
            db_set_state("scan_results", json.dumps({"at": now_iso, "results": results}))
        except Exception as exc:
            logger.warning("تعذر حفظ نتائج فحص الكون: %s", exc)
        ok = True
        if results:
            top3 = " · ".join(f"{r['symbol']} ({r['final']})" for r in results[:3])
            log_and_notify(
                "info",
                f"🛰 فحص الكون ({trigger}): {universe} زوج USDT ← {len(passed)} مرشحًا ← "
                f"حُلل {len(cand)} ← طُبق {len(results)} على قائمة المراقبة\nالأعلى ملاءمة: {top3}",
                "UNIVERSE_SCAN",
            )
        else:
            log_and_notify("warning", "🛰 فحص الكون: لا نتائج — تحقق من فلاتر السيولة/المدى أو اتصال باينانس", "UNIVERSE_SCAN")
        return {"ok": True, "applied": applied, "count": len(results), "universe": universe}
    except Exception as exc:
        with _scanner_lock:
            _scanner_state["running"] = False
            _scanner_state["error"] = f"{type(exc).__name__}: {exc}"[:240]
            _scanner_state["duration_ms"] = int((time.time() - t0) * 1000)
            # [FE1.5.1] حظر باينان (418/429) عند نداء التكتة نفسه — إعادة محاولة قريبة لا 6 ساعات
            _scanner_state["retry_after_sec"] = (SCANNER_BAN_RETRY_SEC
                                                 if _scanner_ban_hint(exc) else None)
        logger.warning("ماسح الكون فشل: %s", exc)
        return {"ok": False, "error": _scanner_state["error"]}
    finally:
        if not ok:
            with _scanner_lock:
                if _scanner_state["running"]:
                    _scanner_state["running"] = False


def restore_scan_results() -> None:
    """[FE1.5.0] استعادة نتائج آخر فحص كون من قاعدة البيانات وتطبيقها فورًا عند
    الإقلاع — فلا يعمل البوت بالقائمة اليدوية القديمة حتى أول فحص (~90 ثانية).
    الرموز ذات الصفقات النشطة تُحفظ دائمًا في كل حالة."""
    global _scanner_boot_restored
    if _scanner_boot_restored or not SCAN_UNIVERSE_ENABLED:
        return
    _scanner_boot_restored = True
    try:
        raw = db_get_state("scan_results", None)
        if not raw:
            return
        payload = json.loads(raw)
        results = payload.get("results") or []
        if not results:
            return
        with _scanner_lock:
            _scanner_results[:] = results
            _scanner_state["last_scan_at"] = payload.get("at")
            _scanner_state["applied"] = True
        if _apply_scan_watchlist(results):
            logger.info("استعادة فحص الكون: %d زوجًا مطبقًا من آخر فحص (%s)", len(results), payload.get("at"))
    except Exception as exc:
        logger.warning("تعذرت استعادة نتائج فحص الكون: %s", exc)


def universe_scan_loop() -> None:
    """خيط الماسح: فحص أول بعد ~90 ثانية من الإقلاع، ثم كل SCAN_INTERVAL_SEC.
    [FE1.5.1] بعد إجهاض 418/429 (حظر IP مشترك Render مؤقت): إعادة محاولة بعد
    SCANNER_BAN_RETRY_SEC (30 دقيقة) لاقتطاف نافذة انتهاء الحظر بدل انتظار 6 ساعات."""
    time.sleep(90.0)
    while True:
        nap = SCAN_INTERVAL_SEC
        try:
            db.ensure()
            if SCAN_UNIVERSE_ENABLED:
                run_universe_scan(trigger="auto")
        except Exception as exc:
            logger.warning("ماسح الكون: فشل دورة: %s", exc)
            with _scanner_lock:
                _scanner_state["running"] = False
                _scanner_state["error"] = str(exc)[:240]
        with _scanner_lock:
            hint = _scanner_state.get("retry_after_sec")
            if hint and hint < nap:
                nap = float(hint)
        mem_check("بعد دورة ماسح الكون")
        try:
            from datetime import timedelta
            _dt = datetime.now(timezone.utc) + timedelta(seconds=nap)
            with _scanner_lock:
                _scanner_state["next_scan_at"] = _dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass
        # نوم مجزأ (60 ثانية) — يسمح بمستقبل مرن للإيقاف ويبقى الخيط خفيفًا
        slept = 0.0
        while slept < nap:
            time.sleep(min(60.0, nap - slept))
            slept += 60.0


# ══════════════════════════════════════════════════════════════════════════════
# [FE1.6.0] بوابة تحيز الفريم الأعلى — اقتباس ElliottWavesEngine: درجات الشهرية/
# اليومية توجّه الساعية. إشارة صاعدة على 15m داخل حقبة هابطة واضحة على اليومي
# = عكس التدفق — أرجح مصادر الخسارة في أنظمة الموجات.
# فشل الجلب = مجهول = يُسمح (fail-open) — البوابة فلتر جودة لا نقطة فشل.
# ══════════════════════════════════════════════════════════════════════════════

_htf_lock = threading.Lock()
_htf_cache: Dict[str, Dict[str, Any]] = {}   # symbol -> {ts, bias, note}


def htf_bias(symbol: str) -> Optional[bool]:
    """تحيز الاتجاه من فريم أعلى (HTF_BIAS_TIMEFRAME الافتراضي 1d):
      True  = لا انحياز هابط قوي — تُسمح الإشارات الصاعدة
      False = حقبة هابطة واضحة (الشرطان الثلاثة معًا): الإغلاق تحت SMA50،
              SMA20 تحت SMA50، وصافي آخر 20 شمعة أسوأ من -8%
      None  = مجهول (فشل جلب/بيانات ناقصة) — يُسمح fail-open
    كاش 4 ساعات لكل رمز (HTF_BIAS_CACHE_SEC) — وزن REST مهمل (~6 نداءات/15 دقيقة)."""
    now = time.time()
    with _htf_lock:
        c = _htf_cache.get(symbol)
        if c and now - c["ts"] < HTF_BIAS_CACHE_SEC:
            return c["bias"]
    bias: Optional[bool] = None
    note = ""
    try:
        df = fetch_ohlcv_df(symbol, HTF_BIAS_TIMEFRAME, limit=80, min_candles=55)
        if df is not None and len(df) >= 55:
            closes = df["close"].to_numpy(dtype=float)
            sma20 = float(closes[-20:].mean())
            sma50 = float(closes[-50:].mean())
            base20 = float(closes[-21])
            net20 = (float(closes[-1]) / base20 - 1.0) if base20 > 0 else 0.0
            last = float(closes[-1])
            strong_bear = last < sma50 and sma20 < sma50 and net20 < -0.08
            bias = not strong_bear
            note = (f"SMA20={sma20:.6g} SMA50={sma50:.6g} "
                    f"net20={net20 * 100:.1f}% strong_bear={strong_bear}")
    except Exception as exc:
        logger.debug("[%s] تعذر حساب تحيز الفريم الأعلى: %s", symbol, exc)
        bias = None
    with _htf_lock:
        _htf_cache[symbol] = {"ts": now, "bias": bias, "note": note}
    if bias is False:
        logger.info("[%s] تحيز %s هابط قوي — رفض الإشارات الصاعدة (%s)",
                    symbol, HTF_BIAS_TIMEFRAME, note)
    return bias


def premise_alive(setup: DetectedSetup, last_close: float) -> bool:
    """[FE1.6.2] بوابة حيوية الفرضية لحظة الإنشاء (اقتباس روح is_wave_invalidated):
    الإعداد الصاعد صالح فقط إذا كان الإغلاق الحالي فوق أصل الموجة 1 (P0) —
    نفس شرط الإبطال البنيوي الذي يطبّقه monitor_step على المعلق بعد دقيقة.
    بدونها يولّد الماسح إشارات من نوافذ P0-P5 تاريخية انهار السعر تحتها بعيدًا،
    فيُبطلها المراقب خلال 60 ثانية (حلقة إنشاء/إلغاء DOA كل دورة مسح 15 دقيقة
    — سبب «لم تقبل ولا صفقة»: 5 من 7 إشارات أُبطلت خلال 60-70 ثانية من ولادتها).
    فشل قراءة المحاور = تساهل (fail-open) — بوابة جودة لا نقطة فشل."""
    try:
        p0 = float(setup.pivot_prices[0])
        return float(last_close) >= p0
    except (TypeError, ValueError, IndexError, AttributeError):
        return True


def structure_fresh(setup: DetectedSetup, df) -> bool:
    """[FE1.7.0] سقف عمر البنية: كم شمعة مرّت منذ نهاية النافذة (P5)؟
    النوافذ تُعاد كل دورة — بنية اكتملت قبل ساعات والسعر متمهل بعدها = مطاردة
    أو إعادة إنشاء حرفية (إثبات حي: محاور UNI/BAT/WLD متطابقة عبر ساعتين).
    فشل القراءة = تساهل (fail-open) — بوابة جودة لا نقطة فشل."""
    if MAX_STRUCTURE_AGE_BARS <= 0:
        return True
    try:
        p5_idx = int(setup.pivot_indices[5])
        age = (len(df) - 1) - p5_idx
        return age <= MAX_STRUCTURE_AGE_BARS
    except (TypeError, ValueError, IndexError, AttributeError):
        return True


def on_symbol_cooldown(symbol: str) -> bool:
    """[FE1.7.0] تبريد الرمز بعد انتهاء/إلغاء أمر معلق حديث — يقتل إعادة الإنشاء
    الحرفية كل دورة (إثبات حي: BAT انتهت 21:45 ← أُعيدت 22:00 بنفس المحاور).
    فشل الاستعلام = تساهل (fail-open)."""
    if SYMBOL_COOLDOWN_SEC <= 0:
        return False
    try:
        cutoff = datetime.fromtimestamp(
            time.time() - SYMBOL_COOLDOWN_SEC, tz=timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = db.query(
            "SELECT COUNT(*) AS n FROM signals WHERE symbol = %s AND status IN ('expired', 'cancelled')"
            " AND COALESCE(closed_at, created_at) >= %s",
            (symbol, cutoff),
        )
        return bool(rows and int(rows[0]["n"]) > 0)
    except Exception as exc:
        logger.debug("[%s] فحص التبريد فشل (تساهل): %s", symbol, exc)
        return False


def same_direction_active(direction: str = "BULLISH") -> int:
    """[FE1.7.0] عدد المراكز النشطة بنفس الاتجاه — لسقف العنقود الاتجاهي:
    5 ألتكوین لونجة تُضرب بشمعة BTC واحدة كأنها رهان بيتا واحد ×5.
    فشل الاستعلام = 0 (تساهل) — بوابة جودة لا نقطة فشل، كبقية البوابات."""
    try:
        rows = db.query(
            "SELECT COUNT(*) AS n FROM signals WHERE status IN ('pending', 'open') AND direction = %s",
            (direction,),
        )
        return int(rows[0]["n"]) if rows else 0
    except Exception as exc:
        logger.debug("فحص العنقود الاتجاهي فشل (تساهل): %s", exc)
        return 0


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
                    last_close = float(df.iloc[-1]["close"])
                    traded = False
                    # [FE1.7.0] إعادة ترتيب البوابات: الحيوية والتقادم أولًا — فرضية ميتة
                    # أو بنية أثرية يجب ألا تُحسب «مشغول» أو «ممتلئ» (كانت تلوث عدادات
                    # الاحتلال: 55% منها أعراض زومبي لا تشدد حقيقي، فتُخفي السبب الحقيقي)
                    if not trading_on:
                        logger.info("[%s] إعداد صاعد صالح لكن توليد الإشارات معطل (ورقي متوقف)", symbol)
                    elif not premise_alive(best, last_close):
                        # [FE1.6.2] الفرضية ماتت قبل الولادة — لا تخلق أمرًا سيُبطل خلال دقيقة
                        with scan_stats_lock:
                            scan_stats["rejected_stale_premise"] += 1
                        logger.info(
                            "[%s] إعداد صاعد متقادم: الإغلاق %s دون أصل الموجة "
                            "P0=%s — لا إشارة",
                            symbol, fmt_price(last_close),
                            fmt_price(float(best.pivot_prices[0])))
                    elif not structure_fresh(best, df):
                        # [FE1.7.0] بنية أتمت قبل زمن طويل — لا إشارات من محاور أثرية
                        with scan_stats_lock:
                            scan_stats["rejected_old_structure"] += 1
                        logger.info("[%s] بنية متقادمة: نهاية النافذة (P5) تجاوزت سقف العمر %s شمعة — لا إشارة",
                                    symbol, MAX_STRUCTURE_AGE_BARS)
                    elif on_symbol_cooldown(symbol):
                        # [FE1.7.0] تبريد بعد انتهاء/إلغاء حديث — لا إعادة إنشاء حرفية
                        with scan_stats_lock:
                            scan_stats["rejected_cooldown"] += 1
                        logger.info("[%s] رمز في فترة تبريد %.0f ثانية بعد انتهاء/إلغاء أمر معلق — لا إشارة",
                                    symbol, SYMBOL_COOLDOWN_SEC)
                    elif symbol_has_active(symbol):
                        with scan_stats_lock:
                            scan_stats["rejected_symbol_busy"] += 1
                    elif CLUSTER_MAX_SAME_DIRECTION > 0 and same_direction_active("BULLISH") >= CLUSTER_MAX_SAME_DIRECTION:
                        # [FE1.7.0] عنقود اتجاهي — 5 لونجات مترابطة تُضرب بشمعة BTC واحدة
                        n_cluster = same_direction_active("BULLISH")
                        with scan_stats_lock:
                            scan_stats["rejected_cluster"] += 1
                        logger.info("[%s] سقف العنقود الاتجاهي: %s إشارات صاعدة نشطة (السقف %s) — لا إشارة",
                                    symbol, n_cluster, CLUSTER_MAX_SAME_DIRECTION)
                    elif active_trade_count() >= MAX_OPEN_TRADES:
                        with scan_stats_lock:
                            scan_stats["rejected_active_limit"] += 1
                    elif HTF_BIAS_ENABLED and htf_bias(symbol) is False:
                        # [FE1.6.0] حقبة هابطة واضحة على الفريم الأعلى — لا دخولات عكس التدفق
                        with scan_stats_lock:
                            scan_stats["rejected_htf_bias"] += 1
                    else:
                        traded = create_pending_signal(symbol, best, last_close=last_close)
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
            _reconcile_maybe()  # [FE1.8.0] مصالقة الوقف الراكن دوريًا (حقيقي فقط)
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
    # [FE1.5.0] فاحصات الصحة ترسل HEAD بلا بيانات دخول — كان يُرد 401 ويظهر خطأ
    # في سجلات Render. HEAD يرجع 200 بلا جسم ولا مصادقة (لا يكشف شيئًا)،
    # وGET / يبقى محميًا بالكامل كما هو.
    if request.method == "HEAD":
        return Response("", 200)
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
        "scanner": {  # [FE1.5.0] ملخص ماسح الكون — عام بلا تفاصيل النتائج (المحمية في /api/all)
            "enabled": SCAN_UNIVERSE_ENABLED,
            "running": bool(_scanner_state["running"]),
            "last_scan_at": _scanner_state["last_scan_at"],
            "results_n": len(_scanner_results),
        },
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
        "risk": risk_snapshot(),  # [FE1.8.0] بطاقة قاطع المخاطر (حد يومي/متتاليات/تبريد)
        "protection": {  # [FE1.8.0] حالة حماية الموضع
            "standing_stop": REAL_STANDING_STOP,
            "be_at_r": BE_AT_R_ENABLED,
            "partial_at_r": PARTIAL_AT_R_ENABLED,
            "partial_pct": PARTIAL_CLOSE_PCT,
            "rr_net_min": RR_NET_MIN,
        },
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
        "scanner": scanner_state_snapshot(),  # [FE1.5.0] ماسح الكون + النتائج
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
    # [FE1.7.0] الحقيقية: الإلغاء يجب أن يمس المنصة فعلًا — الكود القديم كان يقلب الـDB فقط
    # فيبقى LIMIT BUY راكدًا GTC على باينانس (ثغرة مؤكدة: نص اللوحة يعد بـ«إلغاء الأمر
    # الفعلي» ولا يحدث، وإن ملأ الأمر لاحقًا صار موضعًا حقيقيًا يتيمًا بلا تتبع).
    if sig.get("is_real"):
        ex = binance_trade_exchange()
        if ex is None:
            log_and_notify("error", f"❌ تعذر إلغاء {sig['symbol']} حقيقيًا: مفاتيح باينانس غائبة", "REAL_TRADE_ERROR")
            return jsonify({"ok": False, "error": "مفاتيح باينانس غير مضبوطة — لم يُلغَ الأمر الحقيقي على المنصة"}), 503
        if not sig.get("order_id"):
            # أمر قديم بلا معرف منصة — محاسبة محلية فقط
            db.execute(
                "UPDATE signals SET status='cancelled', close_reason=%s, closed_at=%s WHERE id=%s",
                ("إلغاء يدوي من اللوحة (بلا معرف أمر على المنصة)", utc_now_iso(), sig_id),
            )
            return jsonify({"ok": True, "message": f"أُلغي أمر {sig['symbol']} محاسبيًا (بلا معرف أمر على المنصة)"})
        if not cancel_real_order(ex, sig["symbol"], sig["order_id"]):
            # فشل الإلغاء: لا نصفي الـDB — أمر حي على المنصة وإعادة المحاولة آلية في المراقبة
            log_and_notify("warning", f"⚠ فشل إلغاء الأمر الحقيقي {sig['symbol']} — يبقى حيًا على المنصة وإعادة المحاولة آلية في دورة المراقبة", "REAL_TRADE_ERROR")
            return jsonify({"ok": False, "error": "فشل إلغاء الأمر على باينانس — ستُعاد المحاولة آليًا في دورة المراقبة القادمة"}), 502
        _resync_after_cancel_attempt(_parse_sig_row(sig), ex, "إلغاء يدوي من اللوحة")
        fresh = db.query("SELECT status FROM signals WHERE id = %s", (sig_id,))
        new_status = fresh[0]["status"] if fresh else "?"
        log_and_notify("info", f"🚫 [حقيقي] أُرسل إلغاء الأمر لـ {sig['symbol']} — الحالة من المنصة: {new_status}", "ORDER_CANCELLED")
        return jsonify({"ok": True, "message": f"أُلغي الأمر الحقيقي لـ {sig['symbol']} (حالة المنصة الآن: {new_status})"})
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
    # [FE1.5.0] أصبحت محمية — كانت تكشف بيانات الصفقات للعامة بلا مصادقة
    resp = require_dashboard_auth()
    if resp:
        return resp
    rows = db.query("SELECT * FROM signals ORDER BY id DESC LIMIT 100")
    return jsonify({"signals": [_parse_sig_row(r) for r in rows], "version": BOT_VERSION})


@app.route("/api/pnl_history")
def api_pnl_history():
    # [FE1.5.0] أصبحت محمية — كانت تكشف سجل الأرباح للعامة بلا مصادقة
    resp = require_dashboard_auth()
    if resp:
        return resp
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


@app.route("/api/scan/run", methods=["POST"])
def api_scan_run():
    """[FE1.5.0] فحص يدوي فوري لكون باينانس من زر اللوحة — يُنفذ في خيط منفصل
    (يستغرق نحو دقيقة) والنتائج تظهر عبر التحديث الدوري للوحة. محمي بالمصادقة."""
    resp = require_dashboard_auth()
    if resp:
        return resp
    with _scanner_lock:
        running = bool(_scanner_state["running"])
    if running:
        return jsonify({"ok": False, "running": True,
                        "message": "فحص جارٍ بالفعل — النتائج تظهر خلال لحظات"})
    def _job():
        try:
            run_universe_scan(force=True, trigger="manual")
        except Exception as exc:
            logger.warning("فحص يدوي فشل: %s", exc)
    threading.Thread(target=_job, daemon=True, name="manual-scan").start()
    return jsonify({"ok": True, "running": True,
                    "message": "بدأ فحص كون باينانس — النتائج تظهر في قسم «فحص أزواج باينانس» خلال نحو دقيقة"})


@app.route("/api/stats/reset", methods=["POST"])
def api_stats_reset():
    resp = require_dashboard_auth()
    if resp:
        return resp
    body = request.get_json(silent=True) or {}
    confirm = str(body.get("confirm") or request.args.get("confirm") or "").strip().upper()
    # [FE1.7.0] حارس 1: تأكيد صريح — استدعاء POST عابر لا يمحو سجل القياس كله
    if confirm != "RESET":
        return jsonify({"ok": False, "error": "التصفير يتطلب تأكيدًا صريحًا: أرسل confirm=RESET"}), 400
    # [FE1.7.0] حارس 2: لا تصفير فوق صفقات حقيقية نشطة — كان DELETE يمحو تتبع موضع حي فيصير يتيمًا
    active_real = db.query(
        "SELECT COUNT(*) AS n FROM signals WHERE COALESCE(is_real, 0) = 1 AND status IN ('pending', 'open')"
    )
    n_active_real = int(active_real[0]["n"]) if active_real else 0
    if n_active_real > 0:
        return jsonify({"ok": False, "error": f"توجد {n_active_real} صفقة حقيقية نشطة — أغلقها أو ألغها قبل التصفير"}), 409
    # [FE1.7.0] حارس 3: أرشفة قبل الحذف — سجل الصفقات هو أصل التعلم والمعايرة
    # (درس V9: ضغط المستخدم التصفير فعليًا ففقد كل التاريخ)
    all_rows = db.query("SELECT * FROM signals")
    arch_key = "stats_archive_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    try:
        db_set_state(arch_key, json.dumps(all_rows, default=str))
        old_arch = db.query("SELECT key FROM bot_state WHERE key LIKE 'stats_archive_%' ORDER BY key DESC")
        for r in (old_arch or [])[3:]:  # احتفظ بآخر 3 أرشيفات فقط
            db.execute("DELETE FROM bot_state WHERE key = %s", (r["key"],))
    except Exception as exc:
        logger.warning("فشل أرشفة التصفير — أُلغي التصفير كليًا: %s", exc)
        return jsonify({"ok": False, "error": "فشل حفظ الأرشفة — لم يُصفّر شيء"}), 500
    db.execute("DELETE FROM signals")
    db.execute("DELETE FROM notifications")
    set_paper_balance(PAPER_BALANCE_START)
    with detections_lock:
        recent_detections.clear()
    with scan_stats_lock:
        for k in scan_stats:
            scan_stats[k] = 0
    msg = f"🧹 صُفّرت الإحصائيات ({len(all_rows)} صفقة أُرشفت في {arch_key}) وعاد الرصيد الورقي للبداية"
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
    restore_scan_results()  # [FE1.5.0] قبل إقلاع WS — الأسواق المصنوعة تُبنى من القائمة المحدثة
    load_markets_async()
    start_ws_price_feed()  # [FE1.2.0] الأسعار الحية من ويب سوكت — REST احتياطًا فقط
    threading.Thread(target=scan_loop, daemon=True, name="scan-loop").start()
    threading.Thread(target=monitor_loop, daemon=True, name="monitor-loop").start()
    threading.Thread(target=keep_alive_loop, daemon=True, name="keep-alive").start()
    if SCAN_UNIVERSE_ENABLED:  # [FE1.5.0] خيط ماسح الكون — فحص أول بعد 90 ثانية ثم كل SCAN_INTERVAL_SEC
        threading.Thread(target=universe_scan_loop, daemon=True, name="universe-scanner").start()
    ka_target = resolve_keep_alive_url()
    ka_txt = (f"نشط — نبضة كل {int(KEEP_ALIVE_INTERVAL_SEC)} ثانية إلى {ka_target}"
              if (KEEP_ALIVE_ENABLED and ka_target) else "معطل ⚠ (خطر نوم الخدمة على الخطة المجانية)")
    mem_txt = (f"كسول + تقليم + gc عند {int(MEM_GC_THRESHOLD_MB)}MB" if MEM_LAZY_MARKETS
               else "مسبق (الوضع القديم) — خطر OOM")
    real_txt = ("🔴 نشط — الإشارات الجديدة أوامر فعلية على باينانس ⚠" if is_real_mode
                else "⚪ متوقف — وضع ورقي آمن (فعّله من زر اللوحة)")
    scan_txt = (f"مفعّل — فحص كامل كل {int(SCAN_INTERVAL_SEC/60)} دقيقة وأعلى {SCAN_TOP_N} زوجًا يُطبق تلقائيًا"
                if SCAN_UNIVERSE_ENABLED else "معطل (قائمة يدوية من crypto_list.txt)")
    log_and_notify(
        "info",
        f"🚀 Fibo-Elio {BOT_VERSION} أقلع — استراتيجية واحدة: Elliott_Fibonacci (المنطق الأصلي)\n"
        f"الوضع: {'حقيقي 🔴' if is_real_mode else 'ورقي'} | أزواج: {len(watchlist)} | فريم الكشف {SIGNAL_TIMEFRAME} | التنفيذ {ENTRY_TIMEFRAME}\n"
        f"الأسعار الحية: {'ويب سوكت (ccxt.pro) — REST احتياطًا' if WS_ENABLED else 'REST'} | "
        f"انعكاس الزيجزاج {DEVIATION_THRESHOLD*100:.2f}% | أقصى صفقات {MAX_OPEN_TRADES} | مخاطرة {RISK_PCT_PER_TRADE}%\n"
        f"البقاء الحي: {ka_txt}\n"
        f"التداول الحقيقي: {real_txt} | سقف الأمر {REAL_MAX_NOTIONAL_USDT:.0f}$ | تيستنت {'نعم' if BINANCE_TESTNET else 'لا'}\n"
        f"ماسح الكون: {scan_txt}\n"
        f"الذاكرة: {mem_txt} — الحد 512MB",
        "BOOT",
    )


if __name__ == "__main__":
    initialize_bot_services()
    app.run(host="0.0.0.0", port=PORT, threaded=True)
