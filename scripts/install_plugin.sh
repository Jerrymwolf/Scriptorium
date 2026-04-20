#!/usr/bin/env bash
# Symlink the scriptorium plugin surface into ~/.claude/plugins/ so
# Claude Code picks it up on restart. The CLI itself is installed via
# `pipx install scriptorium`.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${HOME}/.claude/plugins/scriptorium"

mkdir -p "$(dirname "$DEST")"

if [ -L "$DEST" ] || [ -e "$DEST" ]; then
  printf 'Removing existing %s\n' "$DEST"
  rm -rf "$DEST"
fi

ln -s "$ROOT" "$DEST"
printf 'Linked %s → %s\n' "$ROOT" "$DEST"
printf 'Restart Claude Code to load the plugin.\n'
