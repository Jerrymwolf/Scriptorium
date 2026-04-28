"""Cowork-runtime detection and backend / reviewer-branch taxonomies.

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

v0.4 / T15 adds a separate reviewer-branch taxonomy for the synthesis-exit
gate. Cowork has no ``Task`` tool to dispatch CC-style sub-agents, so the
gate routes through one of two branches:

  - ``notebooklm``     — preferred branch. The orchestrator ingests
                          ``synthesis.md`` and ``evidence.jsonl`` into
                          NotebookLM as ``source_type="text"`` (T02 spike
                          grade pinned in
                          ``tests/test_layer_b_runtime_parity.py``) and
                          asks a reviewer-style query whose response
                          becomes the §6.3 payload.
  - ``inline_degraded`` — degraded branch. The orchestrator emits the
                          §6.3 payload from its own model turn, walking
                          the citation tokens in-prose (no fresh
                          notebook context). Honest about its limits:
                          no isolated reviewer context, payload may be
                          contaminated by drafting context, parity with
                          NotebookLM is not claimed.

The reviewer-branch literals are reused as audit-row ``details["branch"]``
values, as the SKILL.md tokens readers pin against, and as the smoke-doc
matrix headings. Centralised here so the spelling can't drift across the
MCP server, the SKILL, and the smoke doc.

Note: ``notebooklm`` legitimately appears in BOTH taxonomies — it is the
T13 "fresh notebook per paper" extraction backend and (separately) the
T15 "ingest synthesis as text source" reviewer branch. The two roles are
distinct; the audit-row action distinguishes them
(``extraction.dispatch`` vs. ``cowork.reviewer_branch``).
"""
from __future__ import annotations

import os


_TRUTHY = {"1", "true", "yes"}


# ---------------------------------------------------------------------------
# Extraction-backend taxonomy (T13)
# ---------------------------------------------------------------------------

# Order matters here: documentation reads MCP → NotebookLM → sequential
# (preferred → degraded), and tests pin the order via this tuple.
COWORK_BACKENDS: tuple[str, ...] = ("mcp", "notebooklm", "sequential")

# The single backend that does NOT provide per-paper isolation in the
# T13 sense — papers share a chat-thread context. Any caller that
# branches on "is this backend isolation-honest?" should consult this
# set, not hard-code the literal.
COWORK_DEGRADED_BACKENDS: frozenset[str] = frozenset({"sequential"})


# ---------------------------------------------------------------------------
# Reviewer-branch taxonomy (T15)
# ---------------------------------------------------------------------------

# Order matters: documentation reads NotebookLM → inline-degraded
# (preferred → degraded). Tests pin this order. The preferred literal at
# index 0 must equal the Phase 0 / T02 grade
# (``T15_COWORK_REVIEWER_BRANCH``) — see
# ``tests/test_layer_b_runtime_parity.py``.
COWORK_REVIEWER_BRANCHES: tuple[str, ...] = ("notebooklm", "inline_degraded")

# The single reviewer-branch literal that does NOT provide an isolated
# reviewer context — the orchestrator emits the payload directly from
# its drafting context. T10 runtime-honesty convention: the SKILL.md
# Cowork section labels this branch with the ``⚠`` marker.
COWORK_DEGRADED_REVIEWER_BRANCHES: frozenset[str] = frozenset(
    {"inline_degraded"}
)


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


def is_valid_reviewer_branch(name: str) -> bool:
    """Return True iff ``name`` is one of the canonical reviewer-branch
    literals (T15).

    Pure boolean — no exception raised. Callers that want a structured
    error should branch on this and raise their own ``ScriptoriumError``
    with the right symbol (the MCP ``finalize_synthesis_reviewers`` tool
    uses ``E_REVIEWER_INVALID``).
    """
    return name in COWORK_REVIEWER_BRANCHES
