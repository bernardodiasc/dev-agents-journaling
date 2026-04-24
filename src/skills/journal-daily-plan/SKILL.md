---
name: journal-daily-plan
description: >-
  Two-phase daily planning: first a catch-up from recent entries + any queued context,
  then (after user confirms) save the plan under plans/plan-YYYY-MM-DD.md. Slack
  sibling is produced only at post time.
---

# Daily planning brief (journaling)

Planning is a **conversation**, not a single command. The skill runs in two phases.

## Phase 1 — catch-up (always)

Read the last N days of `entries/YYYY-MM-DD.md` (default 7). Print to chat:

- What was completed / planned / outstanding.
- Recent blockers and which are resolved.
- Any context the user has pre-gathered in `context/` (Slack, Jira) that should factor in.

Then **propose a plan shape** — a few bullets of "here's what I'd focus on today" — and ask the user what they want to keep, drop, or add.

*No files are written during phase 1.* Run `generate_daily_plan.py` without `--save` (print to stdout) to build the catch-up view.

## Phase 2 — generate (on confirmation)

Only once the user has confirmed the plan:

```bash
python3 src/skills/journal-daily-plan/scripts/generate_daily_plan.py \
  --context-file context/slack-C012-2026-04-20-to-2026-04-21.txt \
  --save
# → plans/plan-2026-04-21.md
```

The Slack-mrkdwn sibling (`plans/plan-YYYY-MM-DD.slack.txt`) is **not** produced here. It will be created by `journal-post-slack` only at the moment of posting. A missing `.slack.txt` next to a plan means the plan was never posted.

## Options (`generate_daily_plan.py`)

| Flag | Purpose |
|------|---------|
| `--lookback DAYS` | Days of entries to include (default: 7) |
| `--context-file PATH` | Context file to embed verbatim (Slack dump, Jira link file, notes) |
| `--slack-context-file PATH` | Deprecated alias for `--context-file` |
| `--save` | Auto-save to `plans/plan-YYYY-MM-DD.md` (mutually exclusive with `--output`) |
| `--output PATH` | Write plan to one explicit file inside repo |

## Full flow

```bash
# 1. Gather context (ask-first via journal-gather-context; examples here)
python3 src/skills/journal-fetch-slack/scripts/fetch_slack_messages.py \
  --channel-name dev-qa --hours 24 --save

python3 src/skills/journal-fetch-jira/scripts/save_jira_context.py \
  --kind ticket --url https://x-team-internal.atlassian.net/browse/AIAUT-436

# 2. Phase 1 — catch-up (stdout, no file written)
python3 src/skills/journal-daily-plan/scripts/generate_daily_plan.py \
  --context-file context/slack-C012-2026-04-20-to-2026-04-21.txt

# 3. User confirms → Phase 2 (save)
python3 src/skills/journal-daily-plan/scripts/generate_daily_plan.py \
  --context-file context/slack-C012-2026-04-20-to-2026-04-21.txt --save

# 4. (Optional) Post to Slack — this is when the .slack.txt is created
python3 src/skills/journal-post-slack/scripts/post_slack_message.py \
  --file plans/plan-2026-04-21.md --channel-name self
```

## Examples (chat)

> **You:** help me plan today
>
> **Agent:** (phase 1) reads last 7 days, prints catch-up + suggested focus; asks "want me to fetch Slack or Jira context first? Then keep, drop, or add anything to this draft?"
>
> **You:** fetch dev-qa last 24h, then save plan
>
> **Agent:** fetches, re-runs catch-up with `--context-file`, shows updated draft → waits for confirm → phase 2 saves `plans/plan-2026-04-21.md`.

## Shared helpers

Uses [`_shared/journaling_repo.py`](../_shared/journaling_repo.py) and [`_shared/path_guard.py`](../_shared/path_guard.py). No token needed.
