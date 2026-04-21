# Journaling

Local-first **progress capture**, **context gathering** (Slack + Jira links), **daily planning**, **period reports**, and **Slack delivery** — driven by Cursor skills and the **journaling specialist** subagent.

The agent **asks before assuming**: style of capture, source of context, date range for reports, target channel for Slack. See [`.cursor/rules/journaling-interaction.mdc`](.cursor/rules/journaling-interaction.mdc) for the full interaction contract.

## Layout

| Path | Purpose |
|------|---------|
| `entries/YYYY-MM-DD.md` | Daily hybrid entries (freeform + structured sections); captures can be **technical**. |
| `plans/plan-YYYY-MM-DD.md` | Daily planning brief (catch-up + today's focus). |
| `reports/report-<audience>-<from>-to-<to>.md` | Period reports (Markdown). All four audiences generated in sync. |
| `reports/*.slack.txt` · `plans/*.slack.txt` | Slack-mrkdwn sibling — **created only at post time**; its presence is the delivery receipt. |
| `context/slack-<channel>-<from>-to-<to>.txt` | Fetched Slack channel history (for plan / capture context). |
| `context/jira-<slug>-<date>.txt` | Pasted Atlassian links + notes (ticket, epic, project, freeform). |
| `.cursor/rules/` | Repo rules: architecture, interaction, Slack formatting. |
| `.cursor/agents/journaling-specialist.md` | Subagent: which skill to use and when. |
| `.cursor/skills/journal-*` | One folder per skill (see below). |

## Skills

| Skill | What it does |
|-------|--------------|
| [`journal-capture-progress`](.cursor/skills/journal-capture-progress/) | Append or create daily entries. Ask-first about style and sections. |
| [`journal-gather-context`](.cursor/skills/journal-gather-context/) | Router. Ask what source (Slack / Jira / note) and scope, then delegate. |
| [`journal-fetch-slack`](.cursor/skills/journal-fetch-slack/) | Pull channel history via `conversations.history` (default, alias, or explicit ID). |
| [`journal-fetch-jira`](.cursor/skills/journal-fetch-jira/) | Save pasted Atlassian URLs (ticket / epic / project / note) with optional notes. No API. |
| [`journal-daily-plan`](.cursor/skills/journal-daily-plan/) | Two-phase: catch-up → confirm → save `plans/plan-YYYY-MM-DD.md`. |
| [`journal-generate-manager-report`](.cursor/skills/journal-generate-manager-report/) | Generate all four audience reports in sync. |
| [`journal-render-slack`](.cursor/skills/journal-render-slack/) | Convert a `.md` to its `.slack.txt` sibling (called at post time). |
| [`journal-post-slack`](.cursor/skills/journal-post-slack/) | Post file or text to Slack. For `.md`, renders the `.slack.txt` receipt first. |

## Report audiences

Default behavior writes **all four** as Markdown on every invocation so they stay in sync:

- **`manager`** — Short leadership summary: plain-language paragraph from **Wins** + **Priorities ahead**; no raw freeform.
- **`self`** — Full detail including freeform (technical notes); Slack post can prepend `<@you>` via `JOURNALING_SLACK_USER_ID`.
- **`team`** — Colleague-friendly: highlights, dependencies, coming up.
- **`qa`** — QA / validation lens: deliverables, risks, suggested verification.

See [`.cursor/rules/journaling-repo.mdc`](.cursor/rules/journaling-repo.mdc) for the full schema and the **delivery-receipt** convention.

## Channels (named aliases)

`.env` supports any `JOURNALING_SLACK_CHANNEL_ID_<NAME>`:

```bash
JOURNALING_SLACK_CHANNEL_ID=C0…            # default
JOURNALING_SLACK_CHANNEL_ID_SELF=C0…
JOURNALING_SLACK_CHANNEL_ID_TEAM=C0…
JOURNALING_SLACK_CHANNEL_ID_DEV_QA=C0…
JOURNALING_SLACK_CHANNEL_ID_BENJI3_DEV=C0…
```

Reference them on the CLI with `--channel-name <name>` (case-insensitive, `-` and spaces normalize to `_`). List configured aliases:

```bash
python3 .cursor/skills/journal-fetch-slack/scripts/fetch_slack_messages.py --list-channels
```

## Quick start

1. Copy [`.env.example`](.env.example) to `.env` and fill in at minimum the **bot token** and a default **`JOURNALING_SLACK_CHANNEL_ID`**. Add `JOURNALING_SLACK_USER_ID` for `@`-mentions and as many `JOURNALING_SLACK_CHANNEL_ID_<NAME>` aliases as you want. Invite the bot to each channel; the Slack app needs `chat:write` (post) and `channels:history` / `groups:history` (fetch).

2. From the repo root, ask the journaling specialist in Cursor — or use the scripts directly (see Examples below).

## Examples

### 1. "Capture what I did this afternoon"

Chat flow with the specialist:

> **You:** capture this afternoon's progress
>
> **Agent:** "Quick overview or technical detail? Which sections (wins / blockers / next steps)? Any context from `context/` to link?"
>
> **You:** overview, just wins and next steps, no context needed
>
> **Agent:** drafts bullets from chat, confirms, then runs:

```bash
python3 .cursor/skills/journal-capture-progress/scripts/append_journal_entry.py \
  --win "Merged search-transparency PR" \
  --win "Green CI on main" \
  --next-step "Address reviewer comments on format_response"
```

### 2. "Catch me up and plan today"

> **You:** plan today
>
> **Agent:** (phase 1) "I'll read the last 7 days. Fetch any Slack or Jira context first? Or plan from entries only?"
>
> **You:** pull last 24h from `#dev-qa` and include AIAUT-436 as context
>
> **Agent:** runs:

```bash
python3 .cursor/skills/journal-fetch-slack/scripts/fetch_slack_messages.py \
  --channel-name dev-qa --hours 24 --save
python3 .cursor/skills/journal-fetch-jira/scripts/save_jira_context.py \
  --kind ticket --url https://x-team-internal.atlassian.net/browse/AIAUT-436

python3 .cursor/skills/journal-daily-plan/scripts/generate_daily_plan.py \
  --context-file context/slack-C03333CCCCC-2026-04-20-to-2026-04-21.txt
```

→ prints catch-up + a suggested focus → **waits for you** to confirm or edit → on confirmation:

```bash
python3 .cursor/skills/journal-daily-plan/scripts/generate_daily_plan.py \
  --context-file context/slack-C03333CCCCC-2026-04-20-to-2026-04-21.txt --save
# → plans/plan-2026-04-21.md
```

### 3. "Generate reports for the last two weeks"

> **You:** reports for 2026-04-07 → 2026-04-20
>
> **Agent:** runs:

```bash
python3 .cursor/skills/journal-generate-manager-report/scripts/generate_manager_report.py \
  --from 2026-04-07 --to 2026-04-20
```

→ writes all four `.md` audiences under `reports/` (kept in sync). No `.slack.txt` yet.

### 4. "Post that manager report to the team channel"

> **You:** post the manager report to the team channel, mention me
>
> **Agent:** (confirms target) runs:

```bash
python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  --file reports/report-manager-2026-04-07-to-2026-04-20.md \
  --channel-name team \
  --prepend-user-mention
```

→ renders `reports/report-manager-2026-04-07-to-2026-04-20.slack.txt` (receipt) → posts it → done.

### 5. "What haven't I posted yet?"

```bash
for md in reports/*.md plans/*.md; do
  [ -f "${md%.md}.slack.txt" ] || echo "unposted: $md"
done
```

### 6. "Preview the Slack version of my plan without posting"

```bash
python3 .cursor/skills/journal-post-slack/scripts/post_slack_message.py \
  --file plans/plan-2026-04-21.md --dry-run
```

### 7. "Save an epic as context"

> **You:** remember the onboarding epic, it's AIAUT-400 through AIAUT-420
>
> **Agent:** (asks-first) "Only a title + primary link, or list of child tickets too? Any note on why it matters today?"
>
> **You:** title "Onboarding epic", link the epic page, note it's this sprint's focus

```bash
python3 .cursor/skills/journal-fetch-jira/scripts/save_jira_context.py \
  --kind epic \
  --url https://x-team-internal.atlassian.net/browse/AIAUT-400 \
  --title "Onboarding epic" \
  --note "This sprint's focus; referenced in plans this week."
# → context/jira-aiaut-400-2026-04-21.txt
```

## Secrets and install config

Keep tokens, user IDs, channel IDs, and the Jira base URL in `.env` (gitignored). Never commit `.env`. Placeholders live in [`.env.example`](.env.example).

## Security

Scripts follow [`.cursor/rules/journaling-repo.mdc`](.cursor/rules/journaling-repo.mdc): no hardcoded secrets, safe paths for file arguments, Slack channel IDs (not `#names`), Atlassian URL host enforcement when `JOURNALING_JIRA_BASE_URL` is set. See the rule file for full details.
