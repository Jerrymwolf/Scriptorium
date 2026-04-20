from pathlib import Path

SKILL = Path(".claude-plugin/skills/configuring-scriptorium/SKILL.md")


def test_skill_exists():
    assert SKILL.exists()


def test_frontmatter():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: configuring-scriptorium" in text
    assert "description:" in text


def test_skill_uses_scriptorium_config_set_in_cc():
    text = SKILL.read_text(encoding="utf-8")
    assert "scriptorium config set" in text
    assert "scriptorium config get" in text


def test_skill_rejects_python_c_invocation():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "python -c" not in text
    assert "from scriptorium.config import save_config" not in text


def test_skill_walks_required_settings():
    text = SKILL.read_text(encoding="utf-8").lower()
    for key in ("unpaywall", "openalex", "semantic_scholar", "default_backend", "languages"):
        assert key in text, f"missing setting discussion: {key}"


def test_skill_handles_cowork_branch():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "cowork" in text
    assert "note" in text or "memory" in text


def test_skill_notes_unpaywall_email_required():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "unpaywall" in text
    assert "required" in text or "mandatory" in text
