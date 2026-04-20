from pathlib import Path
from scriptorium.paths import resolve_review_dir
from scriptorium.fulltext.user_pdf import register_user_pdf, find_registered_pdf

FIXTURES = Path(__file__).parent / "fixtures"


def test_register_copies_pdf_into_review_dir(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    src = FIXTURES / "pdfs" / "sample.pdf"
    rec = register_user_pdf(paths, src, paper_id="W1")
    assert rec.cached_path.exists()
    assert rec.cached_path.parent == paths.pdfs
    assert rec.cached_path.name.startswith("W1")
    assert rec.sha256 and len(rec.sha256) == 64


def test_register_is_idempotent(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    src = FIXTURES / "pdfs" / "sample.pdf"
    r1 = register_user_pdf(paths, src, paper_id="W1")
    r2 = register_user_pdf(paths, src, paper_id="W1")
    assert r1.cached_path == r2.cached_path
    assert list(paths.pdfs.iterdir()) == [r1.cached_path]


def test_find_registered_pdf_returns_path(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    src = FIXTURES / "pdfs" / "sample.pdf"
    register_user_pdf(paths, src, paper_id="W1")
    found = find_registered_pdf(paths, "W1")
    assert found and found.exists()
