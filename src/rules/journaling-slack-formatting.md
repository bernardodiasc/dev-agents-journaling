---
description: Slack mrkdwn and message rules — IDs, mentions, and forbidden Markdown for journaling Slack posts.
globs:
  - "journaling/**/*"
alwaysApply: false
---

# Slack formatting (journaling)

Use these rules whenever you **compose or generate text meant for Slack** (`chat.postMessage`, including reports posted via `journal-post-slack`). Slack does **not** render GitHub-style Markdown.

## IDs and mentions

- **User IDs** look like `U08GPLED00M` — they do **not** start with `@`. To mention: `<@U08GPLED00M>`.
- **Channel IDs** look like `C08ERK9DSG1` — they do **not** start with `#`. To link a channel when you know the ID: `<#C08ERK9DSG1>`. The form `#C08ERK9DSG1` is wrong for an ID; `#channel-name` is only for channel **names**, not raw IDs.
- **Message / thread IDs** are timestamps (e.g. `1741903255.653879`). Do not paste broken permalinks; if you reference a thread, use the correct workspace URL shape or the API fields Slack expects.

## Formatting: Slack-native only

Use **Slack mrkdwn** only:

| Intent | Use | Do not use |
|--------|-----|------------|
| Bold | `*bold*` | `**bold**` |
| Italic | `_italic_` | `__italic__` or single `*` for italic (ambiguous with bold) |
| Strike | `~strike~` | ~~markdown~~ |
| Link | `<https://example.com>` or `<https://example.com|label>` | `[label](url)` |
| Section “header” | `*Section title*` on its own line | `#` / `##` / `###` |

Never use Markdown list/block conventions that Slack misreads as literals: avoid `#` headers, `>` blockquotes, and raw `**` / `__` / `[text](url)` in text that will be posted to Slack.

## Mentions: prefer IDs when available

- If you have a **Slack user ID**, mention as `<@SlackUserID>`. Do not rely on `@display_name` when the ID is known.
- If you have a **channel ID**, use `<#ChannelID>`. Use `#channel-name` only when you do **not** have the ID.

## Markdown → Slack (`journal-render-slack`)

Plans and reports stay as GitHub-flavored Markdown on disk; `post_slack_message.py` renders a sibling `.slack.txt` via `render_slack_from_markdown.py`. The renderer converts headings, links, bare URLs, then `**bold**` — so bold around a bare URL does not corrupt the link.

**Authoring tips (fewer surprises even if the renderer changes):**

- Prefer a **bare URL** or `[label](url)` instead of `**https://…**` (bold around URLs is easy to misread in Slack).
- Prefer plain words in `##` headings instead of `## **Section**` (the renderer strips inner `**`, but plain headings are clearer in the source).

## Reports for Slack

Generate the artifact with `generate_reports.py --format slack --report-audience <manager|self|team|qa>` so the body is Slack mrkdwn. Choose **manager** for a short leadership summary without raw technical freeform; **self** for a full check-in (optional `<@user>`); **team** or **qa** for colleague- or validation-focused layouts. Keep `entries/` as Markdown; the posted file follows this rule.
