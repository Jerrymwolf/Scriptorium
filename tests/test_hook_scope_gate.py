"""Tests for the evidence_gate.sh scope-precondition check."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from tests.conftest import SCRIPTORIUM_BIN


HOOK = Path(__file__).resolve().parent.parent / "hooks" / "evidence_gate.sh"


def _run_hook(payload: dict, env: dict | None = None) -> tuple[int, str, str]:
    merged = {**os.environ, **(env or {})}
    # Point the hook at the conftest shim (wrapping `python -m scriptorium.cli`)
    # so a stale system `scriptorium` on PATH can't leak stderr noise.
    if SCRIPTORIUM_BIN and "SCRIPTORIUM_BIN" not in merged:
        merged["SCRIPTORIUM_BIN"] = SCRIPTORIUM_BIN
    result = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=merged,
    )
    return result.returncode, result.stdout, result.stderr


def test_hook_warns_when_scope_missing_and_writing_corpus(tmp_path: Path):
    target = tmp_path / "corpus.jsonl"
    rc, out, err = _run_hook({"tool_input": {"file_path": str(target)}})
    assert rc == 0  # hook NEVER blocks
    assert "scope.json" in err
    assert "lit-scoping" in err


def test_hook_silent_when_scope_exists(tmp_path: Path):
    (tmp_path / "scope.json").write_text(json.dumps({
        "schema_version": 1,
        "created_at": "2026-04-23T10:30:00Z",
        "research_question": "Q?",
        "purpose": "narrative",
        "fields": ["psychology"],
        "population": None,
        "methodology": "any",
        "year_range": [None, None],
        "corpus_target": 25,
        "publication_types": ["peer-reviewed"],
        "depth": "representative",
        "conceptual_frame": None,
        "anchor_papers": [],
        "output_intent": None,
        "known_gaps_focus": False,
        "paradigm": None,
        "soft_warnings": [],
    }))
    target = tmp_path / "corpus.jsonl"
    rc, out, err = _run_hook({"tool_input": {"file_path": str(target)}})
    assert rc == 0
    assert "scope.json" not in err


def test_hook_ignores_unrelated_paths(tmp_path: Path):
    target = tmp_path / "README.md"
    rc, out, err = _run_hook({"tool_input": {"file_path": str(target)}})
    assert rc == 0
    assert err == ""


def test_hook_silent_for_scope_json_itself(tmp_path: Path):
    target = tmp_path / "scope.json"
    rc, out, err = _run_hook({"tool_input": {"file_path": str(target)}})
    assert rc == 0
    assert err == ""
