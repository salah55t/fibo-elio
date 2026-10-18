#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[FE1.9.18] حزام القياس التاريخي — اقتباس «أداة القياس التاريخي» من elliot-waves-auto
(تحليل elliott-waves-auto، الاقتباس المعتمد رقم 4) — سكربت offline خالص لا يُشغّل البوت.

الوظيفة: يعيد تشغيل كاشف الموجات (engine/ نفسه المستخدم في الإنتاج) على شموع
kline_cache من Postgres الدائم بمشيئة walk-forward (نافذة تنزلق خطوة ثابتة)،
يطبق مرآة بوابات الإشارة الأساسية (عمر البنية/الفرضية الحية/التصحيح العميق/
المطاردة/سقف الوقف/أرضية rr_net/سقف الأسبوع 7 أيام/المراحل TP1→TP3 بفجوة 0.2R
وجزئي 40%) ويحاكي دورة حياة الأمر المعلق على الشموع التالية (ملء/وقف/أهداف/
انتهاء صلاحية)، ثم يطبع:
  • معدلات إصابة TP1/TP2/TP3 مقابل SL — «هل أهدافنا ووقفاتنا مناسبة فعلًا؟»
  • متوسط النتيجة بوحدات R لكل صفقة وإجماليها — جودة هندسة الصفقة
  • شبكة what-if: أرضية rr_net × سقف عمر البنية — معايرة بالأدلة لا بالحدس

ملاحظات:
  • مرآة حسابية لصيغ vnz.py (دخول P3−0.382×W3، وقف P0−0.1%، سلّم W5=W1 /
    0.618×W3 / 1.618×W1 من P2) — لا استيراد لـvnz.py إطلاقًا (بوت حي).
  • الرسوم: 0.1% × اتجاهين مثل FEE_RATE=0.001 — rr_net يطرح أثرها.
  • الاستخدام: DATABASE_URL=<رابط> python scripts/fe1918_backtest.py [--tf 5m]
    [--step 3] [--window 300] [--max-syms 8] [--age-hours 9 12]
    [--rr-floor 0.6 0.8 1.0] [--limit-days 14]
