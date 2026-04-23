"""Task 12: docx render failure must not block overview.md write."""
import json
from pathlib import Path
from unittest.mock import patch

from scriptorium.overview.generator import regenerate_overview
from scriptorium.paths import ReviewPaths


def _prepare(tmp_path: Path) -> ReviewPaths:
    paths = ReviewPaths(root=tmp_path)
    paths.data_dir.mkdir(parents=True)
    paths.audit_dir.mkdir(parents=True)
    paths.synthesis.write_text(
        "# S\n\n## C [smith2024:p.1]\n\nBody.\n", encoding="utf-8",
    )
    paths.contradictions.write_text("# X\n\nn/a.\n", encoding="utf-8")
    paths.evidence.write_text(
        '{"paper_id":"smith2024","locator":"p.1","claim":"X","quote":"Y",'
        '"direction":"positive","concept":"effect"}\n',
        encoding="utf-8",
    )
    paths.corpus.write_text("", encoding="utf-8")
    return paths


def test_docx_render_failure_isolated_from_md(tmp_path: Path):
    paths = _prepare(tmp_path)
    with patch(
        "scriptorium.overview.generator.render_overview_docx",
        side_effect=RuntimeError("boom"),
    ):
        regenerate_overview(
            paths=paths,
            model="m",
            seed=1,
            research_question="Q",
            review_id="r",
        )
    assert paths.overview.exists()
    events = [
        json.loads(line)
        for line in paths.audit_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    failures = [e for e in events if e.get("action") == "overview_docx_failed"]
    assert len(failures) == 1
    assert "boom" in failures[0]["details"]["error"]
