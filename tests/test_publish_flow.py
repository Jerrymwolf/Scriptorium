"""§9.4: lock, nlm doctor, notebook create, upload order, artifact trigger."""
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES
from scriptorium.nlm import NotebookCreated, NlmResult


def _make_review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    for name in ("overview.md", "synthesis.md", "contradictions.md"):
        (root / name).write_text("x", encoding="utf-8")
    (root / "data").mkdir(parents=True)
    (root / "data" / "evidence.jsonl").write_text("x", encoding="utf-8")
    pdfs = root / "sources" / "pdfs"
    pdfs.mkdir(parents=True)
    (pdfs / "alpha.pdf").write_bytes(b"a")
    (pdfs / "beta.pdf").write_bytes(b"b")
    return root


@patch("scriptorium.publish.nlm")
def test_upload_order_and_artifact(mock_nlm, tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    monkeypatch.delenv("SCRIPTORIUM_FORCE_COWORK", raising=False)
    monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
    mock_nlm.doctor.return_value = NlmResult(stdout="ok", stderr="", returncode=0)
    mock_nlm.create_notebook.return_value = NotebookCreated(
        notebook_id="abc123",
        notebook_url="https://notebooklm.google.com/notebook/abc123",
        stdout="id: abc123\nurl: https://notebooklm.google.com/notebook/abc123",
    )
    mock_nlm.upload_source.return_value = NlmResult(stdout="ok", stderr="", returncode=0)
    mock_nlm.create_audio.return_value = NlmResult(stdout="id: artifact_1", stderr="", returncode=0)

    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["publish", "--review-dir", str(root), "--generate", "audio", "--json"],
        stdout=out, stderr=err,
    )
    assert rc == 0, err.getvalue()
    calls = mock_nlm.upload_source.call_args_list
    uploaded = [Path(c.args[1]).name for c in calls]
    assert uploaded == [
        "overview.md", "synthesis.md", "contradictions.md",
        "evidence.jsonl", "alpha.pdf", "beta.pdf",
    ]
    mock_nlm.create_audio.assert_called_once_with("abc123")
    payload = json.loads(out.getvalue())
    assert payload["notebook_id"] == "abc123"
    assert payload["uploaded_sources"][:4] == [
        "overview.md", "synthesis.md", "contradictions.md", "evidence.jsonl"
    ]


@patch("scriptorium.publish.nlm")
def test_nlm_doctor_failure_returns_unavailable(mock_nlm, tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    from scriptorium.nlm import NlmUnavailableError
    mock_nlm.doctor.side_effect = NlmUnavailableError("not authed")
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_NLM_UNAVAILABLE"]
    assert "nlm login" in err.getvalue()


@patch("scriptorium.publish.nlm")
def test_lock_held_returns_e_locked(mock_nlm, tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    (root / ".scriptorium").mkdir(parents=True, exist_ok=True)
    (root / ".scriptorium" / "lock").write_text("1\n", encoding="utf-8")
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_LOCKED"]
    mock_nlm.doctor.assert_not_called()


@patch("scriptorium.publish.nlm")
def test_review_incomplete_before_nlm_doctor(mock_nlm, tmp_path, monkeypatch):
    root = tmp_path / "reviews" / "incomplete"
    root.mkdir(parents=True)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_REVIEW_INCOMPLETE"]
    mock_nlm.doctor.assert_not_called()
