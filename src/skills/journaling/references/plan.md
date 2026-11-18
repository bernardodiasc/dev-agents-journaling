# Daily plan

Two steps: show a catch-up, then save once the user is happy with it.

1. **Catch-up** (no files written). Run without `--save`, and also consider running
   `status_context.py` for open PRs/issues — they are usually today's work.
   - **Channel notes.** Read the user's own journal channel since the last saved
     plan: `fetch_slack_messages.py --since <last plan date>` (full text by
     default; `--format json` for the raw messages). Lines marked `(bot)` are this
     skill's earlier posts. The rest are notes the user left for themselves
     (direction, priorities, "drop X"): treat them as the user's input, the same
     as something said in this conversation.
   - **The day's priority.** If neither the user nor a channel note states one,
     ask once: "What's today's priority?" Put the answer in a `⭐ Priority`
     section at the top of the plan, and mark that item's session ⭐
     (`references/workload.md`).
   ```bash
   python3 $SKILL/scripts/generate_daily_plan.py                 # last 7 days of entries
   python3 $SKILL/scripts/generate_daily_plan.py --lookback 3 --context-file context/slack-C0123456789-2026-11-10-to-2026-11-11.txt
   ```
   Reply with a short summary (done / outstanding / blocked) and 3–5 suggested focus
   bullets. Ask "save it?" — one question, not a checklist.
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
(`SKILL.md`): Slack mrkdwn, one line per item, outcome first, bare links at the end.

- **Only actions.** Sections `⭐ Priority` / `🙋 On me` / `⏳ Waiting on review` /
  `🔨 Next`, the same emoji as the session titles. Drop any that would be empty.
- **Follow-ups are tasks.** Every follow-up issue filed since the last plan (while
  merging, or split out of a review) goes in Next, linked.
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

Posting a plan: `post_slack_message.py --file plans/plan-YYYY-MM-DD.md` renders a
`.slack.txt` sibling at post time; that sibling is the receipt that it was posted.
Same one-line confirmation as status updates before posting.

Running the day as a coordinator with subsessions, and the daily handoff:
`references/workload.md`.
