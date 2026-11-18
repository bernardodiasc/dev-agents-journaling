# Workload: a coordinator and its subsessions

The day runs as one **coordinator** session plus one **subsession** per deliverable.
The coordinator plans, tracks, asks and posts; the subsessions do the work. This
needs a host that can start sessions and group them in a sidebar (the Claude desktop
app's Code tab). Elsewhere, use the plan and handoff parts on their own.

## User preferences

Read `context/preferences.md` in the journaling home if it exists. It is gitignored
and holds what differs per user. Use those values; the skill hardcodes none of them.

```markdown
# Journaling preferences (gitignored; never commit)
- Review skill: code-review
- Implement skill: tdd
- Tracking issues: https://github.com/acme/roadmap/issues/1
- Ask about billing: Alice
- Review for: alice, bob-gh
- Review repos: acme/docs, acme/api
```

`Review for` takes GitHub logins and `Review repos` takes `owner/repo`: the plan
suggests their open PRs as reviews (`references/plan.md`).

When a choice depends on a preference that isn't there, ask once, and on the user's
yes save the answer through the script. It finds the journaling home like the other
scripts, so it works from a worktree where direct writes to the main checkout are
blocked, and it changes only that key's line.

```bash
python3 $SKILL/scripts/preferences.py --set "Review for" "alice, bob-gh"
python3 $SKILL/scripts/preferences.py --get "Review for"   # one value; no args prints the file
```

## The coordinator

- **One per day.** Title `📓 Journaling · <Day D Mon>` (`📓 Journaling · Mon 16 Nov`).
  File it in a sidebar group named `<Day D Mon>`, creating the group if it's missing.
- **Delegates every deliverable.** Anything that ends in a PR, review, issue comment
  or doc change starts as a subsession. The coordinator's own output is the plan,
  the handoff, session titles, questions to the user, and Slack posts.
- **First steps:**
  1. Read today's `plans/handoff-YYYY-MM-DD.md` if there is one.
  2. Run the plan flow (`references/plan.md`) with `status_context.py --since
     <handoff date>` to catch anything new, and show the plan as a draft.
  3. Ask once whether to save and post it, then which subsessions to start.

## Subsessions

- Start each one **from the coordinator**, so it's a subsession of that day's
  coordinator, and file it in that day's group. Title: status emoji + short
  deliverable name with its ref (`⏳ api#12 retry backoff`).
- **New work, new subsession.** Ask the user before reusing a session from another
  day, or a top-level session, for today's work. The app can't re-parent a session,
  so a reused one stays outside today's coordinator, and the user can't move it.
- **Archived sessions stay archived.** Unarchive, message or read an archived
  session only when the user asks to look in archived sessions. Work that comes back
  (a reopened PR, a new review round, a follow-up) gets a new subsession, briefed
  from GitHub, the handoff and the plan. Archiving stops a session and usually
  removes its worktree, so a reopened one has no checkout and stale state; its long
  transcript carries old assumptions GitHub has since replaced.
- When `preferences.md` names a skill for this kind of work (review, implement,
  research…), the brief tells the subsession to invoke it.
- A subsession only knows its brief, so every brief carries the approval gate,
  masking and repo-rules lines from SKILL.md's Security notes in one line each.
- When a subsession reports, update its title emoji and the plan.
- **Approvals stay in their session.** When the user says yes in the coordinator
  to something a subsession does (a push, a reply, a merge), that yes doesn't reach
  the subsession, and its permission checks may block the step. Say so, and point
  the user to that session to approve it there. Never redo the blocked step from
  the coordinator.
- **Follow-ups count.** When a subsession files a follow-up issue, record it like
  any other done item: in the next status update (`Follow-up filed: <what>
  repo#N`), in the plan's Next, and linked from its tracking issue
  (`Tracking issues` in `preferences.md`), on the user's yes.
- **Steps only the user can run.** When a subsession hands the user something to
  run (a query, a migration, a console or dashboard action), read it and tell the
  user in a few lines what it does and which environment it touches. Flag any
  production step that blocks the merge.
- **Carried-over subsessions.** Today's coordinator messages them directly by
  session id, never through the coordinator that started them. Every such message
  asks the session to report back to today's coordinator by message: a session's
  automatic turn-end notes reach only the session that started it. Older
  coordinators stay read-only: message one only for context only it holds, or to
  wrap up and archive.

## Status emoji

| Emoji | Meaning |
|---|---|
| 📓 | coordinator |
| 🔨 | in progress: the subsession is working |
| 🔍 | reviewing someone else's PR |
| ✅ | done: nothing left but archiving |
| ⏳ | waiting on others (review, a reply, a deploy) |
| 🙋 | needs the user (a decision, a query to run, a credential to fix, a reviewer to pick) |
| ⭐ | prefix for the day's priority (`⭐🔨 billing#80 webhooks`) |

Change the emoji whenever the state changes, so the sidebar reads as the day's board.
Status update sections use the same emoji (`references/status-update.md`), so the post mirrors the sidebar.

## Merging the user's PR with follow-ups

When the user's own PR is approved but still has open suggestions or questions,
it can merge without blocking on them:

1. Read every open review thread. If one is a real blocker (a bug, a security
   issue, the reviewer asked not to merge), stop and tell the user.
2. Put the rest in one follow-up issue, or reuse one the reviewer already opened.
3. Reply in each thread with a link to that issue, then resolve the thread (branch
   rules may require resolved threads before merging).
4. Comment on the PR: `Merging with follow-ups in #N`.
5. Squash-merge.
6. Record the follow-up: status update (`Follow-up filed: <what> repo#N`), the
   plan's Next, and a link from its tracking issue if `preferences.md` names one.

Each of steps 2–5 is outward-facing: show the issue text, replies and comment,
and get the user's yes once for the batch before acting. Set no labels on the new
issue unless the repo's docs allow agents to (SKILL.md, "Repo rules win").

## Syncing the board

"Sync the board" (or "where are we?") brings every session's emoji in line with
reality:

1. For every open session in today's group and the ones carried over: read its
   title and its last report. Open sessions only: `list_sessions` leaves archived
   ones out by default, so keep it that way.
2. Check each claim against live GitHub (`gh pr view <url> --json
   state,reviewDecision,reviewRequests,latestReviews`). Sessions report what they
   believe; a report saying "Alice was asked to review" means nothing if
   `reviewRequests` is empty.
3. Set the emoji from what GitHub says. An open PR with no requested reviewer is
   🙋 (the user picks one), not ⏳.
4. Append a dated `## Sync · HH:MM` section to today's handoff: one line per
   session whose emoji changed, and any report that didn't match GitHub.
   ```bash
   python3 $SKILL/scripts/generate_daily_plan.py --stdin --replace --output plans/handoff-2026-11-17.md <<'EOF'
   ...the existing handoff, plus the new section...
   EOF
   ```

## Daily handoff

Write it at the end of the day, or first thing the next day if it was missed.

1. **Walk** every open subsession in the day's group (archived ones are out, as in
   "Syncing the board"). Record each one's state, emoji and what closes it.
