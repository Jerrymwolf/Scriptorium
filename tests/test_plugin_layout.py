from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]


def test_plugin_layout_is_rooted():
    """Claude Code scans commands/, skills/, hooks/ at plugin root — not inside .claude-plugin/."""
    assert (REPO_ROOT / "commands").is_dir(), "commands/ must exist at repo root"
    assert (REPO_ROOT / "skills").is_dir(), "skills/ must exist at repo root"
    assert (REPO_ROOT / "hooks").is_dir(), "hooks/ must exist at repo root"
    assert (REPO_ROOT / "CLAUDE.md").is_file(), "CLAUDE.md must exist at repo root"
    assert (REPO_ROOT / ".claude-plugin" / "plugin.json").is_file()
    assert (REPO_ROOT / ".claude-plugin" / "marketplace.json").is_file()
    assert not (REPO_ROOT / ".claude-plugin" / "commands").exists(), \
        "commands/ must not be nested inside .claude-plugin/"
    assert not (REPO_ROOT / ".claude-plugin" / "skills").exists(), \
        "skills/ must not be nested inside .claude-plugin/"
    assert not (REPO_ROOT / ".claude-plugin" / "hooks").exists(), \
        "hooks/ must not be nested inside .claude-plugin/"
    assert not (REPO_ROOT / ".claude-plugin" / "CLAUDE.md").exists(), \
        "CLAUDE.md must not be nested inside .claude-plugin/"
