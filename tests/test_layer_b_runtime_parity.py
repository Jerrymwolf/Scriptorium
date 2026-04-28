"""
Phase 0 / T02: NotebookLM source acceptance for reviewer input.

Records the empirical result of whether NotebookLM ingests synthesis-style
markdown for reviewer-style cite-checking.

Result:       pass
Date:         2026-04-26
Source form:  text (source_type="text")
Notebook:     scriptorium-t02-spike (deleted after probe)
Method:       Added a 10-claim test synthesis (7 cited via [paper:xxx],
              3 intentionally unsupported) via source_add(source_type="text").
              Source ingested cleanly (ready=True, sub-second).
              Reviewer-style query returned a per-claim breakdown that:
                - correctly named all 7 cited claims with their citation marker
                - flagged all 3 unsupported claims with verbatim quotes
              Output included structured citation back-references.

Implication for Phase 5:
    T15 Cowork reviewer branch = `notebooklm`.
    `source_type="text"` is the chosen reviewer-input form for v0.4.
    File/URL forms are not required to ship the cite-reviewer happy path.

Phase 5 / T15 lands the implementation literals on top of this Phase 0 pin.
The implementation tuple `COWORK_REVIEWER_BRANCHES` lives in
`scriptorium.cowork`; the tests below pin it to (preferred → degraded) and
assert the preferred literal == this Phase 0 grade so the spike result and
the wired branch can never silently drift apart.
"""

import hashlib
from pathlib import Path
from typing import Any

import pytest

from scriptorium.errors import EXIT_CODES, ScriptoriumError
from scriptorium.paths import ReviewPaths
from scriptorium.phase_state import init as phase_state_init
from scriptorium.reviewers import finalize_synthesis_phase
from scriptorium.storage.audit import load_audit


ALLOWED_GRADES = {"pass", "partial", "fail"}
ALLOWED_FORMS = {"text", "file", "url"}
# T02 spike grade space — the literal stored here is what Phase 0 chose
# between `notebooklm` (NotebookLM accepted reviewer-style input) and
# `degraded` (NotebookLM rejected; T15 had to ship the inline path
# instead). The implementation literals in COWORK_REVIEWER_BRANCHES are
# tested against this set in `test_t15_branch_literals_match_phase_0`.
ALLOWED_T15_BRANCHES = {"notebooklm", "degraded"}

NOTEBOOKLM_SOURCE_ACCEPTANCE: str = "pass"
NOTEBOOKLM_SOURCE_FORM: str = "text"

T15_COWORK_REVIEWER_BRANCH: str = (
    "notebooklm" if NOTEBOOKLM_SOURCE_ACCEPTANCE == "pass" else "degraded"
)


def test_t02_grade_recorded() -> None:
    assert NOTEBOOKLM_SOURCE_ACCEPTANCE in ALLOWED_GRADES


def test_t02_source_form_recorded() -> None:
    assert NOTEBOOKLM_SOURCE_FORM in ALLOWED_FORMS


def test_t15_branch_consistent_with_t02() -> None:
    assert T15_COWORK_REVIEWER_BRANCH in ALLOWED_T15_BRANCHES
    if NOTEBOOKLM_SOURCE_ACCEPTANCE == "pass":
        assert T15_COWORK_REVIEWER_BRANCH == "notebooklm"
    else:
        assert T15_COWORK_REVIEWER_BRANCH == "degraded"


# ---------------------------------------------------------------------------
# T15 — reviewer-branch taxonomy and runtime-parity pins
# ---------------------------------------------------------------------------
#
# T15 wires the Cowork side of the §6.3 reviewer gate. The Phase 0 spike
# (T02) pinned `notebooklm` as the preferred branch; the implementation
# adds a degraded sibling — `inline_degraded` — for orchestrators that
# don't have NotebookLM enabled. These tests pin:
#
#   A. the implementation tuple matches Phase 0 (preferred literal first)
#   B. the degraded literal is honestly named (no fake parity)
#   C. is_valid_reviewer_branch / COWORK_DEGRADED_REVIEWER_BRANCHES shapes
#   D. both branches accept §6.3 `runtime="cowork"` payloads through
#      `finalize_synthesis_phase` (the runtime field is in the schema; T15
#      does NOT extend it — branch metadata lives in the audit row).
# ---------------------------------------------------------------------------


# The implementation literals — pin them here so a drive-by edit in
# scriptorium/cowork.py can't silently rename them.
T15_PREFERRED_BRANCH: str = "notebooklm"
T15_DEGRADED_BRANCH: str = "inline_degraded"


def _hash_str(s: str) -> str:
    return f"sha256:{hashlib.sha256(s.encode('utf-8')).hexdigest()}"


