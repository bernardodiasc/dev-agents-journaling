---
name: journal-render-slack
description: >-
  Render a Markdown plan or report (.md) into its Slack-mrkdwn sibling (.slack.txt).
  Called just before posting to Slack — the .slack.txt left on disk is the receipt
  that the message was delivered.
---

# Render Markdown → Slack mrkdwn

Slack does not accept GitHub Markdown. This skill converts any `.md` under `plans/`, `reports/`, or elsewhere in the repo into a sibling `.slack.txt` using Slack mrkdwn rules (see [`src/rules/journaling-slack-formatting.md`](../../rules/journaling-slack-formatting.md)).

**Receipt convention:** `.slack.txt` is generated only at post time (automatically, by `journal-post-slack`). If a `.slack.txt` exists alongside a `.md`, that report/plan has been delivered to Slack. If it is missing, the content was generated but never posted.

## When to use

You usually do **not** invoke this directly — `journal-post-slack --file foo.md` handles the render step automatically. Use the script directly only when:
- You want to preview the Slack version without posting (`--stdout`).
- You want to regenerate a `.slack.txt` without posting.

## Quick start

**working_directory:** repository root of `journaling`.

```bash
# Preview what would be posted (does not write a file, does not post)
python3 src/skills/journal-render-slack/scripts/render_slack_from_markdown.py \
  reports/report-manager-2026-04-01-to-2026-04-20.md --stdout

# Force-regenerate a .slack.txt sibling (does not post)
python3 src/skills/journal-render-slack/scripts/render_slack_from_markdown.py \
  plans/plan-2026-04-21.md
# → plans/plan-2026-04-21.slack.txt
```

## Conversion rules (summary)

| Markdown | Slack mrkdwn |
|----------|--------------|
| `# Heading` / `## Heading` / `### Heading` | `*Heading*` on its own line |
| `**bold**` / `__bold__` | `*bold*` |
| `_italic_` | unchanged (Slack also uses `_..._`) |
| `[label](https://url)` | `<https://url\|label>` |
| Bare `https://url` | `<https://url>` |
| `- item` bullets | unchanged |
| ```` ``` code fences ```` | unchanged |

Full rules: [`src/rules/journaling-slack-formatting.md`](../../rules/journaling-slack-formatting.md).

## Options

| Flag | Purpose |
|------|---------|
| `source` (positional) | `.md` file inside the repo |
| `--output PATH` | Override output (default: sibling `.slack.txt`) |
| `--stdout` | Print rendered Slack text to stdout; do not write a file |

## Examples

Chat example:

> **You:** preview how my QA report would look in Slack
>
> **Agent:** runs `render_slack_from_markdown.py reports/report-qa-….md --stdout` and shows the converted text.

## Shared helpers

Uses [`_shared/journaling_repo.py`](../_shared/journaling_repo.py) and [`_shared/path_guard.py`](../_shared/path_guard.py). No Slack token required — pure text conversion.
