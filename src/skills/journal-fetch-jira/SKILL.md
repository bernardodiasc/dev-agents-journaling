---
name: journal-fetch-jira
description: >-
  Save a link-based Jira context file (ticket, epic, project, or freeform note) under
  context/. No API call — just URLs and optional notes. Use as context for capture or
  for daily planning.
---

# Save Jira context (link-based, no API)

Record pasted Jira URLs plus optional notes as a text file under `context/`. The file can then be embedded in a daily plan (`generate_daily_plan.py --context-file …`) or referenced by the journaling specialist during capture.

**No Jira API is called.** This skill is deliberately a lightweight capture surface; the bar for adding it to your workflow is zero (no token, no scopes).

## When to use

Use when the user says things like:
- "save context for the AIAUT-436 ticket"
- "log the onboarding epic from Jira"
- "capture this project board I'm working on"
- "remember this link so we can reference it during planning"

The agent should **ask first** (see [`journaling-interaction.md`](../../rules/journaling-interaction.md)): which kind of context (ticket / epic / project / note)? which URL(s)? any notes on why this matters?

## Quick start

**working_directory:** repository root of `journaling`.

```bash
# Single ticket
python3 src/skills/journal-fetch-jira/scripts/save_jira_context.py \
  --kind ticket \
  --url https://x-team-internal.atlassian.net/browse/AIAUT-436 \
  --note "Blocker for FJ-01 QA"
# → context/jira-aiaut-436-2026-04-21.txt

# Epic with multiple child links + named slug
python3 src/skills/journal-fetch-jira/scripts/save_jira_context.py \
  --kind epic \
  --url https://x-team-internal.atlassian.net/browse/AIAUT-400 \
  --url https://x-team-internal.atlassian.net/browse/AIAUT-436 \
  --slug fj-01-search-transparency \
  --title "Search transparency epic" \
  --note "Business domain scope: candidate-facing job search flow."
# → context/jira-fj-01-search-transparency-2026-04-21.txt
```

## Options

| Flag | Purpose |
|------|---------|
| `--kind ticket\|epic\|project\|note` | Scope classifier (required) |
| `--url URL` (repeatable) | Atlassian URL(s). Required for ticket/epic/project |
| `--title TEXT` | Human title recorded in the file |
| `--note TEXT` (repeatable) | Free-form note(s) about why this context matters |
| `--note-file PATH` | Append notes from a file inside the repo |
| `--slug a-z0-9-` | Filename slug (default: derived from URL key) |
| `--output PATH` | Override output path |
| `--stdout` | Print to stdout (no file written) |

## Security notes

- Only `https://*.atlassian.net/...` URLs are accepted.
- If `JOURNALING_JIRA_BASE_URL` is set, all URLs must match it (prevents cross-workspace mixups).
- Output path is resolved inside the repo only.

## Examples

Chat example:

> **You:** remember the AIAUT-436 ticket as context for today's plan
>
> **Agent:** (asks-first) "What kind of context — just the ticket, or the whole epic? Any notes about why it matters right now?"
>
> **You:** ticket only, it's blocking my FJ-01 QA
>
> **Agent:** runs `save_jira_context.py --kind ticket --url https://…/browse/AIAUT-436 --note "Blocking FJ-01 QA"` and confirms the path.

## Future API support

If we later add a Jira API token, the SKILL will gain `--fetch-summary` to pull issue fields. Not implemented today — the link + notes pattern is sufficient for context purposes.

## Shared helpers

Uses [`_shared/journaling_repo.py`](../_shared/journaling_repo.py), [`_shared/path_guard.py`](../_shared/path_guard.py), and [`_shared/script_utils.py`](../_shared/script_utils.py) for `JOURNALING_JIRA_BASE_URL`.
