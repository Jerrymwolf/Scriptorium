from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / ".claude-plugin" / "commands"


def test_lit_review_threads_overview_and_prompt():
    text = (ROOT / "lit-review.md").read_text(encoding="utf-8")
    assert "scriptorium regenerate-overview" in text
    assert "NotebookLM artifact?" in text
    assert "skip default" in text


def test_lit_config_mentions_new_keys():
    text = (ROOT / "lit-config.md").read_text(encoding="utf-8")
    for key in ("obsidian_vault", "notebooklm_enabled", "notebooklm_prompt"):
        assert key in text


def test_lit_show_audit_understands_publishing_section():
    text = (ROOT / "lit-show-audit.md").read_text(encoding="utf-8")
    assert "## Publishing" in text
