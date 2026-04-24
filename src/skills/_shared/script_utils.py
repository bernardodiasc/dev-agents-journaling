"""Shared helpers for journaling skill scripts (load tokens and install config from ``.env``)."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Slack token env vars: SLACK_* (team convention) or journaling-specific name.
# Max 256 chars total to prevent ReDoS attacks
_TOKEN_VAR_PATTERN = re.compile(r"^(SLACK_[A-Z0-9_]{1,120}|JOURNALING_SLACK_BOT_TOKEN)$", re.VERBOSE)

# Any env var name we will read as install config. Token names are excluded.
# Max 256 chars total to prevent ReDoS attacks
_INSTALL_CONFIG_PATTERN = re.compile(
    r"^JOURNALING_(?:SLACK_CHANNEL_ID(?:_[A-Z0-9_]{1,120})?|SLACK_USER_ID|JIRA_BASE_URL)$", re.VERBOSE
)

# Prefix for named Slack channel aliases (e.g. JOURNALING_SLACK_CHANNEL_ID_TEAM).
_NAMED_CHANNEL_PREFIX = "JOURNALING_SLACK_CHANNEL_ID_"

# Slack channel IDs are 9-11 characters long; cap at 20 to prevent ReDoS
_CHANNEL_ID_RE = re.compile(r"^[CGD][A-Za-z0-9]{8,19}$")


def validate_token_env_var(var_name: str) -> str:
    if not _TOKEN_VAR_PATTERN.fullmatch(var_name):
        sys.exit(
            "ERROR: --token-var must be SLACK_* or JOURNALING_SLACK_BOT_TOKEN.",
        )
    return var_name


def find_dotenv(start: Path | None = None) -> Path | None:
    """Search upward from ``start`` (or this file's directory) for a ``.env`` file."""

    if start is None:
        anchor = Path(__file__).resolve().parent
    else:
        p = Path(start).resolve()
        anchor = p if p.is_dir() else p.parent
    for parent in [anchor, *anchor.parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


def _iter_dotenv_pairs(env_path: Path):
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, value = line.partition("=")
        yield k.strip(), value.strip().strip("'\"")


def load_optional_install_config(key: str, *, start: Path | None = None) -> str | None:
    """Load a non-secret install config value (channel / user ID / Jira base URL).

    Checks ``os.environ`` first, then the first ``.env`` found walking upward from
    ``start`` (default: this file's directory). Returns ``None`` if unset or missing file.

    Supported keys:
      - ``JOURNALING_SLACK_CHANNEL_ID`` (default channel)
      - ``JOURNALING_SLACK_CHANNEL_ID_<NAME>`` (named alias, e.g. ``_TEAM``, ``_DEV_QA``)
      - ``JOURNALING_SLACK_USER_ID``
      - ``JOURNALING_JIRA_BASE_URL``
    """

    if not _INSTALL_CONFIG_PATTERN.fullmatch(key):
        raise ValueError(f"unsupported install config key: {key!r}")

    v = os.environ.get(key, "").strip()
    if v:
        return v

    env_path = find_dotenv(start)
    if env_path is None:
        return None

    # Warn if .env file has overly permissive permissions (world-readable)
    try:
        stat_info = env_path.stat()
        if stat_info.st_mode & 0o004:  # Check if world-readable
            import warnings
            warnings.warn(
                f"WARNING: .env file {env_path} is world-readable; "
                "consider restricting permissions (chmod 600).",
                stacklevel=2,
            )
    except (OSError, AttributeError):
        pass

    for k, value in _iter_dotenv_pairs(env_path):
        if k == key and value:
            return value
    return None


def _normalize_channel_name(name: str) -> str:
    """Normalize a user-provided channel alias to the env-var suffix form (upper + underscores)."""

    cleaned = name.strip().upper().replace("-", "_").replace(" ", "_")
    # Strip any stray chars that aren't A-Z/0-9/_
    return re.sub(r"[^A-Z0-9_]", "", cleaned)


def load_named_channels(*, start: Path | None = None) -> dict[str, str]:
    """Return ``{name: channel_id}`` for every ``JOURNALING_SLACK_CHANNEL_ID_<NAME>`` set.

    Reads ``os.environ`` overlaid on the nearest ``.env`` (env wins). ``name`` is the
    raw suffix (e.g. ``TEAM``, ``DEV_QA``) — use :func:`resolve_channel_by_name` for
    case-insensitive lookup. Does **not** include the default ``JOURNALING_SLACK_CHANNEL_ID``.
    """

    out: dict[str, str] = {}
    env_path = find_dotenv(start)
    if env_path is not None:
        for k, value in _iter_dotenv_pairs(env_path):
            if k.startswith(_NAMED_CHANNEL_PREFIX) and value:
                out[k[len(_NAMED_CHANNEL_PREFIX):]] = value
    for k, value in os.environ.items():
        if k.startswith(_NAMED_CHANNEL_PREFIX) and value.strip():
            out[k[len(_NAMED_CHANNEL_PREFIX):]] = value.strip()
    return out


def resolve_channel_by_name(user_name: str, *, start: Path | None = None) -> str | None:
    """Look up a channel ID by human-provided alias (``dev-qa`` → ``JOURNALING_SLACK_CHANNEL_ID_DEV_QA``).

    Returns the channel ID on match, else ``None``. The caller should fall back to
    the default ``JOURNALING_SLACK_CHANNEL_ID`` and/or raise a helpful error.
    """

    normalized = _normalize_channel_name(user_name)
    if not normalized:
        return None
    channels = load_named_channels(start=start)
    return channels.get(normalized)


def list_channel_aliases(*, start: Path | None = None) -> list[str]:
    """Return sorted alias names (the ``<NAME>`` part of ``JOURNALING_SLACK_CHANNEL_ID_<NAME>``)."""

    return sorted(load_named_channels(start=start).keys())


def validate_channel_id(channel: str) -> None:
    """Exit with a helpful error if ``channel`` is not a Slack conversation ID."""

    if not _CHANNEL_ID_RE.match(channel):
        sys.exit(
            "ERROR: channel must be a Slack conversation ID (e.g. C0123456789), "
            "not a channel name.",
        )


def load_token(var_name: str) -> str:
    """Return token from environment or the first ``.env`` found upward."""

    validate_token_env_var(var_name)
    v = os.environ.get(var_name, "").strip()
    if v:
        # Validate token is not suspiciously short
        if len(v) < 10:
            sys.exit(f"ERROR: {var_name} value is suspiciously short (< 10 chars); check .env or env var.")
        return v

    env_path = find_dotenv()
    if env_path is None:
        sys.exit("ERROR: .env file not found in any parent directory (or set env var).")

    # Warn about world-readable .env file (contains secrets)
    try:
        stat_info = env_path.stat()
        if stat_info.st_mode & 0o004:  # Check if world-readable
            import warnings
            warnings.warn(
                f"WARNING: .env file {env_path} is world-readable and contains secrets; "
                "restrict permissions immediately (chmod 600).",
                stacklevel=2,
            )
    except (OSError, AttributeError):
        pass

    for k, value in _iter_dotenv_pairs(env_path):
        if k == var_name and value:
            if len(value) < 10:
                sys.exit(f"ERROR: {var_name} value is suspiciously short (< 10 chars); check .env.")
            return value

    sys.exit(
        f"ERROR: {var_name} not found or empty in .env / environment (see --token-var).",
    )
