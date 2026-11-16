# Journaling

A Claude Code skill that keeps a personal work log and turns it — plus your GitHub
activity — into short, link-rich Slack status updates.

```
you:    draft status update
claude: Since Mon 00:00 · 2 merged, 15 open PRs
        ```
        *Status update · Tue Nov 11*

        *Done*
        • Search API docs for the v2 endpoints https://github.com/acme/docs/pull/38

        *In progress*
        • Billing webhooks (retries, idempotency) https://github.com/acme/billing/pull/80 🟢 approved https://github.com/acme/billing/pull/81 🟡 in review
        ```
you:    post status update
claude: (shows the text) Post to your channel?   you: yes
claude: Posted — https://your-workspace.slack.com/archives/C0…/p…
```

Every GitHub link gets a live status tag (🟢 approved, 🟡 in review, 🔴 changes
requested, ⚪ draft, 🟣 merged/completed, 🔵 open + labels, 🟠 CI failing). Drafts use bare URLs so they
paste cleanly into Slack; the bot posts a Block Kit message (header, sections, status
chips) with short `repo#123` links and no link previews.

## What it does

| Ask | Result |
|---|---|
| "draft status update" / "weekly update" | Slack-formatted update in a code block, built from `gh` activity + journal + chat |
| "post status update" | One confirmation, then posts to your channel via your Slack bot |
| "log that I merged #412" | Appends to `entries/YYYY-MM-DD.md` |
| "plan my day" | Catch-up + suggested focus → `plans/` |
| "start today's coordinator" / "hand off to tomorrow" | A daily coordinator session with one subsession per deliverable, status emoji on titles, and a handoff → `plans/` |
| "pull #team from yesterday" | Slack history → `context/` |
| "manager report for last two weeks" | manager / self / team / qa reports → `reports/` |

Everything lives in one skill: [`src/skills/journaling/`](src/skills/journaling/SKILL.md)
(`SKILL.md`, `references/`, `scripts/` — stdlib Python + the `gh` CLI).

## Install

```bash
bash scripts/install-user-skill.sh          # ~/.claude/skills/journaling -> this repo
cp .env.example .env && chmod 600 .env      # fill in bot token + channel ID
gh auth status                              # GitHub activity comes from gh
```

Invite the bot to your channel (`/invite @your-bot`). Slack scopes: `chat:write`,
plus `channels:history` / `groups:history` for fetching context.

Journal data (`entries/`, `plans/`, `reports/`, `context/`, `updates/`) and `.env`
stay in this repo and are gitignored. Set `JOURNALING_HOME` to keep them elsewhere.

Cursor / project-level use: `bash scripts/sync-vendor-dirs.sh` symlinks
`.cursor/skills` and `.claude/skills` to `src/skills`.

## Security

- Secrets only in `.env` (gitignored) or env vars; `.env` is read from the journaling
  home only — never searched for in parent directories.
- Network: fixed `https://slack.com/api/` endpoints (`chat.postMessage`,
  `chat.getPermalink`, `conversations.history`) and read-only `gh search` /
  `gh api graphql` (PR/issue status, URLs passed as variables).
- File arguments are confined to the journaling home; scripts never print tokens or
  raw API responses.
- Nothing goes out (Slack posts, PR/issue comments, reviews, pushes) without showing
  the exact text or diff and getting a yes.
- The skill tells Claude to leave data queries to you (it writes aggregate-only SQL)
  and to use invented placeholders in anything public.

Details: [`references/setup.md`](src/skills/journaling/references/setup.md).
