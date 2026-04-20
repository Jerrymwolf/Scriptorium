from pathlib import Path

SKILL = Path(".claude-plugin/skills/lit-publishing/SKILL.md")


def test_frontmatter():
    text = SKILL.read_text(encoding="utf-8")
    assert "name: lit-publishing" in text


def test_four_artifact_types_documented():
    text = SKILL.read_text(encoding="utf-8")
    for art in ("audio", "slides", "infographic", "video"):
        assert art in text.lower()


def test_studio_create_invocation_present():
    text = SKILL.read_text(encoding="utf-8")
    assert "mcp__notebooklm-mcp__studio_create" in text
    assert "mcp__notebooklm-mcp__studio_status" in text
    assert "mcp__notebooklm-mcp__download_artifact" in text


def test_quota_note_present():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "quota" in text


def test_audit_on_generation():
    text = SKILL.read_text(encoding="utf-8")
    assert "audit append" in text
    assert "publishing" in text.lower()
