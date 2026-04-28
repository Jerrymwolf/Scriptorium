"""`scriptorium doctor` verifies version, writable HOME, nlm presence hint."""
import io
from unittest.mock import patch

from scriptorium import __version__
from scriptorium.cli import main
from scriptorium.nlm import NlmUnavailableError, NlmResult


def test_doctor_runs_and_reports_version(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = io.StringIO(); err = io.StringIO()
    with patch("scriptorium.doctor.nlm") as mock_nlm:
        mock_nlm.doctor.return_value = NlmResult("ok", "", 0)
        rc = main(["doctor"], stdout=out, stderr=err)
    assert rc == 0
    assert f"scriptorium {__version__}" in out.getvalue()
    assert "nlm: ok" in out.getvalue()


def test_doctor_reports_nlm_unavailable_without_failing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = io.StringIO(); err = io.StringIO()
    with patch("scriptorium.doctor.nlm") as mock_nlm:
        mock_nlm.doctor.side_effect = NlmUnavailableError("no nlm")
        rc = main(["doctor"], stdout=out, stderr=err)
    assert rc == 0
    assert "nlm: unavailable" in out.getvalue()
