# Slack formatting

Slack uses **mrkdwn**, not GitHub Markdown.

| Intent | Use | Not |
|---|---|---|
| Bold / section title | `*Done*` on its own line | `**Done**`, `## Done` |
| Italic | `_text_` | `*text*` (that's bold) |
| Strike | `~text~` | `~~text~~` |
| Bullet | `• item` (or `- item`) | nested `*` bullets |
| Link (bot post) | `<https://url\|label>` | `[label](url)` |
| Link (pasted draft) | bare `https://url` | `<https://url\|label>` (shows literally when pasted) |
| Code | `` `x` `` / ```` ``` ```` | |

Avoid `#` headings and `>` quotes in updates; Slack shows `#` literally.

## Links

- Drafts the user will paste: bare URLs at the end of the line. Slack auto-links them.
- Bot posts: `post_slack_message.py` rewrites bare GitHub PR/issue URLs to
  `<url|repo#123>`, commit URLs to `<url|repo@abc1234>`, and other URLs to `<url>`.
  Existing `<…>` links and code are untouched. Unfurls are off.

## Status tags (`status_render.py`)

Appended after every GitHub URL from a live GraphQL lookup:

| PR | Issue |
|---|---|
| 🟢 approved · 🟡 in review · 🔴 changes requested · ⚪ draft · 🟣 merged · ⚫ closed | 🔵 open · ✅ closed · ⚫ not planned |

Plus `❌ CI` for open PRs with failing checks and up to 3 labels as `` `label` ``.
Re-rendering strips old tags first, so statuses are always current at post time.

## Block Kit (status update posts)

`post_slack_message.py --status-update` sends `blocks` + fallback `text`, kept to a
handful of blocks so it reads like a normal message:

1. `header` — the first `*line*` of the draft
2. `context` — `--context` (period + counts)
3. `rich_text` — bold section titles and `rich_text_list` bullets; each GitHub link is
   `repo#12` followed by its status dot (`🟡`), `❌ CI` and `label`s in code style
   (paragraphs in the draft become plain `section` blocks in between)
4. `context` — legend of only the statuses that appear (`🟣 merged   🟡 in review`)

Block Kit only exists in bot posts; pasted drafts stay as tagged mrkdwn (with words).

## Mentions and IDs

- User: `<@U0123456789>` (member IDs start with `U`, no `@` in the ID).
- Channel: `<#C0123456789>`. `#name` only when you don't have the ID.
- Never guess IDs. `JOURNALING_SLACK_USER_ID` holds the user's own ID;
  `post_slack_message.py --prepend-user-mention` prepends it.

## Markdown files → Slack

`.md` plans and reports are converted at post time: headings → `*Heading*`,
`**bold**` → `*bold*`, `[label](url)` → `<url|label>`, bare GitHub URLs → `repo#N`
labels; code fences kept.
