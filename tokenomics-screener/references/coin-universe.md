# Coin Universe & CoinGecko ID Mapping

27 coins across 8 categories. CoinGecko IDs used for `/api/v3/coins/markets` queries.

## Layer 1 (10)

| Symbol | CoinGecko ID | Notes |
|--------|-------------|-------|
| BTC | bitcoin | Store of value |
| ETH | ethereum | Smart contract platform |
| SOL | solana | High-performance L1 |
| ADA | cardano | Research-driven L1 |
| AVAX | avalanche-2 | Subnet architecture |
| DOT | polkadot | Interoperability |
| NEAR | near | AI-compatible L1 |
| TRX | tron | Stablecoin ecosystem |
| SUI | sui | Move-based new L1 |
| TON | the-open-network | Telegram-integrated |
| ATOM | cosmos | Cosmos hub |
| APT | aptos | Move-based L1 |

## Layer 2 / Scaling (3)

| Symbol | CoinGecko ID | Notes |
|--------|-------------|-------|
| ARB | arbitrum | Ethereum optimistic rollup |
| OP | optimism | Ethereum optimistic rollup |
| POL | matic-network | Polygon (MATIC→POL migration) |

## DeFi / Infrastructure (3)

| Symbol | CoinGecko ID | Notes |
|--------|-------------|-------|
| UNI | uniswap | DEX protocol |
| AAVE | aave | Lending protocol |
| LINK | chainlink | Oracle network |

## Meme (2)

| Symbol | CoinGecko ID | Notes |
|--------|-------------|-------|
| DOGE | dogecoin | Original meme coin |
| SHIB | shiba-inu | ERC-20 meme token |

## AI / Compute (2)

| Symbol | CoinGecko ID | Notes |
|--------|-------------|-------|
| FET | fetch-ai | AI agent framework |
| RENDER | render-token | GPU compute network |

## Gaming / Metaverse (2)

| Symbol | CoinGecko ID | Notes |
|--------|-------------|-------|
| IMX | immutable-x | Gaming L2 |
| SAND | the-sandbox | Metaverse platform |

## Payment / Enterprise (2)

| Symbol | CoinGecko ID | Notes |
|--------|-------------|-------|
| XRP | ripple | Enterprise payments |
| LTC | litecoin | Legacy payments |

## Exchange Token (1)

| Symbol | CoinGecko ID | Notes |
|--------|-------------|-------|
| BNB | binancecoin | Binance ecosystem |

## Known Data Gaps

- **POL (matic-network)**: CoinGecko `market_cap` returns 0 after MATIC→POL migration. MCap-based scores are unreliable.
- **MKR**: Delisted from OKX spot market. Not included in default universe.
- **FET**: No perpetual swap funding rate data on OKX. Funding score falls to mid-range.
