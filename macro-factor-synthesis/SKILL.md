---
name: macro-factor-synthesis
description: Synthesize 10+ macro indicators into a single directional tilt signal [-1, +1] for crypto/risk assets. 3-bucket architecture (USD liquidity / crypto liquidity / risk appetite), robust z-scores (median+MAD), tanh clamping, correlation modulation, EWM smoothing, dead zone thresholding. Real data pipeline using FRED API + YFinance + DeFi Llama + TuShare. Active production cron daily 22:00 UTC.
tags:
  - macro
  - crypto
  - factor-model
  - signal-generation
  - trading-system
related_skills:
  - macro-monitoring-dashboard
  - trading-signal
---

# Macro Factor Synthesis — Tilt Index

## When to Use
- User asks to build a macro scoring framework for crypto/risk assets
- User wants a composite macro tilt signal as a position-size multiplier (not an entry signal)
- User mentions "宏观倾斜", "因子合成", "tilt index", "方向乘子"
- You need to validate a multi-factor framework before wiring real data
- User provides a FRED API key or asks about crypto liquidity data sources
- Debugging tilt output: check for future dates, z-score collapse on monthly data, or stale cron

## Architecture

### 3 Bucket Design (v2.5 — Daily frequency + NATIVE_FREQ for monthly/weekly indicators)

**Production weight profile (v2.5, activated 2026-06-09):**
| Bucket | Weight | Indicators | Rationale |
|--------|-------:|------------|-----------|
| **usd_liq** | **40%** | real_rate, net_liq, dxy, ffr, global_m2 | Dollar liquidity is the primary tide |
| **crypto_liq** | **35%** | stablecoin_mcap (USDT+USDC) | Crypto-native liquidity. Single indicator — lower weight reduces single-indicator noise |
| **risk** | **25%** | vix, hy_oas, **hyg_price**, fci | Risk appetite drives marginal capital flows. HYG price added as credit proxy covering 2020+ (FRED hy_oas only starts 2023) |

### Signal Chain
```
raw indicators → per-indicator rolling robust z-score (median+MAD) →
  tanh[-1,1] → direction mapping → per-bucket mean (skipna, NaN→0) →
  correlation modulation → weighted sum → EWM(halflife=28 days) →
  dead zone(0.2) → final tilt[-1,+1]
```

**Daily frequency (FREQ='D'):** All indicators resampled to daily grid. Low-frequency indicators (ffr: monthly, global_m2: monthly, net_liq: weekly, fci: weekly) compute z-scores at their NATIVE frequency before upsampling to daily — prevents ffill duplicate values from collapsing the rolling z-score to zero.

### NATIVE_FREQ System (v2.5 Critical Fix)

When switching from weekly to daily frequency, monthly indicators (ffr, global_m2) would produce 30× repeated values via ffill. The 365-day rolling window would see 12 unique values repeated 30 times — median = repeated value, MAD ≈ 0, z-score = 0. **Complete signal collapse.**

**Fix:** Compute z-scores at native frequency first, then upsample z-scores (not raw data) to daily grid:
```python
NATIVE_FREQ = {
    'net_liq': 'W',       # 52-week rolling z-score
    'fci': 'W',           # 52-week rolling z-score
    'ffr': 'M',           # 12-month rolling z-score
    'global_m2': 'M',     # 12-month rolling z-score
}
```

In `build_indicator_df`, low-frequency indicators get `_z` suffix columns (pre-computed z-scores). In `compute_tilt`, columns with `_z` suffix skip the `rolling_robust_zscore` call and directly apply `tanh * direction`.

**Before/after:**
| Indicator | Before (daily without NATIVE_FREQ) | After (with NATIVE_FREQ) |
|-----------|:----------------------------------:|:------------------------:|
| ffr | 0.0000 (collapsed!) | **+0.7740** ✅ (rate cuts detected) |
| global_m2 | 0.0000 (collapsed!) | **+0.9893** ✅ (M2 growth detected) |
| net_liq | 0.0000 (collapsed!) | **+0.3314** ✅ (liquidity expansion) |
| stablecoin_mcap | -1.0000 | -1.0000 (ok, daily data) |
| vix | -0.7592 | -0.7490 (ok, daily data) |

