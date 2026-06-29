# Trading Routine

A Claude Code skill for scanning stocks for the **Manoj-Trade** three-candle pattern.

---

## `/manoj-trade` Skill

### Usage

```
/manoj-trade <TICKER> [INTERVAL] [DAYS]
```

| Argument   | Required | Default | Description                          |
|------------|----------|---------|--------------------------------------|
| `TICKER`   | Yes      | —       | Stock symbol (e.g. `SPY`, `AAPL`)   |
| `INTERVAL` | No       | `1m`    | Candle interval (see table below)    |
| `DAYS`     | No       | `5`     | How many calendar days to look back  |

**Interval options:**

| Input                   | Resolves to |
|-------------------------|-------------|
| `1` or `1m`             | `1m`        |
| `3` or `3m`             | `3m`        |
| `5` or `5m`             | `5m`        |
| `15` or `15m`           | `15m`       |
| `60` or `60m` or `1h`  | `60m`       |
| `day` or `1d` or `1day` | `1d`        |
| `wk` or `1wk` or `week` | `1wk`       |

**Examples:**

```
/manoj-trade SPY
/manoj-trade SPY 5 10
/manoj-trade AAPL 15m 3
/manoj-trade QQQ 1d 30
```

### How it works

The skill runs a Python script that downloads OHLC candle data from Yahoo Finance and scans every group of three consecutive candles for the Manoj-Trade pattern. Signals pass through four filters before appearing in the output:

1. **Proximity to key level** — entry must be within 0.3% of the previous trading day's high or low
2. **Direction alignment** — LONG signals only qualify near Prev Low; SHORT signals only near Prev High
3. **Open filter** — signals within the first 30 minutes after market open (8:30–9:00 CDT) are skipped
4. **Minimum risk** — zero-risk patterns (entry == stop) are discarded

Each qualifying signal is printed as a table row with entry, stop, target, dollar amounts, key level proximity, and outcome.

---

## The Manoj-Trade Pattern

### Pattern definition

The pattern uses three consecutive candles. Each candle is classified as either **boring** or **full**:

- **Boring candle** — body is *smaller* than the total wick (inside-day energy, indecision)
- **Full candle** — body is *greater than or equal to* the total wick (strong directional move)

```
body  = |Close − Open|
wick  = (High − Low) − body
```

### LONG signal

```
Candle-1: Red   + Boring   (sellers losing momentum)
Candle-2: Green + Full     (buyers take over strongly)
Candle-3: Green + Boring   (buyers consolidate — pattern completes)
```

### SHORT signal

```
Candle-1: Green + Boring   (buyers losing momentum)
Candle-2: Red   + Full     (sellers take over strongly)
Candle-3: Red   + Boring   (sellers consolidate — pattern completes)
```

---

## Signal Filters

All four filters must pass for a signal to appear in the output.

### 1. Proximity to previous day high/low (0.3%)

The script fetches the previous trading day's OHLC data and checks whether the entry price is within 0.3% of that day's high or low. Patterns that form away from these key levels are discarded.

```
Near Prev High  if  |entry − prev_high| / prev_high ≤ 0.003
Near Prev Low   if  |entry − prev_low|  / prev_low  ≤ 0.003
```

### 2. Direction alignment

Trades must be taken in the direction the key level supports:

| Signal | Required proximity |
|--------|--------------------|
| LONG   | Near Prev Low only |
| SHORT  | Near Prev High only |

A LONG near Prev High (resistance) or SHORT near Prev Low (support) is filtered out because it is fighting the level rather than bouncing off it.

### 3. Open filter (first 30 minutes)

Signals triggered between 8:30 CDT and 9:00 CDT are skipped. The opening range is the most volatile period of the day and produces disproportionate false breakouts.

### 4. Minimum risk

Signals where `entry == stop` produce zero risk and are discarded.

---

## Stop Loss & Target Calculation

The signal is generated at the **close of candle-3**.

### Entry
```
Entry = Close of candle-3
```

### Stop Loss

**LONG:**
```
Stop = min(candle-1 Low, candle-3 Low)
```
Takes the lower of the two boring candles' lows — the weakest support in the pattern. If price breaks below either boring candle, the pattern is invalidated.

