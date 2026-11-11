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

```bash
python3 $SKILL/scripts/generate_reports.py --from 2026-11-03 --to 2026-11-07
# → reports/report-{manager,self,team,qa}-2026-11-03-to-2026-11-07.md
```

If the user didn't give a range, infer it ("last two weeks" → 14 days ending today)
and state it in your reply rather than asking. `--report-audience X` writes just one.

Reports only see journal entries. If the period has few entries, say so and offer a
status update instead (it also uses GitHub).

Posting: `post_slack_message.py --file reports/report-manager-….md [--channel-name team]`
renders a `.slack.txt` sibling at post time (receipt = it was posted). One-line
confirmation before posting, as with status updates. Unposted reports are `.md`
files with no `.slack.txt` sibling.
