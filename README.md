# Journaling

Local-first **progress capture**, **manager report** generation, and optional **Slack** posting — driven by Cursor skills and the **journaling specialist** subagent.

## Layout

| Path | Purpose |
|------|---------|
| `entries/YYYY-MM-DD.md` | Daily hybrid entries (freeform + structured sections) |
| `reports/manager-report-<from>-to-<to>.md` | Generated manager updates |
| `.cursor/rules/journaling-repo.mdc` | Schema, architecture, editing conventions |
| `.cursor/agents/journaling-specialist.md` | Subagent: which skill to use and when |
| `.cursor/skills/journal-capture-progress/` | Append or create daily entries |
| `.cursor/skills/journal-generate-manager-report/` | Roll entries into a report |
| `.cursor/skills/journal-post-slack/` | Post message or report file to Slack |

## Quick start

1. Copy [`.env.example`](.env.example) to `.env` and set a Slack bot token if you use `journal-post-slack`.
2. Capture progress (from repo root):

   ```bash
   python3 .cursor/skills/journal-capture-progress/scripts/append_journal_entry.py \
     --freeform "What you shipped today." \
     --win "Concrete win"
   ```

3. Generate a manager report:

   ```bash
   python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
     --from 2026-04-01 \
     --to 2026-04-20
   ```

4. Post to Slack (requires channel ID):

   ```bash
   python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
     --file reports/manager-report-2026-04-01-to-2026-04-20.md \
     --channel YOUR_CHANNEL_ID
   ```

In Cursor, use **`@journal-capture-progress`**, **`@journal-generate-manager-report`**, **`@journal-post-slack`**, or the **`journaling-specialist`** agent to chain these steps.

## Secrets

Keep tokens in `.env` (gitignored). See each skill’s `SKILL.md` for `--token-var` options.

## Security

Scripts follow the repo rule [`.cursor/rules/journaling-repo.mdc`](.cursor/rules/journaling-repo.mdc): no hardcoded secrets, safe file paths under this repo for `--file` / `--output`, and Slack channel IDs (not `#names`). If your workspace includes the X-Team standards repo, cross-check `standards/rules/` (e.g. hardcoded secrets, sensitive data in logs/errors).
