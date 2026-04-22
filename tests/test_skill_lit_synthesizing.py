from pathlib import Path

SKILL = Path("skills/lit-synthesizing/SKILL.md")


def test_frontmatter():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: lit-synthesizing" in text


def test_mandatory_step_5_present():
    text = SKILL.read_text(encoding="utf-8")
    assert (
        "Parse each sentence in `synthesis.md` for `[paper_id:locator]` tokens; "
        "confirm each tuple exists in the evidence store. Strip (strict) or flag "
        "`[UNSUPPORTED]` (lenient) any failure."
    ) in text


def test_modes_documented():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "strict" in text
    assert "lenient" in text


def test_hook_is_belt_and_suspenders():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "hook" in text
    assert "scriptorium verify" in text


def test_no_numbered_citations():
    text = SKILL.read_text(encoding="utf-8")
    assert "[paper_id:locator]" in text
    assert "[1]" in text or "numbered" in text.lower()
