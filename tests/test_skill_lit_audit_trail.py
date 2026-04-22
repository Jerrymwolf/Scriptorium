from pathlib import Path

SKILL = Path("skills/lit-audit-trail/SKILL.md")


def test_frontmatter():
    text = SKILL.read_text(encoding="utf-8")
    assert "name: lit-audit-trail" in text


def test_phases_listed():
    text = SKILL.read_text(encoding="utf-8").lower()
    for phase in ("search", "screening", "extraction", "synthesis", "contradiction"):
        assert phase in text, f"missing phase: {phase}"


def test_cc_and_cowork_destinations():
    text = SKILL.read_text(encoding="utf-8")
    assert "scriptorium audit append" in text
    assert "scriptorium audit read" in text
    assert "notebooklm" in text.lower() or "state adapter" in text.lower()


def test_prisma_reference_present():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "prisma" in text
