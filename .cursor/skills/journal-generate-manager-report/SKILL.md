---
name: journal-generate-manager-report
description: >-
  Generate period reports from entries/ with selectable audience (manager, self, team, qa)
  and format (markdown or Slack mrkdwn). Captures stay technical; each audience reshapes tone.
---

# Generate period reports from entries

Reads `entries/YYYY-MM-DD.md` between `--from` and `--to` (inclusive). Missing days are skipped.

**Important:** Daily **captures** can be as technical as you want. **Reports** choose *who* the summary is for via `--report-audience`:

| Audience | Use when | What you get |
|----------|----------|----------------|
| `manager` | Leadership / status | Short plain-language paragraph from **Wins** + priority list (**Next Steps**); optional blockers. **No raw freeform** (avoids jargon in channel). |
| `self` | Your own review | Full wins, blockers, next focus, **freeform** from captures, metrics. Slack: optional `<@YOU>` from `JOURNALING_SLACK_USER_ID` or `--slack-user-id`. |
| `team` | Colleagues / channel | Highlights, dependencies, coming up. |
| `qa` | QA / validation | Deliverables, risks/blockers, suggested verification (+ metrics). |

Slack formatting rules: [`.cursor/rules/journaling-slack-formatting.mdc`](../../rules/journaling-slack-formatting.mdc). Repo schema: [`.cursor/rules/journaling-repo.mdc`](../../rules/journaling-repo.mdc).

## Quick start

**working_directory:** repository root of `journaling`.

```bash
# Default: manager audience, Markdown
python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
  --from 2026-04-01 \
  --to 2026-04-20

# Slack mrkdwn for your manager (concise)
python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
  --from 2026-04-01 \
  --to 2026-04-20 \
  --format slack \
  --report-audience manager
```

## Options

| Flag | Purpose |
|------|---------|
| `--from` / `--to` | Date range (inclusive), `YYYY-MM-DD` |
| `--format` | `markdown` (default) or `slack` |
| `--report-audience` | `manager` (default), `self`, `team`, `qa` |
| `--slack-user-id U…` | With `self` + `slack`: prepend mention (else uses `JOURNALING_SLACK_USER_ID` from `.env`) |
| `--output PATH` | Override file path |

Default output: `reports/report-<audience>-<from>-to-<to>.md` or `.slack.txt`.

## Examples

```bash
# Personal Slack check-in with @mention
python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
  --from 2026-04-18 \
  --to 2026-04-20 \
  --format slack \
  --report-audience self

# QA lens for the team
python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
  --from 2026-04-18 \
  --to 2026-04-20 \
  --format slack \
  --report-audience qa
```

Post with `journal-post-slack` using `--file reports/report-<audience>-….slack.txt`.
