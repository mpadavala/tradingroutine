Analyze a stock ticker for the **Manoj-Trade** three-candle pattern to identify entry and exit points.

**Arguments:** `$ARGUMENTS`

## Parse Arguments

Split `$ARGUMENTS` by spaces:
- Position 1 → TICKER (required, e.g. SPY, AAPL)
- Position 2 → INTERVAL (optional, default `1m`)
- Position 3 → DAYS (optional integer, default `5`)

Interval normalization — if a plain number is given, treat it as minutes:
- `1` or `1m` → `1m`
- `3` or `3m` → `3m`
- `5` or `5m` → `5m`
- `15` or `15m` → `15m`
- `60` or `60m` or `1h` → `60m`
- `1day` or `1d` or `day` → `1d`
- `1wk` or `wk` or `week` → `1wk`

## Task

Run the following command using the Bash tool, substituting the parsed values:

```
python3 /Users/Murali/dev/tradingroutine/.claude/scripts/manoj_trade_analysis.py <TICKER> <INTERVAL> <DAYS>
```

Print the full output verbatim — do not summarize, truncate, or reformat it. If there is an error, show it and suggest fixes (wrong ticker, invalid interval, network issue).
