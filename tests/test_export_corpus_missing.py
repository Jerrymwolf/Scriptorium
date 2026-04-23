"""Test: render_overview_docx returns OverviewDocxResult with corpus status + misses."""
from pathlib import Path

from docx import Document

from scriptorium.export import render_overview_docx


def test_missing_corpus_renders_plain_with_misses(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text("See [smith2024:p.1] and [jones2025:p.3].\n", encoding="utf-8")
    corpus = tmp_path / "data" / "corpus.jsonl"  # does not exist
    docx = tmp_path / "overview.docx"

    result = render_overview_docx(md, docx, corpus)

    assert result.corpus_unavailable is True
    assert set(result.citation_misses) == {"smith2024", "jones2025"}
    doc = Document(str(docx))
    text = doc.paragraphs[0].text
    assert "[smith2024:p.1]" in text
    assert "[jones2025:p.3]" in text


def test_corpus_present_returns_misses_list(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text("Known [a2024:p.1]. Unknown [b2099:p.2].\n", encoding="utf-8")
    corpus = tmp_path / "data" / "corpus.jsonl"
    corpus.parent.mkdir(parents=True, exist_ok=True)
    corpus.write_text(
        '{"paper_id":"a2024","authors":["A."],"year":2024,"doi":"10/a"}\n',
        encoding="utf-8",
    )
    docx = tmp_path / "overview.docx"

    result = render_overview_docx(md, docx, corpus)

    assert result.corpus_unavailable is False
    assert result.citation_misses == ["b2099"]
