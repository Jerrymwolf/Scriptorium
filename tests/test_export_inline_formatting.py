"""Test: inline bold/italic/code produce separate docx runs."""
from pathlib import Path

from docx import Document

from scriptorium.export import render_overview_docx


def test_inline_formatting(tmp_path: Path):
    md = tmp_path / "overview.md"
    md.write_text(
        "This is **bold** and *italic* and `code` in one line.\n",
        encoding="utf-8",
    )
    docx = tmp_path / "overview.docx"
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("", encoding="utf-8")

    render_overview_docx(md, docx, corpus)

    doc = Document(str(docx))
    runs = list(doc.paragraphs[0].runs)
    texts = [(r.text, r.bold, r.italic, r.font.name) for r in runs]
    assert any(t == "bold" and b for t, b, _, _ in texts)
    assert any(t == "italic" and i for t, _, i, _ in texts)
    assert any(t == "code" and f in ("Consolas", "Courier New") for t, _, _, f in texts)
