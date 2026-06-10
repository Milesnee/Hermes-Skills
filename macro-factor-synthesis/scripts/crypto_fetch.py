#!/usr/bin/env python3
"""
Crypto Liquidity Fetcher v2 — stablecoin mcap via CoinGecko (API key)
1. Initial backfill: 365d CoinGecko history → parquet
2. Daily append: current mcap → parquet (uses API key for rate limit)
3. Main pipeline reads parquet during build_indicator_df()

Usage:
  python3 crypto_fetch.py             # backfill + append
  python3 crypto_fetch.py --history   # backfill only
  python3 crypto_fetch.py --daily     # append only (cron)

API key: CG-bueNR3Hh5YWUtKi9vPG9oJpp
  - Demo key — same endpoints as free tier, higher rate limts (50/min)
  - Does NOT unlock days=max or /range or /history (all need paid Pro)
  - Stored in HEADERS constant below

Output: ~/data/macro_tilt/crypto_liq.parquet
"""

import json, os, sys, warnings, time
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings('ignore')

OUTPUT_DIR = Path(os.path.expanduser('~/data/macro_tilt'))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PARQUET_PATH = OUTPUT_DIR / 'crypto_liq.parquet'
CSV_PATH = OUTPUT_DIR / 'crypto_liq.csv'

CG_API_KEY = 'CG-bueNR3Hh5YWUtKi9vPG9oJpp'
CG_BASE = 'https://api.coingecko.com/api/v3'
HEADERS = {'x-cg-demo-api-key': CG_API_KEY}

STABLECOINS = [('tether', 'USDT'), ('usd-coin', 'USDC')]
MAX_RETRIES = 3
TICK = print


def _get(url, retries=MAX_RETRIES):
    """GET with API key header and retry on 429."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                wait = int(r.headers.get('Retry-After', 10))
                TICK(f"  ⚠ Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt < retries - 1:
                TICK(f"  ⚠ Retry {attempt+1}/{retries}: {e}")
                time.sleep(5 * (attempt + 1))
                continue
            raise
    return None


def fetch_stablecoin_history(days=365):
    """CoinGecko 365d stablecoin mcap history with API key."""
    all_data = {}
    for cid, label in STABLECOINS:
        TICK(f"  {label}: fetching {days}d history...")
        url = f'{CG_BASE}/coins/{cid}/market_chart?vs_currency=usd&days={days}'
        try:
            d = _get(url)
            if not d or 'market_caps' not in d:
                TICK(f"  ✗ {label}: empty")
                continue
            mcaps = d['market_caps']
            s = pd.Series(
                [m[1] / 1e9 for m in mcaps],
                index=pd.DatetimeIndex([datetime.fromtimestamp(m[0] / 1000) for m in mcaps])
            )
            all_data[label] = s
            TICK(f"  ✓ {label}: {len(s)} pts ({s.index[0].date()} ~ {s.index[-1].date()})")
        except Exception as e:
            TICK(f"  ✗ {label}: {e}")
        time.sleep(1.5)

    if not all_data:
        return None

    combined = pd.DataFrame(all_data)
    combined['total_stablecoin_mcap'] = combined.sum(axis=1)
    combined = combined[~combined.index.duplicated(keep='first')].sort_index()
    weekly = combined['total_stablecoin_mcap'].resample('W-FRI').last().dropna()

    # Filter: < 200B means partial data (one of USDT/USDC only)
    weekly = weekly[weekly > 200]

    TICK(f"  → Combined: {len(weekly)} weekly pts ({weekly.index[0].date()} ~ {weekly.index[-1].date()})")
    TICK(f"  → Range: ${weekly.min():.1f}B ~ ${weekly.max():.1f}B")
    return weekly


def fetch_current_mcap():
    """Single-point current stablecoin mcap."""
    total = 0
    for cid, label in STABLECOINS:
        url = f'{CG_BASE}/coins/{cid}?localization=false&tickers=false&community_data=false&developer_data=false'
        try:
            d = _get(url)
            mcap = d.get('market_data', {}).get('market_cap', {}).get('usd', 0) / 1e9
            TICK(f"  {label}: ${mcap:.2f}B")
            total += mcap
        except Exception as e:
            TICK(f"  ✗ {label}: {e}")
    return total


def append_daily():
    """Daily append (cron 40092561267b, 06:00 UTC)."""
    total_mcap = fetch_current_mcap()
    if total_mcap <= 0:
        TICK("  ✗ Failed to fetch current mcap")
        return
    today = pd.Timestamp.now().normalize()

    if PARQUET_PATH.exists():
        hist = pd.read_parquet(PARQUET_PATH)
        if today in hist.index:
            TICK(f"  ⚠ {today.date()} exists, skip")
            return hist
    else:
        hist = pd.DataFrame(columns=['total_stablecoin_mcap'])
        hist.index.name = 'date'

    new_row = pd.DataFrame({'total_stablecoin_mcap': [total_mcap]}, index=[today])
    updated = pd.concat([hist, new_row])
    updated.index.name = 'date'
    updated = updated[~updated.index.duplicated(keep='last')].sort_index()
    updated.to_parquet(PARQUET_PATH)
    updated.to_csv(CSV_PATH)
    TICK(f"  ✓ Appended {today.date()}: ${total_mcap:.2f}B (total: {len(updated)})")
    return updated


if __name__ == '__main__':
    if '--daily' in sys.argv:
        append_daily()
    elif '--history' in sys.argv:
        s = fetch_stablecoin_history(days=365)
        if s is not None:
            df = pd.DataFrame({'total_stablecoin_mcap': s})
            df.index.name = 'date'
            df.to_parquet(PARQUET_PATH)
            df.to_csv(CSV_PATH)
            TICK(f"  ✓ Saved ({len(df)} rows)")
    else:
        TICK(f"Crypto Liq Fetcher v2 (API key: {CG_API_KEY[:10]}...)\n{'=' * 55}")
        TICK("[1/2] History:")
        if PARQUET_PATH.exists():
            existing = pd.read_parquet(PARQUET_PATH)
            age = (pd.Timestamp.now() - existing.index.min()).days
            TICK(f"  Existing: {len(existing)} rows ({existing.index[0].date()} ~ {existing.index[-1].date()}), {age}d old")
            if age < 365:
                TICK("  → Skipping (already 365d+)")
            else:
                TICK("  → Less than 365d, refetching...")
                s = fetch_stablecoin_history(days=365)
                if s is not None:
                    df = pd.DataFrame({'total_stablecoin_mcap': s})
                    df.index.name = 'date'
                    df.to_parquet(PARQUET_PATH)
                    df.to_csv(CSV_PATH)
        else:
            TICK("  No data, fetching 365d history...")
            s = fetch_stablecoin_history(days=365)
            if s is not None:
                df = pd.DataFrame({'total_stablecoin_mcap': s})
                df.index.name = 'date'
                df.to_parquet(PARQUET_PATH)
                df.to_csv(CSV_PATH)
                TICK(f"  ✓ Saved ({len(df)} rows)")

        TICK("[2/2] Daily append:")
        append_daily()
        TICK(f"\n  ✓ {PARQUET_PATH}")
