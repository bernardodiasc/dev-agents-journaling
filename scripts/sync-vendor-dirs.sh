#!/usr/bin/env bash
# Regenerate project-level .cursor/skills and .claude/skills as symlinks into src/skills.
#
# Canonical source: src/skills/journaling. Vendor dirs are gitignored and derived on
# demand. For Claude Code across *all* projects, prefer scripts/install-user-skill.sh.
#
# Usage:
#   bash scripts/sync-vendor-dirs.sh            # regenerate (idempotent)
#   bash scripts/sync-vendor-dirs.sh --check    # report-only; exit non-zero on drift

set -euo pipefail

mode="regenerate"
if [[ "${1:-}" == "--check" ]]; then
  mode="check"
elif [[ $# -gt 0 ]]; then
  echo "usage: $0 [--check]" >&2
  exit 2
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ ! -f src/skills/journaling/SKILL.md ]]; then
  echo "ERROR: expected src/skills/journaling/SKILL.md under $repo_root" >&2
  exit 1
fi

drift=0
declare -a links=(
  ".cursor/skills|../src/skills"
  ".claude/skills|../src/skills"
)

for entry in "${links[@]}"; do
  link_path="${entry%%|*}"
  target="${entry#*|}"
  if [[ -L "$link_path" && "$(readlink -- "$link_path")" == "$target" ]]; then
    continue
  fi
  if [[ "$mode" == "check" ]]; then
    echo "drift: $link_path (expected -> $target)"
    drift=1
    continue
  fi
  if [[ -e "$link_path" || -L "$link_path" ]]; then
    # Only replace symlinks or empty dirs; never delete real files.
    if [[ -L "$link_path" ]]; then
      rm -- "$link_path"
    elif [[ -d "$link_path" && -z "$(ls -A -- "$link_path")" ]]; then
      rmdir -- "$link_path"
    else
      echo "ERROR: $link_path exists and is not a symlink; move it aside first." >&2
      exit 1
    fi
  fi
  mkdir -p -- "$(dirname -- "$link_path")"
  ln -s -- "$target" "$link_path"
done

if [[ "$mode" == "check" ]]; then
  [[ $drift -eq 0 ]] && echo "vendor-dirs: OK" || { echo "vendor-dirs: drift (run: bash scripts/sync-vendor-dirs.sh)" >&2; exit 1; }
else
  echo "vendor-dirs: synced (.cursor/skills, .claude/skills)"
fi
