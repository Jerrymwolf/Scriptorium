"""Cowork-runtime detection and backend taxonomy.

Cowork is a sandboxed runtime without local shell access. v0.3 treats the
following env-var truthy values as explicit Cowork mode:
  SCRIPTORIUM_COWORK, SCRIPTORIUM_FORCE_COWORK

v0.4 / T13 adds the extraction-backend taxonomy. The Cowork orchestrator's
`using-scriptorium` runtime probe selects one of three backends per review,
each with a different per-paper isolation guarantee:

  - ``mcp``        — scriptorium-mcp running; per-paper extraction context
                     lives in the MCP server's process. Isolation: HIGH.
  - ``notebooklm`` — fresh notebook (or rotating scratch) per paper via
                     ``mcp__notebooklm-mcp__*``. Isolation: HIGH (fresh)
                     or MEDIUM (rotating scratch).
  - ``sequential`` — single chat thread, papers one at a time, with a
                     context-clear prompt between them. Isolation: LOW —
                     prompt-discipline only. The honest-gap row.

The backend literals are reused as audit-row ``details["backend"]``
values and as the SKILL.md tokens reviewers pin against. Centralised here
so the spelling can't drift across the extraction module, the MCP server,
the SKILL, and the smoke doc.
"""
from __future__ import annotations

import os


_TRUTHY = {"1", "true", "yes"}


# Order matters here: documentation reads MCP → NotebookLM → sequential
# (preferred → degraded), and tests pin the order via this tuple.
COWORK_BACKENDS: tuple[str, ...] = ("mcp", "notebooklm", "sequential")

# The single backend that does NOT provide per-paper isolation in the
# T13 sense — papers share a chat-thread context. Any caller that
# branches on "is this backend isolation-honest?" should consult this
# set, not hard-code the literal.
COWORK_DEGRADED_BACKENDS: frozenset[str] = frozenset({"sequential"})


def is_cowork_mode() -> bool:
    for name in ("SCRIPTORIUM_COWORK", "SCRIPTORIUM_FORCE_COWORK"):
        val = os.environ.get(name)
        if val is None:
            continue
        if val.strip().lower() in _TRUTHY:
            return True
    return False


def is_valid_backend(name: str) -> bool:
    """Return True iff ``name`` is one of the canonical backend literals.

    Pure boolean — no exception raised. Callers that want a structured
    error should branch on this and raise their own ``ScriptoriumError``
    with the right symbol.
    """
    return name in COWORK_BACKENDS