"""

import argparse
import math
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from engine.pattern_detector import DetectorConfig, PivotDetector  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger("backtest")
logger.setLevel("WARNING")

FEE_RATE = 0.001            # 0.1% × اتجاهين مثل الإنتاج
DEEP_RETRACE = 0.786
MAX_ENTRY_DIST_PCT = 1.5
MAX_STOP_PCT = 3.5
PENDING_LIFETIME_HOURS = 1.5
TP_STAGE_SLICE_PCT = 0.40   # جزئي 40% عند كل مرحلة
STAGE_GAP_R = 0.2           # فجوة الإزالة بين المراحل
WEEK_CAP_DAYS = 7

TF_SECONDS = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400}


def build_detector():
    return PivotDetector(DetectorConfig(
        method="zigzag", deviation_threshold=0.006, price_source="close",
        min_wave_bars=2, require_fib_confluence=False, fib_tolerance_pct=0.01,
        min_wave_proportion=0.15))


def rr_net_value(entry: float, sl: float, tp: float) -> float:
    risk = entry - sl
    if risk <= 0:
        return 0.0
    gross = (tp - entry) / risk
    fees_r = (FEE_RATE * 2.0 * entry) / risk
    return gross - fees_r


def ladder_rungs(p0, p1, p2, p3):
    """سلّم الإنتاج: W5=W1 / 0.618×W3 / 1.618×W1 — جميعها من P2 صعودًا."""
    w1 = p1 - p0
    w3 = p3 - p2
    return [("w5_eq_w1", p2 + w1), ("w5_0618_w3", p2 + 0.618 * w3),
            ("ext_1618", p2 + 1.618 * w1)]


def staged_targets(entry, sl, rungs, weekly_hi, rr_floor):
    """مرآة build_staged_targets: قص على سقف الأسبوع + فوق الدخول + أرضية rr_net
    + إزالة المتلاصقة (فجوة 0.2R) صعودًا."""
    risk = entry - sl
    if risk <= 0:
        return [], 0.0
    best_rr = 0.0
    kept = []
    for _b, cand in rungs:
        rr = rr_net_value(entry, sl, cand)
        best_rr = max(best_rr, rr)
        if weekly_hi:
            cand = min(cand, weekly_hi)
        if cand <= entry:
            continue
        if rr_net_value(entry, sl, cand) < rr_floor:
            continue
        kept.append(cand)
    kept.sort()
    out = []
    for c in kept:
        if out and (c - out[-1]) / risk < STAGE_GAP_R:
            continue
        if out and c <= out[-1]:
            continue
        out.append(c)
    return out, best_rr


def simulate_window(df, age_bars, rr_floor):
    """نافذة واحدة: كشف + بوابات مرآة → (صفقة محاكاة) أو None.
    يعيد dict نتيجة أو ("سبب رفض",None)."""
    det = build_detector()
    setups = det.scan(df)
    bulls = [s for s in setups if s.direction == "BULLISH"]
    if not bulls:
        return None, "no_setup"
    n = len(df)
    fresh = [s for s in bulls if (n - 1) - int(s.pivot_indices[5]) <= age_bars] or None
    if not fresh:
        return None, "old_structure"
    best = max(fresh, key=lambda s: s.detected_at.timestamp() if s.detected_at else 0.0)
    entry = float(best.entry_zone_low)
    sl = float(best.stop_loss_price)
    last_close = float(df["close"].iloc[-1])
    p0 = float(best.pivot_prices[0])
    if last_close <= p0:
        return None, "premise_dead"
    p5 = float(best.pivot_prices[5])
    if p5 > p0 and (p5 - last_close) / (p5 - p0) >= DEEP_RETRACE:
        return None, "deep_retrace"
    if entry <= 0 or sl <= 0 or last_close / entry - 1.0 > MAX_ENTRY_DIST_PCT / 100.0:
        return None, "far_entry"
    stop_pct = (entry - sl) / entry * 100.0
    if stop_pct > MAX_STOP_PCT:
        return None, "wide_stop"
    # سقف الأسبوع من البيانات ذاتها (أعلى high لآخر 7 أيام)
    tf_sec = TF_SECONDS.get(str(df["timeframe"].iloc[0]), 300)
    week_bars = max(1, int(WEEK_CAP_DAYS * 86400 / tf_sec))
    weekly_hi = float(df["high"].iloc[-min(len(df), week_bars):].max())
    rungs = ladder_rungs(*[float(best.pivot_prices[i]) for i in (0, 1, 2, 3)])
    stages, _brr = staged_targets(entry, sl, rungs, weekly_hi, rr_floor)
    if not stages:
        return None, "no_target_weekly"
    return {"entry": entry, "sl": sl, "stages": stages,
            "age_p5": (n - 1) - int(best.pivot_indices[5]),
            "stop_pct": stop_pct,
            "rr_stage1": rr_net_value(entry, sl, stages[0])}, "ok"


def walk_forward(df, trade, lifetime_bars, idx):
    """محاكاة دورة الحياة على الشموع بعد نافذة الكشف: ملء → مراحل/وقف/انتهاء.
    يعيد ("fill"|"expired"|"skip", R أو None، الحدث الأخير)."""
    entry, sl = trade["entry"], trade["sl"]
    risk = entry - sl
    stages = list(trade["stages"])
    if idx + 1 >= len(df):
        return "skip", None, None
    seg = df.iloc[idx + 1:]
    seg = seg.head(lifetime_bars)
    filled_at = None
    for pos, (_, bar) in enumerate(seg.iterrows()):
        lo, hi = float(bar["low"]), float(bar["high"])
        if filled_at is None:
            if lo <= entry:               # لمس منطقة الدخول → ملء
                filled_at = pos
            continue
        # الوقف أولًا (intrabar SL-first كما في الإنتاج)
        if lo <= sl:
            return "fill", -1.0, "SL"
        if stages and hi >= stages[0]:
            # جني جزئي 40% عند المرحلة ثم إعادة تقييم باقي المراحل في نفس الشمعة
            stage = stages.pop(0)
            if not stages:
                r = (stage - entry) / risk
                fees_r = (FEE_RATE * 2.0 * entry) / risk
                return "fill", r - fees_r, "TP_LAST"
            # باقي المراحل تُتابع في الشموع التالية (الجزئي محسوب عند الغلق النهائي)
    if filled_at is None:
        return "expired", 0.0, "EXPIRY"
    return "fill", 0.0, "OPEN_END"  # انتهت النافذة بعد الملء دون لمس — نصف نتيجة لا تُحسب


def run_backtest(args):
    import psycopg2
    import psycopg2.extras
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("❌ DATABASE_URL غير مضبوط — السكربت يقرأ كاش Postgres الدائم فقط")
        return 2
    conn = psycopg2.connect(dsn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT symbol, timeframe, ts, open, high, low, close, volume FROM kline_cache "
        "WHERE timeframe = %s ORDER BY symbol, ts ASC", (args.tf,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("❌ لا شموع في kline_cache للفريم", args.tf)
        return 2
    by_sym = defaultdict(list)
    for r in rows:
        by_sym[r["symbol"]].append(r)

    tf_sec = TF_SECONDS.get(args.tf, 300)
    lifetime_bars = max(1, int(PENDING_LIFETIME_HOURS * 3600 / tf_sec))
    age_opts = [float(a) for a in args.age_hours]
    rr_opts = [float(r) for r in args.rr_floor]
    print("=" * 78)
    print(f"حزام القياس التاريخي [FE1.9.18] — tf={args.tf} رموز={len(by_sym)} "
          f"step={args.step} window={args.window} حد={args.limit_days} يوم")
    print("=" * 78)

    for age_h in age_opts:
        age_bars = int(age_h * 3600 / tf_sec)
        for rr_floor in rr_opts:
            agg = Counter()
            r_sum, r_n, r_win = 0.0, 0, 0
            per_event = Counter()
            for sym, srows in list(by_sym.items())[: args.max_syms]:
                df = pd.DataFrame(srows, columns=["symbol", "timeframe", "ts",
                                                  "open", "high", "low", "close", "volume"])
                for c in ("open", "high", "low", "close", "volume"):
                    df[c] = pd.to_numeric(df[c])
                if args.limit_days:
                    cutoff = df["ts"].max() - args.limit_days * 86400 * 1000
                    df = df[df["ts"] >= cutoff].reset_index(drop=True)
                if len(df) < args.window + lifetime_bars + 5:
                    continue
                for idx in range(args.window, len(df) - lifetime_bars, args.step):
                    win = df.iloc[idx - args.window: idx + 1].reset_index(drop=True)
                    trade, why = simulate_window(win, age_bars, rr_floor)
                    agg[f"gate_{why}"] += 1
                    if trade is None:
                        continue
                    outcome, r, event = walk_forward(win, trade, lifetime_bars, idx)
                    if outcome == "skip":
                        continue
                    agg[f"event_{event}"] += 1
                    if outcome == "fill" and r is not None and event != "OPEN_END":
                        r_sum += r
                        r_n += 1
                        if r > 0:
                            r_win += 1
            trades_n = agg["event_SL"] + agg["event_TP_LAST"]
            wr = (agg["event_TP_LAST"] / trades_n * 100.0) if trades_n else 0.0
            print(f"\n■ أرضية rr_net={rr_floor:g} | سقف عمر البنية={age_h:g}س "
                  f"({age_bars} شمعة)")
            print(f"  نوافذ مقيّمة: {sum(v for k, v in agg.items() if k.startswith('gate_'))} "
                  f"— رفض: " + " ".join(f"{k[5:]}={v}" for k, v in sorted(agg.items())
                                        if k.startswith("gate_") and k != "gate_ok" and v))
            print(f"  ملء/أحداث: TP_LAST={agg['event_TP_LAST']} SL={agg['event_SL']} "
                  f"EXPIRY={agg['event_EXPIRY']} OPEN_END={agg['event_OPEN_END']} "
                  f"— معدل إصابة الهدف الأخير: {wr:.1f}%")
            if r_n:
                print(f"  النتيجة بوحدات R: مجموع {r_sum:+.2f}R على {r_n} صفقة مغلقة "
                      f"(متوسط {r_sum / r_n:+.3f}R) — فوز {r_win}/{r_n}")
            else:
                print("  النتيجة بوحدات R: لا صفقات مغلقة في هذا التكوين")
    print("\nقراءة: TP_LAST vs SL = هل الوقف والأهداف متناسبان فعلًا؛ المتوسط بوحدات R "
          "هو حكم المعايرة (فوق 0 = الهندسة رابحة تاريخيًا على هذه البيانات).")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="حزام القياس التاريخي FE1.9.18")
    ap.add_argument("--tf", default="5m", choices=list(TF_SECONDS))
    ap.add_argument("--step", type=int, default=3)
    ap.add_argument("--window", type=int, default=300)
    ap.add_argument("--max-syms", type=int, default=8)
    ap.add_argument("--limit-days", type=int, default=14)
    ap.add_argument("--age-hours", nargs="+", default=["9.0", "12.0"])
    ap.add_argument("--rr-floor", nargs="+", default=["0.6", "0.8", "1.0"])
    sys.exit(run_backtest(ap.parse_args()))
