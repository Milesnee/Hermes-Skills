#!/usr/bin/env python3
"""Quick comparison of daily vs weekly macro tilt signals."""
import json, os, sys

BASE = os.path.expanduser('~/data/macro_tilt')

def load(name):
    try:
        with open(os.path.join(BASE, name)) as f:
            return json.load(f)
    except FileNotFoundError:
        return None

daily = load('macro_tilt_score_daily.json')
weekly = load('macro_tilt_score.json')

if not daily and not weekly:
    print("No tilt data found.")
    sys.exit(1)

print(f"{'Freq':>7} | {'Signal':<22} | Tilt     | Date       | Mult(consv) | Mult(bal) | Mult(aggr)")
print("-" * 90)

for freq, d, suf in [('DAILY', daily, '_daily'), ('WEEKLY', weekly, '')]:
    if not d:
        print(f"{freq:>7} | (no data)")
        continue
    cm = d.get('contrarian_multiplier', {})
    cs = cm.get('conservative', 0)
    ba = cm.get('balanced', 0)
    ag = cm.get('aggressive', 0)
    print(f"{freq:>7} | {d['signal']:<22} | {d['tilt']:+.4f} | {d['date']} | {cs:.2f}x{'':>6} | {ba:.2f}x | {ag:.2f}x")

# Show per-bucket differences
print("\n── Bucket Comparison ──────────────────────────────────────")
print(f"{'Bucket':<16} {'Daily':>8} {'Weekly':>8} {'Delta':>8}")
print("-" * 44)
if daily and weekly:
    for b in daily.get('buckets', {}):
        dv = daily['buckets'][b].get('raw', 0)
        wv = weekly['buckets'][b].get('raw', 0) if b in weekly.get('buckets', {}) else 0
        print(f"{b:<16} {dv:>+8.4f} {wv:>+8.4f} {dv-wv:>+8.4f}")
