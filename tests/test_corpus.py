from scriptorium.paths import resolve_review_dir
from scriptorium.sources.base import Paper
from scriptorium.storage.corpus import add_papers, load_corpus, set_status

def _p(pid, doi=None, title="t", source="openalex"):
    return Paper(paper_id=pid, source=source, title=title, authors=[], year=2020, doi=doi)

def test_add_papers_dedupes_by_doi(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    a = _p("W1", doi="10.1/abc", title="X")
    b = _p("S1", doi="10.1/abc", title="X (alt)", source="semantic_scholar")
    added = add_papers(paths, [a, b])
    assert added == 1
    rows = load_corpus(paths)
    assert len(rows) == 1
    assert rows[0]["doi"] == "10.1/abc"
    assert rows[0]["status"] == "candidate"

def test_add_papers_dedupes_by_paper_id_when_no_doi(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    a = _p("W1", doi=None, title="No DOI paper")
    add_papers(paths, [a])
    added = add_papers(paths, [a])
    assert added == 0
    assert len(load_corpus(paths)) == 1

def test_add_papers_falls_back_to_normalized_title(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    a = _p("W1", doi=None, title="Caffeine and Working Memory")
    b = _p("S99", doi=None, title="caffeine and working memory", source="semantic_scholar")
    add_papers(paths, [a, b])
    assert len(load_corpus(paths)) == 1

def test_set_status_updates_row(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    add_papers(paths, [_p("W1", doi="10.1/abc")])
    set_status(paths, "W1", "kept", reason="meets criteria")
    row = load_corpus(paths)[0]
    assert row["status"] == "kept"
    assert row["reason"] == "meets criteria"
