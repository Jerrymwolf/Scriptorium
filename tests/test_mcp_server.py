# tests/test_mcp_server.py
"""Tests for the Scriptorium MCP server tools (T04).

These tests call the tool functions directly — no network/stdio transport
needed. Each tool is a regular Python callable registered on the FastMCP
instance; we import and call them synchronously.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scriptorium.paths import resolve_review_dir


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _paths(review_dir: Path):
    return resolve_review_dir(explicit=review_dir, create=True)


# ---------------------------------------------------------------------------
# import tools module
# ---------------------------------------------------------------------------


from scriptorium.mcp import server as mcp_server


# ---------------------------------------------------------------------------
# verify tool
# ---------------------------------------------------------------------------


def test_mcp_verify_publish_blocked_when_pending(review_dir):
    result = mcp_server.verify(gate="publish", review_dir=str(review_dir))
    assert result["ok"] is False
    assert "synthesis_status" in result


def test_mcp_verify_publish_passes_when_complete(review_dir):
    from scriptorium import phase_state
    paths = _paths(review_dir)
    sig = "sha256:" + "a" * 64
    phase_state.set_phase(paths, "synthesis", "complete", verifier_signature=sig)
    result = mcp_server.verify(gate="publish", review_dir=str(review_dir))
    assert result["ok"] is True
    assert result["synthesis_status"] == "complete"


def test_mcp_verify_synthesis_clean(review_dir):
    from scriptorium.storage.evidence import EvidenceEntry, append_evidence
    paths = _paths(review_dir)
    append_evidence(paths, EvidenceEntry(
        paper_id="W1", locator="page:4",
        claim="caffeine WM", quote="...",
        direction="positive", concept="c",
    ))
    synth = review_dir / "synthesis.md"
    synth.write_text("Caffeine helps [W1:page:4].\n", encoding="utf-8")
    result = mcp_server.verify(
        gate="synthesis",
        review_dir=str(review_dir),
        synthesis=str(synth),
    )
    assert result["ok"] is True


def test_mcp_verify_unknown_gate(review_dir):
    result = mcp_server.verify(gate="bogus", review_dir=str(review_dir))
    assert result["ok"] is False
    assert "unknown gate" in result["error"]


# ---------------------------------------------------------------------------
# phase_show tool
# ---------------------------------------------------------------------------


def test_mcp_phase_show_returns_all_phases(review_dir):
    result = mcp_server.phase_show(review_dir=str(review_dir))
    assert "phases" in result
    assert "synthesis" in result["phases"]


# ---------------------------------------------------------------------------
# phase_set tool
# ---------------------------------------------------------------------------


def test_mcp_phase_set_running(review_dir):
    result = mcp_server.phase_set(
        review_dir=str(review_dir),
        phase="search",
        status="running",
    )
    assert result["phases"]["search"]["status"] == "running"


def test_mcp_phase_set_complete_with_signature(review_dir):
    sig = "sha256:" + "b" * 64
    result = mcp_server.phase_set(
        review_dir=str(review_dir),
        phase="synthesis",
        status="complete",
        verifier_signature=sig,
    )
    assert result["phases"]["synthesis"]["status"] == "complete"


def test_mcp_phase_set_complete_no_signature_returns_error(review_dir):
    result = mcp_server.phase_set(
        review_dir=str(review_dir),
        phase="synthesis",
        status="complete",
    )
    # Should return error dict, not raise
    assert "error" in result
    assert result["code"] == 20  # E_PHASE_STATE_INVALID


# ---------------------------------------------------------------------------
# phase_override tool
# ---------------------------------------------------------------------------


def test_mcp_phase_override(review_dir):
    # T16: confirm=True is the explicit-marker requirement.
    result = mcp_server.phase_override(
        review_dir=str(review_dir),
        phase="synthesis",
        reason="Emergency skip",
        actor="cowork",
        confirm=True,
    )
    assert result["phases"]["synthesis"]["status"] == "overridden"
    assert result["phases"]["synthesis"]["override"]["actor"] == "cowork"
    assert result["phases"]["synthesis"]["override"]["reason"] == "Emergency skip"


# ---------------------------------------------------------------------------
# extract_paper (T13 — Cowork:mcp dispatch helper)
# ---------------------------------------------------------------------------


def _seed_corpus(review_dir, *, paper_id="W1", status="kept", review_id=None):
    """Append a corpus row for extract_paper tests.

    `corpus.jsonl` is the single source of truth for paper metadata; the
    MCP `extract_paper` tool refuses to dispatch unless the paper exists
    AND is at status='kept'.
    """
    import json
    from scriptorium.paths import resolve_review_dir
    paths = resolve_review_dir(explicit=review_dir, create=True)
    paths.corpus.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "paper_id": paper_id,
        "title": f"Title for {paper_id}",
        "doi": f"10.1234/{paper_id}",
        "abstract": "Some abstract text.",
        "status": status,
        "source": "test",
    }
    if review_id is not None:
        row["review_id"] = review_id
    with paths.corpus.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return paths


def test_mcp_extract_paper_returns_dispatch_payload_for_kept_paper(review_dir):
    _seed_corpus(review_dir, paper_id="W1", status="kept")
    result = mcp_server.extract_paper(
        review_dir=str(review_dir),
        paper_id="W1",
    )
    assert "error" not in result, result
    assert result["paper_id"] == "W1"
    assert result["runtime"] == "cowork"
    assert result["backend"] == "mcp"
    # The prompt must be single-id (the T12 contamination-resistance
    # property reused for Cowork:mcp).
    assert "W1" in result["prompt"]
    assert "lit-extracting" in result["prompt"]
    # Corpus row passed through so the orchestrator can locate the PDF
    # / abstract / DOI without a second roundtrip.
    assert result["corpus_row"]["paper_id"] == "W1"


def test_mcp_extract_paper_review_id_arg_wins_over_corpus_row(review_dir):
    """Explicit `review_id` argument overrides the corpus row's field."""
    _seed_corpus(review_dir, paper_id="W1", status="kept", review_id="row-rev")
    result = mcp_server.extract_paper(
        review_dir=str(review_dir),
        paper_id="W1",
        review_id="explicit-rev",
    )
    assert result["review_id"] == "explicit-rev"


