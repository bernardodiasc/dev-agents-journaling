---
description: Ask-first interaction rules for the journaling specialist — confirmations over assumptions.
globs:
  - "journaling/**/*"
alwaysApply: false
---

# Journaling interaction rules

**Spirit:** this repo is a personal workflow. The user may want different shapes of the same operation on different days. **Assumed defaults are annoying.** The agent should confirm intent before taking any non-trivial action.

## When to ask

Ask the user *before* running a script or editing files when any of the following is unspecified in the request:

| Task | Must clarify before running |
|------|-----------------------------|
| **Capture** | Style (overview / detailed / technical), which sections (wins / next steps / blockers / freeform), any context links (Jira tickets, PRs, fetched context files) to attach, and — if freeform — whether to append under today's entry or create for a specific date. |
| **Plan** | Lookback days; whether to fetch Slack / Jira context first; which audience this plan targets (if any); whether today is a re-plan of yesterday (catch-up vs. fresh). |
| **Context gathering** | Source (Slack channel, Jira ticket, Jira epic, Jira project, pasted notes), scope (date range, specific keys), and what the context will be used for. |
| **Reports** | Date range only — audiences are **always all four** (`manager`, `self`, `team`, `qa`) so the `.md` files stay in sync. |
| **Posting to Slack** | Which file? Which channel (default or a named alias)? Thread? `--prepend-user-mention`? |

Rules of thumb:

- **One question at a time is fine when the answer is obvious; batch them when the user clearly wants to be efficient.**
- **If the user gave enough detail** to pick unambiguously, don't re-ask — proceed.
- **Never invent Slack channels, Jira keys, or user IDs.** Ask if missing.
- **Never post to Slack without explicit confirmation** for that specific file and channel.

## Plan flow (catch-up first)

The plan skill is a **two-phase conversation**, not a single command:

1. **Phase 1 — catch-up (always).** Read the last N days (default: 7) of `entries/`. Print a summary to chat: what was completed, what was planned, what's still outstanding, what's blocked. Include any relevant context the user has queued in `context/`. *Do not write files yet.* Offer a **suggested** plan shape and ask the user to confirm or edit.
2. **Phase 2 — generate (on confirmation).** Run `generate_daily_plan.py --save` (optionally with `--context-file`). Print the plan path. Don't render a `.slack.txt` — that happens only at post time.

A plan is only written when the user says something like "yes, save that" or "generate it."

## Capture flow (ask-first)

Before appending to `entries/YYYY-MM-DD.md`, ask:

- **Style:** overview (1–3 sentences), detailed (paragraph + bullets), or technical (long-form with code / command output)?
- **Sections:** wins, blockers, next steps, metrics, freeform, or a subset?
- **Context links:** any tickets (`AIAUT-…`), PRs, commits, or files from `context/` to reference inline?

If the user pasted a log or chat snippet, suggest a capture **style** based on content — but still confirm before running.

## Report flow (all `.md` together)

- Always run `generate_reports.py --from … --to …` **without** `--report-audience`. This writes all four `.md` reports — `manager`, `self`, `team`, `qa` — so the set stays in sync.
- **Do not** produce `.slack.txt` at report-generation time. That file is only created by `journal-post-slack` at post time (see below).
- A missing `.slack.txt` next to a `.md` means that report has **never been posted** — useful for "what's unposted?" queries.

## Post-to-Slack flow (render-then-post)

- `journal-post-slack --file foo.md` automatically renders the sibling `foo.slack.txt` before posting. The sibling is the **receipt** — its presence means the file was delivered.
- Confirm the **target channel** before posting. If the user said "post it" without a channel, ask: default (`JOURNALING_SLACK_CHANNEL_ID`), a named alias (`--channel-name team` etc.), or an explicit ID?
- Confirm **thread vs. new message** when the user's intent is unclear.
- If posting fails, the render script cleans up the half-written `.slack.txt` so the "exists means delivered" invariant holds.

## Channel alias lookup

`.env` supports any `JOURNALING_SLACK_CHANNEL_ID_<NAME>`. When the user says "post to team" or "fetch from dev-qa," the agent:

1. Lists aliases (`fetch_slack_messages.py --list-channels`) if unsure.
2. Normalizes the user's name (case-insensitive, `-` and space → `_`).
3. Confirms the resolved channel ID with the user the first time it's used in a session.

If the alias is missing, the agent reports the available aliases and asks the user to add the env var (or pass `--channel C…` once).

## What to save vs. not save

- **Save** confirmed operation parameters to memory only if the user explicitly says "always do X this way" — otherwise, honor the ask-first default.
- **Do not** cache ambiguous interpretations. Re-ask each time; the cost of asking is low.
