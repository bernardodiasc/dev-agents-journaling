---
name: journal-post-slack
description: >-
  Post a Slack message using a bot token from .env. Use to share journaling reports
  or status text; supports body from argument, --file, or stdin.
---

# Post to Slack (journaling)

Stdlib-only `chat.postMessage`. Configure **repo-root** `.env` from [`.env.example`](../../.env.example): bot token, optional default **`JOURNALING_SLACK_CHANNEL_ID`**, optional **`JOURNALING_SLACK_USER_ID`** (for `--prepend-user-mention`). Token vars: `JOURNALING_SLACK_BOT_TOKEN` or any `SLACK_*` name.

**Message body:** use **Slack mrkdwn**, not GitHub Markdown. For manager reports, generate with `generate_manager_report.py --format slack` and post the `.slack.txt` file. Rules: [`.cursor/rules/journaling-slack-formatting.mdc`](../../rules/journaling-slack-formatting.mdc).

## Quick start

**working_directory:** repository root of `journaling`.

```bash
# With JOURNALING_SLACK_CHANNEL_ID set in .env — omit --channel
python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  "Weekly update: see thread"
```

## Options

| Flag | Purpose |
|------|---------|
| `message` (positional) | Message text (optional if `--file` or stdin) |
| `--file`, `-f` | Read body from file (e.g. generated report) |
| `--channel` | Slack channel ID (optional if `JOURNALING_SLACK_CHANNEL_ID` is in `.env`) |
| `--prepend-user-mention` | Prepend `<@USER_ID>` using `JOURNALING_SLACK_USER_ID` from `.env` |
| `--thread-ts` | Reply in thread |
| `--token-var` | Env var name (default: `JOURNALING_SLACK_BOT_TOKEN`) |
| `--json` | One JSON line: `ok`, `channel`, `ts` |

## Examples

```bash
# Post a Slack-formatted report (use report-<audience>-… from generate_manager_report)
python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  --file reports/report-manager-2026-04-01-to-2026-04-20.slack.txt

# Override channel for one run
python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  "Hello" \
  --channel C0123456789

# Pipe excerpt (Slack-formatted file)
head -n 40 reports/report-manager-2026-04-01-to-2026-04-20.slack.txt | \
  python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py
```

## Security notes

- **`--channel`** must be a Slack **conversation ID** (e.g. `C0123456789`), not `#channel-name`.
- **`--file`** must point to a path **inside this repository** (relative paths are resolved from the repo root). Large files are rejected; message body must fit Slack’s text limit (see script).
- **Secrets:** token only via env / `.env` — see [`.cursor/rules/journaling-repo.mdc`](../../rules/journaling-repo.mdc).

## Shared helpers

Scripts load tokens via [`.cursor/skills/_shared/script_utils.py`](../_shared/script_utils.py). Repo root and safe paths: [`journaling_repo.py`](../_shared/journaling_repo.py), [`path_guard.py`](../_shared/path_guard.py).
