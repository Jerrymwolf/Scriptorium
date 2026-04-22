from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "commands" / "scriptorium-setup.md"


def test_setup_command_is_post_install_only():
    body = PATH.read_text(encoding="utf-8")
    assert ".claude-plugin" not in body
    assert "install_plugin.sh" not in body
    assert "unpaywall_email" in body
    assert "obsidian_vault" in body


def test_setup_command_references_pipx_install():
    body = PATH.read_text(encoding="utf-8")
    assert "pipx install scriptorium-cli" in body


def test_setup_command_has_preflight_check():
    body = PATH.read_text(encoding="utf-8")
    assert "scriptorium --version" in body


def test_setup_command_references_plugin_marketplace():
    body = PATH.read_text(encoding="utf-8")
    assert "/plugin marketplace add" in body
