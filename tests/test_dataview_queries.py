"""§6.4 scriptorium-queries.md: write-once, five canonical queries."""
from pathlib import Path

from scriptorium.obsidian.queries import write_query_file


EXPECTED_SNIPPETS = [
    'TABLE claim, direction FROM "reviews" WHERE contains(file.name, "evidence")',
    'LIST FROM "reviews" WHERE contains(file.content, "kennedy2017")',
    'TABLE length(file.outlinks) AS "references"',
    'TABLE concept, direction FROM "reviews"',
    'LIST FROM "reviews" WHERE contains(file.name, "contradictions")',
]


def test_write_once_contains_all_queries(tmp_path):
    path = tmp_path / "scriptorium-queries.md"
    status = write_query_file(path)
    assert status == "written"
    body = path.read_text(encoding="utf-8")
    for snippet in EXPECTED_SNIPPETS:
        assert snippet in body, f"missing: {snippet}"
    assert body.count("```dataview") == 5


def test_existing_file_is_not_overwritten(tmp_path):
    path = tmp_path / "scriptorium-queries.md"
    path.write_text("user content\n", encoding="utf-8")
    status = write_query_file(path)
    assert status == "W_QUERIES_EXIST"
    assert path.read_text(encoding="utf-8") == "user content\n"
