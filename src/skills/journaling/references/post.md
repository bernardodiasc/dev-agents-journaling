# Posting

A post is visible to everyone following the channel, so only a saved draft the user
confirmed goes out (`references/draft.md`).

1. **Get the saved draft** of the kind the user named. With none saved, run that
   kind's draft first.

   | Kind | Saved draft |
   |---|---|
   | Status update | `python3 $SKILL/scripts/status_render.py --saved` prints it freshly tagged (exit 2 = none) |
   | Plan | `plans/plan-YYYY-MM-DD.md` with no `.slack.txt` sibling |
   | Report | `reports/report-<audience>-….md` with no `.slack.txt` sibling |

2. **Confirm once**, unless the user's "save and post" already covered this exact
   text: show it and the target channel, then ask "Post to <channel>?". The default
   channel is `JOURNALING_SLACK_CHANNEL_ID` ("my channel"); aliases like "team" map
   to `JOURNALING_SLACK_CHANNEL_ID_TEAM` (`fetch_slack_messages.py --list-channels`).
3. **On yes, post.** Pass text through a quoted heredoc, so `$`, backticks and `!`
   are never shell-expanded.
   ```bash
   # Status update: a compact Block Kit message
   python3 $SKILL/scripts/post_slack_message.py --status-update \
     --context "Since Wed 11:34 · 1 merged · 6 open PRs · 3 reviews" <<'EOF'
   *Status update · Thu Nov 12*
   ...
   EOF
   # Plan or report: the .md is converted to mrkdwn at post time
   python3 $SKILL/scripts/post_slack_message.py --file plans/plan-2026-11-12.md
   ```
   `--status-update` makes the first `*line*` the header, `--context` a small grey
   line under it (period and counts), then one rich-text list and a legend of the
   statuses used (`references/slack-format.md`). It saves the post under `updates/`
   (the start of the next period) and clears the saved draft only when the posted
   text is that draft, so another session's pending draft survives. `--file` writes
   the `.slack.txt` sibling, the receipt that it was posted. Add `--channel-name
   team` for an alias, `--thread-ts <ts>` to reply in a thread, `--no-blocks` for
   plain text. Link previews are off.
4. **After posting**, run the kind's own step if it has one (a status update is
   captured to `entries/`: `references/status-update.md`).
5. **Report back** in one line with the permalink the script prints. If it notes a
   different saved draft is still pending, check it with `--saved`: an earlier
   version of what you just posted gets cleared (`status_render.py --discard`);
   anything else belongs to another session, so leave it and mention it.

If posting fails, relay the short error and its fix from `references/setup.md`
(usual suspects: missing `.env`, bot not in the channel, `not_in_channel`,
`invalid_auth`). Don't retry blindly.
