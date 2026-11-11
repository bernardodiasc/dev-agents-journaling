#!/usr/bin/env bash
# Install the journaling skill for Claude Code at user level, so it works from any
# project: ~/.claude/skills/journaling -> <this repo>/src/skills/journaling
#
# Journal data and .env stay in this repo (scripts resolve the symlink back here).
# Edits to src/skills/journaling are live immediately. Idempotent.
#
# Usage: bash scripts/install-user-skill.sh [--uninstall]

set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
src="$repo_root/src/skills/journaling"
dest_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills"
dest="$dest_dir/journaling"

if [[ "${1:-}" == "--uninstall" ]]; then
  if [[ -L "$dest" ]]; then rm -- "$dest"; echo "removed $dest"; else echo "nothing to remove at $dest"; fi
  exit 0
fi

[[ -f "$src/SKILL.md" ]] || { echo "ERROR: $src/SKILL.md not found" >&2; exit 1; }
mkdir -p -- "$dest_dir"

if [[ -L "$dest" ]]; then
  rm -- "$dest"
elif [[ -e "$dest" ]]; then
  echo "ERROR: $dest exists and is not a symlink; move it aside first." >&2
  exit 1
fi
ln -s -- "$src" "$dest"
echo "installed: $dest -> $src"

if [[ ! -f "$repo_root/.env" ]]; then
  echo "next: cp $repo_root/.env.example $repo_root/.env && chmod 600 $repo_root/.env  (then fill in the bot token + channel ID)"
fi
