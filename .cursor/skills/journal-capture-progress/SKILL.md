---
name: journal-capture-progress
description: >-
  Capture daily progress into journaling entries/YYYY-MM-DD.md from chat context,
  pasted logs, or @ file paths. Use after a job/session or when consolidating wins,
  blockers, and next steps into the repo.
---

# Capture progress into the journaling repo

Turn raw context (freeform narrative, terminal output pasted in chat, or file references) into a structured daily file under `entries/`. Follow schema in [`.cursor/rules/journaling-repo.mdc`](../../rules/journaling-repo.mdc).

## Quick start

**working_directory:** repository root of `journaling` (stdlib only — no extra packages).

```bash
python3 .cursor/skills/journal-capture-progress/scripts/append_journal_entry.py \
  --freeform "Shipped X; fixed Y." \
  --win "Merged PR for X" \
  --blocker "Waiting on API access" \
  --next-step "Ping owner Tuesday"
```

## When the user does not run the script

The agent may **edit `entries/YYYY-MM-DD.md` directly** using the same section headings (`## Freeform`, `## Wins`, …) and append under `### Capture <ISO8601>` inside Freeform for multiple captures per day — matching what the script does.

## Options (`append_journal_entry.py`)

| Flag | Purpose |
|------|---------|
| `--date YYYY-MM-DD` | Entry date (default: today local date from script) |
| `--freeform "..."` | Freeform paragraph |
| `--freeform-file PATH` | Read freeform from file |
| `--win` | Repeatable win bullet |
| `--blocker` | Repeatable blocker bullet |
| `--next-step` | Repeatable next-step bullet |
| `--metric key=value` | Repeatable metric line |
| `--tag TAG` | Repeatable tag (stored in frontmatter) |
| `--audience VALUE` | e.g. `manager_update` |

## Examples

```bash
python3 .cursor/skills/journal-capture-progress/scripts/append_journal_entry.py \
  --date 2026-04-20 \
  --freeform "Debugged Slack formatter; added tests." \
  --tag work --tag benji

python3 .cursor/skills/journal-capture-progress/scripts/append_journal_entry.py \
  --freeform-file /tmp/session-log.txt \
  --win "CI green on main"
```
