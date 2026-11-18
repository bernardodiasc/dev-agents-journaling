# Period reports (multi-audience)

Use only when the user asks for a *report* (not a status update). Reads journal
entries in an inclusive date range and writes four Markdown reports together so they
stay in sync:

| Audience | Shape |
|---|---|
| `manager` | Short outcome paragraph from Wins + priorities ahead; no raw freeform |
| `self` | Everything: wins, blockers, next focus, freeform notes, metrics |
| `team` | Highlights, heads-up / dependencies, coming up |
| `qa` | Deliverables & changes, risks, suggested verification |

A report is a draft like any post (`references/draft.md`): show it with `--stdout`,
then save it on the user's yes.

```bash
python3 $SKILL/scripts/generate_reports.py --from 2026-11-03 --to 2026-11-07 --report-audience manager --stdout
python3 $SKILL/scripts/generate_reports.py --from 2026-11-03 --to 2026-11-07   # save all four
# → reports/report-{manager,self,team,qa}-2026-11-03-to-2026-11-07.md
python3 $SKILL/scripts/generate_reports.py --from 2026-11-03 --to 2026-11-07 --report-audience manager --stdin <<'EOF'
...the draft as the user edited it...
EOF
```

If the user didn't give a range, infer it ("last two weeks" → 14 days ending today)
and state it in your reply rather than asking. `--report-audience X` handles just
one. Saving refuses to overwrite a saved report unless you pass `--replace`.

Reports only see journal entries. If the period has few entries, say so and offer a
status update instead (it also uses GitHub).

Posting a saved report: `references/post.md`.
