from scriptorium.sources.base import Paper, normalize_doi

def test_paper_minimal_fields():
    p = Paper(
        paper_id="W123", source="openalex", title="Caffeine and WM",
        authors=["Smith, J."], year=2023, doi="10.1/abc",
    )
    assert p.paper_id == "W123"
    assert p.source == "openalex"
    assert p.abstract is None
    assert p.venue is None

def test_normalize_doi_lowercases_and_strips_url():
    assert normalize_doi("https://doi.org/10.1234/ABC.def") == "10.1234/abc.def"
    assert normalize_doi("10.1234/ABC.def") == "10.1234/abc.def"
    assert normalize_doi("doi:10.1234/abc") == "10.1234/abc"
    assert normalize_doi(None) is None
    assert normalize_doi("") is None
