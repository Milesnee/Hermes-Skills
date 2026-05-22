# Scoring Methodology

## Normalization

All raw metrics are MinMax-normalized to a 0-100 scale:

```
score = (value - min) / (max - min) * 100
```

For inverse dimensions (lower = better, e.g., volatility, dilution), the score is reversed:

```
score = 100 - (value - min) / (max - min) * 100
```

When all values are identical (max == min), every coin gets 50.0 (neutral).

## Dimension Details

### 1. Market Cap (15%)
- Raw: `log10(market_cap_usd)`
- Log scale prevents BTC/ETH from dominating the scoring distribution
- A coin with $1B MCap (~9.0 log) vs $10B (~10.0 log) differs by ~11 points

### 2. FDV/Dilution (15%)
- Raw: `FDV / MarketCap` ratio
- Inverse scoring: lower ratio = higher score
- Ratio 1.0 = fully diluted, no future unlock pressure
- Ratio 2.5 = 60% supply still locked (high dilution risk)
- Coins with FDV == MCap get ratio 1.0 (no data = assume no dilution)

### 3. Circulation Maturity (10%)
- Raw: `circulating_supply / max_supply * 100`
- When max_supply is null (no cap), assume 100% — the coin has no supply ceiling
- Higher % = more supply already in market = less future sell pressure

### 4. Liquidity Depth (15%)
- Raw: `24h_volume_usd / market_cap_usd`
- Measures how much of the market cap trades daily
- BTC typically 0.02-0.05% (low turnover, deep liquidity)
- Low-cap coins can reach 5-20% (high turnover, thinner books)

### 5. Volatility (10%)
- Raw: `(24h_high - 24h_low) / current_price * 100`
- Inverse scoring: lower volatility = higher score
- Typical range: 1-5% for large caps, 5-15% for small caps

### 6. Funding Sentiment (10%)
- Raw: perpetual swap funding rate (from OKX)
- Positive rate = longs pay shorts = bullish bias
- Most coins cluster at +0.01% (OKX cap); negative rates signal bearish
- Missing funding data (FET) gets 0 → mid-range score after normalization

### 7. Multi-Timeframe Trend (15%)
- Raw: `(3d_change_pct + 7d_change_pct) / 2`
- Averages short and medium-term momentum
- Prevents single-day spikes from dominating

### 8. ATH Recovery (10%)
- Raw: `(1 - current_price / ath) * 100` = drawdown from ATH
- Inverse scoring: smaller drawdown = higher score
- BTC at 38% drawdown = 62 score; SAND at 99% = 1 score

## Edge Cases

- **POL (Polygon)**: CoinGecko returns market_cap=0. Excluded from MCap-based scoring but still appears in rankings. Weight redistributed to other dimensions.
- **MKR**: Delisted from OKX spot. Not in default coin universe.
- **FET**: OKX swap market has no funding rate data. Funding score gets 0 raw → normalized to mid-range.
- **Stablecoins** (USDT/USDC): Excluded — tokenomics scoring doesn't apply.
