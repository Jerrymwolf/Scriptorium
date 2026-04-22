from pathlib import Path

SKILL = Path("skills/lit-screening/SKILL.md")


def test_skill_has_frontmatter():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: lit-screening" in text


def test_names_criteria_vocab():
    text = SKILL.read_text(encoding="utf-8")
    for kw in ("year_min", "year_max", "languages", "must_include", "must_exclude"):
        assert kw in text, f"missing criterion: {kw}"


def test_both_runtimes_covered():
    text = SKILL.read_text(encoding="utf-8")
    assert "scriptorium screen" in text
    assert "corpus" in text.lower()


def test_audit_step_is_required():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "audit" in text
