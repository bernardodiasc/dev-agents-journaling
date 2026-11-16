# Setup and troubleshooting

## Journaling home

Scripts store data and read `.env` from the *journaling home*, resolved as:

1. `$JOURNALING_HOME` if set;
2. the repo this skill is symlinked from (`<repo>/src/skills/journaling`);
3. `~/.journaling`.

Data dirs (created automatically, gitignored): `entries/`, `plans/`, `reports/`,
`context/`, `updates/`. `.env` is read **only** from the home — never searched for
in parent directories.

Per-user preferences (preferred review/implement skill, tracking issues, people to
ask) go in `context/preferences.md`, also gitignored. Format: `references/workload.md`.

## Install (Claude Code, user-level)

```bash
bash scripts/install-user-skill.sh   # from the repo root: symlinks ~/.claude/skills/journaling
```

## `.env` (in the journaling home; `chmod 600 .env`)

```bash
JOURNALING_SLACK_BOT_TOKEN=xoxb-…                # bot token
JOURNALING_SLACK_CHANNEL_ID=C0123456789          # "my channel" — default post target
JOURNALING_SLACK_USER_ID=U0123456789             # optional, for <@you> mentions
JOURNALING_SLACK_CHANNEL_ID_TEAM=C0…             # optional aliases: --channel-name team
JOURNALING_GITHUB_OWNERS=my-org,another-org      # optional: scope GitHub activity
JOURNALING_JIRA_BASE_URL=https://your-org.atlassian.net   # optional
```

Slack app scopes: `chat:write` (post), `channels:history` / `groups:history`
(fetch). Invite the bot to each channel (`/invite @your-bot`).

GitHub: `gh auth status` must show the account that owns the work.

## Common errors

| Error | Fix |
|---|---|
| `no .env in the journaling home` | Create `.env` from `.env.example` in the repo root |
| `not_in_channel` / `channel_not_found` | `/invite @your-bot` in that channel; check the ID |
| `invalid_auth` / `token_revoked` | Regenerate the bot token and update `.env` |
| `missing_scope` | Add the scope in the Slack app config and reinstall it |
| `gh search failed` | `gh auth login`, or pass `--no-github` |
| Wrong period | `status_context.py --since 7d` / `--since 2026-11-03` |
