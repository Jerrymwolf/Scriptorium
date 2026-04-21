"""§12.3: verifier enforces overview lint when the edited file is overview.md."""
import io
from pathlib import Path

from scriptorium.cli import main
from scriptorium.errors import EXIT_CODES


def test_verify_overview_mode_rejects_bad_overview(tmp_path):
    overview = tmp_path / "overview.md"
    overview.write_text("# missing sections\n", encoding="utf-8")
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["verify", "--overview", str(overview)], stdout=out, stderr=err,
    )
    assert rc == EXIT_CODES["E_OVERVIEW_FAILED"]


def test_verify_overview_mode_accepts_valid(tmp_path, monkeypatch):
    from scriptorium.overview.generator import regenerate_overview
    from scriptorium.paths import ReviewPaths
    rp = ReviewPaths(root=tmp_path)
    (tmp_path / "evidence.jsonl").write_text("", encoding="utf-8")
    regenerate_overview(rp, model="opus", seed=1, research_question="q", review_id="r")
    out = io.StringIO(); err = io.StringIO()
    rc = main(
        ["verify", "--overview", str(rp.overview)], stdout=out, stderr=err,
    )
    assert rc == 0
