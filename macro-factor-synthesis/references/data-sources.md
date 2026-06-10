# Macro Tilt — Data Sources Reference

## FRED API
- URL: `https://api.stlouisfed.org/fred/series/observations?series_id={SERIES}&api_key={KEY}&file_type=json`
- Rate limit: 120 req/min
- Key: `bcb3a04759964737cc672555e456ffff` (in config.py)

### Series
| Name | Series ID | Frequency | Notes |
|------|-----------|-----------|-------|
| real_rate | DFII10 | Daily | 10Y TIPS yield |
| net_liq_assets | WALCL | Weekly | Fed total assets ($M) |
| net_liq_tga | WTREGEN | Daily | Treasury General Account ($M) |
| net_liq_rrp | RRPONTSYD | Daily | Overnight RRP ($B) |
| ffr | FEDFUNDS | Daily | Effective Fed Funds Rate |
| global_m2 | M2SL | Monthly | US M2 money stock ($B) |
| hy_oas | BAMLH0A0HYM2 | Daily | ICE BofA HY OAS (%) |
| fci | NFCI | Weekly | Chicago Fed Nat'l FCI |

## YFinance
- Tickers: `^VIX` (CBOE Volatility Index), `DX-Y.NYB` (DXY Dollar Index)
- Resample: W-FRI, last close
- No rate limit concerns for weekly data

## DeFi Llama Stablecoins API (Primary Crypto Source)
- Base URL: `https://stablecoins.llama.fi`
- **No API key required**
- **Rate limit**: ~30 req/min (conservative) — add 1s sleep between USDT and USDC calls

### USDT (`/stablecoin/1`)
Response: 3115 daily points (2017-11 ~ present), ~650KB.
Key field: `tokens[].circulating.peggedUSD` — global circulating supply across ALL chains.

Ethereum-specific: `chainBalances['Ethereum']['tokens'][].circulating.peggedUSD`
TRON-specific: `chainBalances['Tron']['tokens'][].circulating.peggedUSD`
127 total chains tracked.

### USDC (`/stablecoin/2`)
Response: 2829 daily points, ~500KB. Same structure.

### Historical Range (2020-01 ~ 2026-06)
| Coin | Min | Max | Current |
|------|:---:|:---:|:-------:|
| USDT | $2.3B | $187.2B | $186.9B |
| USDC | $1.2B | $76.1B | $76.1B |
| **Total** | **$3.7B** | **$263.3B** | **$263.0B** |

### Verification Against CoinGecko
DeFi Llama total (2026-06-09): $263.0B
CoinGecko total (same date): $262.8B (USDT $186.83B + USDC $75.98B)
**Error: <0.1%** ✅

### Performance Note
Response time: ~3–5s per coin (first call). Cache `crypto_liq.parquet` locally after first fetch.
The `tokens` field inside `chainBalances[chain]` is the same data as the top-level `tokens` — don't double-fetch.

## CoinGecko (Secondary — replaced by DeFi Llama for history)
- **Status**: Replaced. Previously used for history before DeFi Llama discovery.
- Key: `CG-bueNR3Hh5YWUtKi9vPG9oJpp` (demo tier)
- Limit: $365 days history, ~10-50 req/min
- Data: USDT+USDC market_cap_usd from `/coins/{id}/market_chart/range`
- Remaining use: daily incremental append via `crypto_fetch.py --daily` (faster than re-fetching DeFi Llama for a single day)

## TuShare
- Token: `6f13be254a1890150b862ae68dde8d7dd4cd62a36e6049979e9948c2`
- `pro.us_tycr()`: US Treasury yield curve (backup for real_rate)
- `pro.cn_m()`: China M2 (backup for global_m2)

## Bitget (via ccxt)
- Key: saved in `.openclaw/workspace/data/bitget-credentials.json`
- Market data only (no balance permissions)
- `fetch_funding_rate('BTC/USDT:USDT')` — perp funding rate sentiment
- `fetch_open_interest('BTC/USDT:USDT')` — OI for capital flow proxy
