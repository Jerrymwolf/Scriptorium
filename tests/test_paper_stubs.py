"""§6.2: paper stubs with owned regions and user-edit preservation."""
from pathlib import Path

from scriptorium.obsidian.stubs import (
    PaperStubInput,
    write_or_update_paper_stub,
)


def _sample() -> PaperStubInput:
    return PaperStubInput(
        paper_id="nehlig2010",
        title="Is caffeine a cognitive enhancer?",
        authors=["Nehlig, A."],
        year=2010,
        tags=["caffeine"],
        doi="10.3233/JAD-2010-1430",
        full_text_source="user_pdf",
        pdf_path="pdfs/nehlig2010.pdf",
        source_url=None,
        abstract="Caffeine is the most widely consumed stimulant.",
        cited_pages={"page:4": "Caffeine improved accuracy on n-back."},
        review_id="caffeine-wm",
        synthesis_claim=("Caffeine improves WM in healthy adults.",
                         "[[paper#p-4]]"),
        now_iso="2026-04-20T14:32:08Z",
    )


def test_first_write_creates_expected_body(tmp_path):
    stub = tmp_path / "papers" / "nehlig2010.md"
    status = write_or_update_paper_stub(stub, _sample())
    assert status == "created"
    text = stub.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "paper_id: \"nehlig2010\"" in text
    assert "# Nehlig (2010) — Is caffeine a cognitive enhancer?" in text
    assert "**DOI:** 10.3233/JAD-2010-1430" in text
    assert "[[pdfs/nehlig2010.pdf]]" in text
    assert "## Cited pages\n\n### p-4\n\n> Caffeine improved accuracy on n-back." in text
    assert "## Claims in review: caffeine-wm" in text


def test_user_edits_outside_owned_regions_survive(tmp_path):
    stub = tmp_path / "papers" / "nehlig2010.md"
    write_or_update_paper_stub(stub, _sample())
    edited = stub.read_text(encoding="utf-8") + "\n## My notes\n\nA private note.\n"
    stub.write_text(edited, encoding="utf-8")
    status = write_or_update_paper_stub(stub, _sample())
    assert status == "updated"
    text = stub.read_text(encoding="utf-8")
    assert "## My notes\n\nA private note." in text


def test_empty_cited_pages_does_not_write_stub(tmp_path):
    data = _sample()
    data = data.__class__(
        **{**data.__dict__, "cited_pages": {}, "synthesis_claim": None}
    )
    stub = tmp_path / "papers" / "nehlig2010.md"
    status = write_or_update_paper_stub(stub, data)
    assert status == "W_EMPTY_EVIDENCE"
    assert not stub.exists()
