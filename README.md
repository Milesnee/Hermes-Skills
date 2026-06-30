# Hermes Skills Hub

A curated collection of reusable Hermes Agent skills for quantitative trading, macro analysis, and crypto research.

## Skills

### 🪙 tokenomics-screener
Screens 27 major crypto coins across 8 tokenomics dimensions (supply schedule, inflation, vesting, treasury, emissions, staking, governance, utility). Generates structured scoring and risk flags.

**Tags:** `#crypto` `#tokenomics` `#screening` `#fundamental`

### 📈 macro-factor-synthesis
Synthesizes 10+ macro indicators into a single directional tilt signal `[-1, +1]` for crypto/risk assets. 3-bucket architecture — USD liquidity (40%), crypto liquidity (35%), risk appetite (25%). Robust rolling z-scores (median+MAD), tanh clamping, correlation modulation, EWM smoothing (halflife=28d), dead zone (0.2). Dual frequency (daily/weekly) with NATIVE_FREQ system for monthly/weekly indicators. Live FRED API + YFinance + DeFi Llama pipeline.

**Tags:** `#macro` `#crypto` `#factor-model` `#signal-generation` `#trading-system`

### 📹 youtube-content
Extracts and processes YouTube video transcripts — full text, structured notes, summaries. Supports Whisper batch transcription fallback.

**Tags:** `#youtube` `#transcript` `#content` `#media`

### hermes-tweet-signal
Uses the Hermes Tweet plugin for X/Twitter market narrative research, public reply analysis, launch monitoring, and approval-gated account actions.

**Tags:** `#twitter` `#x` `#crypto` `#market-research`

### 🏆 laowang-gold-framework
老王黄金框架改进版 — 五因素黄金多空信号检测。美联储利率(50%)+央行购金(20%)+美股(10%)+ETF/期货(25%)+参考系调节因子(±15%乘性)。含独立评审报告和实时信号脚本。

**Tags:** `#gold` `#commodities` `#macro` `#trading-system` `#factor-model`

## Usage

Skills are designed for [Hermes Agent](https://hermes-agent.nousresearch.com). To use a skill:

```bash
# Load in a session
hermes skill use <skill-name>

# Or reference in cron jobs
hermes cron create --skills <skill-name> --schedule "0 9 * * *" --prompt "..."
```

Each skill directory contains:
- `SKILL.md` — Full documentation with architecture, usage, pitfalls
- `references/` — Detailed guides (data sources, APIs, backtest results)
- `scripts/` — Runnable pipeline scripts
