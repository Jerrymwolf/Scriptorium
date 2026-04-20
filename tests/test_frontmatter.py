"""§5.1 and §5.2 frontmatter schemas + round-trip read/write."""
from datetime import datetime, timezone

import pytest

from scriptorium.frontmatter import (
    FrontmatterError,
    PaperStubFrontmatter,
    ReviewArtifactFrontmatter,
    read_frontmatter,
    strip_frontmatter,
    write_frontmatter,
)


SAMPLE_PAPER = PaperStubFrontmatter(
    schema_version="scriptorium.paper.v1",
    scriptorium_version="0.3.0",
    paper_id="nehlig2010",
    title="Is caffeine a cognitive enhancer?",
    authors=["Nehlig, A."],
    year=2010,
    tags=["caffeine", "wm"],
    reviewed_in=["caffeine-wm"],
    full_text_source="user_pdf",
    created_at="2026-04-20T14:32:08Z",
    updated_at="2026-04-20T14:32:08Z",
    doi="10.3233/JAD-2010-1430",
)


def test_paper_round_trip():
    md = write_frontmatter(SAMPLE_PAPER.to_dict(), body="# body\n")
    loaded = read_frontmatter(md)
    assert loaded["paper_id"] == "nehlig2010"
    assert loaded["full_text_source"] == "user_pdf"
    assert "doi" in loaded
    assert strip_frontmatter(md).strip() == "# body"


def test_paper_rejects_forbidden_field():
    d = SAMPLE_PAPER.to_dict()
    d["not_allowed"] = 1
    with pytest.raises(FrontmatterError):
        PaperStubFrontmatter.validate_dict(d)


def test_paper_rejects_bad_full_text_source():
    d = SAMPLE_PAPER.to_dict()
    d["full_text_source"] = "other"
    with pytest.raises(FrontmatterError):
        PaperStubFrontmatter.validate_dict(d)


def test_review_artifact_requires_review_type():
    with pytest.raises(FrontmatterError):
        ReviewArtifactFrontmatter.validate_dict({
            "schema_version": "scriptorium.review_file.v1",
            "scriptorium_version": "0.3.0",
            "review_id": "caffeine-wm",
            # missing review_type
            "created_at": "2026-04-20T14:32:08Z",
            "updated_at": "2026-04-20T14:32:08Z",
            "research_question": "does caffeine improve wm?",
            "cite_discipline": "locator",
        })


def test_write_returns_delimited_block():
    md = write_frontmatter({"key": "value"}, body="# body\n")
    assert md.startswith("---\n")
    parts = md.split("---\n", 2)
    assert parts[0] == ""
    assert "key:" in parts[1] and "value" in parts[1]
    assert parts[2].startswith("# body")
