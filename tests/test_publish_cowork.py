"""§9.6: publish in Cowork mode emits the block, exits 0, does not call nlm."""
import io
from pathlib import Path
from unittest.mock import patch

from scriptorium.cli import main


def _make_review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    for name in ("overview.md", "synthesis.md", "contradictions.md", "evidence.jsonl"):
        (root / name).write_text("x", encoding="utf-8")
    (root / "pdfs").mkdir()
    return root


def test_cowork_mode_emits_block_and_skips_nlm(tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    monkeypatch.setenv("SCRIPTORIUM_FORCE_COWORK", "1")
    out = io.StringIO(); err = io.StringIO()
    with patch("scriptorium.nlm.doctor") as mock_doctor:
        rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    assert rc == 0
    assert "Publishing to NotebookLM requires local shell access" in out.getvalue()
    mock_doctor.assert_not_called()


def test_cowork_block_lists_relative_files(tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    monkeypatch.setenv("SCRIPTORIUM_FORCE_COWORK", "1")
    out = io.StringIO(); err = io.StringIO()
    rc = main(["publish", "--review-dir", str(root)], stdout=out, stderr=err)
    text = out.getvalue()
    assert "overview.md" in text
    assert "synthesis.md" in text
    assert "contradictions.md" in text
    assert "evidence.jsonl" in text
