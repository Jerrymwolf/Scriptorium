from pathlib import Path
from scriptorium.fulltext.pdf_text import extract_pages, find_quote_locator

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_pages_returns_one_string_per_page():
    pages = extract_pages(FIXTURES / "pdfs" / "multi.pdf")
    assert len(pages) == 3
    assert "hello world" in pages[0].lower()
    assert "caffeine" in pages[1].lower()
    assert "contradiction" in pages[2].lower()


def test_find_quote_locator_returns_page_label():
    pages = extract_pages(FIXTURES / "pdfs" / "multi.pdf")
    loc = find_quote_locator(pages, "caffeine and working memory")
    assert loc == "page:2"


def test_find_quote_locator_returns_none_when_missing():
    pages = extract_pages(FIXTURES / "pdfs" / "multi.pdf")
    assert find_quote_locator(pages, "nonexistent phrase here") is None
