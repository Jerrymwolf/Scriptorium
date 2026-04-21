"""§9.4 step 6: prior-publish prompt; --yes auto-confirms; N/EOF exits 0."""
import io
from pathlib import Path
from unittest.mock import patch

from scriptorium.cli import main
from scriptorium.nlm import NotebookCreated, NlmResult


def _review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    for name in ("overview.md", "synthesis.md", "contradictions.md", "evidence.jsonl"):
        (root / name).write_text("x", encoding="utf-8")
    (root / "pdfs").mkdir()
    (root / "audit.md").write_text(
        "# PRISMA Audit Trail\n\n## Publishing\n\n"
        "### 2026-04-01T00:00:00Z — NotebookLM\n\n"
        '**Notebook:** "Caffeine Wm" (id: `prev`)\n',
        encoding="utf-8",
    )
    return root


@patch("scriptorium.publish.nlm")
def test_no_yes_no_stdin_exits_zero_without_remote_calls(mock_nlm, tmp_path):
    root = _review(tmp_path)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err, stdin=io.StringIO(""))
    assert rc == 0
    mock_nlm.create_notebook.assert_not_called()


@patch("scriptorium.publish.nlm")
def test_yes_flag_bypasses_prompt(mock_nlm, tmp_path):
    root = _review(tmp_path)
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.return_value = NotebookCreated(notebook_id="new", notebook_url="https://x", stdout="id: new\nurl: https://x")
    mock_nlm.upload_source.return_value = NlmResult("", "", 0)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root), "--yes", "--json"], stdout=out, stderr=err)
    assert rc == 0
    mock_nlm.create_notebook.assert_called_once()


@patch("scriptorium.publish.nlm")
def test_yes_response_proceeds(mock_nlm, tmp_path):
    root = _review(tmp_path)
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.return_value = NotebookCreated(notebook_id="new", notebook_url="https://x", stdout="id: new\nurl: https://x")
    mock_nlm.upload_source.return_value = NlmResult("", "", 0)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root), "--json"], stdout=out, stderr=err, stdin=io.StringIO("y\n"))
    assert rc == 0
    mock_nlm.create_notebook.assert_called_once()
