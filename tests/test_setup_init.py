"""§7.2 init flag parsing (actual install is external)."""
import io

from scriptorium.cli import main


def test_init_help_lists_flags(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = io.StringIO(); err = io.StringIO()
    rc = main(["init", "--help"], stdout=out, stderr=err)
    assert rc == 0
    text = out.getvalue()
    assert "--notebooklm" in text
    assert "--skip-notebooklm" in text
    assert "--vault" in text


def test_init_skip_notebooklm_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = io.StringIO(); err = io.StringIO()
    rc = main(["init", "--skip-notebooklm"], stdout=out, stderr=err)
    assert rc == 0
    assert "setup complete" in out.getvalue().lower()
