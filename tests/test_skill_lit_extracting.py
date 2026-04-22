from pathlib import Path

SKILL = Path("skills/lit-extracting/SKILL.md")


def test_frontmatter():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: lit-extracting" in text


def test_cascade_order_named():
    text = SKILL.read_text(encoding="utf-8")
    assert "user_pdf → unpaywall → arxiv → pmc → abstract_only" in text


def test_cc_and_cowork_paths_present():
    text = SKILL.read_text(encoding="utf-8")
    assert "scriptorium fetch-fulltext" in text
    assert "scriptorium extract-pdf" in text
    assert "mcp__claude_ai_PubMed__get_full_text_article" in text


def test_locator_grammar_named():
    text = SKILL.read_text(encoding="utf-8")
    assert "page:N" in text
    assert "[paper_id:locator]" in text
