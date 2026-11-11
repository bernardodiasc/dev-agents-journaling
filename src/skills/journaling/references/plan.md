# Daily plan

Two steps: show a catch-up, then save once the user is happy with it.

1. **Catch-up** (no files written). Run without `--save`, and also consider running
   `status_context.py` for open PRs/issues — they are usually today's work.
   ```bash
   python3 $SKILL/scripts/generate_daily_plan.py                 # last 7 days of entries
   python3 $SKILL/scripts/generate_daily_plan.py --lookback 3 --context-file context/slack-C0123456789-2026-11-10-to-2026-11-11.txt
   ```
   Reply with a short summary (done / outstanding / blocked) and 3–5 suggested focus
   bullets. Ask "save it?" — one question, not a checklist.
2. **Save** on confirmation: same command plus `--save` → `plans/plan-YYYY-MM-DD.md`.

| Flag | Purpose |
|------|---------|
| `--lookback DAYS` | Days of entries to include (default 7) |
| `--context-file PATH` | Embed a context file (Slack dump, link notes) |
| `--save` / `--output PATH` | Write to `plans/` / an explicit path in the journaling home |

Posting a plan: `post_slack_message.py --file plans/plan-YYYY-MM-DD.md` renders a
`.slack.txt` sibling at post time; that sibling is the receipt that it was posted.
Same one-line confirmation as status updates before posting.