### Key Design Decision: Per-Bucket NaN Handling
**Do NOT use `df.dropna()`** — this destroys data when crypto_liq has partial history.

Instead:
- Each indicator gets its z-score from ALL its non-NaN data
- Each bucket uses `mean(skipna=True)` — rows without crypto data just get 0 for that bucket
- Missing buckets have their weight redistributed proportionally to active buckets
- Result: 2352 daily rows preserved (vs 158 with global dropna)

### Indicator Direction Mapping
| Indicator | Dir | Meaning |
|-----------|-----|---------|
| real_rate | -1 | ↑real yield = tightening = bearish |
| net_liq | +1 | ↑liquidity = easing = bullish |
| dxy | -1 | ↑DXY = dollar strength = bearish |
| ffr | -1 | ↑rates = tightening = bearish |
| global_m2 | +1 | ↑global M2 = easing = bullish |
| stablecoin_mcap | +1 | ↑stablecoin = capital inflow = bullish |
| vix | -1 | ↑VIX = fear = bearish |
| hy_oas | -1 | ↑credit spreads = stress = bearish |
| **hyg_price** | **-1** | **↑HYG = risk-on = bearish for tilt (credit proxy)** |
| fci | -1 | ↑FCI = tightening = bearish |

### Ex_btc_balance (reserved)
Direction: -1 (↑exchange balance = selling pressure = bearish). Requires Glassnode/CryptoQuant (paid). When available, add to crypto_liq bucket. Adjust weight to: usd_liq 25%, crypto_liq 45%, risk 30%.

### Pending Indicators (via Bitget API key)

**funding_rate (risk bucket, direction: -1)**
↑funding rate = longs crowded = bearish. Available via any CEX with perpetual futures (Bitget key on file). BTC and ETH funding rates fetchable via ccxt. Full 7-day history at 1h resolution.

**open_interest (risk bucket or crypto_liq bucket)**
↑OI = more capital at risk = bullish in uptrend, bearish in downtrend. Works best as change-based indicator (ΔOI%). Available via ccxt. Bitget OI as of 2026-06: BTC 31,264 (≈$2B), ETH 708,678.

Integration pattern:
```python
import ccxt
bg = ccxt.bitget()
fr = bg.fetch_funding_rate('BTC/USDT:USDT')
oi = bg.fetch_open_interest('BTC/USDT:USDT')
```
See `references/bitget-data-sources.md` for full API detail.

### ⚠️ Weighted Indicator Scoring — global_m2 Double Counting

**Critical fix:** `global_m2` (global M2 in USD) and `dxy` both embed the USD exchange rate effect. A stronger USD suppresses the USD value of foreign M2 while also showing as a higher DXY — the same signal counted twice.

**Fix:** Use `INDICATOR_WEIGHTS` to give `global_m2` a near-zero weight:
```python
INDICATOR_WEIGHTS = {'global_m2': 0.05}  # → 0.05/4.05 = 1.2% of usd_liq bucket
```

**Before/after effect:**
| Metric | Before (uniform) | After (global_m2=0.05) |
|--------|:----------------:|:----------------------:|
| Autocorr(1w) | 0.94 | 0.78 |
| Mild Bear | 0% | 3% |
| usd_liq bucket | +0.0 (masked by M2) | −0.30 (true bearish) |
| Bucket interpretability | Poor | Clean |

## Production Pipeline

### File Layout
```
~/workspace/macro_tilt_pipeline/
  config.py               — Indicator registry, direction mapping, weights, FRED_API_KEY
  macro_tilt_pipeline.py  — Main ETL: FRED API + YFinance + DeFi Llama + TuShare
  crypto_fetch.py         — Standalone crypto_liq fetcher (daily append + history)
  tilt_multiplier.py      — Contrarian multiplier functions (4 presets)
  tilt_signal.py          — Real-time integration: import → get_multiplier()
  macro_tilt_backtest.py  — Formal backtest against SPY/ETH
```

