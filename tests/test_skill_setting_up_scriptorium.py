from pathlib import Path

PATH = (
    Path(__file__).resolve().parent.parent
    / "skills" / "setting-up-scriptorium" / "SKILL.md"
)


def test_setup_skill_does_not_claim_to_install_plugin():
    body = PATH.read_text(encoding="utf-8")
    assert "install_plugin.sh" not in body
    assert ".claude-plugin" not in body
    assert "unpaywall_email" in body


def test_setup_skill_covers_config_keys():
    body = PATH.read_text(encoding="utf-8")
    assert "unpaywall_email" in body
    assert "obsidian_vault" in body
    assert "notebooklm_enabled" in body


def test_setup_skill_references_prerequisites():
    body = PATH.read_text(encoding="utf-8")
    assert "pipx install scriptorium-cli" in body
    assert "/plugin marketplace add" in body


def test_setup_skill_has_preflight_check():
    body = PATH.read_text(encoding="utf-8")
    assert "scriptorium --version" in body
