"""§9.3: publish CLI flag surface and source/notebook-name resolution."""
import io
import json
from pathlib import Path

import pytest

from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES


def _make_review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    (root / "overview.md").write_text("overview", encoding="utf-8")
    (root / "synthesis.md").write_text("synthesis", encoding="utf-8")
    (root / "contradictions.md").write_text("contra", encoding="utf-8")
    (root / "evidence.jsonl").write_text("", encoding="utf-8")
    (root / "pdfs").mkdir()
    return root


def test_invalid_sources_exits_e_sources(tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    monkeypatch.setenv("SCRIPTORIUM_FORCE_COWORK", "0")
    out = io.StringIO()
    err = io.StringIO()
    rc = main(
        ["publish", "--review-dir", str(root), "--sources", "overview,bogus"],
        stdout=out, stderr=err,
    )
    assert rc == EXIT_CODES["E_SOURCES"]
    assert "overview, synthesis, contradictions, evidence, pdfs, stubs" in err.getvalue()


def test_empty_sources_exits_e_sources(tmp_path, monkeypatch):
    root = _make_review(tmp_path)
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["publish", "--review-dir", str(root), "--sources", ""],
        stdout=out, stderr=err,
    )
    assert rc == EXIT_CODES["E_SOURCES"]


def test_notebook_name_default_from_review_dir(tmp_path, monkeypatch):
    from scriptorium.publish import derive_notebook_name
    assert derive_notebook_name("caffeine-wm") == "Caffeine Wm"
    assert derive_notebook_name("my_review_2025") == "My Review 2025"
    with pytest.raises(ValueError):
        derive_notebook_name("")
    with pytest.raises(ValueError):
        derive_notebook_name("---")