**SHORT:**
```
Stop = max(candle-1 High, candle-3 High)
```
Takes the higher of the two boring candles' highs — the strongest resistance in the pattern. If price breaks above either boring candle, the pattern is invalidated.

### Target (1:3 risk/reward)

Only signals with a positive risk are included. The target is always 3× the risk, giving a minimum 1:3 R/R on every trade.

**LONG:**
```
Risk   = Entry − Stop
Target = Entry + (3 × Risk)
```

**SHORT:**
```
Risk   = Stop − Entry
Target = Entry − (3 × Risk)
```

### Example — SHORT signal

```
Entry  = 733.48   ← close of candle-3
Stop   = 734.28   ← highest High of candle-1 or candle-3
Risk   = 734.28 − 733.48 = 0.80
Target = 733.48 − (3 × 0.80) = 731.08
```

---

## Output

```
  SPY — 1m candles — Last 5 day(s)  (2026-06-23 → 2026-06-28)
  1170 candles scanned, 10 pattern(s) near prev-day H/L (6 LONG, 4 SHORT).

  ┌───┬────────┬───────────┬──────────────────────┬────────┬────────┬─────────┬────────┬──────────┬──────────────────┬───────────────────────────────────┬─────────┐
  │ # │ Ticker │ Direction │ Signal Time (CDT)    │ Entry  │ Stop   │ Stop $  │ Target │ Target $ │ Near             │ Outcome                           │ P&L     │
  ├───┼────────┼───────────┼──────────────────────┼────────┼────────┼─────────┼────────┼──────────┼──────────────────┼───────────────────────────────────┼─────────┤
  │ 1 │ SPY    │ SHORT     │ 2026-06-24 10:32 CDT │ 739.29 │ 739.93 │ -0.6400 │ 737.37 │ +1.9200  │ Prev High 739.63 │ Target Hit   2026-06-24 11:36 CDT │ +1.9200 │
  │ 2 │ SPY    │ LONG      │ 2026-06-24 13:14 CDT │ 732.88 │ 732.55 │ -0.3300 │ 733.87 │ +0.9900  │ Prev Low  732.30 │ Target Hit   2026-06-24 13:19 CDT │ +0.9900 │
  ...

  Total P&L   : +4.7251  (4 wins, 6 losses)

  Filters     : entry within 0.3% of prev-day H/L  |  LONG near Prev Low only  |  SHORT near Prev High only  |  skip first 30min after open
```

All times are shown in **CDT (Central Daylight Time)**.

### Columns

| Column | Description |
|--------|-------------|
| `#` | Signal number |
| `Ticker` | Stock symbol |
| `Direction` | `LONG` or `SHORT` |
| `Signal Time (CDT)` | Timestamp of candle-3 close (when pattern completes) |
| `Entry` | Close price of candle-3 |
| `Stop` | Stop loss price |
| `Stop $` | Dollar risk per share (negative) |
| `Target` | Target price at 3× risk |
| `Target $` | Dollar gain per share if target hit (positive) |
| `Near` | Previous trading day level the entry is near |
| `Outcome` | Result after signal (see below) |
| `P&L` | Realized P&L per share, or `—` if still open |

### Outcome column

| Value | Meaning |
|-------|---------|
| `Target Hit   <timestamp>` | Price reached the 3× target; timestamp is the candle where it was first touched |
| `Stopped Out  <timestamp>` | Price hit the stop loss before the target; timestamp is the candle where it was first touched |
| `Closed EOD   <timestamp>` | Neither level was hit; trade closed at the last candle of the signal day at market price |
| `Open` | Signal is in the most recent candles and data has not yet resolved |

When a single candle touches both the stop and the target, the stop loss is assumed to be hit first (conservative/pessimistic assumption). All trades are closed at end of day — no overnight holds.

---

## Data Source

Yahoo Finance via the `yfinance` Python library. Yahoo Finance caps intraday history:

| Interval | Max lookback |
|----------|-------------|
| `1m`     | 7 days      |
| `5m`     | 60 days     |
| `15m`    | 60 days     |
| `60m`    | 730 days    |

The script auto-adjusts `DAYS` if it exceeds the cap for the chosen interval.
