from pathlib import Path
from scriptorium.paths import ReviewPaths


def test_paths_resolve_to_new_layout(tmp_path: Path):
    p = ReviewPaths(root=tmp_path)

    # Prose deliverables stay at root.
    assert p.overview == tmp_path / "overview.md"
    assert p.overview_docx == tmp_path / "overview.docx"
    assert p.synthesis == tmp_path / "synthesis.md"
    assert p.contradictions == tmp_path / "contradictions.md"
    assert p.scope == tmp_path / "scope.json"
    assert p.references_bib == tmp_path / "references.bib"

    # Sources bucket.
    assert p.sources_dir == tmp_path / "sources"
    assert p.pdfs == tmp_path / "sources" / "pdfs"
    assert p.papers == tmp_path / "sources" / "papers"

    # Data bucket.
    assert p.data_dir == tmp_path / "data"
    assert p.evidence == tmp_path / "data" / "evidence.jsonl"
    assert p.corpus == tmp_path / "data" / "corpus.jsonl"
    assert p.extracts == tmp_path / "data" / "extracts"

    # Audit bucket.
    assert p.audit_dir == tmp_path / "audit"
    assert p.audit_md == tmp_path / "audit" / "audit.md"
    assert p.audit_jsonl == tmp_path / "audit" / "audit.jsonl"
    assert p.overview_archive == tmp_path / "audit" / "overview-archive"

    # Internal state.
    assert p.scriptorium_dir == tmp_path / ".scriptorium"
    assert p.lock == tmp_path / ".scriptorium" / "lock"
