from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / ".claude-plugin" / "skills"


def _read(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def test_using_scriptorium_mentions_v03_config_and_publish():
    text = _read("using-scriptorium")
    assert "obsidian_vault" in text
    assert "scriptorium publish" in text
    assert "Cowork" in text


def test_running_lit_review_hands_off_to_overview_and_prompt():
    text = _read("running-lit-review")
    assert "regenerate-overview" in text
    assert "NotebookLM artifact?" in text


def test_configuring_scriptorium_lists_new_keys_and_cowork_parity():
    text = _read("configuring-scriptorium")
    for key in ("obsidian_vault", "notebooklm_enabled", "notebooklm_prompt"):
        assert key in text
    assert "scriptorium-config" in text


def test_lit_extracting_uses_v03_full_text_sources():
    text = _read("lit-extracting")
    for src in ("user_pdf", "unpaywall", "arxiv", "pmc", "abstract_only"):
        assert src in text


def test_lit_synthesizing_uses_wikilinks():
    text = _read("lit-synthesizing")
    assert "[[paper_id#p-N]]" in text
    assert "schema_version" in text


def test_lit_contradiction_check_uses_wikilinks():
    text = _read("lit-contradiction-check")
    assert "[[paper_id#p-N]]" in text


def test_lit_audit_trail_covers_publishing_section():
    text = _read("lit-audit-trail")
    assert "## Publishing" in text
    assert "audit.jsonl" in text
