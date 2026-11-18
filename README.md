# Journaling

A Claude Code skill that keeps a personal work log and turns it — plus your GitHub
activity — into short, link-rich Slack status updates.

## A day with it

Every post (plan, status update, report) is a draft first: you see it, say "save",
and post it then or any time later. Times show how a day flows.

````
09:02 you:    start today's coordinator
09:03 claude: Read yesterday's handoff and your journal channel since then.
              Draft plan for Wed 18 Nov:
              ```
              # Plan · Wed 18 Nov
              ## ⭐ Priority
              - Ship the invoice export job https://github.com/acme/billing/issues/5
              ## 🙋 On me
              - Review Alice's search ranking fix https://github.com/acme/search/pull/14
              - Review open docs PRs https://github.com/acme/docs/pull/40
              ## 🔨 Next
              - Cache invalidation for v2 (follow-up) https://github.com/acme/docs/issues/41
              ```
              Save and post to #my-updates?
09:04 you:    yes
09:04 claude: Saved plans/plan-2026-11-18.md · posted https://acme.slack.com/archives/C…/p…
              Which subsessions should I start?
09:05 you:    the export job and Alice's review
09:05 claude: Started 🔨 billing#5 invoice export and 🔍 search#14 ranking fix.

11:40 you:    pull #team since yesterday
11:41 claude: Saved context/slack-team-2026-11-17-to-2026-11-18.txt. One thing for you:
              Bob asked who owns the staging DB grants.
11:42 you:    log that I'm blocked on staging DB grants from infra
11:42 claude: Logged 1 blocker to entries/2026-11-18.md

13:15 you:    sync the board
13:16 claude: 🔍 search#14 → ✅ (you approved it). 🔨 billing#5 → ⏳ (PR open, review requested from Bob).

16:30 you:    draft status update
16:31 claude: Since Tue 17:10 · 1 merged, 3 open PRs, 2 reviews, 1 journal entry
              ```
              *Status update · Wed Nov 18*

              *✅ Done*
              • Invoice export job https://github.com/acme/billing/pull/82 🟣 merged

              *🔍 Reviewed*
              • Search ranking fix https://github.com/acme/search/pull/14 🟢 approved

              *🚧 Blocked*
              • Staging deploy — waiting on DB grants from infra
              ```
              Save it?
16:32 you:    save, I'll post it later
16:32 claude: Saved updates/draft.txt
17:45 you:    post status update
17:45 claude: (shows the saved draft) Post to #my-updates?   you: yes
17:46 claude: Posted https://acme.slack.com/archives/C…/p… · logged 1 win, 1 blocker
              to entries/2026-11-18.md

18:00 you:    hand off to tomorrow
18:01 claude: Wrote plans/handoff-2026-11-19.md: ✅ search#14 to archive, ⏳ billing#5
              carried over, follow-up docs#41 in Next. Archive search#14?

Fri 17:00 you:    manager report for this week
Fri 17:01 claude: Mon 16 – Fri 20 Nov, from 5 journal entries:
                  ```
                  # Leadership update (2026-11-16 – 2026-11-20)
                  Progress this period included: invoice export job, search ranking fix…
                  ```
                  Save it?
````

Every GitHub link gets a live status tag (🟢 approved, 🟡 in review, 🔴 changes
requested, ⚪ draft, 🟣 merged/completed, 🔵 open + labels, 🟠 CI failing). Drafts use bare URLs so they
paste cleanly into Slack; the bot posts a Block Kit message (header, sections, status
chips) with short `repo#123` links and no link previews.

## What it does

| Ask | Result |
|---|---|
| "draft status update" / "weekly update" | Slack-formatted update in a code block, built from `gh` activity + journal + chat; saved on your yes |
| "post status update" / "post the plan" | One confirmation, then posts the saved draft to your channel via your Slack bot |
| "log that I merged #412" | Appends to `entries/YYYY-MM-DD.md` |
| "plan my day" | Catch-up, including PRs waiting on your review → `plans/` |
| "start today's coordinator" / "sync the board" / "hand off to tomorrow" | A daily coordinator session with one subsession per deliverable, status emoji on titles checked against GitHub, and a handoff → `plans/` |
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