### Running the Pipeline
```bash
# Full run (FRED API + YFinance + DeFi Llama + TuShare)
cd ~/workspace/macro_tilt_pipeline && python3 macro_tilt_pipeline.py

# Output: ~/data/macro_tilt/macro_tilt_score.json (latest snapshot)
#         ~/data/macro_tilt/tilt_history.csv (full history, appended daily)
```

### Cron Jobs
| Cron | Schedule | Job ID | Purpose |
|------|----------|--------|---------|
| `macro-tilt-index-daily` | **Daily 22:00 UTC** | `d1dbe77776b3` | Full pipeline run (was weekly, changed 2026-06-09) |
| `crypto-liq-daily-append` | Daily 06:00 UTC | `40092561267b` | Append stablecoin mcap |

### ⚠️ Date Bug — Never Output Future Dates

**Critical (fixed 2026-06-09):** The pipeline used `pd.date_range(all_dates[0], all_dates[-1], freq='W-FRI')` which extended to the NEXT future Friday. If today is Tuesday (2026-06-09), the latest data point is 2026-06-09, the next Friday is 2026-06-12 — but this date hasn't happened yet. Pipeline output showed tilt for 2026-06-12, three days in the future.

**Fix:** Filter the grid to `<= today`:
```python
today = pd.Timestamp.now().normalize()
daily_grid = daily_grid[daily_grid <= today]
```

This ensures the tilt signal always reports the latest COMPLETE trading day, never a future date.

### Crypto Liquidity Data

- **Stablecoin mcap (USDT+USDC)**: **DeFi Llama Stablecoins API** (`stablecoins.llama.fi/stablecoin/1` for USDT, `/stablecoin/2` for USDC). FREE, no API key required. Covers 2017–present.
- **Daily append**: `crypto_fetch.py --daily` fetches current data and appends to `crypto_liq.parquet`.
- **Historical backfill**: `crypto_fetch.py --history` fetches the full DeFi Llama history (2020-present) in one go.
- ~~**CoinGecko**: Previously the primary source. Now replaced by DeFi Llama.~~
- **BTC exchange balance**: NOT available on free tier (Glassnode/CryptoQuant paid).

### Real-Time Integration (tilt_signal.py)

`tilt_signal.py` is a zero-dependency module for any strategy to import and get the contrarian multiplier:

```python
from tilt_signal import get_multiplier
mult, tilt, label, date = get_multiplier(method='balanced')
# mult=1.0 → regular position
# mult=0.53 → cut to 53% position
# mult=1.67 → increase to 167% position
```

Features:
- **Zero external dependencies** — pure stdlib + JSON
- **Stale data protection** — ≥14 days old → returns 1.0x (no interference)
- **Environment override** — `TILT_DATA_PATH` env var for custom JSON path
- **Methods**: conservative (0.5–1.5x), balanced (0.5–2.0x), aggressive (0.25–3.0x), scaled (continuous 0.3–2.5x)
- **Deadband**: |tilt| < 0.2 → 1.0x (no position adjustment)

The pipeline already writes `contrarian_multiplier` values (4 presets) to the JSON output, so `tilt_signal.py` is just a wrapper. Strategies can also read the JSON directly.

## Production Config (config.py, v2.5)

```python
FRED_API_KEY = 'bcb3a04759964737cc672555e456ffff'

DIRECTION = {
    'real_rate': -1, 'net_liq': 1, 'dxy': -1, 'ffr': -1, 'global_m2': 1,
    'stablecoin_mcap': 1, 'vix': -1, 'hy_oas': -1, 'hyg_price': -1, 'fci': -1,
}

BUCKETS = {
    'usd_liq': ['real_rate', 'net_liq', 'dxy', 'ffr', 'global_m2'],
    'crypto_liq': ['stablecoin_mcap'],
    'risk': ['vix', 'hy_oas', 'hyg_price', 'fci'],
}
BUCKET_WEIGHTS = {'usd_liq': 0.40, 'crypto_liq': 0.35, 'risk': 0.25}
INDICATOR_WEIGHTS = {'global_m2': 0.05}

# Daily frequency (v2.5)
FREQ = 'D'               # Resample frequency: D=daily, was W-FRI
HALFLIFE = 28            # EWM halflife in days (was 4 weeks)
DEAD_ZONE = 0.2
START_DATE = '2020-01-01'
ZSCORE_WINDOW = 365      # Rolling window in days (was 52 weeks)
ZSCORE_MIN_PERIODS = 182 # Min periods (was 26 weeks)

# v2.5: Native frequency for low-freq indicators
NATIVE_FREQ = {
    'net_liq': 'W',      # Weekly: 52-week rolling z-score
    'fci': 'W',          # Weekly: 52-week rolling z-score
    'ffr': 'M',          # Monthly: 12-month rolling z-score
    'global_m2': 'M',    # Monthly: 12-month rolling z-score
}
```

