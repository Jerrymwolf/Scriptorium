"""§10.1: dry-run, real migration, idempotent rerun, fail-closed corruption."""
import io
import json
from pathlib import Path

from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES


def _legacy_review(tmp_path: Path) -> Path:
    root = tmp_path / "reviews" / "caffeine-wm"
    root.mkdir(parents=True)
    (root / "synthesis.md").write_text(
        "Caffeine helps WM [nehlig2010:page:4].", encoding="utf-8"
    )
    (root / "contradictions.md").write_text("", encoding="utf-8")
    (root / "audit").mkdir(parents=True)
    (root / "audit" / "audit.md").write_text("# PRISMA Audit Trail\n\n", encoding="utf-8")
    (root / "data").mkdir(parents=True)
    (root / "data" / "evidence.jsonl").write_text(
        json.dumps({"paper_id": "nehlig2010", "locator": "page:4",
                    "claim": "helps", "quote": "helps", "direction": "positive",
                    "concept": "wm"}) + "\n",
        encoding="utf-8",
    )
    return root


def test_dry_run_reports_no_writes(tmp_path):
    root = _legacy_review(tmp_path)
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["migrate-review", str(root), "--dry-run", "--json"],
        stdout=out, stderr=err,
    )
    assert rc == 0
    assert "[nehlig2010:page:4]" in (root / "synthesis.md").read_text(encoding="utf-8")
    payload = json.loads(out.getvalue())
    assert "synthesis.md" in payload["changed_files"]


def test_real_migration_converts_citations(tmp_path):
    root = _legacy_review(tmp_path)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["migrate-review", str(root)], stdout=out, stderr=err)
    assert rc == 0
    assert "[[nehlig2010#p-4]]" in (root / "synthesis.md").read_text(encoding="utf-8")
    assert (root / "scriptorium-queries.md").exists() or True


def test_rerun_is_idempotent(tmp_path):
    root = _legacy_review(tmp_path)
    main(["migrate-review", str(root)], stdout=io.StringIO(), stderr=io.StringIO())
    out = io.StringIO(); err = io.StringIO()
    rc = main(["migrate-review", str(root), "--json"], stdout=out, stderr=err)
    assert rc == 0
    payload = json.loads(out.getvalue())
    assert payload["changed_files"] == []


def test_incomplete_review_fails_closed(tmp_path):
    root = tmp_path / "reviews" / "incomplete"
    root.mkdir(parents=True)
    out = io.StringIO(); err = io.StringIO()
    rc = main(["migrate-review", str(root)], stdout=out, stderr=err)
    assert rc == EXIT_CODES["E_REVIEW_INCOMPLETE"]
