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

The skill runs a Python script that downloads OHLC candle data from Yahoo Finance and scans every group of three consecutive candles for the Manoj-Trade pattern. Each signal is printed as a table row with entry, stop, and target prices.

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
  SPY — 1m candles — Last 3 day(s)  (2026-06-25 → 2026-06-28)
  650 candles scanned, 20 pattern(s) found (14 LONG, 6 SHORT).

  ┌────┬────────┬───────────┬──────────────────────┬────────┬────────┬─────────┐
  │ #  │ Ticker │ Direction │ Signal Time (CDT)    │ Entry  │ Stop   │ Target  │
  ...
```

All times are shown in **CDT (Central Daylight Time)**.

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
