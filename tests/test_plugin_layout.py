from pathlib import Path


def test_plugin_layout_is_rooted():
    """Claude Code scans commands/, skills/, hooks/ at plugin root — not inside .claude-plugin/."""
    assert Path("commands").is_dir()
    assert Path("skills").is_dir()
    assert Path("hooks").is_dir()
    assert Path("CLAUDE.md").is_file()
    assert Path(".claude-plugin/plugin.json").is_file()
    assert Path(".claude-plugin/marketplace.json").is_file()
    assert not Path(".claude-plugin/commands").exists()
    assert not Path(".claude-plugin/skills").exists()
    assert not Path(".claude-plugin/hooks").exists()
    assert not Path(".claude-plugin/CLAUDE.md").exists()
