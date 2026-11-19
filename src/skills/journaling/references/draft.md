# Drafts

Every post (status update, plan, report) goes **draft → save → post**. What a kind
contains and how it's built lives in its own file: `references/status-update.md`,
`references/plan.md`, `references/reports.md`. This file is the part they share;
how every post's lines read is in `references/slack-format.md` → Writing a post.

1. **Draft.** Build it by the kind's rules and show it, nothing written yet:
   - one line: the period and sources it was built from,
   - the draft in a single ```` ``` ```` code block, so it copies cleanly,
   - optionally one line on judgment calls ("grouped 6 agent PRs into one line").

   Nothing else: no preamble, no recap of the draft in prose.
2. **Ask once.** "Save it?", or "Save and post to <channel>?" when the user wants it
   posted (name the channel: `references/post.md`). Edits mean a new draft and the
   same question again.
3. **Save on yes**, through the kind's script, never by writing the file directly:
   the scripts find the journaling home, also from a git worktree. A saved draft is
   one the user confirmed, so "post it" later, from any session, posts exactly
   that file instead of rewriting it. Replacing a saved file needs the user's yes
   for that replacement.
4. **Post** if the user said so (`references/post.md`). Otherwise the file waits:
   an unposted draft is `updates/draft.txt`, or a plan or report `.md` with no
   `.slack.txt` sibling.