def test_mcp_extract_paper_falls_back_to_corpus_review_id(review_dir):
    _seed_corpus(review_dir, paper_id="W1", status="kept", review_id="row-rev")
    result = mcp_server.extract_paper(
        review_dir=str(review_dir),
        paper_id="W1",
    )
    assert result["review_id"] == "row-rev"


def test_mcp_extract_paper_falls_back_to_review_dir_basename(review_dir):
    _seed_corpus(review_dir, paper_id="W1", status="kept")  # no review_id
    result = mcp_server.extract_paper(
        review_dir=str(review_dir),
        paper_id="W1",
    )
    # `review_dir` fixture is `tmp_path / "review"`, basename = "review"
    assert result["review_id"] == review_dir.name


def test_mcp_extract_paper_unknown_paper_returns_error(review_dir):
    _seed_corpus(review_dir, paper_id="W1", status="kept")
    result = mcp_server.extract_paper(
        review_dir=str(review_dir),
        paper_id="W999",
    )
    assert "error" in result
    assert result["code"] == 29  # E_EXTRACT_PAPER_NOT_KEPT
    assert "W999" in result["error"]


def test_mcp_extract_paper_candidate_status_returns_error(review_dir):
    """Papers at status='candidate' have not passed screening; the MCP
    tool must refuse to build a dispatch payload (mirrors the SKILL's
    HARD-GATE)."""
    _seed_corpus(review_dir, paper_id="W2", status="candidate")
    result = mcp_server.extract_paper(
        review_dir=str(review_dir),
        paper_id="W2",
    )
    assert "error" in result
    assert result["code"] == 29  # E_EXTRACT_PAPER_NOT_KEPT
    assert "candidate" in result["error"]


def test_mcp_extract_paper_excluded_status_returns_error(review_dir):
    _seed_corpus(review_dir, paper_id="W3", status="excluded")
    result = mcp_server.extract_paper(
        review_dir=str(review_dir),
        paper_id="W3",
    )
    assert "error" in result
    assert result["code"] == 29


def test_mcp_extract_paper_appends_audit_row(review_dir):
    """Successful dispatch appends one extraction.dispatch row with
    runtime='cowork' and backend='mcp'."""
    from scriptorium.storage.audit import load_audit
    paths = _seed_corpus(review_dir, paper_id="W1", status="kept", review_id="rev-aud")
    mcp_server.extract_paper(
        review_dir=str(review_dir),
        paper_id="W1",
    )
    rows = load_audit(paths)
    # Filter to the extraction.dispatch action so any unrelated audit
    # rows from fixture setup don't trip this test.
    dispatch_rows = [r for r in rows if r.action == "extraction.dispatch"]
    assert len(dispatch_rows) == 1, (
        f"expected exactly one extraction.dispatch row, got "
        f"{len(dispatch_rows)}"
    )
    row = dispatch_rows[0]
    assert row.phase == "extraction"
    assert row.status == "success"
    assert row.details["paper_id"] == "W1"
    assert row.details["review_id"] == "rev-aud"
    assert row.details["runtime"] == "cowork"
    assert row.details["backend"] == "mcp"


