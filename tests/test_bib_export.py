from scriptorium.paths import resolve_review_dir
from scriptorium.sources.base import Paper
from scriptorium.storage.corpus import add_papers, set_status
from scriptorium.reasoning.bib_export import export_bibtex, export_ris


def test_bibtex_emits_one_entry_per_kept_paper(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    add_papers(paths, [
        Paper(paper_id="W1", source="openalex", title="Caffeine WM",
              authors=["Smith, J.", "Lee, M."], year=2019, doi="10.1/abc",
              venue="J Exp Psy"),
    ])
    set_status(paths, "W1", "kept")
    bib = export_bibtex(paths)
    assert "@article{W1" in bib
    assert "title = {Caffeine WM}" in bib
    assert "author = {Smith, J. and Lee, M.}" in bib
    assert "year = {2019}" in bib
    assert "doi = {10.1/abc}" in bib


def test_ris_emits_well_formed_record(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    add_papers(paths, [
        Paper(paper_id="W1", source="openalex", title="Caffeine WM",
              authors=["Smith, J."], year=2019, doi="10.1/abc", venue="J Exp Psy"),
    ])
    set_status(paths, "W1", "kept")
    ris = export_ris(paths)
    assert ris.startswith("TY  - JOUR")
    assert "TI  - Caffeine WM" in ris
    assert "AU  - Smith, J." in ris
    assert "PY  - 2019" in ris
    assert "DO  - 10.1/abc" in ris
    assert ris.rstrip().endswith("ER  -")


def test_export_skips_dropped_papers(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    add_papers(paths, [
        Paper(paper_id="W1", source="openalex", title="Keep",
              authors=["A"], year=2020, doi="10.1/k"),
        Paper(paper_id="W2", source="openalex", title="Drop",
              authors=["B"], year=2020, doi="10.1/d"),
    ])
    set_status(paths, "W1", "kept")
    set_status(paths, "W2", "dropped", reason="off-topic")
    bib = export_bibtex(paths)
    assert "Keep" in bib and "Drop" not in bib
