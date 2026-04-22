#!/usr/bin/env bash
# Scriptorium Codex parity: build .codex/skills and .codex/commands as
# symlinks into .claude-plugin/. Safe to rerun — stale links are wiped.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC_SKILLS="$ROOT/skills"
SRC_COMMANDS="$ROOT/commands"
DST_SKILLS="$ROOT/.codex/skills"
DST_COMMANDS="$ROOT/.codex/commands"

mkdir -p "$DST_SKILLS" "$DST_COMMANDS"

# Wipe stale symlinks in each destination
find "$DST_SKILLS" -mindepth 1 -maxdepth 1 -type l -delete
find "$DST_COMMANDS" -mindepth 1 -maxdepth 1 -type l -delete

# Skills — one symlink per skill directory.
if [ -d "$SRC_SKILLS" ]; then
  for dir in "$SRC_SKILLS"/*/; do
    [ -d "$dir" ] || continue
    name="$(basename "$dir")"
    ln -sfn "../../skills/$name" "$DST_SKILLS/$name"
  done
fi

# Commands — one symlink per .md file.
if [ -d "$SRC_COMMANDS" ]; then
  for f in "$SRC_COMMANDS"/*.md; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"
    ln -sfn "../../commands/$name" "$DST_COMMANDS/$name"
  done
fi

n_skills=$(find "$DST_SKILLS" -mindepth 1 -maxdepth 1 -type l | wc -l | tr -d ' ')
n_commands=$(find "$DST_COMMANDS" -mindepth 1 -maxdepth 1 -type l | wc -l | tr -d ' ')
printf 'Linked %s skills, %s commands into .codex/.\n' "$n_skills" "$n_commands"