def test_mcp_extract_paper_does_not_audit_on_failed_lookup(review_dir):
    """If the paper is missing/not-kept, no `extraction.dispatch` row
    should be appended — we don't audit a refusal as a successful
    dispatch (it never happened)."""
    from scriptorium.storage.audit import load_audit
    paths = _seed_corpus(review_dir, paper_id="W1", status="candidate")
    mcp_server.extract_paper(
        review_dir=str(review_dir),
        paper_id="W1",
    )
    rows = load_audit(paths)
    dispatch_rows = [r for r in rows if r.action == "extraction.dispatch"]
    assert dispatch_rows == [], (
        "extract_paper must NOT append an extraction.dispatch row when "
        "the paper is missing or not at status='kept'"
    )


def test_mcp_phase_show_does_not_create_sibling_dirs(tmp_path):
    """phase_show against a fresh dir must NOT create data/, audit/, sources/."""
    fresh = tmp_path / "fresh_review"
    fresh.mkdir()
    # Calling phase_show should succeed (phase_state.read auto-inits the state
    # under .scriptorium/) but must NOT create the data/audit/sources siblings
    # that resolve_review_dir(create=True) would have materialised.
    result = mcp_server.phase_show(review_dir=str(fresh))
    assert "phases" in result  # tool succeeded
    assert not (fresh / "data").exists(), "data/ must not be created by phase_show"
    assert not (fresh / "audit").exists(), "audit/ must not be created by phase_show"
    assert not (fresh / "sources").exists(), "sources/ must not be created by phase_show"


# ---------------------------------------------------------------------------
# validate_reviewer_output tool
# ---------------------------------------------------------------------------


def test_mcp_validate_reviewer_output_valid():
    payload = {
        "reviewer": "cite",
        "runtime": "cowork",
        "verdict": "pass",
        "summary": "All citations verified.",
        "findings": [],
        "synthesis_sha256": "sha256:" + "c" * 64,
        "reviewer_prompt_sha256": "sha256:" + "d" * 64,
        "created_at": "2026-01-01T00:00:00Z",
    }
    result = mcp_server.validate_reviewer_output(payload=payload)
    assert result["ok"] is True


def test_mcp_validate_reviewer_output_invalid():
    payload = {
        "reviewer": "cite",
        "runtime": "cowork",
        "verdict": "fail",
        "summary": "issues found",
        "findings": [],  # fail requires findings
        "synthesis_sha256": "sha256:" + "e" * 64,
        "reviewer_prompt_sha256": "sha256:" + "f" * 64,
        "created_at": "2026-01-01T00:00:00Z",
    }
    result = mcp_server.validate_reviewer_output(payload=payload)
    assert result["ok"] is False
    assert result["code"] == 22  # E_REVIEWER_INVALID


# ---------------------------------------------------------------------------
# INJECTION.md path and warning
# ---------------------------------------------------------------------------


def test_mcp_injection_path_is_correct():
    """The INJECTION.md path should resolve relative to the plugin root."""
    expected = (
        Path(__file__).resolve().parents[1]
        / "skills" / "using-scriptorium" / "INJECTION.md"
    )
    assert mcp_server._INJECTION_PATH == expected


def test_mcp_instructions_from_injection_file(tmp_path):
    """When INJECTION.md exists, instructions are loaded from it."""
    import importlib
    import unittest.mock as mock

    injection_content = "# Scriptorium MCP Instructions\nUse these tools wisely.\n"
    fake_path = tmp_path / "INJECTION.md"
    fake_path.write_text(injection_content, encoding="utf-8")

    with mock.patch.object(mcp_server, "_INJECTION_PATH", fake_path):
        instructions = mcp_server._load_instructions()
    assert instructions == injection_content


def test_mcp_instructions_empty_when_injection_missing(tmp_path, capsys):
    """When INJECTION.md is absent, instructions are empty and warning is printed."""
    import unittest.mock as mock

    missing_path = tmp_path / "nonexistent" / "INJECTION.md"
    with mock.patch.object(mcp_server, "_INJECTION_PATH", missing_path):
        instructions = mcp_server._load_instructions()
    assert instructions == ""
    captured = capsys.readouterr()
    assert "INJECTION.md not found" in captured.err


# ---------------------------------------------------------------------------
# six tools are registered
# ---------------------------------------------------------------------------


def test_mcp_six_tools_registered():
    """All 6 §6.5 tools must be registered on the FastMCP instance."""
    import asyncio
    tools = asyncio.run(mcp_server.mcp.list_tools())
    tool_names = {t.name for t in tools}
    expected = {
        "verify",
        "phase_show",
        "phase_set",
        "phase_override",
        "extract_paper",
        "validate_reviewer_output",
    }
    assert expected <= tool_names, f"Missing tools: {expected - tool_names}"
