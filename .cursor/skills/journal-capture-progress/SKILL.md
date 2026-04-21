---
name: journal-capture-progress
description: >-
  Capture daily progress into journaling entries/YYYY-MM-DD.md. Ask the user about
  style (overview / detailed / technical), which sections to fill, and any context
  links to attach before running the script.
---

# Capture progress into the journaling repo

Turn raw context (freeform narrative, terminal output pasted in chat, or file references) into a structured daily file under `entries/`. Follow schema in [`.cursor/rules/journaling-repo.mdc`](../../rules/journaling-repo.mdc).

## Ask first — do not assume defaults

Before appending, the agent should confirm at least the following (see [`journaling-interaction.mdc`](../../rules/journaling-interaction.mdc)):

1. **Style** — overview (1–3 sentences), detailed (paragraph + bullets), or technical (long-form with code / command output)?
2. **Sections** — wins, blockers, next steps, metrics, freeform, or a subset?
3. **Context to link** — tickets (`AIAUT-…`), PRs, commits, fetched `context/…` files — include any? If there's a relevant file in `context/`, suggest it.
4. **Date** — today (default) or a specific `--date YYYY-MM-DD`?
5. **Append or overwrite** — if an entry already exists for the date, always prefer append under `### Capture <ISO8601>` in `## Freeform`.

Good captures are shaped by the user, not by a default template.

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
| `--freeform-file PATH` | Read freeform from file (path must be **inside this repo**; relative paths resolve from repo root) |
| `--win` | Repeatable win bullet |
| `--blocker` | Repeatable blocker bullet |
| `--next-step` | Repeatable next-step bullet |
| `--metric key=value` | Repeatable metric line |
| `--tag TAG` | Repeatable tag (stored in frontmatter) |
| `--audience VALUE` | e.g. `manager_update` |

## Examples

Chat example — overview style:

> **You:** capture today's progress
>
> **Agent:** (asks-first) "Quick overview or a detailed technical log? Any wins/blockers/next steps, or just freeform? Anything from `context/` to reference?"
>
> **You:** overview, just wins and next steps, reference context/jira-aiaut-436-….txt
>
> **Agent:** drafts bullets from chat so far, confirms, then runs `append_journal_entry.py --win … --next-step … --freeform "See context/jira-aiaut-436-….txt for background"`.

Script examples:

```bash
python3 .cursor/skills/journal-capture-progress/scripts/append_journal_entry.py \
  --date 2026-04-20 \
  --freeform "Debugged Slack formatter; added tests." \
  --tag work --tag benji

python3 .cursor/skills/journal-capture-progress/scripts/append_journal_entry.py \
  --freeform-file /tmp/session-log.txt \
  --win "CI green on main"
```
