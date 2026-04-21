"""§8.5 + §8.6: regenerate-overview CLI, archive, failed-draft handling."""
import io
import json
from pathlib import Path

from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES


def _seed_review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    (root / "synthesis.md").write_text(
        "Caffeine helps WM [[nehlig2010#p-4]].", encoding="utf-8"
    )
    (root / "contradictions.md").write_text("", encoding="utf-8")
    (root / "evidence.jsonl").write_text(
        json.dumps({"paper_id": "nehlig2010", "locator": "page:4",
                    "claim": "caffeine helps", "quote": "helps",
                    "direction": "positive", "concept": "wm"}) + "\n",
        encoding="utf-8",
    )
    return root


def test_first_generation_writes_overview(tmp_path, monkeypatch):
    root = _seed_review(tmp_path)
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["regenerate-overview", str(root), "--json"], stdout=out, stderr=err,
    )
    assert rc == 0, err.getvalue()
    overview = root / "overview.md"
    assert overview.exists()
    payload = json.loads(out.getvalue())
    assert payload["path"].endswith("overview.md")
    assert "corpus_hash" in payload


def test_regeneration_archives_previous(tmp_path):
    root = _seed_review(tmp_path)
    main(["regenerate-overview", str(root)], stdout=io.StringIO(), stderr=io.StringIO())
    main(["regenerate-overview", str(root)], stdout=io.StringIO(), stderr=io.StringIO())
    archive = root / "overview-archive"
    assert archive.is_dir()
    assert list(archive.glob("*.md"))


def test_failed_draft_written_on_lint_failure(tmp_path, monkeypatch):
    root = _seed_review(tmp_path)
    # Force a lint failure by making synthesis.md have no citation.
    (root / "synthesis.md").write_text("x", encoding="utf-8")
    err = io.StringIO()
    rc = main(["regenerate-overview", str(root)], stdout=io.StringIO(), stderr=err)
    assert rc == EXIT_CODES["E_OVERVIEW_FAILED"]
    failed = list(root.glob("overview.failed.*.md"))
    assert failed
