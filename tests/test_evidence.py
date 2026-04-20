from scriptorium.paths import resolve_review_dir
from scriptorium.storage.evidence import EvidenceEntry, append_evidence, load_evidence, find_by_paper


def test_append_then_load_roundtrip(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    entry = EvidenceEntry(
        paper_id="W123",
        locator="page:4",
        claim="Caffeine improves working-memory accuracy at moderate doses.",
        quote="Working-memory accuracy was significantly higher in the caffeine group (p=.02).",
        direction="positive",
        concept="caffeine_wm_accuracy",
    )
    append_evidence(paths, entry)
    rows = load_evidence(paths)
    assert len(rows) == 1
    assert rows[0].paper_id == "W123"
    assert rows[0].direction == "positive"


def test_append_is_append_only(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    for i in range(3):
        append_evidence(paths, EvidenceEntry(
            paper_id=f"W{i}", locator="abstract",
            claim=f"claim {i}", quote=f"quote {i}",
            direction="neutral", concept="c",
        ))
    rows = load_evidence(paths)
    assert [r.paper_id for r in rows] == ["W0", "W1", "W2"]


def test_find_by_paper(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    append_evidence(paths, EvidenceEntry(paper_id="W1", locator="page:1", claim="a", quote="q", direction="positive", concept="x"))
    append_evidence(paths, EvidenceEntry(paper_id="W2", locator="page:2", claim="b", quote="q", direction="negative", concept="x"))
    append_evidence(paths, EvidenceEntry(paper_id="W1", locator="page:3", claim="c", quote="q", direction="neutral", concept="y"))
    found = find_by_paper(paths, "W1")
    assert len(found) == 2
    assert {f.locator for f in found} == {"page:1", "page:3"}


def test_load_empty_returns_empty_list(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    assert load_evidence(paths) == []
