#!/usr/bin/env python3
import sys
import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

CDT = ZoneInfo("America/Chicago")

def to_cdt(ts):
    if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
        return ts.astimezone(CDT).strftime("%Y-%m-%d %H:%M CDT")
    return str(ts)

# ── Args ───────────────────────────────────────────────────────────────────────
args = sys.argv[1:]
if not args:
    print("Usage: manoj_trade_analysis.py <TICKER> [INTERVAL] [DAYS]")
    sys.exit(1)

ticker       = args[0].upper()
interval_raw = args[1] if len(args) > 1 else "1m"
days         = int(args[2]) if len(args) > 2 else 5

_imap = {
    "1":"1m","3":"3m","5":"5m","15":"15m","30":"30m",
    "60":"60m","90":"90m","1h":"60m","day":"1d","1day":"1d",
    "1d":"1d","week":"1wk","1wk":"1wk","wk":"1wk",
}
interval = _imap.get(interval_raw.lower(), interval_raw.lower())

_max_days = {"1m":7,"2m":60,"5m":60,"15m":60,"30m":60,"60m":730,"90m":60}
if interval in _max_days and days > _max_days[interval]:
    print(f"[warn] {interval} data is capped at {_max_days[interval]} days by Yahoo Finance. Adjusting.")
    days = _max_days[interval]

# ── Fetch data ─────────────────────────────────────────────────────────────────
end   = datetime.now()
start = end - timedelta(days=days)

df = yf.download(ticker, start=start, end=end, interval=interval,
                 auto_adjust=True, progress=False)

if df.empty:
    print(f"[error] No data returned for {ticker} with interval={interval}. "
          "Check the ticker and interval are valid.")
    sys.exit(1)

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df = df.dropna()

# ── Pattern helpers ────────────────────────────────────────────────────────────
def body(r):      return abs(r["Close"] - r["Open"])
def wick(r):      return (r["High"] - r["Low"]) - body(r)
def is_boring(r): return body(r) < wick(r) and (r["High"] - r["Low"]) > 0
def is_full(r):   return body(r) >= wick(r) and (r["High"] - r["Low"]) > 0
def is_green(r):  return r["Close"] > r["Open"]
def is_red(r):    return r["Close"] < r["Open"]

# ── Pattern detection ──────────────────────────────────────────────────────────
signals = []

for i in range(2, len(df)):
    c1, c2, c3 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
    t1, t2, t3 = df.index[i-2], df.index[i-1], df.index[i]

    # Bullish: RED boring → GREEN full → GREEN boring
    if (is_boring(c1) and is_red(c1) and
        is_full(c2)   and is_green(c2) and
        is_boring(c3) and is_green(c3)):
        entry     = round(float(c3["Close"]), 4)
        stop_loss = round(min(float(c1["Low"]), float(c3["Low"])), 4)
        risk      = round(entry - stop_loss, 4)
        signals.append({
            "direction": "LONG",
            "signal_time": to_cdt(t3),
            "entry": entry,
            "stop_loss": stop_loss,
            "target": round(entry + 2 * risk, 4),
        })

    # Bearish: GREEN boring → RED full → RED boring
    elif (is_boring(c1) and is_green(c1) and
          is_full(c2)   and is_red(c2) and
          is_boring(c3) and is_red(c3)):
        entry     = round(float(c3["Close"]), 4)
        stop_loss = round(max(float(c1["High"]), float(c3["High"])), 4)
        risk      = round(stop_loss - entry, 4)
        signals.append({
            "direction": "SHORT",
            "signal_time": to_cdt(t3),
            "entry": entry,
            "stop_loss": stop_loss,
            "target": round(entry - 2 * risk, 4),
        })

# ── Output ─────────────────────────────────────────────────────────────────────
long_count  = sum(1 for s in signals if s["direction"] == "LONG")
short_count = sum(1 for s in signals if s["direction"] == "SHORT")

print(f"\n  {ticker} — {interval} candles — Last {days} day(s)  "
      f"({start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')})")
print(f"  {len(df)} candles scanned, {len(signals)} pattern(s) found "
      f"({long_count} LONG, {short_count} SHORT).\n")

if not signals:
    print("  No Manoj-Trade patterns found in the selected period.")
    print("  Tips: try a longer DAYS window or a different interval (e.g. 5m, 15m)")
else:
    rows = [(str(idx),
             ticker,
             s["direction"],
             s["signal_time"],
             str(s["entry"]),
             str(s["stop_loss"]),
             str(s["target"]))
            for idx, s in enumerate(signals, 1)]

    headers = ("#", "Ticker", "Direction", "Signal Time (CDT)", "Entry", "Stop", "Target")
    widths  = [max(len(h), max(len(r[i]) for r in rows))
               for i, h in enumerate(headers)]

    def hline(l, m, r):
        return l + m.join("─" * (w + 2) for w in widths) + r

    def dline(cells):
        return "│" + "│".join(f" {c.ljust(w)} " for c, w in zip(cells, widths)) + "│"

    print("  " + hline("┌", "┬", "┐"))
    print("  " + dline(headers))
    print("  " + hline("├", "┼", "┤"))
    for i, row in enumerate(rows):
        print("  " + dline(row))
        if i < len(rows) - 1:
            print("  " + hline("├", "┼", "┤"))
    print("  " + hline("└", "┴", "┘"))

    print()
    print("  Risk/Reward : 2:1 on all signals")
    print("  Stop loss   = extreme low/high of candle-1 or candle-3")
    print("  Target      = entry ± 2× risk")
    print()
    print("  Pattern legend:")
    print("    Red boring → Green full → Green boring  →  LONG")
    print("    Green boring → Red full → Red boring    →  SHORT")
