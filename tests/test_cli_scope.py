"""Tests for the `scriptorium scope` CLI subcommands."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from scriptorium.cli import main
from scriptorium.scope import SCHEMA_VERSION


MINIMAL_VALID = {
    "schema_version": SCHEMA_VERSION,
    "created_at": "2026-04-23T10:30:00Z",
    "research_question": "Does X affect Y?",
    "purpose": "dissertation",
    "fields": ["psychology"],
    "population": None,
    "methodology": "any",
    "year_range": [2018, 2026],
    "corpus_target": 50,
    "publication_types": ["peer-reviewed"],
    "depth": "representative",
    "conceptual_frame": None,
    "anchor_papers": [],
    "output_intent": None,
    "known_gaps_focus": False,
    "paradigm": None,
    "soft_warnings": [],
}


def _run(argv, cwd: Path):
    out, err = io.StringIO(), io.StringIO()
    rc = main(argv, cwd=cwd, stdout=out, stderr=err, stdin=io.StringIO())
    return rc, out.getvalue(), err.getvalue()


def test_scope_validate_ok(tmp_path: Path):
    (tmp_path / "scope.json").write_text(json.dumps(MINIMAL_VALID))
    rc, out, err = _run(["scope", "validate"], cwd=tmp_path)
    assert rc == 0, err
    assert "valid" in out.lower()


def test_scope_validate_missing_file(tmp_path: Path):
    rc, out, err = _run(["scope", "validate"], cwd=tmp_path)
    assert rc == 2
    assert "scope.json" in err


def test_scope_validate_bad_schema(tmp_path: Path):
    bad = dict(MINIMAL_VALID, purpose="book")
    (tmp_path / "scope.json").write_text(json.dumps(bad))
    rc, out, err = _run(["scope", "validate"], cwd=tmp_path)
    assert rc == 3
    assert "purpose" in err


def test_scope_validate_explicit_path(tmp_path: Path):
    custom = tmp_path / "sub" / "scope.json"
    custom.parent.mkdir()
    custom.write_text(json.dumps(MINIMAL_VALID))
    rc, out, err = _run(["scope", "validate", "--path", str(custom)], cwd=tmp_path)
    assert rc == 0, err


def test_verify_scope_ok(tmp_path: Path):
    (tmp_path / "scope.json").write_text(json.dumps(MINIMAL_VALID))
    rc, out, err = _run(["verify", "--scope", str(tmp_path / "scope.json")], cwd=tmp_path)
    assert rc == 0, err


def test_verify_scope_missing_tier1(tmp_path: Path):
    data = dict(MINIMAL_VALID, research_question="   ")
    (tmp_path / "scope.json").write_text(json.dumps(data))
    rc, out, err = _run(["verify", "--scope", str(tmp_path / "scope.json")], cwd=tmp_path)
    assert rc == 3
    assert "research_question" in err
