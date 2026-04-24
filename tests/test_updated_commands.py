from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "commands"


def test_lit_review_threads_overview_and_prompt():
    text = (ROOT / "lit-review.md").read_text(encoding="utf-8")
    assert "scriptorium regenerate-overview" in text
    # Post-cite-check, the command offers the NotebookLM artifact choice.
    # v0.3+ uses AskUserQuestion with audio/deck/mindmap/skip options.
    assert "NotebookLM" in text
    assert "AskUserQuestion" in text
    for option in ("Audio overview", "Slide deck", "Mind map", "Skip"):
        assert option in text, f"missing artifact option: {option}"


def test_lit_config_mentions_new_keys():
    text = (ROOT / "lit-config.md").read_text(encoding="utf-8")
    for key in ("obsidian_vault", "notebooklm_enabled", "notebooklm_prompt"):
        assert key in text


def test_lit_show_audit_understands_publishing_section():
    text = (ROOT / "lit-show-audit.md").read_text(encoding="utf-8")
    assert "## Publishing" in text
