# 日频/周频双模式 & NATIVE_FREQ 实现笔记

## 背景

2026-06-09 会话中将 macro-tilt 从周频(W-FRI)升级为日频(D)，同时保留周频版并行运行。

## 架构决策

### 1. Env Var 切换模式

`config.py` 通过 `MACRO_TILT_FREQ=daily|weekly` 环境变量控制所有频率敏感参数。
默认为 `daily`。周频用 `MACRO_TILT_FREQ=weekly`。

频率敏感参数包括：
- `FREQ` — 重采样频次 (D / W-FRI)
- `ZSCORE_WINDOW` — 滚动z分窗口 (365 / 52)
- `HALFLIFE` — EWM半衰期 (28 / 4)
- `NATIVE_FREQ` — 低频率指标处理策略
- `OUTPUT_SUFFIX` — 输出文件后缀

### 2. NATIVE_FREQ 模式背后的统计问题

**问题发现过程：**
- 日频版首次跑：ffr z=0.0000, global_m2 z=0.0000
- 但周频版显示正常：ffr z=+0.7616, global_m2 z=+0.9344
- 原因：FFR是月频数据(77个点)，ffill到日频后(2352行)，365日滚动窗口内全是重复值
- 中位数 = 所有值 → z = (x - median)/MAD ≈ 0

**解决方案：**
对低频率指标，在原生频率上算z分，再上采样z分本身（而非数据）到日频。

**Native freq z-score 代码模式：**
```python
native_s = s.resample(native_freq).last().dropna()
window_map = {'W': 52, 'M': 12}
z_win = window_map.get(native_freq, ZSCORE_WINDOW)
z = rolling_robust_zscore(native_s, window=z_win, min_periods=z_win//2)
z = z.reindex(daily_grid).ffill()
aligned[name + '_z'] = z  # _z suffix marks pre-computed z-scores
```

然后在 `compute_tilt` 中，`_z` 列跳过第二次 `robust_zscore`，直接 `tanh(z) * direction`。

### 3. 输出文件隔离

两个版本同时运行必须写入不同文件：
- Daily: `macro_tilt_score_daily.json`, `tilt_history_daily.csv`
- Weekly: `macro_tilt_score.json`, `tilt_history.csv`

### 4. 日期截断 Bug

**问题：** 周频版 `W-FRI` 重采样，最新的FRED数据到周二(2026-06-09)但输出日期为2026-06-12（未来周五）。

**修复：** `weekly_grid = weekly_grid[weekly_grid <= today]`

## 历史键文件
- `config.py` — 双模式配置
- `macro_tilt_pipeline.py` — `NATIVE_FREQ`分支逻辑 + `_z`列处理
- `tilt_signal.py` — 默认读日频版JSON

## Cron 配置
- Daily: ID `d1dbe77776b3` → 每日22:00 UTC
- Weekly: ID `b029604e96ee` → 每周五20:00 UTC
