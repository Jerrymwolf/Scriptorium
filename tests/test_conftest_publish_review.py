"""Meta-tests for the shared ``publish_review_factory`` / ``publish_review_dir``
fixtures introduced in T17.

These pin the contract every consuming test relies on:

* the canonical directory shape (overview/synthesis/contradictions, data/
  evidence.jsonl, sources/pdfs/),
* the optional PDF list,
* the optional ``seed_audit_md`` for idempotency-style tests,
* the ``slug`` override (load-bearing for derive_notebook_name assertions).
"""
from __future__ import annotations

from pathlib import Path


def test_publish_review_dir_default_shape(publish_review_dir: Path) -> None:
    """Default fixture produces the publish-flow canonical shape."""
    root = publish_review_dir
    assert root.is_dir()
    assert root.name == "caffeine-wm"
    for name in ("overview.md", "synthesis.md", "contradictions.md"):
        assert (root / name).is_file()
        assert (root / name).read_text(encoding="utf-8")  # non-empty
    assert (root / "data" / "evidence.jsonl").is_file()
    assert (root / "sources" / "pdfs").is_dir()
    # No PDFs by default.
    assert list((root / "sources" / "pdfs").iterdir()) == []
    # No seeded audit.md by default.
    assert not (root / "audit" / "audit.md").exists()


def test_publish_review_factory_pdfs(publish_review_factory) -> None:
    """``pdfs`` arg drops one byte per name into ``sources/pdfs/``."""
    root = publish_review_factory(pdfs=("alpha.pdf", "beta.pdf"))
    pdfs_dir = root / "sources" / "pdfs"
    names = sorted(p.name for p in pdfs_dir.iterdir())
    assert names == ["alpha.pdf", "beta.pdf"]


def test_publish_review_factory_seed_audit_md(publish_review_factory) -> None:
    """``seed_audit_md`` writes the given text to ``audit/audit.md``."""
    seed = "# PRISMA Audit Trail\n\n## Publishing\nprior\n"
    root = publish_review_factory(seed_audit_md=seed)
    assert (root / "audit" / "audit.md").read_text(encoding="utf-8") == seed


def test_publish_review_factory_custom_slug(publish_review_factory) -> None:
    """``slug`` controls the leaf directory name (used by notebook-name tests)."""
    root = publish_review_factory(slug="other-topic")
    assert root.name == "other-topic"
    assert root.parent.name == "reviews"