## Scoring Engine (core pattern)

```python
from scipy.stats import median_abs_deviation

def rolling_robust_zscore(series, window=365, min_periods=182):
    def _z(arr):
        x = arr[~np.isnan(arr)]
        if len(x) < min_periods:
            return np.nan
        med = np.median(x)
        mad = median_abs_deviation(x, nan_policy='omit')
        return (x[-1] - med) / (mad + 1e-10)
    return series.rolling(window=window, min_periods=min_periods).apply(_z, raw=True)

# Pre-computed z-scores (_z suffix) skip robust_zscore → direct tanh*direction
# Daily-data indicators use rolling_robust_zscore as above
for col in df.columns:
    if col.endswith('_z'):
        scores_full[col_base] = np.tanh(df[col].fillna(0.0)) * DIRECTION[col_base]
        continue
    valid = df[col].dropna()
    z = rolling_robust_zscore(valid) if len(valid) >= ZSCORE_MIN_PERIODS else ...
```

## Data Sources (production)

See `references/data-sources.md` for full detail.

| Source | What | How | Status |
|--------|------|-----|--------|
| **FRED API** | real_rate, net_liq, ffr, global_m2, hy_oas, fci | JSON API with api_key | ✅ All working |
| **YFinance** | dxy, vix, **HYG** | Daily resample | ✅ Full history |
| **DeFi Llama** | stablecoin_mcap (USDT+USDC) | `stablecoins.llama.fi/stablecoin/1` + `/2` | ✅ Free, full history |
| **TuShare** | tnx (US 10Y backup), cn_m2 (China M2) | `pro.us_tycr()` / `pro.cn_m()` | ✅ Fallback only |
| **Bitget API** (via ccxt) | funding_rate, open_interest | `ccxt.bitget()` | ✅ Available, market data only |

## Interpret Output

### Contrarian Position Sizing

**Macro tilt as a lagging indicator** — the macro environment doesn't change until AFTER the market has already repriced. Use tilt as a **position-sizing multiplier**, not an entry signal.

| Tilt Value | Signal | Position Size | Rationale |
|------------|--------|:-------------:|-----------|
| > +0.3 | Euphoric | **0.30×** | Market already priced in the good macro — trim |
| +0.2 ~ +0.3 | Bullish | **0.50×** | Late to the party |
| < 0.2 (dead zone) | Neutral | **1.00×** | No macro edge — full throttle |
| < -0.3 | Fear | **1.50-2.00×** | Maximum contrarian conviction — buy the fear |

### Daily vs Weekly Frequency Trade-off

**Switched to daily (v2.5, 2026-06-09):**

| Aspect | Weekly (v2.4) | Daily (v2.5) |
|--------|:-------------:|:------------:|
| Resolution | 1 data point/week | 1 data point/day |
| Signal lag | Up to 7 days | 1 day |
| SPY recent Sharpe | 1.56 | **1.21** |
| ETH recent Total | -10.1% | **-40.6%** |
| Signal stability | More stable | More responsive |
| Bear signal % | 16% | **15%** |

**Why daily vs weekly matters:** 7 of 10 indicators update daily or faster. Weekly resampling throws away 6/7 of signal resolution. Daily captures stablecoin_mcap changes, VIX spikes, and HYG credit moves the same day they happen. The trade-off: more sensitivity means more dead-zone entries (27% vs 25%), and in a sustained ETH bear, more time at full exposure.

