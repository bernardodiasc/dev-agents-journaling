# Daily plan

A plan is a draft like any post (`references/draft.md`): catch up, show the plan,
save it on the user's yes, post it now or later.

1. **Catch-up** (no files written). Run without `--save`, plus `status_context.py
   --notifications` for open PRs/issues and unread GitHub notifications; they are
   usually today's work.
   - **Channel notes.** Read the user's own journal channel since the last saved
     plan: `fetch_slack_messages.py --since <last plan date>` (full text by
     default; `--format json` for the raw messages). Lines marked `(bot)` are this
     skill's earlier posts. The rest are notes the user left for themselves
     (direction, priorities, "drop X"): treat them as the user's input, the same
     as something said in this conversation.
   - **Today's notes.** Read `context/*-<today>*` (Slack pulls, ticket links saved
     this morning) as the user's input, like channel notes.
   - **GitHub notifications.** "On me" items (review requests, re-reviews,
     mentions, assignments, activity on the user's threads) go to 🙋 On me. A
     re-review is 🙋 even when the PR shows approved: the user's earlier review was
     dismissed or a new round was asked for. "Watching" items enter the plan only
     when they touch today's priority; `[other org: …]` ones stay out.
   - **The day's priority.** If neither the user nor a channel note states one,
     ask once: "What's today's priority?" Put the answer in a `⭐ Priority`
     section at the top of the plan, and mark that item's session ⭐
     (`references/workload.md`).
   - **Reviews waiting on me.** `status_context.py` prints "PRs waiting on my
     review": open PRs requesting the user, PRs opened in the period by the logins
     in `Review for:`, and open PRs in the `Review repos:` the user hasn't reviewed
     yet (`context/preferences.md`); teammates often request no reviewer. Suggest
     each in 🙋 On me as a review; the user drops what isn't their concern.
   ```bash
   python3 $SKILL/scripts/generate_daily_plan.py                 # last 7 days of entries
   python3 $SKILL/scripts/generate_daily_plan.py --lookback 3 --context-file context/slack-C0123456789-2026-11-10-to-2026-11-11.txt
   ```
   Show the plan as a draft ("What a plan says" below), then ask the one question
   from `references/draft.md`.
2. **Save** on confirmation, always through the script:
   - the generated brief: same command plus `--save` → `plans/plan-YYYY-MM-DD.md`;
   - a plan you wrote (from a handoff, or edited with the user): pipe it in with
     `--stdin --save`.
   ```bash
   python3 $SKILL/scripts/generate_daily_plan.py --stdin --save <<'EOF'
   # Plan · Mon 16 Nov
   ...
   EOF
   ```
   Planning ahead ("plan tomorrow", the evening before): add `--date next` (the
   next working day, so Friday plans Monday) or `--date YYYY-MM-DD`. Without it the
   file is dated by the local clock, which is still the earlier day. Saving never
   overwrites an existing file unless you pass `--replace`; use it only to replace
   that same day's plan.

## What a plan says

A saved plan is the text that gets posted, so it follows the status update's rules
(`references/status-update.md`): Slack mrkdwn, one line per item, outcome first, bare links at the end.

- **Only actions.** Sections `⭐ Priority` / `🙋 On me` / `⏳ Waiting on review` /
  `🔨 Next`, the same emoji as the session titles. Drop any that would be empty.
- **Audit Next.** Walk every open follow-up the user filed or is assigned (while
  merging, or split out of a review), plus the open children of the tracking or
  map issues (`preferences.md`), and add what's missing, linked. Mark each blocker
  with an em dash: `— waiting on an owner`, `— after repo#12 merges`.
- **Focus on the ⭐.** When the day has a priority, Next carries only that
  priority's follow-ups: the open children of its map or tracking issue and the
  follow-ups filed from it. Other scopes wait until the user asks for them; 🙋 On
  me and reviews stay. Without a priority, Next covers every front.
- **No history.** Earlier posts in the channel already carry what happened and why:
  no "where things stand", no recap of yesterday, no reasons, no counts.
- **Nothing internal.** Session ids, workflow notes, archive lists and the
  coordinator's tracking tables go in `plans/handoff-YYYY-MM-DD.md`
  (`references/workload.md`), never in the plan.
- **Waiting items** collapse into one line of links. Their state is already in the
  channel.

```markdown
# Plan · Tue 17 Nov

## ⭐ Priority
- Ship the invoice export job https://github.com/acme/billing/issues/5

## 🙋 On me
- Answer review on the billing agents https://github.com/acme/agents/pull/12 https://github.com/acme/agents/pull/13
- Search ranking brief review https://github.com/acme/docs/pull/89

## ⏳ Waiting on review
- https://github.com/acme/billing/pull/76 https://github.com/acme/billing/pull/36

## 🔨 Next
- Cache invalidation for v2 (follow-up) https://github.com/acme/docs/issues/41
```

The script resolves the journaling home itself, which may be a different checkout
from the session's working directory. In a git worktree, direct file writes to the
main checkout are blocked; the script still reaches it. Run it from `$SKILL` (the
installed path): a copy inside a worktree of this repo treats that worktree as home.

| Flag | Purpose |
|------|---------|
| `--lookback DAYS` | Days of entries to include (default 7) |
| `--context-file PATH` | Embed a context file (Slack dump, link notes) |
| `--stdin` | Save the Markdown piped in, as-is, instead of generating the brief |
| `--save` / `--output PATH` | Write to `plans/plan-YYYY-MM-DD.md` / an explicit path in the journaling home (e.g. `plans/handoff-YYYY-MM-DD.md`) |
| `--date DAY` | Day the plan is for: `today` (default), `next` (next working day) or `YYYY-MM-DD` |
| `--replace` | Allow overwriting an existing file (refused by default) |

Posting a saved plan: `references/post.md`.

Running the day as a coordinator with subsessions, and the daily handoff:
`references/workload.md`.
