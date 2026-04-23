"""Test: regenerate_overview writes both .md and .docx and logs audit event."""
import json
from pathlib import Path

from docx import Document

from scriptorium.overview.generator import regenerate_overview
from scriptorium.paths import ReviewPaths


def _prepare_review(tmp_path: Path) -> ReviewPaths:
    paths = ReviewPaths(root=tmp_path)
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.audit_dir.mkdir(parents=True, exist_ok=True)
    paths.synthesis.write_text(
        "# Synthesis\n\n## Claim 1 [smith2024:p.1]\n\nBody.\n",
        encoding="utf-8",
    )
    paths.contradictions.write_text(
        "# Contradictions\n\nNone noted.\n", encoding="utf-8"
    )
    paths.evidence.write_text(
        '{"paper_id":"smith2024","locator":"p.1","claim":"X","quote":"Y",'
        '"direction":"positive","concept":"effect"}\n',
        encoding="utf-8",
    )
    paths.corpus.write_text(
        '{"paper_id":"smith2024","authors":["Smith, J."],"year":2024,"doi":"10/a"}\n',
        encoding="utf-8",
    )
    return paths


def test_regenerate_overview_writes_md_and_docx(tmp_path: Path):
    paths = _prepare_review(tmp_path)
    regenerate_overview(
        paths=paths,
        model="test-model",
        seed=1,
        research_question="Does X improve Y?",
        review_id="test-review",
    )
    assert paths.overview.exists()
    assert paths.overview_docx.exists()
    Document(str(paths.overview_docx))  # raises on corruption


def test_regenerate_overview_appends_audit_event(tmp_path: Path):
    paths = _prepare_review(tmp_path)
    regenerate_overview(
        paths=paths,
        model="m",
        seed=1,
        research_question="Q",
        review_id="r",
    )
    events = [
        json.loads(line)
        for line in paths.audit_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rendered = [e for e in events if e.get("action") == "overview_rendered"]
    assert len(rendered) == 1
    ev = rendered[0]
    assert ev["status"] == "success"
    d = ev["details"]
    assert set(d["wrote"]) == {"overview.md", "overview.docx"}
    assert "source_sha256" in d
    assert d["citation_misses"] == []
