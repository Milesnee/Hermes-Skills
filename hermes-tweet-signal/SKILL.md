---
name: hermes-tweet-signal
description: Use Hermes Tweet for X/Twitter market narrative research, crypto project monitoring, public replies, and approval-gated account actions.
version: 0.1.6
author: Xquik
license: MIT
tags:
  - hermes-agent
  - xquik
  - twitter
  - crypto
  - market-research
---

# Hermes Tweet Signal

Use this skill when crypto, macro, or content research needs current X/Twitter
signals through the native Hermes Tweet plugin.

## Install

```bash
hermes plugins install Xquik-dev/hermes-tweet --enable
hermes tools list
```

Set `XQUIK_API_KEY` in the Hermes runtime environment before authenticated
reads. Keep `HERMES_TWEET_ENABLE_ACTIONS` disabled unless the user explicitly
approves a write or account action.

## Workflow

1. Define the asset, project, account, keyword, or narrative to inspect.
2. Use `tweet_explore` to choose the endpoint.
3. Use `tweet_read` for searches, replies, profiles, trends, and monitoring context.
4. Summarize evidence and separate market signal from speculation.
5. Use `tweet_action` only after confirming the exact account, payload, and reason.

## Useful Outputs

- Narrative snapshot for a token or macro theme.
- Reply themes under a founder, protocol, or news post.
- Launch monitoring notes for a crypto or content campaign.
- Approved post or reply draft with source-backed context.
