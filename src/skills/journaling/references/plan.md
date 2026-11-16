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
2. **Save** on confirmation, always through the script:
   - the generated brief: same command plus `--save` → `plans/plan-YYYY-MM-DD.md`;
   - a plan you wrote (from a handoff, or edited with the user): pipe it in with
     `--stdin --save`.
   ```bash
   python3 $SKILL/scripts/generate_daily_plan.py --stdin --save <<'EOF'
   # Plan · Mon 16 Nov
   ...
   EOF
   ```

The script resolves the journaling home itself, which may be a different checkout
from the session's working directory. In a git worktree, direct file writes to the
main checkout are blocked; the script still reaches it. Run it from `$SKILL` (the
installed path): a copy inside a worktree of this repo treats that worktree as home.

| Flag | Purpose |
|------|---------|
| `--lookback DAYS` | Days of entries to include (default 7) |
| `--context-file PATH` | Embed a context file (Slack dump, link notes) |
| `--stdin` | Save the Markdown piped in, as-is, instead of generating the brief |
| `--save` / `--output PATH` | Write to `plans/plan-YYYY-MM-DD.md` / an explicit path in the journaling home (e.g. `plans/handoff-YYYY-MM-DD.md`) |

Posting a plan: `post_slack_message.py --file plans/plan-YYYY-MM-DD.md` renders a
`.slack.txt` sibling at post time; that sibling is the receipt that it was posted.
Same one-line confirmation as status updates before posting.

Running the day as a coordinator with subsessions, and the daily handoff:
`references/workload.md`.