def _make_paths(review_dir: Path) -> ReviewPaths:
    for sub in (
        "sources/pdfs",
        "sources/papers",
        "data/extracts",
        "audit/overview-archive",
        ".scriptorium",
    ):
        (review_dir / sub).mkdir(parents=True, exist_ok=True)
    return ReviewPaths(root=review_dir)


def _cowork_payload(
    *,
    reviewer: str,
    verdict: str = "pass",
    findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a §6.3 payload with `runtime="cowork"`.

    The §6.3 schema's `runtime` field is `claude_code|cowork`; the runtime
    string is part of the payload, not the branch. Cowork-branch metadata
    is recorded in the `cowork.reviewer_branch` audit row (T15), NOT in
    the §6.3 payload.
    """
    return {
        "reviewer": reviewer,
        "runtime": "cowork",
        "verdict": verdict,
        "summary": f"cowork-{reviewer}-{verdict}",
        "findings": findings if findings is not None else [],
        "synthesis_sha256": _hash_str(f"synthesis-{reviewer}"),
        "reviewer_prompt_sha256": _hash_str(f"prompt-{reviewer}"),
        "created_at": "2026-04-28T00:00:00Z",
    }


@pytest.fixture
def cowork_paths(tmp_path: Path) -> ReviewPaths:
    rd = tmp_path / "review"
    rd.mkdir()
    paths = _make_paths(rd)
    phase_state_init(paths)
    paths.synthesis.write_text("Cowork synthesis body.\n", encoding="utf-8")
    return paths


# --- A. implementation tuple matches Phase 0 ------------------------------


def test_t15_branch_tuple_exists_and_matches_phase_0_grade() -> None:
    """`COWORK_REVIEWER_BRANCHES` must exist on `scriptorium.cowork`,
    and its ordering must read preferred → degraded with the preferred
    literal == the Phase 0 / T02 grade."""
    from scriptorium.cowork import COWORK_REVIEWER_BRANCHES

    assert isinstance(COWORK_REVIEWER_BRANCHES, tuple)
    assert len(COWORK_REVIEWER_BRANCHES) == 2, (
        "T15 ships exactly two branches: preferred + one honest degraded path"
    )
    # Preferred literal sits at index 0 and must match Phase 0.
    assert COWORK_REVIEWER_BRANCHES[0] == T15_COWORK_REVIEWER_BRANCH
    assert COWORK_REVIEWER_BRANCHES[0] == T15_PREFERRED_BRANCH


def test_t15_branch_tuple_includes_pinned_literals() -> None:
    from scriptorium.cowork import COWORK_REVIEWER_BRANCHES

    assert COWORK_REVIEWER_BRANCHES == (
        T15_PREFERRED_BRANCH,
        T15_DEGRADED_BRANCH,
    )


# --- B. honest degraded labeling ------------------------------------------


def test_t15_degraded_branch_is_in_degraded_set() -> None:
    """The degraded branch must be flagged via
    `COWORK_DEGRADED_REVIEWER_BRANCHES`. A caller asking
    "is this branch honest about its limits?" must consult this set,
    not the literal."""
    from scriptorium.cowork import (
        COWORK_DEGRADED_REVIEWER_BRANCHES,
        COWORK_REVIEWER_BRANCHES,
    )

    assert isinstance(COWORK_DEGRADED_REVIEWER_BRANCHES, frozenset)
    assert T15_DEGRADED_BRANCH in COWORK_DEGRADED_REVIEWER_BRANCHES
    # The preferred branch is NOT degraded.
    assert T15_PREFERRED_BRANCH not in COWORK_DEGRADED_REVIEWER_BRANCHES
    # Every degraded literal must also appear in the canonical tuple.
    for d in COWORK_DEGRADED_REVIEWER_BRANCHES:
        assert d in COWORK_REVIEWER_BRANCHES


def test_t15_degraded_literal_uses_honest_name() -> None:
    """No "fake equivalence" between notebooklm and the degraded path —
    the degraded literal must read as a degraded label (contains
    'degraded' or 'inline'), not e.g. 'standard' or 'baseline'."""
    parts = T15_DEGRADED_BRANCH.lower()
    assert ("degraded" in parts) or ("inline" in parts), (
        f"degraded branch literal {T15_DEGRADED_BRANCH!r} must read as a "
        "degraded label so the audit row is self-explanatory"
    )


# --- C. is_valid_reviewer_branch boolean ----------------------------------


def test_t15_is_valid_reviewer_branch_accepts_canonical_literals() -> None:
    from scriptorium.cowork import (
        COWORK_REVIEWER_BRANCHES,
        is_valid_reviewer_branch,
    )

    for literal in COWORK_REVIEWER_BRANCHES:
        assert is_valid_reviewer_branch(literal), (
            f"{literal!r} should be valid"
        )


def test_t15_is_valid_reviewer_branch_rejects_unknown_strings() -> None:
    from scriptorium.cowork import is_valid_reviewer_branch

    for bad in ("", "claude_code", "mcp", "sequential", "Notebooklm", " notebooklm "):
        assert not is_valid_reviewer_branch(bad), (
            f"{bad!r} must NOT be a valid reviewer-branch literal"
        )


def test_t15_branch_taxonomy_does_not_overlap_with_extraction_taxonomy() -> None:
    """Reviewer-branches and extraction-backends are different taxonomies;
    a token from one must not implicitly act as the other. Pin the
    expectation that `mcp` and `sequential` (extraction-backend literals)
    are NOT valid reviewer branches."""
    from scriptorium.cowork import (
        COWORK_BACKENDS,
        COWORK_REVIEWER_BRANCHES,
    )

    # Defensive sanity: the two tuples must be disjoint EXCEPT possibly
    # `notebooklm` which legitimately appears in both (different role
    # per taxonomy: extraction backend vs. reviewer branch).
    extraction_only = set(COWORK_BACKENDS) - {"notebooklm"}
    for literal in extraction_only:
        assert literal not in COWORK_REVIEWER_BRANCHES, (
            f"{literal!r} is an extraction backend, not a reviewer branch — "
            "the taxonomies must not silently overlap"
        )


# --- D. both branches accept runtime="cowork" payloads --------------------


@pytest.mark.parametrize(
    "branch", ["notebooklm", "inline_degraded"]
)
def test_t15_finalize_accepts_cowork_payloads_unchanged(
    cowork_paths: ReviewPaths, branch: str
) -> None:
    """`finalize_synthesis_phase` already accepts `runtime="cowork"`
    (T14 made it runtime-agnostic). T15 must NOT extend the §6.3 schema —
    the test pins that a Cowork payload from EITHER branch flows through
    the same finalize without raising and converges on the same status
    as a Claude Code payload would."""
    cite = _cowork_payload(reviewer="cite", verdict="pass")
    contra = _cowork_payload(reviewer="contradiction", verdict="pass")
    result = finalize_synthesis_phase(
        cowork_paths,
        cite_result=cite,
        contradiction_result=contra,
    )
    # Same aggregation rule as CC: both pass + synthesis.md exists →
    # complete. The branch metadata is orthogonal — finalize doesn't see
    # it, and the §6.3 audit row preserves the runtime literal verbatim.
    assert result["synthesis_status"] == "complete"
    rows = load_audit(cowork_paths)
    cite_rows = [r for r in rows if r.action == "reviewer.cite"]
    assert len(cite_rows) == 1
    assert cite_rows[0].details["runtime"] == "cowork"


def test_t15_finalize_runtime_cowork_fail_keeps_running(
    cowork_paths: ReviewPaths,
) -> None:
    """Honest behavior: a Cowork-runtime fail aggregates exactly the same
    way as a CC-runtime fail. Parity must be honest — same rule, same
    outcome, same audit shape."""
    cite = _cowork_payload(
        reviewer="cite",
        verdict="fail",
        findings=[
            {"paper_id": "P1", "locator": "page:1",
             "kind": "unsupported_claim", "detail": "no row"}
        ],
    )
    contra = _cowork_payload(reviewer="contradiction", verdict="pass")
    result = finalize_synthesis_phase(
        cowork_paths,
        cite_result=cite,
        contradiction_result=contra,
    )
    assert result["synthesis_status"] == "running"


# ---------------------------------------------------------------------------
# T15 — MCP tool `finalize_synthesis_reviewers`
# ---------------------------------------------------------------------------
#
# The CC reviewer gate calls `scriptorium.reviewers.finalize_synthesis_phase`
# directly. Cowork has no Bash / no Python REPL — it must reach the gate
# through an MCP tool. T15 adds `finalize_synthesis_reviewers` that:
#
#   1. Validates `cowork_branch` against `COWORK_REVIEWER_BRANCHES`.
#   2. Calls `finalize_synthesis_phase(...)` unchanged.
#   3. Appends ONE additional audit row (`cowork.reviewer_branch`)
#      recording which branch produced the payloads.
#   4. Returns the merged result dict (finalize keys + cowork_branch).
#
# Audit-row contract per Cowork gate run: 4 rows total.
#   reviewer.cite + reviewer.contradiction + synthesis.gate (the standard
#   T14 trio) + cowork.reviewer_branch (T15 metadata).
# ---------------------------------------------------------------------------


def _cite(verdict: str = "pass") -> dict[str, Any]:
    return _cowork_payload(reviewer="cite", verdict=verdict)


def _contra(verdict: str = "pass") -> dict[str, Any]:
    return _cowork_payload(reviewer="contradiction", verdict=verdict)


@pytest.mark.parametrize(
    "branch", ["notebooklm", "inline_degraded"]
)
def test_t15_mcp_tool_accepts_canonical_branches(
    tmp_path: Path, branch: str
) -> None:
    """Both canonical branches must flow through the new MCP tool
    cleanly. Honest runtime parity: the result's `synthesis_status`
    matches what the CC path would produce for an identical pass+pass
    pair."""
    from scriptorium.mcp import server as mcp_server

    rd = tmp_path / "review"
    rd.mkdir()
    paths = _make_paths(rd)
    phase_state_init(paths)
    paths.synthesis.write_text("Hello.\n", encoding="utf-8")

    result = mcp_server.finalize_synthesis_reviewers(
        review_dir=str(rd),
        cite_result=_cite("pass"),
        contradiction_result=_contra("pass"),
        cowork_branch=branch,
    )
    assert "error" not in result, result
    assert result["synthesis_status"] == "complete"
    assert result["cowork_branch"] == branch


def test_t15_mcp_tool_rejects_unknown_branch(tmp_path: Path) -> None:
    """An unknown branch literal must short-circuit BEFORE finalize is
    called — no audit row, no phase-state mutation. Returns a structured
    error dict like other MCP tools (no exception)."""
    from scriptorium.mcp import server as mcp_server

    rd = tmp_path / "review"
    rd.mkdir()
    paths = _make_paths(rd)
    phase_state_init(paths)

    result = mcp_server.finalize_synthesis_reviewers(
        review_dir=str(rd),
        cite_result=_cite("pass"),
        contradiction_result=_contra("pass"),
        cowork_branch="bogus",
    )
    assert "error" in result
    # Branch validation reuses the existing E_REVIEWER_INVALID symbol
    # (per the brief: "no new error symbols unless the test surface
    # forces one"; this surface does not.)
    assert result["code"] == EXIT_CODES["E_REVIEWER_INVALID"]
    # No audit rows must have been written.
    assert load_audit(paths) == []


def test_t15_mcp_tool_rejects_invalid_payload(tmp_path: Path) -> None:
    """If finalize itself raises (bad §6.3 payload), the MCP tool
    surfaces the error code and DOES NOT append the cowork.reviewer_branch
    row — the branch row is emitted only on a successful finalize, so
    the audit trail can't claim a Cowork-branch dispatch happened when
    finalize never reached it."""
    from scriptorium.mcp import server as mcp_server

    rd = tmp_path / "review"
    rd.mkdir()
    paths = _make_paths(rd)
    phase_state_init(paths)

    bad_cite = {"reviewer": "cite"}  # missing required fields
    result = mcp_server.finalize_synthesis_reviewers(
        review_dir=str(rd),
        cite_result=bad_cite,
        contradiction_result=_contra("pass"),
        cowork_branch="notebooklm",
    )
    assert "error" in result
    assert result["code"] == EXIT_CODES["E_REVIEWER_INVALID"]
    rows = load_audit(paths)
    branch_rows = [r for r in rows if r.action == "cowork.reviewer_branch"]
    assert branch_rows == [], (
        "cowork.reviewer_branch row must NOT be appended when finalize "
        "never ran"
    )


def test_t15_mcp_tool_appends_branch_audit_row(tmp_path: Path) -> None:
    """On a successful finalize, the tool appends ONE
    `cowork.reviewer_branch` audit row carrying the branch literal."""
    from scriptorium.mcp import server as mcp_server

    rd = tmp_path / "review"
    rd.mkdir()
    paths = _make_paths(rd)
    phase_state_init(paths)
    paths.synthesis.write_text("Body.\n", encoding="utf-8")

    mcp_server.finalize_synthesis_reviewers(
        review_dir=str(rd),
        cite_result=_cite("pass"),
        contradiction_result=_contra("pass"),
        cowork_branch="notebooklm",
    )
    rows = load_audit(paths)
    branch_rows = [r for r in rows if r.action == "cowork.reviewer_branch"]
    assert len(branch_rows) == 1
    row = branch_rows[0]
    assert row.phase == "synthesis"
    assert row.details["branch"] == "notebooklm"
    # Status must reflect "this is metadata, not a verdict" — `success`
    # for the preferred branch, `warning` for the degraded one (so
    # the audit-md skim flags degraded runs).
    assert row.status == "success"


def test_t15_mcp_tool_marks_degraded_branch_as_warning(tmp_path: Path) -> None:
    """The `cowork.reviewer_branch` audit row for a degraded branch must
    carry `status='warning'` so a human auditor scanning audit.md sees
    "this run used the degraded path" without reading every row."""
    from scriptorium.mcp import server as mcp_server

    rd = tmp_path / "review"
    rd.mkdir()
    paths = _make_paths(rd)
    phase_state_init(paths)
    paths.synthesis.write_text("Body.\n", encoding="utf-8")

    mcp_server.finalize_synthesis_reviewers(
        review_dir=str(rd),
        cite_result=_cite("pass"),
        contradiction_result=_contra("pass"),
        cowork_branch="inline_degraded",
    )
    rows = load_audit(paths)
    branch_rows = [r for r in rows if r.action == "cowork.reviewer_branch"]
    assert len(branch_rows) == 1
    assert branch_rows[0].status == "warning"
    assert branch_rows[0].details["branch"] == "inline_degraded"
    assert branch_rows[0].details.get("degraded") is True


def test_t15_mcp_tool_writes_four_audit_rows_total(tmp_path: Path) -> None:
    """Per the brief: T15's audit-row contract is the T14 trio + ONE
    extra branch row = 4 rows total per Cowork gate run."""
    from scriptorium.mcp import server as mcp_server

    rd = tmp_path / "review"
    rd.mkdir()
    paths = _make_paths(rd)
    phase_state_init(paths)
    paths.synthesis.write_text("Body.\n", encoding="utf-8")

    mcp_server.finalize_synthesis_reviewers(
        review_dir=str(rd),
        cite_result=_cite("pass"),
        contradiction_result=_contra("pass"),
        cowork_branch="notebooklm",
    )
    rows = load_audit(paths)
    actions = sorted(r.action for r in rows)
    assert actions == sorted([
        "reviewer.cite",
        "reviewer.contradiction",
        "synthesis.gate",
        "cowork.reviewer_branch",
    ])
    assert len(rows) == 4


def test_t15_mcp_tool_branch_row_appended_after_finalize_trio(
    tmp_path: Path,
) -> None:
    """Audit-row ordering: the standard T14 trio comes first, then the
    branch row. Pin this so a reader of audit.md sees the gate
    aggregation BEFORE the branch metadata (cause → metadata)."""
    from scriptorium.mcp import server as mcp_server

    rd = tmp_path / "review"
    rd.mkdir()
    paths = _make_paths(rd)
    phase_state_init(paths)
    paths.synthesis.write_text("Body.\n", encoding="utf-8")

    mcp_server.finalize_synthesis_reviewers(
        review_dir=str(rd),
        cite_result=_cite("pass"),
        contradiction_result=_contra("pass"),
        cowork_branch="notebooklm",
    )
    rows = load_audit(paths)
    # Last row is the cowork.reviewer_branch row.
    assert rows[-1].action == "cowork.reviewer_branch"
    # Trio precedes it, in the documented order.
    earlier_actions = [r.action for r in rows[:-1]]
    assert earlier_actions == [
        "reviewer.cite",
        "reviewer.contradiction",
        "synthesis.gate",
    ]


def test_t15_mcp_tool_returns_merged_result(tmp_path: Path) -> None:
    """The tool's return dict must include the finalize result keys
    AND the chosen branch — the orchestrator's caller reads both."""
    from scriptorium.mcp import server as mcp_server

    rd = tmp_path / "review"
    rd.mkdir()
    paths = _make_paths(rd)
    phase_state_init(paths)
    paths.synthesis.write_text("Body.\n", encoding="utf-8")

    result = mcp_server.finalize_synthesis_reviewers(
        review_dir=str(rd),
        cite_result=_cite("pass"),
        contradiction_result=_contra("pass"),
        cowork_branch="notebooklm",
    )
    # Finalize keys preserved.
    assert "synthesis_status" in result
    assert "phase_state" in result
    assert "cite_verdict" in result
    assert "contradiction_verdict" in result
    # T15 additions.
    assert result["cowork_branch"] == "notebooklm"


def test_t15_mcp_tool_registered_on_fastmcp() -> None:
    """The new tool must be registered alongside the existing 6 §6.5
    tools so a Cowork orchestrator can discover it via list_tools()."""
    import asyncio
    from scriptorium.mcp import server as mcp_server

    tools = asyncio.run(mcp_server.mcp.list_tools())
    tool_names = {t.name for t in tools}
    assert "finalize_synthesis_reviewers" in tool_names
