"""The evidence gate must accept both citation forms."""
from scriptorium.paths import ReviewPaths
from scriptorium.reasoning.verify_citations import verify_synthesis
from scriptorium.storage.evidence import EvidenceEntry, append_evidence


def test_mixed_forms_both_supported(tmp_path):
    paths = ReviewPaths(root=tmp_path)
    append_evidence(paths, EvidenceEntry(
        paper_id="nehlig2010",
        locator="page:4",
        claim="caffeine helps",
        quote="helps",
        direction="positive",
        concept="wm",
    ))
    text = (
        "Caffeine helps working memory [nehlig2010:page:4]. "
        "Corroborated elsewhere [[nehlig2010#p-4]]."
    )
    report = verify_synthesis(text, paths)
    assert report.ok, report
