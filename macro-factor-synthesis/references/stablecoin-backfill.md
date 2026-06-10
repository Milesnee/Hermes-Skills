# DeFi Llama Stablecoin Backfill — 2352 Days of USDT+USDC

## Why DeFi Llama

| Source | History | Cost | Coverage | State |
|--------|:------:|:----:|:--------:|:-----:|
| CoinGecko (free) | 365 days | Free (10 req/min) | ETH only | ❌ Replaced |
| CoinGecko (Analyst) | Unlimited | $79/mo | ETH only | ❌ Too expensive |
| CoinPaprika | 365 days | Free | Multi-chain | ❌ Paywalled |
| Messari | 365 days | Free | Multi-chain | ❌ Paywalled |
| **DeFi Llama** | **2017→今** | **Free, no key** | **All chains** | ✅ **Winner** |

## API Endpoints

```
GET https://stablecoins.llama.fi/stablecoin/1  → USDT (Tether)
GET https://stablecoins.llama.fi/stablecoin/2  → USDC (Circle)
```

Response structure:
```json
{
  "tokens": [
    {
      "date": 1577836800,            // unix timestamp
      "circulating": {
        "peggedUSD": 3700000000      // global circulating supply in USD
      }
    },
    // ... one entry per day
  ],
  "chainBalances": {
    "Ethereum": { "tokens": [...] },
    "Tron": { "tokens": [...] },
    "Solana": { "tokens": [...] },
    "BNB Chain": { "tokens": [...] },
    // ... other chains
  }
}
```

Key observations:
- `tokens` array at the top level contains **aggregated global** circulating supply across ALL chains
- Each entry is daily resolution (1 day granularity)
- Response size: ~650KB (USDT) + ~500KB (USDC)
- No pagination needed — returns all history in one call
- Rate limit: ~1 req/sec (not documented but safe)

## Backfill Results

| Metric | Value |
|--------|:-----:|
| Date range | 2020-01-01 ~ 2026-06-09 |
| Daily points | **2,352** |
| Min supply | $3.7B (Jan 2020) |
| Max supply | $268.2B (early 2026) |
| Latest | $263.0B |
| Growth | **71×** (2020→2026) |

## Weekly Aggregation

```python
s = df['total_stablecoin_mcap'].resample('W-FRI').last().dropna()
# Results: 337 weekly points matching the pipeline's weekly grid
```

## Daily Append (Cron)

```bash
# Job: crypto-liq-daily-append (40092561267b)
# Schedule: Daily 06:00 UTC
python3 ~/workspace/macro_tilt_pipeline/crypto_fetch.py --daily
```

- Fetches current USDT+USDC mcap via `/stablecoin/{id}` endpoint
- Appends to `crypto_liq.parquet` (idempotent — skips if date exists)
- Also saves `crypto_liq.csv` for easy inspection

## Data Files

```
~/data/macro_tilt/
  crypto_liq.parquet   ← Production: 2352 rows, daily frequency
  crypto_liq.csv       ← Same data in CSV (for quick checks)
```

## Historical Coverage Assessment

| Period | Stablecoin Supply | Quality |
|--------|:----------------:|:-------:|
| 2020 | $3.7B~$21B | ✅ Full, covers early bull market |
| 2021 | $21B~$143B | ✅ Covers DeFi summer peak |
| 2022 | $143B~$153B (LUNA dip to $130B) | ✅ Captures Terra collapse |
| 2023 | $130B~$143B | ✅ Crypto winter stabilization |
| 2024 | $143B~$195B | ✅ ETF-driven inflow |
| 2025 | $195B~$268B | ✅ All-time highs |
| 2026 (YTD) | $268B→$263B | ✅ Current (ongoing daily append) |

## DeFi Llama Coverage by Chain

The `tokens` field aggregates across ALL chains. The raw breakdown is in `chainBalances`:

| Chain | USDT | USDC | Notes |
|-------|:---:|:----:|-------|
| Ethereum | ~50% | ~70% | Primary for USDC |
| Tron (TRC-20) | ~45% | ~5% | Primary for USDT |
| Solana | ~2% | ~10% | Growing |
| BNB Chain | ~2% | ~5% | Stable |
| Others | ~1% | ~10% | Polygon, Avalanche, etc. |

**Important:** DeFi Llama's global `circulating.peggedUSD` already includes ALL chains. No need to sum per-chain data — the top-level `tokens[].circulating` is **global aggregate**.

## Why Not CoinGecko

Previous CoinGecko implementation tried:
1. `/coins/tether` — current mcap only, no history
2. `/coins/tether/market_chart?days=1825` — 401 without API key
3. `/coins/tether/history?date=2021-01-01` — 401 without API key
4. `/simple/price?ids=tether,usd-coin&vs_currencies=usd&include_market_cap=true` — current only

The demo key (`CG-*` prefix) is rate-limited to 10-50 req/min and only allows 365-day lookback on `/market_chart/range`. Even the $79/mo Analyst tier only adds higher rate limits — full history requires Enterprise ($80k/yr).
