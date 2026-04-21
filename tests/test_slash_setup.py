from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / ".claude-plugin" / "commands" / "scriptorium-setup.md"


def test_file_exists_and_references_flags():
    text = PATH.read_text(encoding="utf-8")
    for flag in ("--notebooklm", "--skip-notebooklm", "--vault"):
        assert flag in text
    assert "uv pip install scriptorium-cli" in text
    assert "pip install scriptorium-cli" in text
    assert "nlm doctor" in text
    assert "nlm login" in text


def test_file_warns_dedicated_google_account():
    text = PATH.read_text(encoding="utf-8")
    assert "dedicated Google account" in text
    assert "browser automation" in text


def test_file_references_setting_up_scriptorium_skill():
    text = PATH.read_text(encoding="utf-8")
    assert "setting-up-scriptorium" in text
