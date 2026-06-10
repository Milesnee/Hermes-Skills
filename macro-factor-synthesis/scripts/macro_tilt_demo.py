#!/usr/bin/env python3
"""
Macro Tilt Index — Full Pipeline Demo

Usage:
    python3 scripts/macro_tilt_demo.py

Produces:
    - Current macro tilt score [-1, +1]
    - Bucket contribution breakdown
    - Indicator z-score rankings
    - Historical trend (last 15 weeks)
    - Full distribution diagnostics
"""

import numpy as np
import pandas as pd
from scipy.stats import median_abs_deviation
import yfinance as yf
import requests

# ── Configuration ──────────────────────────────────────────────────────────
DIRECTION = {
    'real_rate': -1, 'net_liq': 1, 'dxy': -1, 'ffr': -1, 'global_m2': 1,
    'stablecoin_mcap': 1, 'ex_btc_balance': -1,
    'vix': -1, 'hy_oas': -1, 'fci': -1
}
BUCKETS = {
    'usd_liq': ['real_rate', 'net_liq', 'dxy', 'ffr', 'global_m2'],
    'crypto_liq': ['stablecoin_mcap', 'ex_btc_balance'],
    'risk': ['vix', 'hy_oas', 'fci']
}
BUCKET_WEIGHTS = {'usd_liq': 0.40, 'crypto_liq': 0.35, 'risk': 0.25}
HALFLIFE = 4       # EWM smoothing weeks
DEAD_ZONE = 0.2    # |tilt| < this → 0
START = '2020-01-01'
END = '2025-06-08'

# ── 1. Load real data ──────────────────────────────────────────────────────
def load_yfinance():
    """Fetch and resample to weekly Friday close."""
    tickers = {'^VIX': 'vix', 'DX-Y.NYB': 'dxy', '^TNX': 'tnx', 'HYG': 'hyg'}
    results = {}
    for t, name in tickers.items():
        df = yf.download(t, start=START, end=END, progress=False)['Close']
        w = df.resample('W-FRI').last().dropna()
        # yfinance multi-index fix
        results[name] = w.values.flatten() if isinstance(w, pd.DataFrame) else w.values
        if name not in ['vix', 'dxy', 'tnx', 'hyg']:
            pass  # will handle below
    idx = w.index if isinstance(w, pd.Series) else df.resample('W-FRI').last().dropna().index
    return pd.DataFrame(results, index=idx)

def load_coingecko(coin_id):
    """Fetch stablecoin market cap history."""
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=1825'
    r = requests.get(url, timeout=15)
    data = r.json()
    if 'market_caps' not in data:
        raise ValueError(f"CoinGecko {coin_id}: {data.get('status', {}).get('error_message', 'unknown')}")
    mcaps = data['market_caps']
    return [(pd.to_datetime(m[0], unit='ms'), m[1] / 1e9) for m in mcaps]  # in billions

# ── 2. Core framework ──────────────────────────────────────────────────────
def robust_zscore(series):
    """Median + MAD — robust to fat tails."""
    med = series.median()
    mad = median_abs_deviation(series)
    return (series - med) / (mad + 1e-10)

def compute_macro_index(data, hl=HALFLIFE, dz=DEAD_ZONE):
    """Full pipeline: z-scores → tanh → direction → bucket → modulation → EWM → deadzone."""
    scores = pd.DataFrame(index=data.index)
    for col in data.columns:
        z = robust_zscore(data[col])
        scores[col] = np.tanh(z) * DIRECTION[col]

    # Correlation modulation
    bucket_corr = {}
    for bucket, cols in BUCKETS.items():
        corr = scores[cols].corr()
        pos_ratio = (corr.values[np.triu_indices_from(corr.values, k=1)] > 0.3).mean()
        bucket_corr[bucket] = pos_ratio

    # Bucket scores
    bucket_scores = {}
    for bucket, cols in BUCKETS.items():
        raw = scores[cols].mean(axis=1)
        mod = 0.5 + 0.5 * bucket_corr[bucket]
        bucket_scores[bucket] = raw * mod

    # Weighted sum
    final = pd.Series(0.0, index=data.index)
    for bucket, bs in bucket_scores.items():
        final += bs * BUCKET_WEIGHTS[bucket]

    # Smooth + dead zone
    smoothed = final.ewm(halflife=hl).mean()
    smoothed[np.abs(smoothed) < dz] = 0.0

    return smoothed, bucket_scores, scores, bucket_corr

