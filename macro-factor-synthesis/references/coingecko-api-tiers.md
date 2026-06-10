# CoinGecko API Tiers — What Each Level Unlocks

This documents what a "CG-" demo API key can and cannot do for crypto liquidity data fetching. Useful reference when a user provides a CoinGecko API key or asks why full history isn't available.

## Key Insight

A **CG-prefixed demo API key** (free registration) provides the same endpoint access as the public free tier — it only increases the rate limit. It does NOT unlock any paid-only endpoints.

## Capabilities By Endpoint

### `GET /coins/{id}` — Current snapshot
- **Free**: ✅ Works
- **Demo (CG-)**: ✅ Works
- **Paid**: ✅ Works
- Returns: current market data including `market_data.market_cap.usd`

### `GET /coins/{id}/market_chart?days=365`
- **Free**: ✅ Works (366 daily points)
- **Demo (CG-)**: ✅ Works
- **Paid**: ✅ Works
- Key constraint: **Hard 365-day lookback limit**. `days=365` gives data starting exactly 365 days before today. Cannot fetch "365 days ago from 2023" — always relative to now.

### `GET /coins/{id}/market_chart?days=max`
- **Free**: ❌ Returns empty/401
- **Demo (CG-)**: ❌ Still returns 401
- **Paid**: ✅ Works. Returns all available history (since coin inception).

### `GET /coins/{id}/market_chart/range?from={ts}&to={ts}`
- **Free**: ❌ Returns 401
- **Demo (CG-)**: ❌ Returns 401
- **Paid**: ✅ Works. Can fetch arbitrary historical ranges.

### `GET /coins/{id}/history?date=DD-MM-YYYY`
- **Free**: ❌ Returns 401 (deprecated as of ~2025)
- **Demo (CG-)**: ❌ Still 401
- **Paid**: ✅ May work

### `GET /global`
- **Free**: ✅ Works (current snapshot only)
- **Demo (CG-)**: ✅ Works
- **Paid**: ✅ Works
- Returns: total crypto mcap, BTC dominance, volume, etc. **No historical endpoint**.

## Rate Limits

| Tier | Calls/Min | Notes |
|------|-----------|-------|
| Public (no key) | 10-30 | Often 429s under any moderate load |
| Demo (CG- key) | 50 | Reliable for 1-2 sequential calls with 1s sleep |
| Paid (Pro) | 500+ | Depends on plan |

## Practical Strategy

Given these constraints, the production pipeline uses a **hybrid approach**:

1. **Initial backfill**: `days=365` gives 366 daily points. This covers ~1 year.
2. **Daily append**: Cron at 06:00 UTC appends current USDT+USDC mcap via `/coins/{id}`.
3. **Full history gap**: Data before ~12 months ago is unreachable. For crypto_liq bucket, this means the indicator only activates from ~June 2025 onwards.
4. **Weight redistribution**: Pre-crypto_liq rows keep usd_liq + risk buckets active. crypto_liq weight redistributes proportionally.

## Alternative Sources (for full history)

If full stablecoin history is essential:

| Source | Access | Notes |
|--------|--------|-------|
| **CoinGecko Pro** | Paid (starts ~$79/mo) | Full `days=max` and `/range` |
| **DefiLlama** | Free API | `https://api.llama.fi/stablecoin/total` — but endpoint unstable/empty in tests |
| **Tether Transparency** | Web | SPA with JS-rendered data — no easy scrape |
| **CoinMetrics** | Free community tier | Deprecated v2, new v4 requires key |
| **CryptoCompare** | Free | `/blockchain/histo/day` — historical data limited |
| **The Block** | Mixed | Some free endpoints, mostly paid |

## Implementation Pattern

```python
CG_API_KEY = 'CG-xxxx...'  # Demo key — rate limit increase only
HEADERS = {'x-cg-demo-api-key': CG_API_KEY}

# ✅ Stablecoin daily append
r = requests.get(f'{BASE}/coins/tether?localization=false&tickers=false', headers=HEADERS)
mcap = r.json()['market_data']['market_cap']['usd']

# ✅ 365-day history
r = requests.get(f'{BASE}/coins/tether/market_chart?vs_currency=usd&days=365', headers=HEADERS)
pts = r.json()['market_caps']  # 366 points

# ❌ Won't work even with key
r = requests.get(f'{BASE}/coins/tether/market_chart?days=max', headers=HEADERS)
print(r.status_code)  # 401
```

## Related

- See `data-sources.md` for full data source mapping (FRED, YFinance, TuShare)
- See `scripts/crypto_fetch.py` for the actual implementation
