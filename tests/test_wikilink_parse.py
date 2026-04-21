"""§6.3 legacy `[id:loc]` + v0.3 `[[id#p-N]]` must resolve to the same row."""
import pytest

from scriptorium.citations import Citation, parse_citations


def test_legacy_form():
    cites = parse_citations("Caffeine helps WM [nehlig2010:page:4].")
    assert cites == [Citation(paper_id="nehlig2010", locator="page:4")]


def test_v03_wikilink_form():
    cites = parse_citations("Caffeine helps WM [[nehlig2010#p-4]].")
    assert cites == [Citation(paper_id="nehlig2010", locator="page:4")]


def test_mixed_file():
    text = "A [nehlig2010:page:4] and B [[smith2018#p-7]]."
    cites = parse_citations(text)
    assert Citation("nehlig2010", "page:4") in cites
    assert Citation("smith2018", "page:7") in cites


def test_wikilink_section_locator_is_preserved():
    cites = parse_citations("See [[paper#methods]].")
    assert cites == [Citation(paper_id="paper", locator="methods")]


def test_legacy_non_page_locator_preserved():
    cites = parse_citations("[paper:sec:Methods]")
    assert cites == [Citation(paper_id="paper", locator="sec:Methods")]


def test_ignores_non_citation_brackets():
    assert parse_citations("not a [normal link](url) here") == []
    assert parse_citations("not a [[wiki style only]] link") == []
