---
name: journal-gather-context
description: >-
  Umbrella skill for assembling context files under context/. The user asks for
  "context" and this skill figures out the source (Slack channel, Jira link,
  freeform note) and routes to the right sub-skill. Always asks first.
---

# Gather context (router)

This is the front door for **"give me context about X."** Context files live under `context/` and can be referenced anywhere a `--context-file` flag is accepted (e.g. `journal-daily-plan`), or manually linked during capture.

**This skill is prompt-only — there is no `scripts/` directory.** It exists so the journaling specialist always:

1. Asks the user **what kind** of context and **what scope** (see decision tree below).
2. Invokes the correct sub-skill.
3. Confirms the saved file path before proceeding.

## Ask-first decision tree

If the user's request is ambiguous, the agent must ask before doing anything:

- **What source?** Slack channel, Jira ticket, Jira epic, Jira project, pasted notes, or something else.
- **What scope?** Date range (Slack), specific keys / URLs (Jira), or a freeform title (notes).
- **What's this for?** Feeding into today's plan? Referenced during a capture? Just archived?

Only after the answers are clear, run the corresponding sub-skill. Full ask-first rules: [`../../rules/journaling-interaction.md`](../../rules/journaling-interaction.md).

## Routing table

| User intent | Sub-skill | Output |
|-------------|-----------|---------|
| "Catch me up on #dev-qa from yesterday" | [`journal-fetch-slack`](../journal-fetch-slack/SKILL.md) | `context/slack-<channel>-<from>-to-<to>.txt` |
| "Save the AIAUT-436 ticket as context" | [`journal-fetch-jira`](../journal-fetch-jira/SKILL.md) | `context/jira-<key>-<today>.txt` |
| "Remember this onboarding epic and its tickets" | [`journal-fetch-jira`](../journal-fetch-jira/SKILL.md) `--kind epic --slug …` | `context/jira-<slug>-<today>.txt` |
| "Capture this freeform briefing" | [`journal-fetch-jira`](../journal-fetch-jira/SKILL.md) `--kind note --slug …` | `context/jira-<slug>-<today>.txt` (works fine for pure notes) |
| "Pull activity from #team and #dev-qa over 24h" | [`journal-fetch-slack`](../journal-fetch-slack/SKILL.md) twice, one per channel | two files under `context/` |

## Filename conventions

All context files live in `context/` with a date in the name so they stay organized over time:

- `context/slack-<channel_id>-<from>-to-<to>.txt` — from `journal-fetch-slack --save`.
- `context/jira-<slug>-<today>.txt` — from `journal-fetch-jira`.
- `context/note-<slug>-<today>.txt` — (future) freeform, if we add a dedicated note skill.

Large stale files can be archived or deleted manually; this skill does not garbage-collect.

## Examples

> **You:** get me context for planning — I've been active in dev-qa and working on AIAUT-436
>
> **Agent:** (asks-first) "Two sources then: (a) how many hours back on the dev-qa Slack channel, and (b) ticket-only for AIAUT-436 or the whole epic?"
>
> **You:** last 24 hours of dev-qa; ticket only for AIAUT-436
>
> **Agent:**
> 1. runs `fetch_slack_messages.py --channel-name dev-qa --hours 24 --save`
> 2. runs `save_jira_context.py --kind ticket --url https://…/browse/AIAUT-436`
> 3. confirms both paths, ready to pass to `journal-daily-plan`.

---

> **You:** save a context note about the Q2 migration
>
> **Agent:** (asks-first) "Got a link for it, or is this freeform notes only? Slug to use for the filename?"

## Shared behavior

- Always writes under `context/`.
- Never assumes a Slack channel or Jira URL — ask.
- Never fabricates links or ticket keys.
- Never calls external APIs beyond what the sub-skill supports (Slack `conversations.history` only; Jira is link-only).
