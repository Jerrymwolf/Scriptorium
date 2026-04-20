from pathlib import Path

SKILL = Path(".claude-plugin/skills/lit-searching/SKILL.md")

FENCING_RULE = (
    'From Consensus results, extract ONLY `{title, authors, year, doi, url}` '
    'into corpus.jsonl. NEVER propagate Consensus\'s numbered citations into '
    '`evidence.jsonl` or `synthesis.md` — our grammar is `[paper_id:locator]`. '
    "Consensus's sign-up line only appears if a user-facing turn ends directly "
    "on Consensus output; corpus-building turns never do."
)


def test_skill_exists_and_has_frontmatter():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: lit-searching" in text


def test_consensus_fencing_rule_is_verbatim():
    text = SKILL.read_text(encoding="utf-8")
    assert FENCING_RULE in text


def test_source_matrix_rows_present():
    text = SKILL.read_text(encoding="utf-8")
    for row in (
        "| OpenAlex | — | `scriptorium search --source openalex` | Default breadth (CC) |",
        "| Consensus | `mcp__claude_ai_Consensus__search` | — | Default in Cowork; claim-first |",
        "| PubMed | `mcp__claude_ai_PubMed__search_articles` + `get_article_metadata` | — | Biomed / OA full text |",
        "| User PDFs | Cowork file upload + `source_add` | `scriptorium register-pdf` | Always highest priority |",
    ):
        assert row in text, f"missing row: {row}"


def test_skill_references_both_runtimes():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "claude code" in text
    assert "cowork" in text
    assert "scriptorium search" in text
    assert "mcp__claude_ai_consensus__search" in text


def test_skill_names_corpus_add_path():
    text = SKILL.read_text(encoding="utf-8")
    assert "scriptorium corpus add" in text
    assert "corpus.jsonl" in text
