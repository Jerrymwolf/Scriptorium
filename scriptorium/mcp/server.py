"""Scriptorium MCP server — Cowork-facing enforcement surface (T04).

Exposes the same enforcement tools as the CLI so Cowork can call them via the
Model Context Protocol.  The six registered tools match §6.5:

    verify, phase_show, phase_set, phase_override,
    extract_paper (stub), validate_reviewer_output

INJECTION.md is loaded from ``<plugin_root>/skills/using-scriptorium/INJECTION.md``
(plugin root = three levels up from this file: mcp/ → scriptorium/ → repo root).
If the file is absent the server starts with an empty instructions string and
emits a warning to stderr.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from scriptorium.paths import resolve_review_dir

# ---------------------------------------------------------------------------
# Plugin root and INJECTION.md
# ---------------------------------------------------------------------------

_PLUGIN_ROOT = Path(__file__).resolve().parents[2]
_INJECTION_PATH = _PLUGIN_ROOT / "skills" / "using-scriptorium" / "INJECTION.md"


def _load_instructions() -> str:
    if _INJECTION_PATH.exists():
        return _INJECTION_PATH.read_text(encoding="utf-8")
    print(
        f"WARNING: INJECTION.md not found at {_INJECTION_PATH}; using empty instructions",
        file=sys.stderr,
    )
    return ""


# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("scriptorium", instructions=_load_instructions())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _paths(review_dir: str, *, create: bool = False):
    """Resolve a ReviewPaths from a string path.

    Pass ``create=True`` only for tools that need to write to the review dir.
    Read-only tools pass the default ``create=False`` so a typo'd path does
    not silently materialise a junk directory.
    """
    return resolve_review_dir(explicit=Path(review_dir), create=create)


# ---------------------------------------------------------------------------
# Tool: verify
# ---------------------------------------------------------------------------


@mcp.tool()
def verify(
    gate: str,
    review_dir: str,
    scope: str | None = None,
    overview: str | None = None,
    synthesis: str | None = None,
) -> dict[str, Any]:
    """Run a verification gate.

    gate: one of scope | synthesis | publish | overview
    review_dir: path to the review directory
    scope: path to scope.json (used with gate=scope)
    overview: path to overview.md (used with gate=overview)
    synthesis: path to synthesis.md (used with gate=synthesis)
    """
    from scriptorium.errors import EXIT_CODES, ScriptoriumError
    from scriptorium import phase_state as ps
    from scriptorium.scope import ScopeValidationError, load_scope
    from scriptorium.reasoning.verify_citations import verify_synthesis

    paths = _paths(review_dir)

    if gate == "publish":
        try:
            state = ps.read(paths)
        except ScriptoriumError as e:
            return {"ok": False, "error": str(e), "code": EXIT_CODES[e.symbol]}
        synth_status = state["phases"].get("synthesis", {}).get("status", "pending")
        if synth_status in ("complete", "overridden"):
            return {"ok": True, "synthesis_status": synth_status}
        return {
            "ok": False,
            "publish_blocked": True,
            "reason": f"synthesis phase status is {synth_status!r}; must be 'complete' or 'overridden'",
            "synthesis_status": synth_status,
        }

    if gate == "scope":
        scope_path = Path(scope) if scope else paths.scope
        try:
            load_scope(scope_path)
        except FileNotFoundError:
            return {"ok": False, "error": f"scope.json not found at {scope_path}"}
        except ScopeValidationError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "scope_path": str(scope_path)}

    if gate == "overview":
        if not overview:
            return {"ok": False, "error": "gate=overview requires overview path"}
        from scriptorium.frontmatter import strip_frontmatter
        from scriptorium.overview.linter import OverviewLintError, lint_overview
        body = strip_frontmatter(Path(overview).read_text(encoding="utf-8"))
        try:
            lint_overview(body)
        except OverviewLintError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True}

    if gate == "synthesis":
        synth_path = Path(synthesis) if synthesis else paths.synthesis
        if not synth_path.exists():
            return {"ok": False, "error": f"synthesis file not found: {synth_path}"}
        text = synth_path.read_text(encoding="utf-8")
        report = verify_synthesis(text, paths)
        return {
            "ok": report.ok,
            "unsupported_sentences": report.unsupported_sentences,
            "missing_citations": [list(c) for c in report.missing_citations],
        }

    return {"ok": False, "error": f"unknown gate {gate!r}; choose scope|synthesis|publish|overview"}


# ---------------------------------------------------------------------------
# Tool: phase_show
# ---------------------------------------------------------------------------


@mcp.tool()
def phase_show(review_dir: str) -> dict[str, Any]:
    """Return the full phase-state JSON for a review."""
    from scriptorium.errors import EXIT_CODES, ScriptoriumError
    from scriptorium import phase_state as ps

    paths = _paths(review_dir)
    try:
        return ps.read(paths)
    except ScriptoriumError as e:
        return {"error": str(e), "code": EXIT_CODES[e.symbol]}


# ---------------------------------------------------------------------------
# Tool: phase_set
# ---------------------------------------------------------------------------


@mcp.tool()
def phase_set(
    review_dir: str,
    phase: str,
    status: str,
    artifact_path: str | None = None,
    verifier_signature: str | None = None,
    verified_at: str | None = None,
) -> dict[str, Any]:
    """Set a phase to a given status.

    phase: one of scoping|search|screening|extraction|synthesis|contradiction|audit
    status: pending|running|complete|failed  (use phase_override for overridden)
    verifier_signature: required when status=complete (sha256:<64 hex>)
    """
    from scriptorium.errors import EXIT_CODES, ScriptoriumError
    from scriptorium import phase_state as ps

    paths = _paths(review_dir, create=True)
    try:
        return ps.set_phase(
            paths, phase, status,
            artifact_path=artifact_path,
            verifier_signature=verifier_signature,
            verified_at=verified_at,
        )
    except ScriptoriumError as e:
        return {"error": str(e), "code": EXIT_CODES[e.symbol]}


# ---------------------------------------------------------------------------
# Tool: phase_override
# ---------------------------------------------------------------------------


@mcp.tool()
def phase_override(
    review_dir: str,
    phase: str,
    reason: str,
    actor: str,
) -> dict[str, Any]:
    """Mark a phase as overridden with a justification record.

    actor: name of the caller (Cowork must supply this explicitly).
    """
    from scriptorium.errors import EXIT_CODES, ScriptoriumError
    from scriptorium import phase_state as ps

    paths = _paths(review_dir, create=True)
    try:
        return ps.override_phase(paths, phase, reason=reason, actor=actor)
    except ScriptoriumError as e:
        return {"error": str(e), "code": EXIT_CODES[e.symbol]}


# ---------------------------------------------------------------------------
# Tool: extract_paper  (stub — T12/T13)
# ---------------------------------------------------------------------------


@mcp.tool()
def extract_paper(
    review_dir: str,
    paper_id: str,
) -> dict[str, Any]:
    """Extract structured evidence from a paper (NOT YET IMPLEMENTED in v0.4).

    This tool will be wired in T12/T13.  Returns a structured error now so
    Cowork can handle it gracefully rather than receiving an exception.
    """
    from scriptorium.errors import EXIT_CODES
    return {
        "error": "extract_paper not yet implemented in v0.4 (T12/T13)",
        "code": EXIT_CODES["E_NOT_IMPLEMENTED"],
    }


# ---------------------------------------------------------------------------
# Tool: validate_reviewer_output
# ---------------------------------------------------------------------------


@mcp.tool()
def validate_reviewer_output(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a reviewer output payload against the §6.3 schema.

    Returns {"ok": true} on success, or {"ok": false, "error": ..., "code": 22}
    on schema violation.
    """
    from scriptorium.errors import EXIT_CODES, ScriptoriumError
    from scriptorium.reviewers import validate_reviewer_output as _validate

    try:
        _validate(payload)
        return {"ok": True}
    except ScriptoriumError as e:
        return {"ok": False, "error": str(e), "code": EXIT_CODES[e.symbol]}
