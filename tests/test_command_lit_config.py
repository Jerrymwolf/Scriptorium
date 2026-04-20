from pathlib import Path

CMD = Path(".claude-plugin/commands/lit-config.md")


def test_command_exists():
    assert CMD.exists()


def test_command_frontmatter():
    text = CMD.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "description:" in text


def test_command_delegates_to_skill():
    text = CMD.read_text(encoding="utf-8")
    assert "configuring-scriptorium" in text


def test_command_never_shell_execs_python():
    text = CMD.read_text(encoding="utf-8").lower()
    assert "python -c" not in text
    assert "save_config(config(" not in text.replace(" ", "")


def test_command_mentions_config_set_subcommand():
    text = CMD.read_text(encoding="utf-8")
    assert "scriptorium config set" in text or "config set" in text
