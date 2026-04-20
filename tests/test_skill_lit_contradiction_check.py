from pathlib import Path

SKILL = Path(".claude-plugin/skills/lit-contradiction-check/SKILL.md")


def test_frontmatter():
    text = SKILL.read_text(encoding="utf-8")
    assert "name: lit-contradiction-check" in text


def test_names_direction_pairs():
    text = SKILL.read_text(encoding="utf-8")
    assert "positive" in text and "negative" in text


def test_cc_cli_path_present():
    text = SKILL.read_text(encoding="utf-8")
    assert "scriptorium contradictions" in text


def test_named_camps_pattern():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "camp" in text or "name the disagreement" in text
