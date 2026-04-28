"""§9.7: audit entry under ## Publishing and audit.jsonl publishing row."""
import io, json
from unittest.mock import patch
from scriptorium.cli import main
from scriptorium.nlm import NotebookCreated, NlmResult


@patch("scriptorium.publish.nlm")
def test_success_writes_audit_markdown_and_jsonl(mock_nlm, publish_review_dir):
    root = publish_review_dir
    mock_nlm.doctor.return_value = NlmResult("", "", 0)
    mock_nlm.create_notebook.return_value = NotebookCreated(notebook_id="abc123", notebook_url="https://x/abc123", stdout="id: abc123\nurl: https://x/abc123")
    mock_nlm.upload_source.return_value = NlmResult("", "", 0)
    mock_nlm.create_audio.return_value = NlmResult("id: artifact_1", "", 0)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root), "--generate", "audio", "--json"], stdout=out, stderr=err)
    assert rc == 0
    md = (root / "audit" / "audit.md").read_text(encoding="utf-8")
    assert "## Publishing" in md
    assert '**Notebook:** "Caffeine Wm" (id: `abc123`)' in md
    assert "**Status:** success" in md
    rows = [json.loads(l) for l in (root / "audit" / "audit.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    pr = [r for r in rows if r["phase"] == "publishing"]
    assert pr and pr[-1]["status"] == "success"
    assert pr[-1]["details"]["notebook_id"] == "abc123"
