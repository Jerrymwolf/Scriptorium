from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scriptorium.paths import resolve_review_dir
from scriptorium.storage.evidence import EvidenceEntry, append_evidence

HOOK = Path("hooks/evidence_gate.sh").resolve()


pytestmark = pytest.mark.skipif(
    shutil.which("scriptorium") is None,
    reason="scriptorium CLI must be on PATH (run `pip install -e .` first)",
)


def _invoke(payload: dict, *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        env={**os.environ, "SCRIPTORIUM_REVIEW_DIR": str(cwd) if cwd else ""},
    )


def test_hook_is_executable():
    assert HOOK.exists(), f"hook missing at {HOOK}"
    first_line = HOOK.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!"), "hook missing shebang"


def test_hook_no_op_on_unrelated_file(review_dir):
    payload = {"tool_input": {"file_path": str(review_dir / "notes.md")}}
    res = _invoke(payload, cwd=review_dir)
    assert res.returncode == 0, res.stderr
    assert res.stderr == "" or "evidence-first gate" not in res.stderr


def test_hook_exit_zero_and_silent_on_clean_synthesis(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    append_evidence(paths, EvidenceEntry(
        paper_id="W1", locator="p.1", claim="caffeine helps WM",
        quote="Moderate caffeine improves working memory",
        direction="positive", concept="caffeine_wm",
    ))
    paths.synthesis.write_text(
        "Moderate caffeine improves working memory [W1:p.1].\n",
        encoding="utf-8",
    )
    payload = {"tool_input": {"file_path": str(paths.synthesis)}}
    res = _invoke(payload, cwd=review_dir)
    assert res.returncode == 0
    assert "evidence-first gate" not in res.stderr


def test_hook_exit_zero_but_stderr_diagnostic_on_failing_synthesis(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    append_evidence(paths, EvidenceEntry(
        paper_id="W1", locator="p.1", claim="caffeine helps WM",
        quote="Moderate caffeine improves working memory",
        direction="positive", concept="caffeine_wm",
    ))
    paths.synthesis.write_text(
        "Moderate caffeine improves working memory [W1:p.1].\n"
        "Megadoses cure Alzheimer's.\n",
        encoding="utf-8",
    )
    payload = {"tool_input": {"file_path": str(paths.synthesis)}}
    res = _invoke(payload, cwd=review_dir)
    assert res.returncode == 0
    assert "evidence-first gate" in res.stderr
    assert "lit-synthesizing" in res.stderr


def test_hook_tolerates_missing_file_path_key():
    payload = {"tool_input": {}}
    res = _invoke(payload)
    assert res.returncode == 0


def test_hook_tolerates_malformed_payload():
    res = subprocess.run(
        ["bash", str(HOOK)],
        input="not json at all",
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0


def test_hooks_json_registers_post_tool_use_on_write_and_edit():
    manifest = Path("hooks/hooks.json")
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert "hooks" in data
    assert "PostToolUse" in data["hooks"]
    entries = data["hooks"]["PostToolUse"]
    assert isinstance(entries, list) and entries
    entry = entries[0]
    assert "Write" in entry["matcher"]
    assert "Edit" in entry["matcher"]
    command = entry["hooks"][0]["command"]
    assert "evidence_gate.sh" in command
    assert "evidence_first_gate.py" not in command
