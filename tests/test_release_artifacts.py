from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_readme_names_scriptorium_cli_and_beta():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "pip install scriptorium-cli" in text
    assert "beta" in text.lower()


def test_changelog_has_v030_entry():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "0.3.0" in text


def test_install_script_wraps_scriptorium_init():
    text = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
    assert "scriptorium-cli" in text
    assert "scriptorium init" in text


def test_obsidian_integration_doc_mentions_portability_tradeoff():
    text = (ROOT / "docs" / "obsidian-integration.md").read_text(encoding="utf-8")
    assert "not self-contained" in text
    assert "papers/" in text


def test_publishing_notebooklm_doc_has_manual_upload_template():
    text = (ROOT / "docs" / "publishing-notebooklm.md").read_text(encoding="utf-8")
    assert "## Publishing" in text
    assert "nlm notebook create" in text