# ── 3. Output ───────────────────────────────────────────────────────────────
def print_results(tilt, bucket_scores, indicator_scores, corr_mod, raw_data):
    tag = lambda v: (
        '🟢 Strongly Bullish' if v > 0.3 else
        '🔶 Mildly Bullish' if v > 0.2 else
        '⏸️  Neutral (Dead Zone)' if v > -0.2 else
        '🔶 Mildly Bearish' if v > -0.3 else
        '🔴 Strongly Bearish'
    )

    print(f"\n{'=' * 60}")
    print(f"Macro Tilt Index — {raw_data.index[-1].date()}")
    print(f"{'=' * 60}")
    print(f"\nFinal Score: {tilt.iloc[-1]:+.4f}  →  {tag(tilt.iloc[-1])}")

    print(f"\n📦  Bucket Contributions")
    total = 0
    for b in BUCKETS:
        raw = bucket_scores[b].iloc[-1]
        w = BUCKET_WEIGHTS[b]
        contrib = raw * w
        total += contrib
        corr_pct = corr_mod[b] * 100
        print(f"  {b:12s} ({w*100:.0f}%): {raw:+.4f} × {w:.0f} = {contrib:+.4f} [corr: {corr_pct:.0f}%]")
    print(f"  {'─' * 50}")
    print(f"  Raw composite: {total:+.4f}  →  EWM(hl={HALFLIFE}): {tilt.iloc[-1]:+.4f}")

    print(f"\n🔬  Indicator Z-Scores (sorted)")
    for col in sorted(indicator_scores.columns,
                      key=lambda c: indicator_scores[c].iloc[-1], reverse=True):
        z = indicator_scores[col].iloc[-1]
        raw = raw_data[col].iloc[-1]
        bucket = next(b for b, cs in BUCKETS.items() if col in cs)
        emoji = '🟢' if z > 0.1 else ('🔴' if z < -0.1 else '⚪')
        print(f"  {emoji} {col:20s} z={z:+.3f}  [{bucket}]")

    print(f"\n📈  History (last 10 weeks)")
    for i in range(-10, 0):
        d = raw_data.index[i]
        t = tilt.iloc[i]
        if t != 0:
            parts = ' | '.join(f"{b}:{bucket_scores[b].iloc[i]:+.3f}" for b in BUCKETS)
        else:
            parts = '(dead zone)'
        print(f"  {d.date()}  →  {t:+.4f}  [{parts}]")

    print(f"\n📊  Distribution (n={len(tilt)})")
    print(f"  Strongly bullish (>+0.3):    {np.mean(tilt>0.3)*100:.0f}%")
    print(f"  Mildly bullish (0.2~0.3):    {np.mean((tilt>0.2)&(tilt<=0.3))*100:.0f}%")
    print(f"  Neutral (|z|<0.2, dead zone): {np.mean(np.abs(tilt)<=0.2)*100:.0f}%")
    print(f"  Mildly bearish (-0.3~-0.2):  {np.mean((tilt<-0.2)&(tilt>=-0.3))*100:.0f}%")
    print(f"  Strongly bearish (<-0.3):     {np.mean(tilt<-0.3)*100:.0f}%")

# ── 4. Main ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("Loading YFinance data...")
    weekly = load_yfinance()
    print(f"Loaded {len(weekly)} weeks ({weekly.index[0].date()} ~ {weekly.index[-1].date()})")

    # For a complete run, we also need:
    #   - stablecoin market cap (CoinGecko)
    #   - economic indicators (FRED / TuShare)
    # See references/data-sources.md for endpoints.
    #
    # When real data is unavailable, the skill provides a synthetic
    # data generation method in the SKILL.md for validation purposes.

    # For now, show available columns
    print(f"Available: {list(weekly.columns)}")
    print(f"Latest: VIX={weekly['vix'].iloc[-1]:.1f}, DXY={weekly['dxy'].iloc[-1]:.1f}, "
          f"10Y={weekly['tnx'].iloc[-1]:.2f}%, HYG={weekly['hyg'].iloc[-1]:.1f}")
