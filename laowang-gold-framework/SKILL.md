---
name: laowang-gold-framework
description: 老王黄金框架改进版 — 五因素黄金多空信号检测。美联储利率50%+央行购金20%+美股10%+ETF/期货25%+参考系调节因子15%。
triggers: gold|黄金|XAU|老王框架
tags: ['#黄金', '#commodities', '#macro', '#trading-system', '#factor-model']
---

# 老王黄金框架改进版

老王黄金框架的 Agent 改进版 — 经过独立评审验证，权重已调整。

## 框架权重（改进后）

| 因素 | 权重 | 说明 |
|------|------|------|
| ① 美联储利率政策 | **50%** | 黄金无息，实际利率即持有成本。新任鹰派主席是变量 |
| ② 各国央行购金 | **20%** | 上调自10%，2022-2025各国年均购金~1000吨，地缘去美元化趋势强化 |
| ③ 美股表现（风险偏好） | **10%** | 风险偏好 vs 避险需求的跷跷板 |
| ④ 黄金ETF/期货持仓 | **25%** | 削减自30%，COMEX持仓+ETF流量是定价核心 |
| ⑤ 两大参考系 | **±15%乘性** | 大宗商品全局 vs 黄金特质跌，区分度有实战价值 |

**总分 = (①×50% + ②×20% + ③×10% + ④×25%) × (1 + ⑤)**

## 权重调整理由

详见 [references/review-2026-06-12.md](references/review-2026-06-12.md)

## 数据采集方法

### 当前行情（Yahoo Finance API）

```bash
# 黄金现货 - Gold API
curl -s "https://api.gold-api.com/price/XAU"

# 黄金期货
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?range=1d&interval=1d" -H "User-Agent: Mozilla/5.0" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['chart']['result'][0]['meta']['regularMarketPrice'])"

# 10Y收益率 ^TNX
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX?range=1d&interval=1d" -H "User-Agent: Mozilla/5.0"

# S&P 500
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=1d&interval=1d" -H "User-Agent: Mozilla/5.0"

# DXY
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?range=1d&interval=1d" -H "User-Agent: Mozilla/5.0"

# GLD ETF (6mo)
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/GLD?range=6mo&interval=1mo" -H "User-Agent: Mozilla/5.0"

# 白银
curl -s "https://api.gold-api.com/price/XAG"
```

### 黄金历史趋势

```bash
# 1年周线数据看顶部底部
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?range=1y&interval=1wk" -H "User-Agent: Mozilla/5.0"
```

### 美联储预期利率

```bash
# Fed Funds futures (ZQ=F)
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/ZQ%3DF?range=1d&interval=1d" -H "User-Agent: Mozilla/5.0" | python3 -c "import sys,json; d=json.load(sys.stdin); p=d['chart']['result'][0]['meta']['regularMarketPrice']; print(f'Implied rate: {100-p:.2f}%')"
```

## 评分标准

### ① 美联储利率政策（50%）

- **利多(+1)**: 利率稳定/下降预期，Fed Funds futures implied rate < 当前有效利率
- **利空(-1)**: 加息或紧缩预期，实际利率上升
- **中性(0)**: 预期模糊或方向不明

### ② 各国央行购金（20%）

- **利多(+1)**: 月度净购金持续>80吨/全球央行增持趋势
- **利空(-1)**: 净卖出/增持减速
- **中性(0)**: 持平历史均值

### ③ 美股表现（10%）

- **利多(+1)**: 美股大幅回调(避险)→黄金受益；或美股大涨(通胀对冲)→黄金受益
- **利空(-1)**: 美股温和上涨分流资金/紧缩担忧
- **中性(0)**: 窄幅震荡

### ④ 黄金ETF/期货持仓（25%）

- **利多(+1)**: COMEX净多单增加/GLD持仓增长
- **利空(-1)**: 持仓下降/净多单减少
- **中性(0)**: 持仓稳定

### ⑤ 两大参考系调节因子（±15%乘性）

- **+15%**: 大宗商品整体走强 AND 黄金相对强势(金/银比偏低)
- **-15%**: 大宗商品走弱 OR 黄金相对弱势
- **0%**: 中性

## 信号阈值

| 总分区间 | 信号 |
|----------|------|
| > +0.6 | 强多头 🟢 |
| +0.2 ~ +0.6 | 弱多头 🟡 |
| -0.2 ~ +0.2 | 中性 ⚪ |
| -0.6 ~ -0.2 | 弱空头 🟠 |
| < -0.6 | 强空头 🔴 |

## 脚本化执行

一键运行脚本：[scripts/gold_framework.py](scripts/gold_framework.py)

```bash
python3 scripts/gold_framework.py
```
