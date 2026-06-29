#!/usr/bin/env python3
import sys
import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

CDT = ZoneInfo("America/Chicago")

# How close entry must be to prev-day high or low (0.3% of price)
PROX_PCT = 0.003

# Skip signals within this many minutes of the market open (9:30 ET = 8:30 CDT)
OPEN_FILTER_MINS = 30

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

# ── Fetch intraday data ────────────────────────────────────────────────────────
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

# ── Fetch daily data for prev-day H/L (extra buffer for weekends/holidays) ────
daily_df = yf.download(ticker, start=start - timedelta(days=14), end=end,
                       interval="1d", auto_adjust=True, progress=False)
if isinstance(daily_df.columns, pd.MultiIndex):
    daily_df.columns = daily_df.columns.get_level_values(0)
daily_df = daily_df.dropna()
# Normalise index to date-only for easy comparison
daily_df.index = pd.to_datetime(daily_df.index).normalize().tz_localize(None)

def prev_day_level(signal_ts, entry):
    """Return (label, is_high, is_low) if entry is within PROX_PCT of
    previous trading day high or low, else None."""
    if hasattr(signal_ts, "tzinfo") and signal_ts.tzinfo is not None:
        sig_date = pd.Timestamp(signal_ts.astimezone(CDT).date())
    else:
        sig_date = pd.Timestamp(signal_ts.date())

    prior = daily_df.index[daily_df.index < sig_date]
    if len(prior) == 0:
        return None
    row = daily_df.loc[prior[-1]]
    ph, pl = float(row["High"]), float(row["Low"])

    near_high = abs(entry - ph) / ph <= PROX_PCT
    near_low  = abs(entry - pl) / pl  <= PROX_PCT

    if not (near_high or near_low):
        return None
    if near_high and near_low:
        label = f"Prev H&L  {ph:.2f}/{pl:.2f}"
    elif near_high:
        label = f"Prev High {ph:.2f}"
    else:
        label = f"Prev Low  {pl:.2f}"
    return label, near_high, near_low

def is_past_open_filter(signal_ts):
    """Return True if signal is at least OPEN_FILTER_MINS after market open."""
    if hasattr(signal_ts, "tzinfo") and signal_ts.tzinfo is not None:
        cdt_ts = signal_ts.astimezone(CDT)
    else:
        cdt_ts = signal_ts
    # Market open = 8:30 CDT
    open_cdt = cdt_ts.replace(hour=8, minute=30, second=0, microsecond=0)
    return (cdt_ts - open_cdt).total_seconds() >= OPEN_FILTER_MINS * 60

# ── Pattern helpers ────────────────────────────────────────────────────────────
def body(r):      return abs(r["Close"] - r["Open"])
def wick(r):      return (r["High"] - r["Low"]) - body(r)
def is_boring(r): return body(r) < wick(r) and (r["High"] - r["Low"]) > 0
def is_full(r):   return body(r) >= wick(r) and (r["High"] - r["Low"]) > 0
def is_green(r):  return r["Close"] > r["Open"]
def is_red(r):    return r["Close"] < r["Open"]

# ── Outcome check ──────────────────────────────────────────────────────────────
def signal_date(signal_idx):
    t = df.index[signal_idx]
    return t.astimezone(CDT).date() if hasattr(t, "tzinfo") and t.tzinfo else t.date()

def resolve_outcome(signal_idx, direction, entry, stop_loss, target):
    sig_date = signal_date(signal_idx)
    last_close = None
    last_ts = None
    for j in range(signal_idx + 1, len(df)):
        c = df.iloc[j]
        t = df.index[j]
        candle_date = t.astimezone(CDT).date() if hasattr(t, "tzinfo") and t.tzinfo else t.date()
        # End of day: candle crossed into a new trading day — close at last candle's close
        if candle_date > sig_date:
            eod_price = last_close
            if direction == "LONG":
                return f"Closed EOD   {to_cdt(last_ts)}", round(eod_price - entry, 4)
            else:
                return f"Closed EOD   {to_cdt(last_ts)}", round(entry - eod_price, 4)
        hi, lo = float(c["High"]), float(c["Low"])
        last_close = float(c["Close"])
        last_ts = t
        if direction == "LONG":
            if lo <= stop_loss:
                return f"Stopped Out  {to_cdt(t)}", round(stop_loss - entry, 4)
            if hi >= target:
                return f"Target Hit   {to_cdt(t)}", round(target - entry, 4)
        else:  # SHORT
            if hi >= stop_loss:
                return f"Stopped Out  {to_cdt(t)}", round(entry - stop_loss, 4)
            if lo <= target:
                return f"Target Hit   {to_cdt(t)}", round(entry - target, 4)
    # Still open in last available data
    if last_close is not None:
        if direction == "LONG":
            return f"Closed EOD   {to_cdt(last_ts)}", round(last_close - entry, 4)
        else:
            return f"Closed EOD   {to_cdt(last_ts)}", round(entry - last_close, 4)
    return "Open", None

# ── Pattern detection ──────────────────────────────────────────────────────────
signals = []