**Recommended approach:** Daily for production (faster response), weekly for longer-term strategy validation (less noise).

### Backtest Results (v2.5, daily frequency, with NATIVE_FREQ + HYG proxy)

#### Signal Distribution (2020-01 ~ 2026-06, n=2352 daily rows)
- **25% Strong Bull** | **33% Mild Bull** | **27% Neutral** | **5% Mild Bear** | **10% Strong Bear**
- vs weekly v2.4: 32%/27%/25%/4%/12% — similar distribution, slight shift from strong to mild bull

#### SPY
| Period | Metric | Tilt-Sized | Buy&Hold |
|--------|--------|:----------:|:--------:|
| **Full (336w)** | Sharpe | 0.53 | 0.83 |
| | Total Ret | +59.9% | +148.3% |
| | MaxDD | -31.8% | -31.8% |
| **Recent 2yr** | **Sharpe** | **1.21** | 1.20 |
| | Total Ret | +25.1% | +41.8% |
| | MaxDD | **-8.4%** | -16.9% |

#### ETH
| Period | Metric | Tilt-Sized | Buy&Hold |
|--------|--------|:----------:|:--------:|
| **Full (336w)** | Sharpe | 0.61 | 0.88 |
| | Total Ret | +204.6% | +1066% |
| | MaxDD | **-69.3%** | -77.3% |
| **Recent 2yr** | **Total Ret** | **-40.6%** | -54.4% |
| | MaxDD | **-55.0%** | -67.3% |
| | Ann Vol | **40.0%** | 64.4% |

**Key insight:** Daily version is more responsive but more sensitive. In a sustained bear (ETH -54%), daily tilt enters dead zone more often (27% vs 25%), resetting to 1.0x exposure at inopportune times. Weekly version's slower-moving signal stays directionally bearish longer, keeping size down. The trade-off is real — pick frequency based on holding period and signal responsiveness needs.

## 双模式架构 / Dual Mode

支持日频/周频两版并行，通过环境变量切换（2026-06-09 新增）：

```bash
# 日频（默认）
python3 macro_tilt_pipeline.py

# 周频
MACRO_TILT_FREQ=weekly python3 macro_tilt_pipeline.py
```

### 参数对比

| 参数 | 日频(D) | 周频(W-FRI) |
|------|---------|-------------|
| FREQ | D | W-FRI |
| ZSCORE_WINDOW | 365 | 52 |
| HALFLIFE | 28 | 4 |
| ZSCORE_MIN_PERIODS | 182 | 26 |
| OUTPUT_SUFFIX | `_daily` | `''` |

### NATIVE_FREQ 模式（仅日频使用）

低频率指标（月频/周频）不允许直接ffill到日频后再算滚动z分——大量重复值会淹没信号（z≈0）。正确做法：在**原生频率**上算滚动z分，再上采样到日频。

```python
NATIVE_FREQ = {
    'net_liq': 'W',     # Fed balance sheet → 52周z分
    'fci': 'W',         # NFCI → 52周z分
    'ffr': 'M',         # FOMC利率 → 12月z分
    'global_m2': 'M',   # M2 → 12月z分
}
```

**代码流程：**
1. `s.resample(native_freq).last()` — 在原生频率上保留原始数据点
2. `rolling_robust_zscore(window=z_win)` — 原生频率的滚动z分
3. `reindex(daily_grid).ffill()` — z分上采样到日频

预计算的z分用`_z`后缀标记列名，在`compute_tilt`引擎中跳过二次标准化（仅应用tanh+方向）。

### 输出文件分离

两版输出不同文件避免覆盖：

| 文件 | 日频 | 周频 |
|------|------|------|
| JSON | `macro_tilt_score_daily.json` | `macro_tilt_score.json` |
| CSV | `tilt_history_daily.csv` | `tilt_history.csv` |

`tilt_signal.py`（实盘接入模块）默认读日频版，可设`TILT_DATA_PATH`环境变量切换。

### 日期截断

