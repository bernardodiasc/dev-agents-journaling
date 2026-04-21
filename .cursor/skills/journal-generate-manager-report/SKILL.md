---
name: journal-generate-manager-report
description: >-
  Generate period reports from entries/ for all audiences (manager, self, team, qa)
  as Markdown — kept in sync. Slack sibling .slack.txt is produced only at post time.
---

# Generate period reports from entries

Reads `entries/YYYY-MM-DD.md` between `--from` and `--to` (inclusive). Missing days are skipped. The default behavior writes **all four audience `.md` reports together** so the set on disk stays in sync — if one is out of date, they all are.

**Captures** in `entries/` can stay as technical as you want. **Reports** reshape the same fields per audience:

| Audience | Use when | What you get |
|----------|----------|--------------|
| `manager` | Leadership / status | Short plain-language paragraph from Wins + priority list (Next Steps); optional blockers. No raw freeform. |
| `self` | Personal review | Full wins, blockers, next focus, freeform from captures, metrics. |
| `team` | Colleagues / channel | Highlights, dependencies, coming up. |
| `qa` | QA / validation | Deliverables, risks/blockers, suggested verification (+ metrics). |

Slack `.slack.txt` is **not** generated here — it is created at post time by [`journal-post-slack`](../journal-post-slack/SKILL.md). See [`journaling-interaction.mdc`](../../rules/journaling-interaction.mdc) for the rationale (the sibling is a delivery receipt).

## Ask first

Before running, confirm with the user (see [`journaling-interaction.mdc`](../../rules/journaling-interaction.mdc)):

- **Date range** (`--from` / `--to`).
- **Which subset to post later** (reports are always generated in full; posting is a separate decision).

## Quick start

**working_directory:** repository root of `journaling`.

```bash
# Default: all audiences, Markdown (kept in sync)
python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
  --from 2026-04-01 --to 2026-04-20
# → reports/report-manager-2026-04-01-to-2026-04-20.md
# → reports/report-self-2026-04-01-to-2026-04-20.md
# → reports/report-team-2026-04-01-to-2026-04-20.md
# → reports/report-qa-2026-04-01-to-2026-04-20.md
```

## Options

| Flag | Purpose |
|------|---------|
| `--from` / `--to` | Date range (inclusive), `YYYY-MM-DD` |
| `--all-audiences` | Write all four Markdown reports (default when `--report-audience` is omitted) |
| `--report-audience manager\|self\|team\|qa` | Write just one audience (advanced; breaks sync invariant) |
| `--output PATH` | Override output path (requires `--report-audience`) |
| `--format markdown\|slack` | Default `markdown`. `slack` is retained for advanced use — prefer `journal-post-slack` instead. |
| `--slack-user-id U…` | With `--report-audience self --format slack`: prepend mention (else uses `JOURNALING_SLACK_USER_ID`) |

## Examples

```bash
# Generate all four reports for last two weeks
python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
  --from 2026-04-07 --to 2026-04-20

# (advanced) just the QA audience, custom output path
python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
  --from 2026-04-18 --to 2026-04-20 \
  --report-audience qa --output reports/qa-preview.md
```

## Chat example

> **You:** report for the last two weeks
>
> **Agent:** (asks-first) "Date range: 2026-04-07 → 2026-04-20? I'll generate all four `.md` audiences so they stay in sync. Post to Slack afterwards?"
>
> **You:** yes, and post the manager one to the team channel after
>
> **Agent:** runs `generate_manager_report.py --from 2026-04-07 --to 2026-04-20` → confirms 4 files → then `post_slack_message.py --file reports/report-manager-… .md --channel-name team` (which renders `.slack.txt` at post time).

## Finding unposted reports

Any `.md` in `reports/` without a sibling `.slack.txt` has never been posted:

```bash
for md in reports/*.md; do
  [ -f "${md%.md}.slack.txt" ] || echo "unposted: $md"
done
```

Full Slack formatting rules: [`.cursor/rules/journaling-slack-formatting.mdc`](../../rules/journaling-slack-formatting.mdc). Repo schema: [`.cursor/rules/journaling-repo.mdc`](../../rules/journaling-repo.mdc).
