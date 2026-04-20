from pathlib import Path
from scriptorium.paths import resolve_review_dir
from scriptorium.storage.evidence import EvidenceEntry, append_evidence
from scriptorium.reasoning.verify_citations import (
    parse_citations, split_sentences, verify_synthesis, VerificationReport,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_citations_extracts_paper_locator():
    text = "Caffeine helps [W1:page:4]. Sleep matters too [W2:abstract]."
    cites = parse_citations(text)
    assert ("W1", "page:4") in cites
    assert ("W2", "abstract") in cites


def test_split_sentences_does_not_break_on_eg_or_ie():
    """Defect-fix #7: 'e.g.' and 'i.e.' must NOT trigger a sentence split."""
    src = "Stimulants (e.g. caffeine, modafinil) help [W1:page:4]. Sleep also helps [W2:page:1]."
    sents = split_sentences(src)
    assert len(sents) == 2
    assert "e.g. caffeine" in sents[0]


def test_split_sentences_handles_et_al_and_other_abbrevs():
    src = "Smith et al. (2020) reported gains [W1:page:4]. Cf. Lee (2018) for the opposite [W2:page:1]."
    sents = split_sentences(src)
    assert len(sents) == 2
    assert "Smith et al." in sents[0]


def test_verify_clean_synthesis_passes(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    append_evidence(paths, EvidenceEntry(paper_id="W1", locator="page:4",
        claim="caffeine improves WM", quote="...", direction="positive", concept="caffeine_wm"))
    append_evidence(paths, EvidenceEntry(paper_id="W2", locator="page:7",
        claim="high doses dim returns", quote="...", direction="negative", concept="caffeine_wm"))
    src = (FIXTURES / "synthesis" / "clean.md").read_text()
    rep = verify_synthesis(src, paths)
    assert rep.ok is True
    assert rep.unsupported_sentences == []
    assert rep.missing_citations == []


def test_verify_eg_sentence_passes(review_dir):
    """Sentence containing 'e.g.' is one sentence and is supported by its single citation."""
    paths = resolve_review_dir(explicit=review_dir)
    append_evidence(paths, EvidenceEntry(paper_id="W1", locator="page:4",
        claim="x", quote="x", direction="positive", concept="c"))
    src = (FIXTURES / "synthesis" / "with_eg.md").read_text()
    rep = verify_synthesis(src, paths)
    assert rep.ok is True


def test_verify_planted_finds_unsupported_and_missing(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    append_evidence(paths, EvidenceEntry(paper_id="W1", locator="page:4",
        claim="x", quote="x", direction="positive", concept="c"))
    src = (FIXTURES / "synthesis" / "planted_unsupported.md").read_text()
    rep = verify_synthesis(src, paths)
    assert rep.ok is False
    assert any("Megadoses" in s for s in rep.unsupported_sentences)
    assert ("W999", "page:1") in rep.missing_citations


def test_strict_mode_strips_unsupported(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    append_evidence(paths, EvidenceEntry(paper_id="W1", locator="page:4",
        claim="x", quote="x", direction="positive", concept="c"))
    src = (FIXTURES / "synthesis" / "planted_unsupported.md").read_text()
    rep = verify_synthesis(src, paths)
    cleaned = rep.apply_strict(src)
    assert "Megadoses" not in cleaned
    assert "W999" not in cleaned
    assert "[W1:page:4]" in cleaned


def test_lenient_mode_flags_inline(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    append_evidence(paths, EvidenceEntry(paper_id="W1", locator="page:4",
        claim="x", quote="x", direction="positive", concept="c"))
    src = (FIXTURES / "synthesis" / "planted_unsupported.md").read_text()
    rep = verify_synthesis(src, paths)
    flagged = rep.apply_lenient(src)
    assert "[UNSUPPORTED]" in flagged
    assert "Megadoses cure Alzheimer's disease. [UNSUPPORTED]" in flagged
