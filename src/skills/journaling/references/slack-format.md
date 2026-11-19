# Slack formatting

Slack uses **mrkdwn**, not GitHub Markdown.

## Writing a post

Every post this skill sends (status update, plan, report, any message to Slack)
follows these line rules; each post type adds only its own sections.

- **One line per item, outcome first.** Rewrite PR titles as what changed for the
  reader ("Per-service database users"), not how ("Give each service its own…").
  Strip ticket prefixes like `[#669]:`. No "I", no adjectives, no why — the PR has the why.
- **Group related work, but keep lines short.** Several PRs for one feature become
  one line — at most ~3 links per line and roughly one short clause of text. If a
  group needs more, split it into two lines by sub-theme rather than chaining "X, Y
  and Z" plus five URLs. Never merge unrelated work into one line just to save
  lines. Aim for ≤ 8 lines total; readers skim, and a 300-character line with five
  URLs reads as noise.
- **State**: GitHub items get their state from the script's tags, so don't repeat
  "— in review" / "— draft" in the text. Use an em dash only for state GitHub can't
  know: `— waiting on DB grants from infra`.
- **Links at the end of the line, bare URLs** in drafts. Slack's message box doesn't
  render `<url|label>` when pasted, but auto-links bare URLs. When the bot posts, the
  script rewrites GitHub URLs to short `repo#123` / `repo@abc1234` labels — so never
  hand-write `<url|label>` in the draft.
- **Slack mrkdwn**: `*bold*` (single asterisks), `_italic_`, `•` bullets; no `#`
  headings, `**` or `[text](url)` (Syntax below). Plans and reports are `.md` files
  converted at post time ("Markdown files → Slack"), so they keep `#` headings.

## Syntax

| Intent | Use | Not |
|---|---|---|
| Bold / section title | `*✅ Done*` on its own line | `**Done**`, `## Done` |
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
| 🟢 approved · 🟡 in review · 🔴 changes requested · ⚪ draft · 🟣 merged · ⚫ closed | 🔵 open · 🟣 completed · ⚫ not planned |

Repos that don't require reviews report no review decision, so an approved PR
there would read as in review. The script then decides from each reviewer's latest
approving or change-requesting review: any change request → 🔴, else any
approval → 🟢.

Plus `🟠 CI failing` for open PRs with failing checks and up to 3 labels as `` `label` ``. Every status is a circle in GitHub's colors; states sharing a circle share one legend entry (`🟣 merged/completed`).
Re-rendering strips old tags first, so statuses are always current at post time.

## Block Kit (status update posts)

`post_slack_message.py --status-update` sends `blocks` + fallback `text`, kept to a
handful of blocks so it reads like a normal message:

1. `header` — the first `*line*` of the draft
2. `context` — `--context` (period + counts)
3. `rich_text` — bold section titles and `rich_text_list` bullets; each GitHub link is
   `repo#12` followed by its status circle (`🟡`), `🟠` for failing CI and `label`s in code style
   (paragraphs such as a context line render the same way, inside the list block)
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
