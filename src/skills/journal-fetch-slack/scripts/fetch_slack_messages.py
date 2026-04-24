"""Fetch recent messages from a Slack channel (conversations.history, stdlib only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.journaling_repo import find_journaling_repo_root
from _shared.path_guard import resolve_write_path_under_repo, atomic_write_text
from _shared.script_utils import (
    list_channel_aliases,
    load_optional_install_config,
    load_token,
    resolve_channel_by_name,
    validate_channel_id,
    validate_token_env_var,
)

SLACK_HISTORY_URL = "https://slack.com/api/conversations.history"
DEFAULT_TOKEN_VAR = "JOURNALING_SLACK_BOT_TOKEN"
HTTP_TIMEOUT_SECONDS = 15
MAX_LIMIT = 200
DEFAULT_LIMIT = 50
_MAX_MSG_TEXT_CHARS = 500


def fetch_history(token: str, channel: str, limit: int, oldest: float | None) -> list[dict]:
    params: dict[str, str | int] = {"channel": channel, "limit": min(limit, MAX_LIMIT)}
    if oldest is not None:
        params["oldest"] = f"{oldest:.6f}"

    url = f"{SLACK_HISTORY_URL}?{urlencode(params)}"
    req = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            raw = resp.read()
    except (URLError, TimeoutError):
        sys.exit("ERROR: Slack API request failed (network or timeout).")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit("ERROR: Slack API returned a non-JSON response.")
    if not data.get("ok"):
        sys.exit(f"ERROR: Slack API error: {data.get('error', 'unknown')}.")
    return data.get("messages", [])


def format_text(messages: list[dict]) -> str:
    lines = []
    for msg in reversed(messages):  # chronological order
        ts = float(msg.get("ts", 0))
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        author = msg.get("user") or msg.get("bot_id") or "unknown"
        text = msg.get("text", "").strip()
        if not text:
            continue
        if len(text) > _MAX_MSG_TEXT_CHARS:
            text = text[:_MAX_MSG_TEXT_CHARS - 3] + "..."
        lines.append(f"[{dt}] <@{author}>: {text}")
    return "\n".join(lines)


def _resolve_channel(args: argparse.Namespace, repo: Path) -> str:
    if args.channel_name:
        resolved = resolve_channel_by_name(args.channel_name, start=repo)
        if resolved:
            return resolved
        aliases = list_channel_aliases(start=repo)
        hint = ", ".join(aliases) if aliases else "(none configured)"
        sys.exit(
            f"ERROR: --channel-name {args.channel_name!r} not found. "
            f"Available aliases: {hint}. Add JOURNALING_SLACK_CHANNEL_ID_<NAME> to .env.",
        )
    if args.channel:
        return args.channel
    default = load_optional_install_config("JOURNALING_SLACK_CHANNEL_ID", start=repo)
    if default:
        return default
    sys.exit(
        "ERROR: pass --channel, --channel-name, or set JOURNALING_SLACK_CHANNEL_ID "
        "in .env (see .env.example).",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch recent Slack channel messages")
    parser.add_argument(
        "--channel",
        default=None,
        help="Slack channel ID (overrides --channel-name and .env default)",
    )
    parser.add_argument(
        "--channel-name",
        default=None,
        help="Alias from JOURNALING_SLACK_CHANNEL_ID_<NAME> in .env (e.g. team, dev-qa, self)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        metavar="N",
        help=f"Max messages to fetch (default: {DEFAULT_LIMIT}, max: {MAX_LIMIT})",
    )
    parser.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        default=None,
        help="Fetch messages on or after this date (mutually exclusive with --hours)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=None,
        metavar="N",
        help="Fetch messages from last N hours (mutually exclusive with --since)",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="Write output to explicit file inside repo (mutually exclusive with --save)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help=(
            "Auto-save to context/slack-{channel}-{from}-to-{to}.txt "
            "(mutually exclusive with --output)"
        ),
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--token-var",
        default=DEFAULT_TOKEN_VAR,
        help="Env var for bot token (SLACK_* or JOURNALING_SLACK_BOT_TOKEN)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print one JSON line: ok, count, path (requires --output or --save)",
    )
    parser.add_argument(
        "--list-channels",
        action="store_true",
        help="Print configured channel aliases (JOURNALING_SLACK_CHANNEL_ID_*) and exit",
    )
    args = parser.parse_args()

    if args.list_channels:
        repo = find_journaling_repo_root(Path(__file__))
        default = load_optional_install_config("JOURNALING_SLACK_CHANNEL_ID", start=repo)
        aliases = list_channel_aliases(start=repo)
        if default:
            print(f"(default)  JOURNALING_SLACK_CHANNEL_ID -> {default}")
        for name in aliases:
            cid = load_optional_install_config(f"JOURNALING_SLACK_CHANNEL_ID_{name}", start=repo)
            print(f"{name.lower():<20} JOURNALING_SLACK_CHANNEL_ID_{name} -> {cid}")
        if not default and not aliases:
            print("(no channels configured in .env)")
        return

    if args.since and args.hours is not None:
        sys.exit("ERROR: use --since or --hours, not both.")
    if args.output and args.save:
        sys.exit("ERROR: use --output or --save, not both.")
    if args.channel and args.channel_name:
        sys.exit("ERROR: use --channel or --channel-name, not both.")
    if args.limit <= 0:
        sys.exit("ERROR: --limit must be a positive integer.")

    validate_token_env_var(args.token_var)
    repo = find_journaling_repo_root(Path(__file__))
    token = load_token(args.token_var)

    channel = _resolve_channel(args, repo)
    validate_channel_id(channel)

    today = date.today()
    oldest: float | None = None
    from_date: str | None = None

    if args.since:
        try:
            dt = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            sys.exit("ERROR: --since must be YYYY-MM-DD.")
        oldest = dt.timestamp()
        from_date = args.since
    elif args.hours is not None:
        if args.hours <= 0:
            sys.exit("ERROR: --hours must be a positive integer.")
        oldest = (datetime.now(tz=timezone.utc) - timedelta(hours=args.hours)).timestamp()
        from_date = str((datetime.now(tz=timezone.utc) - timedelta(hours=args.hours)).date())

    messages = fetch_history(token, channel, args.limit, oldest)

    if args.format == "json":
        output = json.dumps(messages, indent=2)
    else:
        output = format_text(messages)
        if not output:
            output = "(no messages found)"

    save_path_str: str | None = args.output
    if args.save:
        suffix = f"{from_date}-to-{today}" if from_date else str(today)
        save_path_str = f"context/slack-{channel}-{suffix}.txt"

    if save_path_str:
        out_path = resolve_write_path_under_repo(repo, save_path_str)
        atomic_write_text(out_path, output)
        if args.json:
            print(json.dumps({"ok": True, "count": len(messages), "path": str(out_path)}))
        else:
            print(f"Fetched {len(messages)} messages → {out_path}")
    else:
        if args.json:
            sys.exit("ERROR: --json requires --output or --save.")
        print(output)


if __name__ == "__main__":
    main()
