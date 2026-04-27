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
    result = mcp_server.phase_override(
        review_dir=str(review_dir),
        phase="synthesis",
        reason="Emergency skip",
        actor="cowork",
    )
    assert result["phases"]["synthesis"]["status"] == "overridden"
    assert result["phases"]["synthesis"]["override"]["actor"] == "cowork"
    assert result["phases"]["synthesis"]["override"]["reason"] == "Emergency skip"


# ---------------------------------------------------------------------------
# extract_paper stub
# ---------------------------------------------------------------------------


def test_mcp_extract_paper_returns_not_implemented(review_dir):
    result = mcp_server.extract_paper(
        review_dir=str(review_dir),
        paper_id="W1",
    )
    assert "error" in result
    assert result["code"] == "E_NOT_IMPLEMENTED"
    assert "T12" in result["error"]


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