`weekly_grid` = `pd.date_range(...)` → `weekly_grid[weekly_grid <= today]`
禁止输出未来日期（之前bug：周二数据→W-FRI重采样输出了周五）。

## Pitfalls

### CRITICAL: Future Date Bug
Pipeline may output tilt for a date that hasn't happened yet. If today is Tuesday and the grid extends to the next Friday, tilt shows a future date. **Always filter `daily_grid <= pd.Timestamp.now().normalize()`.**

### CRITICAL: NATIVE_FREQ for Monthly/Weekly Data
Without NATIVE_FREQ, switching to daily frequency collapses ffr, global_m2, and net_liq z-scores to zero. The 365-day rolling window on 30× ffill-repeated values produces median=value, MAD≈0 → z=0.

**Symptoms:** `ffr z=0.0000`, `global_m2 z=0.0000` in daily output.
**Fix:** Check config.py has NATIVE_FREQ defined. Rerun pipeline.

### FREQ Change Requires Backfill
Changing from W-FRI to D (or back) requires a full pipeline regeneration. The resampling window changes all historical z-scores, so tilt_history.csv must be rebuilt. **Do not just update cron — run pipeline.py once manually after any FREQ change.**

### FRED API key required
Without it, DFII10 and RRPONTSYD are unreachable. TuShare tnx is a poor proxy for real_rate (nominal, not real).

### global_m2 / DXY double counting
global_m2 is in USD (multicurrency converted). When DXY rises, the USD value of foreign M2 falls — the same dollar-strength signal enters both. Fix: `INDICATOR_WEIGHTS = {'global_m2': 0.05}`. Without this, autocorrelation jumps to 0.94 and usd_liq bucket appears falsely neutral.

### CoinGecko 365-day limit
Free/demo tier limited to 365 days. Use DeFi Llama Stablecoins API for full history.

### No exchange balance free tier
BTC exchange balance requires paid source. crypto_liq has only one indicator (stablecoin_mcap).

### Persistent bullish bias from stablecoin mcap growth
USDT+USDC grew from $4B→$263B (2020–2026). With 35% weight, tilt is structurally bullish ~58% of days. **This is correct behavior** — stablecoin liquidity IS a structural macro tailwind — but means tilt should not be a standalone entry signal.

### Correlation modulation limited
crypto_liq only has one indicator, so corr_mod is always 0.5. Adding ex_btc_balance would activate it.

### Signal is slow-moving
EWM with halflife=28 days + dead zone=0.2 means the tilt changes on slow macro timescales. Not useful for intraweek timing.

### Bucket cancellation
A 0 output does not mean "no macro news" — it often means opposing forces. Always decompose into bucket contributions.

### yfinance MultiIndex
After `yf.download`, `df['Close']` returns a DataFrame. Use `.iloc[-1].iloc[0]` not `float(series)`.

## Troubleshooting Guide

### Symptom: "tilt shows future date"
→ `daily_grid = daily_grid[daily_grid <= pd.Timestamp.now().normalize()]` is missing

### Symptom: "ffr z=0.0000, global_m2 z=0.0000"
→ NATIVE_FREQ not defined or not imported. Check config.py.

### Symptom: "tilt stuck at +0.999 for weeks"
→ Using full-history z-score instead of rolling. Check `rolling_robust_zscore` is the active function.

### Symptom: "crypto_liq missing values after 2023"
→ DeFi Llama endpoint changed or crypto_liq.parquet corrupted. Rerun `crypto_fetch.py --history`.

### Symptom: "no hy_oas before 2023"
→ Expected — FRED BAMLH0A0HYM2 only starts 2023-06. HYG price proxy should fill the gap.

## References
- `references/data-sources.md` — Full data source documentation
- `references/coingecko-api-tiers.md` — CoinGecko key tier limits
- `references/bitget-data-sources.md` — Bitget API integration guide
- `references/contrarian-multiplier.md` — Contrarian multiplier function API
- `references/tilt-position-sizing-eth.md` — ETH position sizing backtest detail
- `references/stablecoin-backfill.md` — DeFi Llama backfill guide
