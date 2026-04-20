"""Post a message to Slack using ``chat.postMessage`` (stdlib only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.script_utils import load_token, validate_token_env_var

SLACK_API_URL = "https://slack.com/api/chat.postMessage"
DEFAULT_TOKEN_VAR = "JOURNALING_SLACK_BOT_TOKEN"
HTTP_TIMEOUT_SECONDS = 15


def send_message(
    token: str,
    message: str,
    channel: str,
    thread_ts: str | None = None,
) -> dict:
    payload: dict[str, str] = {"channel": channel, "text": message}
    if thread_ts:
        payload["thread_ts"] = thread_ts

    data = json.dumps(payload).encode()
    req = Request(
        SLACK_API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read())
    except (URLError, TimeoutError):
        sys.exit("ERROR: Slack API request failed (network or timeout).")


def read_message_text(args: argparse.Namespace) -> str:
    if args.message:
        return args.message
    if args.file:
        return Path(args.file).read_text()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    sys.exit("ERROR: provide a positional message, --file, or pipe stdin.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Post a Slack message (journaling)")
    parser.add_argument(
        "message",
        nargs="?",
        default=None,
        help="Message text (optional if --file or stdin)",
    )
    parser.add_argument(
        "--file",
        "-f",
        default=None,
        help="Read message body from file (e.g. a generated report)",
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Slack channel ID (required)",
    )
    parser.add_argument(
        "--thread-ts",
        default=None,
        help="Thread timestamp for threaded replies",
    )
    parser.add_argument(
        "--token-var",
        default=DEFAULT_TOKEN_VAR,
        help="Env var for bot token (SLACK_* or JOURNALING_SLACK_BOT_TOKEN)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print one JSON line with ok, channel, ts",
    )
    args = parser.parse_args()

    validate_token_env_var(args.token_var)
    text = read_message_text(args)
    if not text.strip():
        sys.exit("ERROR: message is empty.")

    token = load_token(args.token_var)
    result = send_message(token, text, args.channel, args.thread_ts)

    if result.get("ok"):
        ts = result.get("ts", "")
        channel = result.get("channel", args.channel)
        if args.json:
            print(json.dumps({"ok": True, "channel": channel, "ts": ts}))
        else:
            print(f"Message sent successfully (channel={channel}, ts={ts})")
    else:
        error = result.get("error", "unknown")
        print(f"ERROR: Slack API returned error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
