#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حِمالة معاينة FE1.9.16 — اللوحة الحقيقية ببيانات وهمية غنية (نمط FE1.9.13).
تعمل على 127.0.0.1:5055 لالتقاط لقطات متصفح: النافذة العائمة + الحالة الفارغة.
صفر تغيير على panel.py — المعاينة تجاور فقط."""

import random
import time

import os
from flask import Flask, jsonify, request, send_from_directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

import panel

app = Flask(__name__, static_folder=None)
random.seed(1914)

SYMS = ["BTC/USDT", "SOL/USDT", "APT/USDT", "TIA/USDT", "WLD/USDT"]


def fake_candles(sym, n=180, step=300_000):
    base = int(time.time() * 1000) - n * step
    price = {"BTC/USDT": 82000.0, "SOL/USDT": 190.0}.get(sym, 1.5 + len(sym) % 3)
    out, p = [], price
    for i in range(n):
        d = (random.random() - 0.5) * price * 0.006
        o = p
        c = p + d
        h = max(o, c) + price * 0.001
        lo = min(o, c) - price * 0.001
        out.append([base + i * step, o, h, lo, c, random.random() * 900])
        p = c
    return out


@app.get("/")
def home():
    return panel.PANEL_HTML


@app.get("/static/<path:p>")
def staticf(p):
    return send_from_directory(STATIC_DIR, p)


@app.get("/lwc.js")
def lwc():
    return send_from_directory(STATIC_DIR, "lightweight-charts.standalone.production.js")


@app.get("/api/all")
def api_all():
    return jsonify({
        "version": panel.BOT_VERSION,
        "watchlist": SYMS,
        "trading_enabled": True,
        "real_trading": False,
        "entry_timeframe": "5m",
        "signal_timeframe": "15m",
        "open_signals": [
            {"id": 1, "symbol": "BTC/USDT", "direction": "BULLISH", "status": "open",
             "entry_price": 82100.0, "entry_zone_low": 81800.0, "entry_zone_high": 82300.0,
             "stop_loss": 81000.0, "current_price": 82450.0, "rr_ratio": 1.8,
             "tp1": 83300.0, "tp2": 84100.0, "tp3": 85200.0,
             "tp_stages": [[83300.0, "w5_eq_w1"], [84100.0, "ext_0618w3"]],
             "weekly_high": 86500.0, "created_at": "2026-10-17T18:00:00Z"},
            {"id": 2, "symbol": "SOL/USDT", "direction": "BULLISH", "status": "pending",
             "entry_price": 189.4, "entry_zone_low": 188.9, "entry_zone_high": 189.9,
             "stop_loss": 185.2, "current_price": 190.1, "rr_ratio": 1.5,
             "tp1": 194.0, "tp2": 197.5, "tp3": 201.0,
             "tp_stages": [[194.0, "w5_eq_w1"]], "weekly_high": 205.0,
             "created_at": "2026-10-17T19:30:00Z", "expires_at": "2026-10-17T20:00:00Z"},
        ],
        "closed_signals": [
            {"id": 3, "symbol": "APT/USDT", "direction": "BULLISH", "status": "closed",
             "entry_price": 1.20, "close_price": 1.26, "pnl_usdt": 1.9, "pnl_pct": 5.0,
             "closed_at": "2026-10-17T15:12:00Z", "filled_at": "2026-10-17T13:02:00Z"},
        ],
         "detections": [
            {"symbol": "BTC/USDT", "direction": "BULLISH", "valid": True, "age_bars": 6,
             "retrace": {"w2": 0.55, "w2_in_zone": True, "w4": 0.42, "w4_in_zone": True},
             "rules": [{"name": "Rule-1", "passed": True}, {"name": "Rule-2", "passed": True}, {"name": "Rule-3", "passed": True}],
             "verdict": "بنية صالحة ✅", "pivots": [], "created_at": "2026-10-17T20:40:00Z"},
        ],
        "performance": {"trades": [{"pnl_usdt": 1.9, "cum_usdt": 1.9}, {"pnl_usdt": -0.4, "cum_usdt": 1.5},
                                    {"pnl_usdt": 0.8, "cum_usdt": 2.3}, {"pnl_usdt": 2.2, "cum_usdt": 4.5}],
                        "net_profit_usdt": 4.5, "win_rate": 48.0, "profit_factor": 1.35,
                        "total_closed_trades": 57, "avg_win": 1.4, "avg_loss": -0.6,
                        "max_drawdown_usdt": 1.1, "today_pnl": 2.1, "avg_duration_min": 95},
        "gates": {"tp_ladder": 12, "weekly_cap": 3, "evidence": 5},
        "scanner": {"running": True, "last_scan_at": "2026-10-17T21:00:00Z",
                    "results": [{"symbol": s} for s in SYMS]},
        "stats": {"closed_n": 57, "win_rate": 41.3, "net_pnl": -0.42, "pf": 1.01},
        "protections": {},
        "notifications": [],
        "memory": {"rss_mb": 285.1, "critical_mb": 440},
        "ws": {"enabled": True, "live_streams": 30},
        "raw": {"connected": True, "ticks": 41233, "age_sec": 0.05},
    })


@app.get("/api/ws/status")
def api_ws():
    return jsonify({"enabled": True, "loop_alive": True, "live_streams": 30,
                    "prices": {s: {"age_sec": 0.4, "source": "binance"} for s in SYMS},
                    "raw": {"enabled": True, "connected": True, "ticks": 41233, "age_sec": 0.05}})


@app.get("/api/klines")
def api_klines():
    sym = (request.args.get("symbol") or "").upper()
    if sym == "VOID/USDT":  # محاكاة رمز بلا بيانات — الحالة الفارغة الصادقة
        return jsonify({"symbol": sym, "tf": "5m", "candles": [], "source": "none",
                        "count": 0, "stale": False, "filled": False, "reason": "cooldown"})
    c = fake_candles(sym)
    return jsonify({"symbol": sym, "tf": "5m", "candles": c, "source": "cache+live",
                    "count": len(c), "stale": False, "filled": False})


@app.get("/api/ew_strategy")
def api_ew():
    return jsonify({"setup": None, "zigzag": [], "note": "لا بنية صالحة حاليًا"})


@app.get("/api/notifications")
def api_notif():
    return jsonify({"items": [
        {"level": "info", "message": "معاينة FE1.9.14 — النافذة العائمة والحالة الصادقة",
         "created_at": "2026-10-17T21:00:00Z"}]})


@app.get("/health")
def health():
    return jsonify({"ok": True, "version": panel.BOT_VERSION})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5055, threaded=True)
