"""End-to-end: scope creation → verify CLI → hook silence → hook fire."""
from __future__ import annotations

import io
import json
import os
import subprocess
from pathlib import Path

import pytest

from scriptorium.cli import main
from scriptorium.scope import Scope, save_scope


HOOK = Path(__file__).resolve().parent.parent / "hooks" / "evidence_gate.sh"


def _cli(argv, cwd):
    out, err = io.StringIO(), io.StringIO()
    rc = main(argv, cwd=cwd, stdout=out, stderr=err, stdin=io.StringIO())
    return rc, out.getvalue(), err.getvalue()


def _hook(payload):
    result = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stderr


def test_e2e_happy_path(tmp_path: Path):
    # 1. Create scope
    scope = Scope(
        research_question="Does SDT predict intrinsic motivation at work?",
        purpose="dissertation",
        fields=["organizational psychology"],
        methodology="any",
        year_range=[2018, 2026],
        corpus_target=50,
        publication_types=["peer-reviewed"],
        depth="representative",
        known_gaps_focus=False,
    )
    save_scope(tmp_path / "scope.json", scope)

    # 2. Verify CLI
    rc, out, err = _cli(
        ["verify", "--scope", str(tmp_path / "scope.json")], cwd=tmp_path
    )
    assert rc == 0, err

    # 3. Hook is silent when scope.json is present
    corpus = tmp_path / "corpus.jsonl"
    rc, err = _hook({"tool_input": {"file_path": str(corpus)}})
    assert rc == 0
    assert "scope.json missing" not in err

    # 4. Delete scope; hook now warns
    (tmp_path / "scope.json").unlink()
    rc, err = _hook({"tool_input": {"file_path": str(corpus)}})
    assert rc == 0
    assert "scope.json missing" in err
    assert "lit-scoping" in err
