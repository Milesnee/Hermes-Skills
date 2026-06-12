#!/usr/bin/env python3
"""老王黄金框架 — 一键跑五因素评分"""
import urllib.request, json

def yf(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        d = json.load(resp)
    return d['chart']['result'][0]['meta']['regularMarketPrice']

def yf_1y(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1wk"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        d = json.load(resp)
    result = d['chart']['result'][0]
    close = [c for c in result['indicators']['quote'][0]['close'] if c]
    return close[0], close[-1], max(close), min(close)

print("=" * 60)
print("老王黄金框架改进版 — 实时信号检测")
print("=" * 60)

gold = yf("GC%3DF")
spx = yf("%5EGSPC")
tnx = yf("%5ETNX")
dxy = yf("DX-Y.NYB")
gld = yf("GLD")
silver = yf("SI%3DF")
ratio = gold / silver if silver else 0
gold_1y_start, gold_1y_end, gold_1y_high, gold_1y_low = yf_1y("GC%3DF")

print(f"当前黄金: ${gold:.0f}  (1y高 ${gold_1y_high:.0f} / 低 ${gold_1y_low:.0f})")
print(f"10Y收益率: {tnx:.2f}%")
print(f"S&P 500: {spx:.0f}")
print(f"DXY: {dxy:.2f}")
print(f"G/S比: {ratio:.1f}")

ff_price = yf("ZQ%3DF")
implied_rate = 100 - ff_price
current_effective = 4.33
print(f"\nFed Funds futures implied rate: {implied_rate:.2f}%")
print(f"当前有效联邦基金利率: {current_effective:.2f}%")
print(f"市场预期降息: {(current_effective - implied_rate)*100:.0f}bps")

score_1 = 1 if implied_rate < current_effective else (-1 if implied_rate > current_effective + 0.5 else 0)
score_2 = 1  # 默认央行购金趋势向上
score_3 = -0.5 if spx > 7000 else 0.5
score_4 = -1 if gld < 390 else (1 if gld > 450 else 0)

factor_5 = 0
if dxy < 100 and ratio < 70:
    factor_5 = 0.15
elif dxy > 103:
    factor_5 = -0.15

total = (score_1 * 0.50 + score_2 * 0.20 + score_3 * 0.10 + score_4 * 0.25) * (1 + factor_5)

print(f"\n{'='*60}")
print(f"①美联储利率(50%): {'利多' if score_1>0 else '利空' if score_1<0 else '中性'} ({score_1:+.1f})")
print(f"②央行购金(20%):   {'利多' if score_2>0 else '利空' if score_2<0 else '中性'} ({score_2:+.1f})")
print(f"③美股(10%):       {'利多' if score_3>0 else '利空' if score_3<0 else '中性'} ({score_3:+.1f})")
print(f"④ETF/期货(25%):   {'利多' if score_4>0 else '利空' if score_4<0 else '中性'} ({score_4:+.1f})")
print(f"⑤参考系调节:      {factor_5*100:+.0f}%")
print(f"{'='*60}")
print(f"加权总分: {total:+.3f}")
if total > 0.6: signal = "强多头 🟢"
elif total > 0.2: signal = "弱多头 🟡"
elif total > -0.2: signal = "中性 ⚪"
elif total > -0.6: signal = "弱空头 🟠"
else: signal = "强空头 🔴"
print(f"信号: {signal}")