2. **✅ sessions:** list them for archiving and archive on the user's yes.
3. **⏳ and 🙋 sessions:** carry each into the next handoff, with what closes it.
   The next coordinator takes over tracking them, whichever coordinator started
   them, so the user only follows today's coordinator ("Carried-over
   subsessions"). Older coordinators stay open until their children close:
   archiving a parent also archives its idle children that have no PR of their own.
4. **Staleness** counts working days only; weekends don't count. Waiting on someone
   is fine. The day's age alone is no reason to nudge.
5. **No reviewer, no movement.** A PR with no reviewer requested won't move by
   waiting (`gh pr view <url> --json reviewRequests`), so it's 🙋, not ⏳.
   Requesting one is a coordinator action, on the user's yes. It isn't a nudge.
6. **Follow-ups.** List every follow-up issue filed today. Check each one is in the
   next plan's Next and linked from its tracking issue (`preferences.md`); fix
   either on the user's yes.
7. **Save** through the script (see `references/plan.md`), dated for the day it's for.
   The handoff is internal: session ids, tracking tables, archive lists. If the user
   also wants the next day's plan ready, save it as a separate file with only the
   actions ("What a plan says" in `references/plan.md`). That plan is what gets posted.
   ```bash
   python3 $SKILL/scripts/generate_daily_plan.py --stdin --output plans/handoff-2026-11-17.md <<'EOF'
   ...
   EOF
   python3 $SKILL/scripts/generate_daily_plan.py --stdin --save --date next <<'EOF'
   # Plan · Tue 17 Nov
   ...
   EOF
   ```

Handoff shape:

```markdown
# Handoff → 📓 Journaling · Tue 17 Nov

_From the Mon 16 Nov coordinator. Internal: gitignored `plans/`, never copy into tracked files._

## New today
- [ ] Review Alice's https://github.com/acme/docs/pull/38 (start as a subsession)

## Conclude Monday's sessions (3)
| Session | State | What closes it |
|---|---|---|
| ✅ api#12 retry backoff | done | Archive on your yes |
| 🙋 billing#80 webhooks | needs you | **No reviewer requested yet.** Pick one (Bob?) |
| 🙋 infra#79 DB users | needs you | Run `counts.sql`, paste the output |

## Follow-ups filed today
- https://github.com/acme/docs/issues/41 cache invalidation, from docs#38's review. In the plan's Next; linked from roadmap#1

## Unblocked work
- https://github.com/acme/billing/issues/5 invoice export, no blocker

## First steps
1. Plan flow since this handoff, save the plan, ask whether to post it.
2. Ask which subsessions to start.
```

## Plans from tracking issues (optional)

If `preferences.md` lists tracking or map issues, read each during the plan step
(`gh issue view <url> --comments`). List its open, unblocked child items under
"Unblocked work", linked, so the user can pick the day's subsessions from them.
