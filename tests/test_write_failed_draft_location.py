"""Test: write_failed_draft lands in audit/overview-archive, not root."""
from pathlib import Path
from scriptorium.overview.generator import write_failed_draft
from scriptorium.paths import ReviewPaths


def test_failed_draft_goes_to_overview_archive(tmp_path: Path):
    paths = ReviewPaths(root=tmp_path)
    result = write_failed_draft(paths, body="# broken\n")
    assert result.parent == paths.overview_archive
    assert result.exists()
    assert result.name.endswith(".md")
    # Should not pollute review root.
    root_failed = list(tmp_path.glob("overview.failed.*.md"))
    assert root_failed == []
