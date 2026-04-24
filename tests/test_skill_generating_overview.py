from pathlib import Path

PATH = (
    Path(__file__).resolve().parent.parent
    / "skills" / "generating-overview" / "SKILL.md"
)


def test_file_exists_and_covers_key_points():
    text = PATH.read_text(encoding="utf-8")
    for token in (
        "nine sections", "TL;DR", "Scope & exclusions",
        "Most-cited works in this corpus", "Current findings",
        "Contradictions in brief", "Recent work in this corpus",
        "Methods represented in this corpus", "Gaps in this corpus",
        "Reading list", "<!-- synthesis -->", "<!-- provenance:",
        "corpus-bounded", "regenerate-overview",
    ):
        assert token in text, f"missing: {token}"
