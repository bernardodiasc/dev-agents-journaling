---
name: journal-post-slack
description: >-
  Post a Slack message using a bot token. If --file points to a .md, renders the
  Slack-mrkdwn sibling .slack.txt just-in-time and posts that. The .slack.txt is
  the receipt — its presence means the file was delivered.
---

# Post to Slack (journaling)

Stdlib-only `chat.postMessage`. Configure **repo-root** `.env` from [`.env.example`](../../.env.example): bot token, optional `JOURNALING_SLACK_CHANNEL_ID` (default channel), optional `JOURNALING_SLACK_USER_ID` (for `--prepend-user-mention`), and any number of `JOURNALING_SLACK_CHANNEL_ID_<NAME>` aliases.

**Receipt invariant:** when the target is a `.md` under `reports/` or `plans/`, this skill renders the sibling `.slack.txt` *just before* posting (via [`journal-render-slack`](../journal-render-slack/SKILL.md)) and posts that content. The sibling is **left on disk as proof of delivery** — the existence of `plan-2026-04-21.slack.txt` means that plan was posted. If the Slack API call fails, the half-written sibling is deleted so the invariant holds.

## Channel selection

Same three-way resolution as [`journal-fetch-slack`](../journal-fetch-slack/SKILL.md):

1. `--channel C0…` — explicit ID.
2. `--channel-name alias` — looks up `JOURNALING_SLACK_CHANNEL_ID_<ALIAS>` in `.env` (case-insensitive, `-` / space → `_`).
3. Fall back to `JOURNALING_SLACK_CHANNEL_ID`.

**Always confirm the target channel** before posting (see [`journaling-interaction.mdc`](../../rules/journaling-interaction.mdc)).

## Quick start

**working_directory:** repository root of `journaling`.

```bash
# Post a Markdown report to the default channel (renders .slack.txt first)
python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  --file reports/report-manager-2026-04-01-to-2026-04-20.md

# Post a plan to a named channel
python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  --file plans/plan-2026-04-21.md --channel-name self

# Dry-run: preview the rendered Slack text, do not post
python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  --file reports/report-team-2026-04-01-to-2026-04-20.md --dry-run

# Inline message
python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  "Weekly update: see thread" --channel-name team
```

## Options

| Flag | Purpose |
|------|---------|
| `message` (positional) | Message text (optional if `--file` or stdin) |
| `--file`, `-f` | Read body from file. `.md` → renders sibling `.slack.txt` first; other types are posted as-is. |
| `--channel` | Explicit Slack channel ID |
| `--channel-name` | Alias from `.env` (e.g. `team`, `dev-qa`, `self`) |
| `--prepend-user-mention` | Prepend `<@USER_ID>` using `JOURNALING_SLACK_USER_ID` |
| `--thread-ts` | Reply in thread |
| `--dry-run` | Render (if `.md`) but do not post; prints body that would be sent |
| `--token-var` | Env var name (default: `JOURNALING_SLACK_BOT_TOKEN`) |
| `--json` | One JSON line: `ok`, `channel`, `ts` (or `ok`, `dry_run` for `--dry-run`) |

## Examples (chat)

> **You:** post my latest plan
>
> **Agent:** (asks-first) "Found `plans/plan-2026-04-21.md`. Which channel — default `JOURNALING_SLACK_CHANNEL_ID`, or an alias like `self` / `team`? Should I `@`-mention you?"
>
> **You:** self, mention me
>
> **Agent:** runs `post_slack_message.py --file plans/plan-2026-04-21.md --channel-name self --prepend-user-mention` → writes `plans/plan-2026-04-21.slack.txt` (the receipt) → posts → shows message ts.

Find unposted reports/plans:

```bash
# Any .md under reports/ or plans/ without a .slack.txt sibling is unposted.
for md in reports/*.md plans/*.md; do
  [ -f "${md%.md}.slack.txt" ] || echo "unposted: $md"
done
```

## Security notes

- **`--channel`** must be a Slack **conversation ID** (e.g. `C0123456789`), not `#channel-name`.
- **`--file`** must point to a path **inside this repository** (relative paths are resolved from the repo root). Large files are rejected; message body must fit Slack's text limit (see script).
- **Secrets:** token only via env / `.env` — see [`.cursor/rules/journaling-repo.mdc`](../../rules/journaling-repo.mdc).

## Shared helpers

Scripts load tokens via [`.cursor/skills/_shared/script_utils.py`](../_shared/script_utils.py). Repo root and safe paths: [`journaling_repo.py`](../_shared/journaling_repo.py), [`path_guard.py`](../_shared/path_guard.py). Slack conversion: [`journal-render-slack`](../journal-render-slack/SKILL.md).
