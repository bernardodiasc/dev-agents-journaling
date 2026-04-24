"""Post a message to Slack using ``chat.postMessage`` (stdlib only).

If ``--file`` points to a ``.md`` (report or plan), renders the Slack-mrkdwn sibling
``.slack.txt`` just-in-time via ``journal-render-slack`` and posts that. The sibling
is left on disk as a receipt: its presence indicates the file was posted.
"""

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
from _shared.path_guard import (
    MAX_READ_BYTES_FOR_SLACK_POST,
    read_text_limited,
    resolve_under_repo,
    resolve_write_path_under_repo,
    atomic_write_text,
)
from _shared.script_utils import (
    list_channel_aliases,
    load_optional_install_config,
    load_token,
    resolve_channel_by_name,
    validate_channel_id,
    validate_token_env_var,
)

# Render helper (md → Slack mrkdwn). Import after sys.path tweak.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "journal-render-slack" / "scripts"))
from render_slack_from_markdown import render_markdown_to_slack  # noqa: E402

SLACK_API_URL = "https://slack.com/api/chat.postMessage"
DEFAULT_TOKEN_VAR = "JOURNALING_SLACK_BOT_TOKEN"
HTTP_TIMEOUT_SECONDS = 15
# https://api.slack.com/methods/chat.postMessage — text field size limit
SLACK_TEXT_MAX_CHARS = 40_000
_SLACK_USER_ID = re.compile(r"^U[A-Za-z0-9]{8,}$")
_SLACK_THREAD_TS = re.compile(r"^\d{8,20}\.\d{1,10}$")


def _validate_user_id(user_id: str) -> None:
    if not _SLACK_USER_ID.match(user_id):
        sys.exit(
            "ERROR: JOURNALING_SLACK_USER_ID must look like a Slack member ID "
            "(e.g. U0123456789).",
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


def _resolve_body(repo_root: Path, args: argparse.Namespace) -> tuple[str, Path | None]:
    """Return (message text, *pending* slack-sibling path or None).

    The sibling is **not written here** — :func:`_write_sibling_receipt` writes it
    right before a successful post so the "exists ⇒ delivered" invariant holds.
    Dry-run renders in-memory and never writes.
    """

    if args.message:
        return args.message, None

    if args.file:
        src = resolve_under_repo(repo_root, args.file)
        if src.suffix.lower() == ".md":
            md_text = read_text_limited(src, max_bytes=MAX_READ_BYTES_FOR_SLACK_POST)
            slack_text = render_markdown_to_slack(md_text)
            sibling = resolve_write_path_under_repo(
                repo_root, str(src.with_suffix(".slack.txt").relative_to(repo_root)),
            )
            return slack_text, sibling
        # Already a .slack.txt (or other) — read as-is, no receipt to write
        return read_text_limited(src, max_bytes=MAX_READ_BYTES_FOR_SLACK_POST), None

    if not sys.stdin.isatty():
        data = sys.stdin.read()
        if len(data) > MAX_READ_BYTES_FOR_SLACK_POST:
            sys.exit(
                f"ERROR: stdin input exceeds max read size ({MAX_READ_BYTES_FOR_SLACK_POST} bytes).",
            )
        return data, None

    sys.exit("ERROR: provide a positional message, --file, or pipe stdin.")


def _write_sibling_receipt(sibling: Path, text: str) -> None:
    atomic_write_text(sibling, text)


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
        help="Read body from file. If a .md is passed, renders sibling .slack.txt first.",
    )
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
        "--dry-run",
        action="store_true",
        help="Render (if .md) but do not post; prints the body that would be sent.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print one JSON line with ok, channel, ts (or ok, dry_run for --dry-run)",
    )
    args = parser.parse_args()

    if args.channel and args.channel_name:
        sys.exit("ERROR: use --channel or --channel-name, not both.")

    validate_token_env_var(args.token_var)
    repo = find_journaling_repo_root(Path(__file__))

    text, pending_sibling = _resolve_body(repo, args)

    user_id = load_optional_install_config("JOURNALING_SLACK_USER_ID", start=repo)
    if args.prepend_user_mention:
        if not user_id:
            sys.exit(
                "ERROR: --prepend-user-mention requires JOURNALING_SLACK_USER_ID in .env.",
            )
        _validate_user_id(user_id)
        text = f"<@{user_id}>\n\n{text}"

    if not text.strip():
        sys.exit("ERROR: message is empty.")
    if len(text) > SLACK_TEXT_MAX_CHARS:
        sys.exit(
            f"ERROR: message is {len(text)} characters; Slack allows at most "
            f"{SLACK_TEXT_MAX_CHARS}. Post an excerpt or split into multiple messages.",
        )

    if args.dry_run:
        # Dry-run never writes the sibling receipt — "exists ⇒ delivered."
        if args.json:
            payload = {"ok": True, "dry_run": True}
            if pending_sibling is not None:
                payload["would_render"] = str(pending_sibling.relative_to(repo))
            print(json.dumps(payload))
        else:
            if pending_sibling is not None:
                print(
                    f"(dry-run) would render → {pending_sibling.relative_to(repo)}",
                    file=sys.stderr,
                )
            print(text)
        return

    channel = _resolve_channel(args, repo)
    validate_channel_id(channel)
    _validate_thread_ts(args.thread_ts)
    token = load_token(args.token_var)
    result = send_message(token, text, channel, args.thread_ts)

    if result.get("ok"):
        ts = result.get("ts", "")
        channel_out = result.get("channel", channel)
        # Write the receipt *after* a successful post.
        if pending_sibling is not None:
            _write_sibling_receipt(pending_sibling, text)
        if args.json:
            payload = {"ok": True, "channel": channel_out, "ts": ts}
            if pending_sibling is not None:
                payload["rendered"] = str(pending_sibling.relative_to(repo))
            print(json.dumps(payload))
        else:
            if pending_sibling is not None:
                print(f"Rendered → {pending_sibling.relative_to(repo)}")
            print(f"Message sent successfully (channel={channel_out}, ts={ts})")
    else:
        error = result.get("error", "unknown")
        print(f"ERROR: Slack API returned error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
