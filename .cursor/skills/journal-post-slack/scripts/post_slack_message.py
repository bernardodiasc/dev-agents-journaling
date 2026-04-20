"""Post a message to Slack using ``chat.postMessage`` (stdlib only)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.journaling_repo import find_journaling_repo_root
from _shared.path_guard import MAX_READ_BYTES_FOR_SLACK_POST, read_text_limited, resolve_under_repo
from _shared.script_utils import load_optional_install_config, load_token, validate_token_env_var

SLACK_API_URL = "https://slack.com/api/chat.postMessage"
DEFAULT_TOKEN_VAR = "JOURNALING_SLACK_BOT_TOKEN"
HTTP_TIMEOUT_SECONDS = 15
# https://api.slack.com/methods/chat.postMessage — text field size limit
SLACK_TEXT_MAX_CHARS = 40_000
_SLACK_CHANNEL_ID = re.compile(r"^[CGD][A-Za-z0-9]{8,}$")
_SLACK_USER_ID = re.compile(r"^U[A-Za-z0-9]{8,}$")
_SLACK_THREAD_TS = re.compile(r"^\d{8,20}\.\d{1,10}$")


def _validate_user_id(user_id: str) -> None:
    if not _SLACK_USER_ID.match(user_id):
        sys.exit(
            "ERROR: JOURNALING_SLACK_USER_ID must look like a Slack member ID "
            "(e.g. U0123456789).",
        )


def _validate_channel_id(channel: str) -> None:
    if not _SLACK_CHANNEL_ID.match(channel):
        sys.exit(
            "ERROR: --channel must be a Slack channel or conversation ID "
            "(e.g. C0123456789), not a channel name.",
        )


def _validate_thread_ts(thread_ts: str | None) -> None:
    if thread_ts is None:
        return
    if not _SLACK_THREAD_TS.match(thread_ts):
        sys.exit(
            "ERROR: --thread-ts must look like a Slack message timestamp "
            "(e.g. 1711900000.000100).",
        )


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
            raw = resp.read()
    except (URLError, TimeoutError):
        sys.exit("ERROR: Slack API request failed (network or timeout).")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        sys.exit("ERROR: Slack API returned a non-JSON response.")


def read_message_text(repo_root: Path, args: argparse.Namespace) -> str:
    if args.message:
        return args.message
    if args.file:
        path = resolve_under_repo(repo_root, args.file)
        return read_text_limited(path, max_bytes=MAX_READ_BYTES_FOR_SLACK_POST)
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        if len(data) > MAX_READ_BYTES_FOR_SLACK_POST:
            sys.exit(
                f"ERROR: stdin input exceeds max read size ({MAX_READ_BYTES_FOR_SLACK_POST} bytes).",
            )
        return data
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
        default=None,
        help="Slack channel ID (default: JOURNALING_SLACK_CHANNEL_ID from .env)",
    )
    parser.add_argument(
        "--prepend-user-mention",
        action="store_true",
        help="Prepend <@USER_ID> using JOURNALING_SLACK_USER_ID from .env",
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
    repo = find_journaling_repo_root(Path(__file__))
    channel = args.channel or load_optional_install_config(
        "JOURNALING_SLACK_CHANNEL_ID",
        start=repo,
    )
    if not channel:
        sys.exit(
            "ERROR: pass --channel or set JOURNALING_SLACK_CHANNEL_ID in .env "
            "(see .env.example).",
        )
    _validate_channel_id(channel)

    user_id = load_optional_install_config("JOURNALING_SLACK_USER_ID", start=repo)
    if args.prepend_user_mention:
        if not user_id:
            sys.exit(
                "ERROR: --prepend-user-mention requires JOURNALING_SLACK_USER_ID in .env.",
            )
        _validate_user_id(user_id)

    _validate_thread_ts(args.thread_ts)
    text = read_message_text(repo, args)
    if args.prepend_user_mention and user_id:
        text = f"<@{user_id}>\n\n{text}"
    if not text.strip():
        sys.exit("ERROR: message is empty.")
    if len(text) > SLACK_TEXT_MAX_CHARS:
        sys.exit(
            f"ERROR: message is {len(text)} characters; Slack allows at most "
            f"{SLACK_TEXT_MAX_CHARS}. Post an excerpt or split into multiple messages.",
        )

    token = load_token(args.token_var)
    result = send_message(token, text, channel, args.thread_ts)

    if result.get("ok"):
        ts = result.get("ts", "")
        channel_out = result.get("channel", channel)
        if args.json:
            print(json.dumps({"ok": True, "channel": channel_out, "ts": ts}))
        else:
            print(f"Message sent successfully (channel={channel_out}, ts={ts})")
    else:
        error = result.get("error", "unknown")
        print(f"ERROR: Slack API returned error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
