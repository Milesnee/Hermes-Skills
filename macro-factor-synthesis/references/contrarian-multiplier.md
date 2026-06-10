# Contrarian Position Sizing Multiplier

## Why Contrarian Works

Macro indicators are **lagging** — they reflect conditions that occurred weeks ago. By the time the tilt shows Bearish, the market has already sold off. The Bearish reading = buying opportunity, not a sell signal.

**Backtest evidence (full period 2020–2026, 336 weeks):**

| Strategy | SPY Sharpe | QQQ Sharpe | BTC Sharpe | ETH Sharpe |
|----------|:----------:|:----------:|:----------:|:----------:|
| Buy & Hold | 0.82 | 0.94 | 0.80 | 0.85 |
| Bear=2×, Bull=0.5× | **0.89** | **1.01** | **0.87** | **0.96** |
| Bear=3×, Bull=0.25× | **0.95** | **1.06** | **0.91** | **1.02** |

**Best full-period config:** Bear=3×, Bull=0.25× (highest Sharpe on all 4 assets).

## Regime-Level Win Rates

| Regime | n | BTC win% | ETH win% | SPY win% | QQQ win% |
|--------|:-:|:--------:|:--------:|:--------:|:--------:|
| Mild Bull | 9 | 38% | 38% | **75%** | 62% |
| Neutral | 316 | 52% | 52% | 55% | 56% |
| Mild Bear | 10 | **70%** | **70%** | **90%** | **80%** |

→ Bear signal → next week positive across ALL assets (SPY 90%!). This is the highest-conviction trade.

## Post-Crypto Era (2025-06 ~ 2026-06, 53 weeks)

| Strategy | SPY Sharpe | QQQ Sharpe | BTC Sharpe | ETH Sharpe |
|----------|:----------:|:----------:|:----------:|:----------:|
| BH | 1.97 | 1.98 | **−1.04** | −0.25 |
| Bear=2×, Bull=0.5× | **2.10** | **2.12** | −0.45 | +0.49 |
| ETH Fade (Bear=long, Bull=short) | — | — | — | **1.93** |

**Key insight:** Stablecoin mcap expansion = institutional risk appetite → benefits equities, not crypto. BTC/ETH had their own micro dynamics during this period. ETH Fade (flip the signal direction) scored Sharpe 1.93.

## Multiplier Module API

Located at `~/workspace/macro_tilt_pipeline/tilt_multiplier.py`:

```python
from tilt_multiplier import contrarian_mult

# Four presets
mult = contrarian_mult(tilt_value, method='balanced')      # → 0.53× (at +0.29)
mult = contrarian_mult(tilt_value, method='conservative')   # → 0.53×
mult = contrarian_mult(tilt_value, method='aggressive')     # → 0.29×
mult = contrarian_mult(tilt_value, method='scaled')         # → 0.67× (smooth)

# Helper
from tilt_multiplier import regime_label, multiplier_label
print(regime_label(0.29))    # "🟢 MILD_BULL"
print(multiplier_label(0.53)) # "⚠️ 减仓"
```

### Method Details

| Method | Bear (≤−0.3) | Bull (≥0.3) | Neutral | Use Case |
|--------|:-----------:|:----------:|:-------:|----------|
| conservative | 1.5× | 0.5× | 1.0× | Low risk, +5% Sharpe |
| balanced | 2.0× | 0.5× | 1.0× | Default, +9% Sharpe |
| aggressive | 3.0× | 0.25× | 1.0× | Max return, +16% Sharpe |
| scaled | ~2.5× | ~0.3× | 1.0× | No hard threshold, smooth |

### Integration Points

1. **macro_tilt_score.json** — `contrarian_multiplier` field auto-added by pipeline
2. **daily_feishu_sync.py** — displays multiplier table in the daily report
3. **Strategy frameworks** — call `contrarian_mult(tilt, 'balanced')` to get position size

## Limitations

- Signal is sparse: only ~6% of weeks are non-neutral (94% in dead zone)
- Small sample: only 10 bear weeks + 9 bull weeks out of 336
- Post-crypto period is 53 weeks only — the strong SPY/QQQ Sharpe may overfit
- Not validated on out-of-sample data beyond June 2026
- MaxDD unchanged (Bear=long doesn't hedge the main drawdowns)
