# Journaling

Local-first **progress capture**, **period reports** (multiple audiences), and optional **Slack** posting — driven by Cursor skills and the **journaling specialist** subagent.

## Layout

| Path | Purpose |
|------|---------|
| `entries/YYYY-MM-DD.md` | Daily hybrid entries (freeform + structured sections); captures can be **technical**. |
| `reports/report-<audience>-<from>-to-<to>.md` | Generated reports (Markdown). |
| `reports/report-<audience>-<from>-to-<to>.slack.txt` | Same report as Slack **mrkdwn** for posting. |
| `.cursor/rules/journaling-repo.mdc` | Schema, report audiences, editing conventions |
| `.cursor/agents/journaling-specialist.md` | Subagent: which skill to use and when |
| `.cursor/skills/journal-capture-progress/` | Append or create daily entries |
| `.cursor/skills/journal-generate-manager-report/` | Build reports from `entries/` |
| `.cursor/skills/journal-post-slack/` | Post message or report file to Slack |

## Report audiences

Use `--report-audience` when generating reports:

- **`manager`** — Short leadership summary: plain-language paragraph from **Wins** + **Priorities ahead**; no raw freeform dump.
- **`self`** — Full detail including freeform (your technical notes); Slack can prepend `<@you>` via `JOURNALING_SLACK_USER_ID`.
- **`team`** — Colleague-friendly: highlights, dependencies, coming up.
- **`qa`** — QA / validation lens: deliverables, risks, suggested verification.

See [`.cursor/rules/journaling-repo.mdc`](.cursor/rules/journaling-repo.mdc) for the full table.

## Quick start

1. Copy [`.env.example`](.env.example) to `.env` and fill in at least the **bot token** and **`JOURNALING_SLACK_CHANNEL_ID`**. Set **`JOURNALING_SLACK_USER_ID`** if you want `@mentions` on **self** Slack reports or `post_slack_message.py --prepend-user-mention`. Invite the bot to the channel; app needs `chat:write`.

2. Capture progress (from repo root):

   ```bash
   python3 .cursor/skills/journal-capture-progress/scripts/append_journal_entry.py \
     --freeform "What you shipped today." \
     --win "Concrete win"
   ```

3. Generate reports:

   ```bash
   # Leadership / manager (default) — Markdown
   python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
     --from 2026-04-01 \
     --to 2026-04-20

   # Slack file for your manager (concise mrkdwn)
   python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
     --from 2026-04-01 \
     --to 2026-04-20 \
     --format slack \
     --report-audience manager
   ```

4. Post to Slack (see [`.cursor/rules/journaling-slack-formatting.mdc`](.cursor/rules/journaling-slack-formatting.mdc)):

   ```bash
   python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
     --file reports/report-manager-2026-04-01-to-2026-04-20.slack.txt
   ```

In Cursor, use **`@journal-capture-progress`**, **`@journal-generate-manager-report`**, **`@journal-post-slack`**, or the **`journaling-specialist`** agent to chain these steps.

## Secrets and install config

Keep **tokens** and **Slack IDs** in `.env` (gitignored). Do not commit `.env`. See [`.env.example`](.env.example).

## Security

Scripts follow [`.cursor/rules/journaling-repo.mdc`](.cursor/rules/journaling-repo.mdc): no hardcoded secrets, safe paths for `--file` / `--output`, Slack channel IDs (not `#names`). If your workspace includes the X-Team standards repo, cross-check `standards/rules/` where relevant.
