"""Test: render_overview_docx emits H1/H2/H3 headings and paragraphs."""
from pathlib import Path

from docx import Document

from scriptorium.export import render_overview_docx


def test_headings_and_paragraphs(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text(
        "# Title\n\nIntro paragraph.\n\n"
        "## Section A\n\nBody of A.\n\n"
        "### Subsection\n\nDeeper body.\n",
        encoding="utf-8",
    )
    docx = tmp_path / "overview.docx"
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("", encoding="utf-8")

    render_overview_docx(md, docx, corpus)

    doc = Document(str(docx))
    paras = [(p.text, p.style.name) for p in doc.paragraphs]
    assert ("Title", "Heading 1") in paras
    assert ("Section A", "Heading 2") in paras
    assert ("Subsection", "Heading 3") in paras
    bodies = [t for t, _ in paras]
    assert "Intro paragraph." in bodies
    assert "Body of A." in bodies
    assert "Deeper body." in bodies
