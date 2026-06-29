# Manoj-Trade Strategy Assessment

## Strategy Classification

Mean-reversion, key-level bounce strategy with momentum confirmation. Intraday, rule-based, direction-biased. Systematic version of a discretionary price-action setup.

## Closest Known Strategies

- **Morning Star / Evening Star** — structurally closest. Both use 3-candle reversal (indecision → strong → confirmation). Manoj-Trade is stricter: requires the third candle to also be boring (consolidation), not just any same-direction close.
- **Inside Bar with Breakout** — "boring" candle (body < wick) is a close cousin of the inside bar. Both signal compression/indecision at support/resistance.
- **Previous Day High/Low Fade** — well-documented institutional concept. Manoj-Trade overlays a pattern filter on top of the level rather than trading any touch.
- **VWAP Bounce** — same spirit, different anchor. VWAP uses volume-weighted average price; Manoj-Trade uses prev-day H/L.
- **Opening Range Breakout (ORB)** — opposite philosophy. ORB trades the open breakout; Manoj-Trade explicitly avoids the first 30 minutes.

## Differentiators vs Typical Retail Strategies

| Feature | Manoj-Trade | Typical retail |
|---------|-------------|----------------|
| Entry trigger | 3-candle structural pattern | Single candle or indicator cross |
| Level anchor | Previous day H/L (objective) | VWAP, MAs, Fibonacci (more subjective) |
| Direction filter | Enforced (LONG at Low, SHORT at High) | Often discretionary |
| R/R | Hard minimum 1:3 | Often 1:1 or 1:2 |
| Overnight exposure | None (EOD close enforced) | Common in swing setups |
| Open avoidance | Hard 30-min filter | Rarely enforced systematically |

## Strengths

- 1:3 R/R means only ~25% win rate needed to break even; current results (30–40% on good tickers) exceed that.
- Fully rule-based, no subjectivity.
- Direction-alignment filter was a significant improvement (SPY: -$0.20 → +$4.73).
- Prev-day H/L is an institutional-grade anchor, not an arbitrary indicator.

## Weaknesses / Gaps vs Professional Strategies

- **Sample size** — 5–7 days of 1m data is not statistically significant. Need 2–5 years across market regimes.
- **No volume filter** — a full candle on low volume is much weaker; professional strategies require volume confirmation on the momentum candle.
- **No trend context** — doesn't know if broader market is trending hard. LONG near Prev Low during a downtrend is inherently riskier.
- **Clustering risk** — multiple signals on the same day at the same level (e.g., GOOG #1–5 all SHORTs at Prev High 348.72) concentrates risk rather than diversifying.

## Next Steps to Validate

Run extended backtest across hundreds of trading days and multiple market regimes (trending, choppy, high-VIX). The existing infrastructure makes this straightforward to extend.

Priority improvements:
1. **Volume filter** — require above-average volume on the full (candle-2) momentum candle
2. **Trend context** — only take LONGs when price is above a rolling average, SHORTs below
3. **Extended backtest** — run on 5m data (60-day window) for a statistically meaningful sample
