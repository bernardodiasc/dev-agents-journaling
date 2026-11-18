# Capture progress (daily log)

Appends to `entries/YYYY-MM-DD.md` in the journaling home. Status updates read these
entries, so a quick log line today makes tomorrow's update better. Posting a status
update logs its Done, Blocked and Next lines here too (`references/status-update.md`).

## Defaults — just do it

"log that I merged #412 and I'm blocked on staging access" → write it. Infer the
section from the wording (shipped/merged/fixed → win, waiting/blocked → blocker,
will/next/tomorrow → next step) and keep the user's words. Today's date unless they
name one. Keep any GitHub URLs they mention — they become links in status updates.
Confirm afterwards in one line ("Logged 1 win, 1 blocker to entries/2026-11-11.md").
Only ask when you truly can't tell what to log.

```bash
python3 $SKILL/scripts/append_journal_entry.py \
  --win "Merged search filters https://github.com/acme/api/pull/412" \
  --blocker "Waiting on staging DB access from infra" \
  --next-step "Start invoice export"
```

| Flag | Purpose |
|------|---------|
| `--date YYYY-MM-DD` | Entry date (default today) |
| `--freeform "..."` / `--freeform-file PATH` | Narrative / technical notes (file must be inside the journaling home) |
| `--win`, `--blocker`, `--next-step` | Repeatable bullets |
| `--metric key=value` | Repeatable metric |
| `--tag TAG` | Repeatable frontmatter tag |

Multiple captures on one day append under `### Capture <ISO8601>` in `## Freeform`;
existing content is never overwritten. You may also edit the file directly using the
same headings (`## Freeform`, `## Wins`, `## Blockers`, `## Next Steps`, `## Metrics`).

## Entry schema

```markdown
---
date: 2026-11-11
tags: [work]
---
## Freeform
### Capture 2026-11-11T14:02:00Z
Free text…

## Wins
- …
## Blockers
- …
## Next Steps
- …
## Metrics
- prs_merged: 2
```
