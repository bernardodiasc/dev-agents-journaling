---
name: journal-generate-manager-report
description: >-
  Build a manager-focused markdown report from entries/ for an inclusive date range.
  Writes reports/manager-report-<from>-to-<to>.md.
---

# Generate manager report from entries

Reads `entries/YYYY-MM-DD.md` files between `--from` and `--to` (inclusive). Days without a file are skipped. Output format is documented in [`.cursor/rules/journaling-repo.mdc`](../../rules/journaling-repo.mdc).

## Quick start

**working_directory:** repository root of `journaling`.

```bash
python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
  --from 2026-04-01 \
  --to 2026-04-20
```

## Options

| Flag | Purpose |
|------|---------|
| `--from YYYY-MM-DD` | Start date (inclusive) |
| `--to YYYY-MM-DD` | End date (inclusive) |
| `--output PATH` | Override output path (default: `reports/manager-report-<from>-to-<to>.md`) |

## Behavior

- **Executive summary** — short bullets from wins and next steps in range.
- **Highlights** — deduplicated wins.
- **Completed work** — freeform sections per day.
- **Blockers / risks**, **Next actions**, **Metrics snapshot** — aggregated lists.
- **Source entries** — list of files used.

## Example

```bash
python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
  --from 2026-04-18 \
  --to 2026-04-20 \
  --output reports/manager-update-sprint.md
```
