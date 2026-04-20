from scriptorium.paths import resolve_review_dir
from scriptorium.storage.evidence import EvidenceEntry, append_evidence
from scriptorium.reasoning.contradictions import find_contradictions


def _e(pid, direction, concept="caffeine_wm"):
    return EvidenceEntry(paper_id=pid, locator="page:1", claim=f"claim by {pid}",
                         quote=f"quote {pid}", direction=direction, concept=concept)


def test_finds_positive_vs_negative_pair_on_same_concept(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    for e in [_e("W1", "positive"), _e("W2", "negative")]:
        append_evidence(paths, e)
    pairs = find_contradictions(paths)
    assert len(pairs) == 1
    p = pairs[0]
    assert p.concept == "caffeine_wm"
    assert {p.a.paper_id, p.b.paper_id} == {"W1", "W2"}


def test_no_pair_when_all_same_direction(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    for e in [_e("W1", "positive"), _e("W2", "positive")]:
        append_evidence(paths, e)
    assert find_contradictions(paths) == []


def test_neutral_does_not_contradict_neutral(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    for e in [_e("W1", "neutral"), _e("W2", "neutral")]:
        append_evidence(paths, e)
    assert find_contradictions(paths) == []


def test_pairs_only_within_same_concept(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    append_evidence(paths, _e("W1", "positive", concept="a"))
    append_evidence(paths, _e("W2", "negative", concept="b"))
    assert find_contradictions(paths) == []
