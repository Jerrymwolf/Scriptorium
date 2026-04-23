#!/usr/bin/env bash
# Scriptorium PostToolUse evidence-first gate — belt-and-suspenders only.
#
# Discipline: lit-synthesizing step 5 (mandatory cite-check inside the skill)
# is authoritative. This hook re-runs the same check via `scriptorium verify`
# after Write/Edit tool calls on synthesis.md, and writes a diagnostic to
# stderr if the verification fails. The hook NEVER blocks the edit — exit
# code is always 0 — so that user work is never lost.
#
# Input: Claude Code PostToolUse JSON payload on stdin.
# Output: nothing on stdout; diagnostic on stderr.
# Exit:   always 0.

set +e

payload="$(cat 2>/dev/null || true)"

file_path="$(
  printf '%s' "$payload" | python3 -c '
import json, sys
try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception:
    data = {}
tool_input = data.get("tool_input") or {}
print(tool_input.get("file_path", ""))
' 2>/dev/null)"

# Scope precondition check — called from downstream-phase branches.
_check_scope_precondition() {
  local target_file="$1"
  local review_dir
  review_dir="$(dirname "$target_file")"
  local scope_file="$review_dir/scope.json"
  if [ ! -f "$scope_file" ]; then
    printf '[scope gate] scope.json missing at %s — run /scriptorium:lit-scoping before continuing.\n' "$scope_file" >&2
    return 0
  fi
  if command -v scriptorium >/dev/null 2>&1; then
    if ! scriptorium verify --scope "$scope_file" >/dev/null 2>&1; then
      printf '[scope gate] scope.json at %s is invalid — run /scriptorium:lit-scoping --edit to fix.\n' "$scope_file" >&2
    fi
  fi
}

case "$file_path" in
  *corpus.jsonl)
    _check_scope_precondition "$file_path"
    ;;
  *evidence.jsonl)
    _check_scope_precondition "$file_path"
    ;;
  *contradictions.md)
    _check_scope_precondition "$file_path"
    ;;
  *overview.md)
    if ! command -v scriptorium >/dev/null 2>&1; then
      printf '[evidence-first gate] scriptorium CLI not on PATH — skipping overview lint.\n' >&2
      exit 0
    fi
    out="$(scriptorium verify --overview "$file_path" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
      printf '[evidence-first gate] scriptorium verify --overview %s exited %s\n' "$file_path" "$rc" >&2
      printf '%s\n' "$out" >&2
    fi
    ;;
  *synthesis.md)
    if ! command -v scriptorium >/dev/null 2>&1; then
      printf '[evidence-first gate] scriptorium CLI not on PATH — skipping redundancy check; lit-synthesizing step 5 remains authoritative.\n' >&2
      exit 0
    fi
    out="$(scriptorium verify --synthesis "$file_path" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
      printf '[evidence-first gate] scriptorium verify --synthesis %s exited %s\n' "$file_path" "$rc" >&2
      printf '%s\n' "$out" >&2
      printf '[evidence-first gate] Skill lit-synthesizing step 5 is authoritative; this hook is belt-and-suspenders.\n' >&2
    fi
    ;;
  *)
    :
    ;;
esac

exit 0
