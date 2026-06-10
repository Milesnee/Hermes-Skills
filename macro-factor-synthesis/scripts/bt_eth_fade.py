#!/usr/bin/env python3
"""
ETH Fade Backtest — Standalone
===============================
Bear做多/Bull做空 ETH 的宏观Contrarian策略的独立回测。
基于 macro_tilt_pipeline 的历史 tilt 数据。

核心规则:
  tilt < -deadband → LONG ETH  (+1)
  tilt > +deadband → SHORT ETH (-1)
  其他 → FLAT (0)

用法:
  python3 bt_eth_fade.py [--deadband 0.3] [--min-weeks 5]
"""

import numpy as np
import pandas as pd
import yfinance as yf
import warnings, sys, os, argparse
from pathlib import Path

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser('~/workspace/macro_tilt_pipeline'))
from config import OUTPUT_DIR

DATA = Path(os.path.expanduser(OUTPUT_DIR))
TILT_CSV = DATA / 'tilt_history.csv'

def main(deadband=0.3, min_weeks=5):
    # ── Load tilt history ──
    if not TILT_CSV.exists():
        print(f"❌ Tilt data not found: run macro_tilt_pipeline first")
        return

    tilt_df = pd.read_csv(TILT_CSV, index_col=0, parse_dates=True)
    print(f"  Tilt data: {len(tilt_df)} rows ({tilt_df.index[0].date()} ~ {tilt_df.index[-1].date()})")

    # ── Fetch ETH weekly prices ──
    print("  Fetching ETH-USD...", end=' ')
    df = yf.download('ETH-USD', start='2020-01-01', auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        close_series = df['Close']['ETH-USD'] if 'ETH-USD' in df['Close'].columns else df['Close'].iloc[:, 0]
    else:
        close_series = df['Close']
    weekly = close_series.resample('W-FRI').last().pct_change().dropna()
    weekly.index = weekly.index.tz_localize(None) if weekly.index.tz else weekly.index
    print(f"{len(weekly)} weeks")

    # ── Align ──
    prices = weekly.loc['2020-01-03':]
    tilt_aligned = tilt_df.reindex(prices.index, method='ffill').dropna()
    prices = prices.loc[tilt_aligned.index]
    tilt_signal = tilt_aligned['tilt'].values
    n = len(tilt_signal)
    print(f"\n  Aligned: {tilt_aligned.index[0].date()} ~ {tilt_aligned.index[-1].date()} ({n} weeks)")

    # ── Post-crypto split ──
    crypto_col = tilt_aligned['crypto_liq_score'] if 'crypto_liq_score' in tilt_aligned.columns else pd.Series(np.nan, index=tilt_aligned.index)
    crypto_start = tilt_aligned.index[crypto_col.notna() & (crypto_col != 0)].min()
    print(f"  Crypto_liq active from: {crypto_start.date() if isinstance(crypto_start, pd.Timestamp) else 'N/A'}")

    # ── Signal function ──
    def fade_pos(t):
        if t <= -deadband:
            return 1.0    # LONG
        elif t >= deadband:
            return -1.0   # SHORT
        return 0.0        # FLAT

    positions = np.array([fade_pos(v) for v in tilt_signal])
    rets = prices.values

    # Strategy returns: position at week t × return at week t+1
    port_rets = positions[:-1] * rets[1:]
    bh_rets = rets[1:]

    def compute_stats(r, ann=52):
        if len(r) < min_weeks:
            return None
        cum = (1 + r).cumprod()
        peak = np.maximum.accumulate(cum)
        dd = (cum - peak) / peak

        ann_ret = np.mean(r) * ann
        ann_vol = np.std(r) * np.sqrt(ann) if np.std(r) > 0 else 0.01
        sharpe = ann_ret / ann_vol

        neg = r[r < 0]
        down_vol = np.std(neg) * np.sqrt(ann) if len(neg) > 5 else ann_vol
        sortino = ann_ret / down_vol

        return {
            'ann_ret': ann_ret,
            'ann_vol': ann_vol,
            'sharpe': sharpe,
            'sortino': sortino,
            'maxdd': np.min(dd),
            'win_rate': np.mean(r > 0),
            'total_return': cum.iloc[-1] - 1 if isinstance(cum, pd.Series) else cum[-1] - 1,
            'n_trades': int(np.sum(r != 0)),
            'avg_trade': np.mean(r[r != 0]) * 100 if np.any(r != 0) else 0,
        }

    # ── Full period ──
    print(f"\n{'='*65}")
    print(f"  ETH FADE — Full Period")
    print(f"{'='*65}")
    print(f"  Rule: tilt < -{deadband} → LONG, tilt > +{deadband} → SHORT")

    flip_points = np.where(np.diff(np.sign(positions)) != 0)[0] + 1
    print(f"  Regime flips: {len(flip_points)}")
    regime_counts = {'BEAR/LONG': int(np.sum(positions > 0)),
                     'BULL/SHORT': int(np.sum(positions < 0)),
                     'NEUTRAL/FLAT': int(np.sum(positions == 0))}
    print(f"  Position distribution: {regime_counts}")

    s = compute_stats(port_rets)
    b = compute_stats(bh_rets)
    if s:
        print(f"\n  {'Metric':<15} {'ETH Fade':>12} {'Buy&Hold':>12} {'Delta':>10}")
        print(f"  {'-'*15} {'-'*12} {'-'*12} {'-'*10}")
        print(f"  {'Ann Return':<15} {s['ann_ret']*100:>10.1f}% {b['ann_ret']*100:>10.1f}% {s['ann_ret']*100 - b['ann_ret']*100:>+9.1f}%")
        print(f"  {'Ann Vol':<15} {s['ann_vol']*100:>10.1f}% {b['ann_vol']*100:>10.1f}% {s['ann_vol']*100 - b['ann_vol']*100:>+9.1f}%")
        print(f"  {'Sharpe':<15} {s['sharpe']:>10.2f} {b['sharpe']:>10.2f} {s['sharpe'] - b['sharpe']:>+9.2f}")
        print(f"  {'Sortino':<15} {s['sortino']:>10.2f} {b['sortino']:>10.2f} {s['sortino'] - b['sortino']:>+9.2f}")
        print(f"  {'Max DD':<15} {s['maxdd']*100:>10.1f}% {b['maxdd']*100:>10.1f}% {s['maxdd']*100 - b['maxdd']*100:>+9.1f}%")
        print(f"  {'Win Rate':<15} {s['win_rate']*100:>10.0f}% {b['win_rate']*100:>10.0f}% {s['win_rate']*100 - b['win_rate']*100:>+9.0f}%")
        print(f"  {'Total Return':<15} {s['total_return']*100:>10.1f}% {b['total_return']*100:>10.1f}% {s['total_return']*100 - b['total_return']*100:>+9.1f}%")

    # ── Post-crypto ──
    if isinstance(crypto_start, pd.Timestamp):
        post_mask = tilt_aligned.index >= crypto_start
        post_n = post_mask.sum()
        if post_n >= min_weeks:
            pc_start = np.where(post_mask)[0][0]
            port_post = port_rets[pc_start:]
            bh_post = bh_rets[pc_start:]

            sp = compute_stats(port_post)
            bp = compute_stats(bh_post)
            if sp:
                print(f"\n{'='*65}")
                print(f"  POST-CRYPTO ERA (since {crypto_start.date()}) — {post_n} weeks")
                print(f"{'='*65}")
                print(f"  {'Metric':<15} {'ETH Fade':>12} {'Buy&Hold':>12} {'Delta':>10}")
                print(f"  {'-'*15} {'-'*12} {'-'*12} {'-'*10}")
                print(f"  {'Ann Return':<15} {sp['ann_ret']*100:>10.1f}% {bp['ann_ret']*100:>10.1f}% {sp['ann_ret']*100 - bp['ann_ret']*100:>+9.1f}%")
                print(f"  {'Ann Vol':<15} {sp['ann_vol']*100:>10.1f}% {bp['ann_vol']*100:>10.1f}% {sp['ann_vol']*100 - bp['ann_vol']*100:>+9.1f}%")
                print(f"  {'Sharpe':<15} {sp['sharpe']:>10.2f} {bp['sharpe']:>10.2f} {sp['sharpe'] - bp['sharpe']:>+9.2f}")
                print(f"  {'Sortino':<15} {sp['sortino']:>10.2f} {bp['sortino']:>10.2f} {sp['sortino'] - bp['sortino']:>+9.2f}")
                print(f"  {'Max DD':<15} {sp['maxdd']*100:>10.1f}% {bp['maxdd']*100:>10.1f}% {sp['maxdd']*100 - bp['maxdd']*100:>+9.1f}%")
                print(f"  {'Win Rate':<15} {sp['win_rate']*100:>10.0f}% {bp['win_rate']*100:>10.0f}% {sp['win_rate']*100 - bp['win_rate']*100:>+9.0f}%")
                print(f"  {'Total Return':<15} {sp['total_return']*100:>10.1f}% {bp['total_return']*100:>10.1f}% {sp['total_return']*100 - bp['total_return']*100:>+9.1f}%")

    # ── Per-trade analysis ──
    print(f"\n{'='*65}")
    print(f"  PER-TRADE ANALYSIS (full period)")
    print(f"{'='*65}")

    trade_starts = np.where(np.diff(np.concatenate([[0], positions.astype(int)])) != 0)[0]
    trade_returns = []
    for i in range(len(trade_starts) - 1):
        start = trade_starts[i]
        end = trade_starts[i + 1]
        dir_label = 'LONG' if positions[start] > 0 else ('SHORT' if positions[start] < 0 else 'FLAT')
        if dir_label == 'FLAT':
            continue
        seg_rets = port_rets[start:end]
        if len(seg_rets) > 0:
            cum_ret = (1 + seg_rets).prod() - 1
            trade_returns.append({'direction': dir_label, 'weeks': len(seg_rets), 'return': cum_ret})

    if trade_returns:
        long_rets = [t['return'] for t in trade_returns if t['direction'] == 'LONG']
        short_rets = [t['return'] for t in trade_returns if t['direction'] == 'SHORT']
        print(f"  Total trades: {len(trade_returns)} ({len(long_rets)} LONG, {len(short_rets)} SHORT)")
        if long_rets:
            print(f"  LONG trades: win={np.mean([r>0 for r in long_rets])*100:.0f}%, "
                  f"avg={np.mean(long_rets)*100:.1f}%, median={np.median(long_rets)*100:.1f}%")
        if short_rets:
            print(f"  SHORT trades: win={np.mean([r>0 for r in short_rets])*100:.0f}%, "
                  f"avg={np.mean(short_rets)*100:.1f}%, median={np.median(short_rets)*100:.1f}%")

    print(f"\n  ✅ Done — deadband={deadband}, min_weeks={min_weeks}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ETH Fade Backtest')
    parser.add_argument('--deadband', type=float, default=0.3, help='Signal deadband (default: 0.3)')
    parser.add_argument('--min-weeks', type=int, default=5, help='Min weeks for stat computation')
    args = parser.parse_args()
    main(deadband=args.deadband, min_weeks=args.min_weeks)
