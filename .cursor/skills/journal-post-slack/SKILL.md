---
name: journal-post-slack
description: >-
  Post a Slack message using a bot token from .env. Use to share journaling reports
  or status text; supports body from argument, --file, or stdin.
---

# Post to Slack (journaling)

Stdlib-only `chat.postMessage`. Token resolution matches team convention: set `JOURNALING_SLACK_BOT_TOKEN` or any `SLACK_*` variable in repo-root `.env` (see `.env.example`).

## Quick start

**working_directory:** repository root of `journaling`.

```bash
python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  "Weekly update: see thread" \
  --channel YOUR_CHANNEL_ID
```

## Options

| Flag | Purpose |
|------|---------|
| `message` (positional) | Message text (optional if `--file` or stdin) |
| `--file`, `-f` | Read body from file (e.g. generated report) |
| `--channel` | **Required.** Slack channel ID |
| `--thread-ts` | Reply in thread |
| `--token-var` | Env var name (default: `JOURNALING_SLACK_BOT_TOKEN`) |
| `--json` | One JSON line: `ok`, `channel`, `ts` |

## Examples

```bash
# Post a generated report
python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  --file reports/manager-report-2026-04-01-to-2026-04-20.md \
  --channel C0123456789

# Pipe excerpt
head -n 40 reports/manager-report-2026-04-01-to-2026-04-20.md | \
  python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  --channel C0123456789
```

## Security notes

- **`--channel`** must be a Slack **conversation ID** (e.g. `C0123456789`), not `#channel-name`.
- **`--file`** must point to a path **inside this repository** (relative paths are resolved from the repo root). Large files are rejected; message body must fit Slack’s text limit (see script).
- **Secrets:** token only via env / `.env` — see [`.cursor/rules/journaling-repo.mdc`](../../rules/journaling-repo.mdc).

## Shared helpers

Scripts load tokens via [`.cursor/skills/_shared/script_utils.py`](../_shared/script_utils.py). Repo root and safe paths: [`journaling_repo.py`](../_shared/journaling_repo.py), [`path_guard.py`](../_shared/path_guard.py).
