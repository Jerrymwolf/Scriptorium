# tests/test_readme.py
"""README content test — locks in the Superpowers credit, the install
surface, the dual-runtime framing, and the defect-fix #8 anti-pattern.
"""
import os
from pathlib import Path

README = Path(__file__).parent.parent / "README.md"


def test_readme_exists():
    assert README.exists()


def test_superpowers_credit_is_present_and_near_the_top():
    text = README.read_text(encoding="utf-8")
    assert "Superpowers" in text
    credit_idx = text.find("Superpowers")
    install_idx = text.find("## Install")
    assert credit_idx != -1
    if install_idx != -1:
        assert credit_idx < install_idx


def test_dual_runtime_framing():
    text = README.read_text(encoding="utf-8").lower()
    assert "claude code" in text
    assert "cowork" in text


def test_cc_install_uses_pipx_and_installer_script():
    text = README.read_text(encoding="utf-8")
    assert "pipx install scriptorium" in text or "pipx install ." in text
    assert "install_plugin.sh" in text


def test_cowork_install_lists_connectors():
    text = README.read_text(encoding="utf-8")
    for conn in ("Consensus", "Scholar Gateway", "PubMed", "NotebookLM"):
        assert conn in text, f"missing Cowork connector: {conn}"


def test_defect_fix_eight_no_bundle_submission_language():
    """Defect-fix #8: no 'Cowork bundle submission' language allowed."""
    text = README.read_text(encoding="utf-8").lower()
    forbidden = [
        "cowork bundle",
        "submit the bundle",
        "bundle submission",
        "submit to the cowork plugin library",
    ]
    for phrase in forbidden:
        assert phrase not in text, f"defect #8 regression — remove: {phrase}"


def test_three_disciplines_listed():
    text = README.read_text(encoding="utf-8").lower()
    assert "evidence-first" in text
    assert "prisma" in text
    assert "contradiction" in text


def test_test_and_license_sections_present():
    text = README.read_text(encoding="utf-8")
    assert "## Test" in text or "### Test" in text
    assert "## License" in text or "### License" in text


def test_install_plugin_script_exists_and_executable():
    script = Path(__file__).parent.parent / "scripts/install_plugin.sh"
    assert script.exists()
    assert os.access(script, os.X_OK), "install_plugin.sh not executable"
