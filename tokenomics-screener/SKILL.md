---
name: tokenomics-screener
description: "Screens 27 major crypto coins across 8 tokenomics dimensions (market cap, FDV/dilution risk, circulation maturity, liquidity, volatility, funding sentiment, trend, ATH recovery) and ranks them with a composite score. Uses OKX real-time market data + CoinGecko supply data. Generates a ranked report and pushes it to Feishu. Use when the user asks to screen coins, rank tokens, evaluate tokenomics, check FDV or dilution risk, find top coins, run a coin screener, compare crypto fundamentals, or do supply analysis — especially if they mention market cap, fully diluted valuation, max supply, or circulating supply."
license: MIT
metadata:
  version: "2.1.0"
  requires:
    bins: ["okx"]
    packages: []
---

# Tokenomics Screener V2

Multi-dimension coin screening combining real-time market data (OKX) with on-chain supply data (CoinGecko).

## Quick Run

```bash
export HOME=$(echo ~) 2>/dev/null || export HOME=/root
python3 ~/.hermes/scripts/tokenomics_screener.py --feishu
```

Script: `~/.hermes/scripts/tokenomics_screener.py`
Output: JSON at `/tmp/hermes_analysis/tokenomics_v2_scored.json` + Feishu doc

## Verification Checklist

After running, verify ALL of these before considering the task done:

- [ ] Script exit code is 0 (no crashes)
- [ ] Output shows "✅ Done." at the end
- [ ] JSON file exists and has 27 entries: `python3 -c "import json; print(len(json.load(open('/tmp/hermes_analysis/tokenomics_v2_scored.json'))))"`
- [ ] Top 3 coins have composite ≥ 60 (healthy market conditions) or note market weakness
- [ ] Feishu doc URL is printed and accessible
- [ ] No coin has `market_cap: 0` except POL (known CoinGecko data gap)
- [ ] Dilution risk table has SUI, IMX, OP flagged (known high-FDV coins)

If any check fails, re-run the script. If same failure repeats, check:
- OKX CLI: `okx market ticker BTC-USDT` (should return data)
- CoinGecko: `python3 -c "import urllib.request,json; print(json.loads(urllib.request.urlopen('https://api.coingecko.com/api/v3/ping').read()))"` (should return `{"gecko_says": "(V3) To the Moon!"}`)
- lark-cli: `lark-cli doctor` (should pass)

## Dimensions (8-factor)

| # | Dimension | Weight | Source | Metric |
|---|-----------|--------|--------|--------|
| 1 | Market Cap | 15% | CoinGecko | log(market_cap), size stability |
| 2 | FDV/Dilution | 15% | CoinGecko | 1 / FDV_MCap ratio (lower dilution = higher score) |
| 3 | Circulation Maturity | 10% | CoinGecko | circulating / max_supply % |
| 4 | Liquidity Depth | 15% | OKX | 24h_volume / market_cap |
| 5 | Volatility | 10% | OKX | 1 / 24h_range_pct |
| 6 | Funding Sentiment | 10% | OKX | funding_rate (higher = long dominance) |
| 7 | Multi-TF Trend | 15% | Both | avg(3d_change, 7d_change) |
| 8 | ATH Recovery | 10% | CoinGecko | 1 / ath_drawdown_pct |

All dimensions MinMax-normalized to 0-100. See `references/methodology.md` for scoring details and edge cases.

## Data Sources

1. **OKX Agent Trade Kit** (`okx-trade-cli`): market tickers, funding rates, candles
   - Install: `npm install -g @okx_ai/okx-trade-cli@1.3.2`
   - No API key needed for market data

2. **CoinGecko Public API**: market cap, FDV, supply data
   - Endpoint: `/api/v3/coins/markets?vs_currency=usd&ids=...`
   - No API key, use Python `urllib` with SSL context (blocks curl from some hosts)

## Coin Universe

27 coins across categories — see `references/coin-universe.md` for full list with CoinGecko ID mappings.

## Feishu Delivery

Uses `lark-cli docs +create --markdown`. Requires bound credentials:
```bash
lark-cli config bind --source hermes --identity bot-only
```

## Pitfalls

- CoinGecko `current_price` / `price_change_percentage_*` can be `None` — always use `or` fallback
- OKX candles return list-of-lists (not dicts): `[ts, open, high, low, close, vol, volCcy, volCcyQuote, confirm]`
- MKR delisted from OKX spot; POL CoinGecko market cap returns 0
- lark-cli needs `HOME` in env; script auto-detects home directory
- lark-cli `--markdown @file` requires a **relative path** from cwd

## Cron Usage

```bash
cronjob create \
  --prompt "Run tokenomics screener with verification: python3 ~/.hermes/scripts/tokenomics_screener.py --feishu" \
  --schedule "0 10 * * *" \
  --deliver feishu:<chat_id> \
  --skills tokenomics-screener
```
