from scriptorium.paths import resolve_review_dir
from scriptorium.storage.audit import AuditEntry, append_audit, load_audit


def test_append_writes_both_markdown_and_jsonl(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    entry = AuditEntry(
        phase="search",
        action="openalex.query",
        details={"query": "caffeine working memory", "n_results": 42},
    )
    append_audit(paths, entry)
    md = paths.audit_md.read_text()
    assert "search" in md and "openalex.query" in md and "42" in md
    rows = load_audit(paths)
    assert len(rows) == 1
    assert rows[0].phase == "search"
    assert rows[0].details["n_results"] == 42


def test_audit_entries_are_chronological(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    for phase in ("search", "screening", "extraction"):
        append_audit(paths, AuditEntry(phase=phase, action=f"{phase}.done", details={}))
    rows = load_audit(paths)
    assert [r.phase for r in rows] == ["search", "screening", "extraction"]


def test_audit_markdown_is_human_readable(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    append_audit(paths, AuditEntry(
        phase="screening",
        action="rule.apply",
        details={"kept": 28, "dropped": 14, "reason_top": "year<2015"},
    ))
    md = paths.audit_md.read_text()
    assert "## " in md or "### " in md
    assert "kept" in md and "28" in md