for i in range(2, len(df)):
    c1, c2, c3 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
    t3 = df.index[i]

    # Bullish: RED boring → GREEN full → GREEN boring
    if (is_boring(c1) and is_red(c1) and
        is_full(c2)   and is_green(c2) and
        is_boring(c3) and is_green(c3)):
        entry     = round(float(c3["Close"]), 4)
        stop_loss = round(min(float(c1["Low"]), float(c3["Low"])), 4)
        risk      = round(entry - stop_loss, 4)
        if risk <= 0:
            continue
        if not is_past_open_filter(t3):
            continue
        near_result = prev_day_level(t3, entry)
        if near_result is None:
            continue
        near, near_high, near_low = near_result
        # Direction alignment: LONG only near Prev Low
        if not near_low:
            continue
        target = round(entry + 3 * risk, 4)
        outcome, pnl = resolve_outcome(i, "LONG", entry, stop_loss, target)
        signals.append({
            "direction":   "LONG",
            "signal_time": to_cdt(t3),
            "entry":       entry,
            "stop_loss":   stop_loss,
            "target":      target,
            "stop_amt":    risk,
            "target_amt":  round(3 * risk, 4),
            "near":        near,
            "outcome":     outcome,
            "pnl":         pnl,
        })

    # Bearish: GREEN boring → RED full → RED boring
    elif (is_boring(c1) and is_green(c1) and
          is_full(c2)   and is_red(c2) and
          is_boring(c3) and is_red(c3)):
        entry     = round(float(c3["Close"]), 4)
        stop_loss = round(max(float(c1["High"]), float(c3["High"])), 4)
        risk      = round(stop_loss - entry, 4)
        if risk <= 0:
            continue
        if not is_past_open_filter(t3):
            continue
        near_result = prev_day_level(t3, entry)
        if near_result is None:
            continue
        near, near_high, near_low = near_result
        # Direction alignment: SHORT only near Prev High
        if not near_high:
            continue
        target = round(entry - 3 * risk, 4)
        outcome, pnl = resolve_outcome(i, "SHORT", entry, stop_loss, target)
        signals.append({
            "direction":   "SHORT",
            "signal_time": to_cdt(t3),
            "entry":       entry,
            "stop_loss":   stop_loss,
            "target":      target,
            "stop_amt":    risk,
            "target_amt":  round(3 * risk, 4),
            "near":        near,
            "outcome":     outcome,
            "pnl":         pnl,
        })

# ── Output ─────────────────────────────────────────────────────────────────────
long_count  = sum(1 for s in signals if s["direction"] == "LONG")
short_count = sum(1 for s in signals if s["direction"] == "SHORT")

print(f"\n  {ticker} — {interval} candles — Last {days} day(s)  "
      f"({start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')})")
print(f"  {len(df)} candles scanned, {len(signals)} pattern(s) near prev-day H/L "
      f"({long_count} LONG, {short_count} SHORT).\n")

if not signals:
    print("  No Manoj-Trade patterns near previous day high/low in the selected period.")
    print("  Tips: try a longer DAYS window, different interval, or widen PROX_PCT threshold.")
else:
    def fmt_pnl(pnl):
        if pnl is None:
            return "—"
        return f"+{pnl:.4f}" if pnl >= 0 else f"{pnl:.4f}"

    rows = [(str(idx),
             ticker,
             s["direction"],
             s["signal_time"],
             str(s["entry"]),
             str(s["stop_loss"]),
             f"-{s['stop_amt']:.4f}",
             str(s["target"]),
             f"+{s['target_amt']:.4f}",
             s["near"],
             s["outcome"],
             fmt_pnl(s["pnl"]))
            for idx, s in enumerate(signals, 1)]

    headers = ("#", "Ticker", "Direction", "Signal Time (CDT)", "Entry", "Stop", "Stop $", "Target", "Target $", "Near", "Outcome", "P&L")
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

    closed_pnls = [s["pnl"] for s in signals if s["pnl"] is not None]
    total_pnl   = round(sum(closed_pnls), 4)
    wins        = sum(1 for p in closed_pnls if p > 0)
    losses      = sum(1 for p in closed_pnls if p < 0)
    open_count  = sum(1 for s in signals if s["pnl"] is None)

    total_str = f"+{total_pnl:.4f}" if total_pnl >= 0 else f"{total_pnl:.4f}"
    print()
    print(f"  Total P&L   : {total_str}  ({wins} wins, {losses} losses"
          + (f", {open_count} open" if open_count else "") + ")")
    print()
    print(f"  Filters     : entry within {PROX_PCT*100:.1f}% of prev-day H/L  |  LONG near Prev Low only  |  SHORT near Prev High only  |  skip first {OPEN_FILTER_MINS}min after open")
    print("  Risk/Reward : 1:3 minimum on all signals")
    print("  Stop loss   = extreme low/high of candle-1 or candle-3")
    print("  Target      = entry ± 3× risk")
    print("  Outcome     = first level touched after signal; closed at day's last candle if neither level hit (stop checked before target within same candle)")
    print()
    print("  Pattern legend:")
    print("    Red boring → Green full → Green boring  →  LONG  (near Prev Low)")
    print("    Green boring → Red full → Red boring    →  SHORT (near Prev High)")
