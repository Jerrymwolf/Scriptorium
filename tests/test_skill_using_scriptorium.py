"""Verbatim-content test for using-scriptorium."""
from pathlib import Path

SKILL = Path(".claude-plugin/skills/using-scriptorium/SKILL.md")


def test_skill_exists():
    assert SKILL.exists()


def test_frontmatter_names_the_skill():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: using-scriptorium" in text
    assert "description:" in text


def test_capability_table_is_verbatim():
    text = SKILL.read_text(encoding="utf-8")
    assert "| Skills (SKILL.md + description match) | ✓ | ✓ (only portable surface) |" in text
    assert "| Slash commands (`/lit-review`) | ✓ | ✗ — natural-language fires skill |" in text
    assert "| State home | disk | NotebookLM → Drive → Notion → session-only |" in text


def test_state_adapter_mapping_is_verbatim():
    text = SKILL.read_text(encoding="utf-8")
    for line in (
        "review root → `cwd` → one notebook → one folder → one page",
        "`corpus.jsonl` → file → note titled `corpus` → `corpus.jsonl` file → child page `Corpus`",
        "`evidence.jsonl` → file → note titled `evidence` → `evidence.jsonl` file → child page `Evidence`",
    ):
        assert line in text, f"missing: {line}"


def test_runtime_probe_decision_tree_present():
    text = SKILL.read_text(encoding="utf-8")
    for phrase in (
        "scriptorium --version",
        "mcp__claude_ai_Consensus__search",
        "mcp__claude_ai_Scholar_Gateway__semanticSearch",
        "mcp__claude_ai_PubMed__search_articles",
        "mcp__notebooklm-mcp__notebook_create",
    ):
        assert phrase in text, f"missing probe: {phrase}"


def test_three_disciplines_named():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "evidence-first" in text
    assert "prisma" in text
    assert "contradiction" in text


def test_when_to_fire_table_lists_downstream_skills():
    text = SKILL.read_text(encoding="utf-8")
    for skill in (
        "lit-searching", "lit-screening", "lit-extracting",
        "lit-synthesizing", "lit-contradiction-check",
        "lit-audit-trail", "lit-publishing",
    ):
        assert skill in text, f"missing downstream skill: {skill}"
