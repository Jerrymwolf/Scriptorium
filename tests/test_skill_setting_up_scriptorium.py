from pathlib import Path

PATH = (
    Path(__file__).resolve().parent.parent
    / ".claude-plugin" / "skills" / "setting-up-scriptorium" / "SKILL.md"
)


def test_exists_and_covers_flow():
    text = PATH.read_text(encoding="utf-8")
    for token in (
        "uv pip install scriptorium-cli", "pip install scriptorium-cli",
        "scriptorium --version", "scriptorium 0.3.1",
        "uv tool install notebooklm-mcp-cli", "pipx install notebooklm-mcp-cli",
        "nlm login", "nlm doctor",
        "notebooklm_enabled true", "--skip-notebooklm",
        "dedicated Google account", "setup-state.json",
    ):
        assert token in text, f"missing: {token}"
