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
```

When a choice depends on a preference that isn't there, ask once and suggest the
user add the answer to that file.

## The coordinator

- **One per day.** Title `📓 Journaling · <Day D Mon>` (`📓 Journaling · Mon 16 Nov`).
  File it in a sidebar group named `<Day D Mon>`, creating the group if it's missing.
- **Delegates every deliverable.** Anything that ends in a PR, review, issue comment
  or doc change starts as a subsession. The coordinator's own output is the plan,
  the handoff, session titles, questions to the user, and Slack posts.
- **First steps:**
  1. Read today's `plans/handoff-YYYY-MM-DD.md` if there is one.
  2. Run the plan flow (`references/plan.md`) with `status_context.py --since
     <handoff date>` to catch anything new, and save the plan.
  3. Ask once whether to post it, then which subsessions to start.

## Subsessions

- Start each one **from the coordinator**, so it's a subsession of that day's
  coordinator, and file it in that day's group. Title: status emoji + short
  deliverable name with its ref (`⏳ api#12 retry backoff`).
- When `preferences.md` names a skill for this kind of work (review, implement,
  research…), the brief tells the subsession to invoke it.
- A subsession only knows its brief, so every brief carries the approval gate
  and masking rules from SKILL.md's Security notes in one line each.
- When a subsession reports, update its title emoji and the plan.

## Status emoji

| Emoji | Meaning |
|---|---|
| 📓 | coordinator |
| ✅ | done: nothing left but archiving |
| ⏳ | waiting on others (review, a reply, a deploy) |
| 🙋 | needs the user (a decision, a query to run, a credential to fix) |

Change the emoji whenever the state changes, so the sidebar reads as the day's board.

## Daily handoff

Write it at the end of the day, or first thing the next day if it was missed.

1. **Walk** every subsession in the day's group. Record each one's state, emoji
   and what closes it.
2. **✅ sessions:** list them for archiving and archive on the user's yes.
3. **⏳ and 🙋 sessions:** carry each into the next handoff, with what closes it.
   The next coordinator takes over tracking them, whichever coordinator started
   them, so the user only follows today's coordinator. Older coordinators stay
   open but read-only until their children close: archiving a parent also archives
   its idle children that have no PR of their own.
4. **Staleness** counts working days only; weekends don't count. Waiting on someone
   is fine. The day's age alone is no reason to nudge.
5. **No reviewer, no movement.** A ⏳ PR with no reviewer requested won't move by
   waiting (`gh pr view <url> --json reviewRequests`). Requesting one is a coordinator
   action, on the user's yes. It isn't a nudge.
6. **Save** through the script (see `references/plan.md`), dated for the day it's for.
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
| ⏳ billing#80 webhooks | waiting | Bob's review. **No reviewer requested yet.** |
| 🙋 infra#79 DB users | needs you | Run `counts.sql`, paste the output |

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
