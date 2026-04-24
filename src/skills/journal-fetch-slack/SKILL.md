---
name: journal-fetch-slack
description: >-
  Fetch recent messages from a Slack channel (default, named alias, or explicit ID)
  to use as context for progress capture or daily planning. Writes human-readable
  text or raw JSON to stdout or a file under context/.
---

# Fetch Slack messages (journaling context)

Stdlib-only `conversations.history` fetch. Requires bot token in `.env`; bot must be a member of the channel. Required Slack app scopes: `channels:history` (public channels) or `groups:history` (private channels).

## Channels: default, alias, or explicit

Three ways to pick a channel (most-specific wins):

1. `--channel C0123456789` — explicit ID, overrides everything.
2. `--channel-name team` — looks up `JOURNALING_SLACK_CHANNEL_ID_TEAM` in `.env`. Case-insensitive; `-` and spaces are normalized to `_`.
3. Neither — falls back to `JOURNALING_SLACK_CHANNEL_ID` (default).

The `.env` pattern is open-ended: **any** `JOURNALING_SLACK_CHANNEL_ID_<NAME>` works. Example aliases in [`.env.example`](../../.env.example):

```bash
JOURNALING_SLACK_CHANNEL_ID_SELF=C0…
JOURNALING_SLACK_CHANNEL_ID_TEAM=C0…
JOURNALING_SLACK_CHANNEL_ID_DEV_QA=C0…
JOURNALING_SLACK_CHANNEL_ID_BENJI3_DEV=C0…
```

The agent should **ask first** when a channel is ambiguous (see [`journaling-interaction.md`](../../rules/journaling-interaction.md)) and can list configured aliases with `--list-channels`.

## Quick start

**working_directory:** repository root of `journaling`.

```bash
# List configured aliases
python3 src/skills/journal-fetch-slack/scripts/fetch_slack_messages.py --list-channels

# Default channel, last 50 messages (stdout)
python3 src/skills/journal-fetch-slack/scripts/fetch_slack_messages.py

# Named alias, last 24 hours, auto-save to context/
python3 src/skills/journal-fetch-slack/scripts/fetch_slack_messages.py \
  --channel-name dev-qa --hours 24 --save
# → context/slack-C03333CCCCC-2026-04-20-to-2026-04-21.txt
```

## Options

| Flag | Purpose |
|------|---------|
| `--channel` | Explicit Slack channel ID (overrides `--channel-name` and default) |
| `--channel-name` | Alias from `JOURNALING_SLACK_CHANNEL_ID_<NAME>` (e.g. `team`, `dev-qa`, `self`) |
| `--limit N` | Max messages to fetch (default: 50, max: 200) |
| `--since YYYY-MM-DD` | Fetch messages on or after this date |
| `--hours N` | Fetch messages from last N hours |
| `--save` | Auto-save to `context/slack-{channel}-{from}-to-{to}.txt` |
| `--output PATH` | Write to explicit file inside repo (mutually exclusive with `--save`) |
| `--format text\|json` | Output format (default: text) |
| `--token-var` | Env var for bot token (default: `JOURNALING_SLACK_BOT_TOKEN`) |
| `--json` | Print one JSON line: `ok`, `count`, `path` (requires `--output` or `--save`) |
| `--list-channels` | Print configured aliases and exit |

`--since` and `--hours` are mutually exclusive. `--save` and `--output` are mutually exclusive. `--channel` and `--channel-name` are mutually exclusive.

## Examples

```bash
# Pull from team channel since a specific date and save
python3 src/skills/journal-fetch-slack/scripts/fetch_slack_messages.py \
  --channel-name team --since 2026-04-20 --save

# One-off channel ID, last 8 hours
python3 src/skills/journal-fetch-slack/scripts/fetch_slack_messages.py \
  --hours 8 --channel C0987654321 --save
```

## Chat example

> **You:** catch me up on dev-qa from yesterday
>
> **Agent:** (asks-first) "Last 24 hours on `#dev-qa`? That's `JOURNALING_SLACK_CHANNEL_ID_DEV_QA` → `C0…` in your `.env`. OK to save to `context/`?"
>
> **You:** yes
>
> **Agent:** runs `fetch_slack_messages.py --channel-name dev-qa --hours 24 --save` and summarizes the thread back to you.

## Typical use in daily planning flow

1. Fetch channel activity (`--save` → `context/slack-…txt`).
2. Pass that file to `generate_daily_plan.py --context-file context/slack-…txt`.
3. Review the plan → use `journal-capture-progress` to log today's entry.

## Security notes

- `--channel` must be a Slack **conversation ID** (e.g. `C0123456789`), not `#channel-name`.
- `--output` must point to a path **inside this repository**.
- Token only via env / `.env` — see [`src/rules/journaling-repo.md`](../../rules/journaling-repo.md).
- Message text is truncated at 500 chars per message in text format to keep context manageable.

## Shared helpers

Scripts load tokens via [`src/skills/_shared/script_utils.py`](../_shared/script_utils.py). Repo root and safe paths: [`journaling_repo.py`](../_shared/journaling_repo.py), [`path_guard.py`](../_shared/path_guard.py).
