# Bitget Data Sources for Macro Factor Synthesis

## Credentials

| Field | Value |
|-------|-------|
| apiKey | `bg-993ac814ec9272d87b95742e9b256c6b` |
| secret | (stored in `.openclaw/workspace/data/bitget-credentials.json`) |
| passphrase | `Bitget123` |
| File path | `~/.openclaw/workspace/data/bitget-credentials.json` |

**Permissions**: Market data ONLY (balance/trading not enabled). API key returned 40037 on `fetch_balance()`.

## Available Data (all via ccxt)

### Funding Rate (risk bucket — sentiment)
```python
import ccxt
bg = ccxt.bitget({
    'apiKey': '...', 'secret': '...', 'password': '...'
})

# Real-time
fr = bg.fetch_funding_rate('BTC/USDT:USDT')
print(fr['fundingRate'])  # e.g. +0.0049%

# 7-day history (1h bars)
fr_h = bg.fetch_funding_rate_history('BTC/USDT:USDT', limit=168)
rates = [r['fundingRate'] for r in fr_h]
```

**Direction**: -1 (↑funding = longs crowded = bearish)

**Typical range**: BTC funding -0.0107% ~ +0.0100% (as of 2026-06). Extreme values >p95 or <p5 signal crowded positioning.

### Open Interest (risk or crypto_liq bucket — positioning)
```python
oi = bg.fetch_open_interest('BTC/USDT:USDT')
# openInterestAmount: 31264 (BTC count)
# openInterestValue: None on Bitget ccxt mapping (use amount * price instead)
```

**Typical values** (2026-06):
- BTC: 31,264 coins (~$2B)
- ETH: 708,678 coins

**Direction**: Context-dependent. ↑OI + ↑price = new longs (bullish). ↑OI + ↓price = new shorts (bearish). Best used as ΔOI% over 1d/7d.

### Ticker (for price context)
```python
t = bg.fetch_ticker('BTC/USDT')
print(t['last'], t['quoteVolume'])
```

## V2 REST API Notes

ccxt handles V2 routing internally. Direct REST for reference:

```python
import requests
base = 'https://api.bitget.com'

# Ticker (V2)
r = requests.get(f'{base}/api/v2/spot/market/tickers?symbol=BTCUSDT')

# OI (V2)
r = requests.get(f'{base}/api/v2/mix/market/open-interest?symbol=BTCUSDT&productType=USDT-FUTURES')
```

V1 endpoints (`/api/spot/v1/...`) are decommissioned (code 30032).

## Limitations

| Limitation | Detail |
|------------|--------|
| No exchange balance | Single-CEX BTC balance ≠ global aggregate. Need Glassnode/CryptoQuant. |
| No long/short ratio | Bitget public API doesn't expose this on free tier. |
| OI value unavailable | `openInterestValue` returns None in ccxt Bitget mapping. Use `amount × price` instead. |
| Funding history limited | Only recent data. No multi-year historical backfill via ccxt. |

## Integration Notes

- Funding rate + OI are **not yet wired** into the production pipeline. They're documented as pending indicators for future integration.
- Both are fast-moving (1h granularity) unlike the weekly-level macro indicators. Consider a different EWM halflife (1-2 weeks) if added.
- The API key is shared between macro pipeline and Bitget trading — avoid conflicting rate limits.
