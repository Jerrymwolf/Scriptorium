#!/usr/bin/env bash
# Scriptorium SessionStart hook — Layer-A discipline injection.
#
# Streams skills/using-scriptorium/INJECTION.md to stdout so Claude Code can
# inject it as session context. The Cowork runtime delivers the same file via
# the FastMCP `instructions` field (see scriptorium/mcp/server.py); this hook
# is the Claude-Code-side delivery so both runtimes share one canonical path.
#
# Input:  none (Claude Code may pass JSON on stdin; we ignore it).
# Output: INJECTION.md contents on stdout when the file exists and is non-empty.
# Stderr: diagnostic only — never duplicates injection text.
# Exit:   always 0 (must never block a session).

set +e

INJECTION_REL="skills/using-scriptorium/INJECTION.md"

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  printf '[scriptorium session-start] CLAUDE_PLUGIN_ROOT not set; cannot locate INJECTION.md.\n' >&2
  exit 0
fi

INJECTION_PATH="${CLAUDE_PLUGIN_ROOT}/${INJECTION_REL}"

if [ ! -f "${INJECTION_PATH}" ]; then
  printf '[scriptorium session-start] INJECTION.md missing at %s; session continues without discipline injection.\n' "${INJECTION_PATH}" >&2
  exit 0
fi

if [ ! -s "${INJECTION_PATH}" ]; then
  printf '[scriptorium session-start] INJECTION.md is empty at %s; session continues without discipline injection.\n' "${INJECTION_PATH}" >&2
  exit 0
fi

cat "${INJECTION_PATH}"
exit 0
