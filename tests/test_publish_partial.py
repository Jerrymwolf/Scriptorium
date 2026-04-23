"""§9.5: timeout and partial-failure must write a partial audit entry."""
import io, json
from pathlib import Path
from unittest.mock import patch
from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES
from scriptorium.nlm import NlmCommandError, NlmTimeoutError, NlmResult, NotebookCreated


def _review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    for name in ("overview.md", "synthesis.md", "contradictions.md"):
        (root / name).write_text("x" * 10, encoding="utf-8")
    (root / "data").mkdir(parents=True)
    (root / "data" / "evidence.jsonl").write_text("x" * 10, encoding="utf-8")
    (root / "sources" / "pdfs").mkdir(parents=True)
    return root


@patch("scriptorium.publish.nlm")
def test_upload_failure_exits_e_upload_with_partial_audit(mock_nlm, tmp_path):
    root = _review(tmp_path)
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.return_value = NotebookCreated(notebook_id="n1", notebook_url="https://x/n1", stdout="id: n1\nurl: https://x/n1")
    def _side(nid, path):
        if Path(path).name == "synthesis.md":
            raise NlmCommandError("upload error", returncode=2, stderr="boom")
        return NlmResult("", "", 0)
    mock_nlm.upload_source.side_effect = _side
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_NLM_UPLOAD"]
    rows = [json.loads(l) for l in (root / "audit" / "audit.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    pr = [r for r in rows if r["phase"] == "publishing"]
    assert pr[-1]["status"] == "partial"
    assert pr[-1]["details"]["failing_command"]
    assert pr[-1]["details"]["captured_exit_code"] == 2


@patch("scriptorium.publish.nlm")
def test_timeout_exits_e_timeout(mock_nlm, tmp_path):
    root = _review(tmp_path)
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.side_effect = NlmTimeoutError("timeout")
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_TIMEOUT"]
