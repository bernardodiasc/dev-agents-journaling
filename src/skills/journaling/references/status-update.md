# Status update

A short, scannable, link-rich update of what changed since the last one. Readers
follow up through the links, so the update's job is to point, not to explain. It is
drafted, saved and posted like every post (`references/draft.md`, `references/post.md`).

## Collect context

One call:

```bash
python3 $SKILL/scripts/status_context.py            # since the last posted update
python3 $SKILL/scripts/status_context.py --since 7d  # "weekly update"
```

Flags: `--since auto|Nd|YYYY-MM-DD|ISO`, `--owner ORG` (repeatable; default
`JOURNALING_GITHUB_OWNERS`), `--no-github`. It prints the period and why it was
chosen, your GitHub activity with each item's live status (`[🟢 approved]`,
`[⚪ draft]`, labels…), **PRs you reviewed** (from your activity feed, so reviews
made minutes ago are included, with your verdict), PRs waiting on your review, and
journal entries.

Merge in anything the user said in this conversation ("mention I'm blocked on
infra", "only about X", "add a context paragraph"): it outranks the digest and the
default format. If there is genuinely nothing (no GitHub activity, no journal,
nothing in chat), say so in one line and ask what to include. Never invent items.

## Tag and save

Write the draft with bare URLs and no status tags, then tag it in one call:

```bash
python3 $SKILL/scripts/status_render.py --no-save <<'EOF'   # preview
*Status update · Thu Nov 12*
...
EOF
```

It appends `🟢 approved` / `🟡 in review` / `🔴 changes requested` / `⚪ draft` /
`🟣 merged` / `🔵 open` / `🟣 completed`, `🟠 CI failing` when checks fail, and up
to 3 labels as `` `label` `` after every GitHub URL. Statuses come from GitHub, never
from you: don't hand-type them. The reply's one line is the period and sources
("Since Mon 10:00 · 2 merged, 15 open PRs, no journal entries").

Saving is the same call without `--no-save`: it writes `updates/draft.txt`, the
pending status update that "post status update" posts from any session.

## Format

Draft (what you write):

```
*Status update · Thu Nov 12*

*✅ Done*
• Search API docs for the v2 endpoints https://github.com/acme/docs/pull/38
• Follow-up filed: cache invalidation for v2 https://github.com/acme/docs/issues/41

*🔨 In progress*
• Billing webhooks (retries, idempotency) https://github.com/acme/billing/pull/80 https://github.com/acme/billing/pull/81

*⏳ Waiting on review*
• Per-service database users https://github.com/acme/infra/pull/79

*🙋 Next*
• Answer Alice's review on the export job https://github.com/acme/billing/pull/77
• Cache invalidation for v2 https://github.com/acme/docs/issues/41

*🔍 Reviewed*
• Search ranking fixes https://github.com/acme/search/pull/12 https://github.com/acme/search/pull/14
• Dependency security bumps https://github.com/acme/web/pull/301 https://github.com/acme/api/pull/77

*🚧 Blocked*
• Staging deploy — waiting on DB grants from infra
```

After `status_render.py` (what the user sees and pastes):

```
• Billing webhooks (retries, idempotency) https://github.com/acme/billing/pull/80 🟢 approved https://github.com/acme/billing/pull/81 🔴 changes requested 🟠 CI failing
• Invoice export job https://github.com/acme/billing/issues/5 🔵 open `billing` `q4`
```

Every line follows the post rules in `references/slack-format.md` (one line per item,
outcome first, ≤ ~3 bare links, state from tags, mrkdwn). Specific to status updates:

- **Sections** mirror the sidebar's session emoji (`references/workload.md`):
  `✅ Done` / `🔨 In progress` / `⏳ Waiting on review` / `🙋 Next` / `🔍 Reviewed` /
  `🚧 Blocked`, in that order. Drop any section that would be empty — an empty
  "Blocked: none" is noise.
- **Only what changed since the last post.** Readers already have the earlier posts
  in the channel. An item goes in only if it is new or its state moved since then
  (merged, approved, new change requests, newly filed). A PR still waiting with no
  new review stays out.
- **Follow-ups are done work.** An issue filed while merging, or split out of a
  review, goes in Done as `Follow-up filed: <what> repo#N`, and its work goes in
  Next (and in the plan's Next).
- **Review threads with change requests** on the user's PRs go in Next: answering
  them is the user's next action.
- **🔍 Reviewed**: others' PRs you reviewed in the period, grouped by theme or repo
  (≤ 3 links per line, one short clause: "Dependency security bumps"). Reviews are
  real work readers care about — include them whenever the digest has any.
- **Context paragraph**: allowed when the user asks for one (or for a single-topic
  update that needs framing) — 1–3 sentences right after the header.
- **Header**: `*Status update · <Day Mon D>*` (or `*Weekly update · Nov 3–7*` for a
  week). No intro or sign-off lines.

## After posting

Capture it (`references/capture.md`) with `--tag status-update`, in one call and without
asking: posting is what fills `entries/`, which reports and plans are built from.
Each ✅ Done line is a `--win`, each em-dash or 🚧 Blocked line a `--blocker`, each
🙋 Next line a `--next-step`; keep the line's text and URLs, without status tags. A
later draft the same day reads these again; "Only what changed since the last post"
keeps them out of it.
