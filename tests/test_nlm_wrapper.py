"""§0.2 verified nlm commands: construction, capture, failure mapping."""
from pathlib import Path
from unittest.mock import patch

import pytest

from scriptorium.errors import ScriptoriumError
from scriptorium.nlm import (
    NlmResult,
    NlmUnavailableError,
    NlmTimeoutError,
    doctor,
    create_audio,
    create_mindmap,
    create_notebook,
    create_slides,
    create_video,
    upload_source,
)


class _FakeCompleted:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@patch("scriptorium.nlm._run")
def test_doctor_success(mock_run):
    mock_run.return_value = _FakeCompleted(stdout="nlm is healthy\n")
    res = doctor()
    mock_run.assert_called_once_with(["nlm", "doctor"], timeout=60)
    assert res.returncode == 0


@patch("scriptorium.nlm._run")
def test_doctor_failure_raises_unavailable(mock_run):
    mock_run.return_value = _FakeCompleted(returncode=1, stderr="not authed")
    with pytest.raises(NlmUnavailableError):
        doctor()


@patch("scriptorium.nlm._run")
def test_create_notebook_cmd(mock_run):
    mock_run.return_value = _FakeCompleted(stdout="id: abc123\nurl: https://x\n")
    res = create_notebook("Caffeine Wm")
    mock_run.assert_called_once_with(
        ["nlm", "notebook", "create", "Caffeine Wm"], timeout=300
    )
    assert res.notebook_id == "abc123"
    assert res.notebook_url == "https://x"


@patch("scriptorium.nlm._run")
def test_upload_source_cmd(mock_run, tmp_path):
    f = tmp_path / "s.md"
    f.write_text("x", encoding="utf-8")
    mock_run.return_value = _FakeCompleted(stdout="ok\n")
    upload_source("abc", f)
    mock_run.assert_called_once_with(
        ["nlm", "source", "add", "abc", "--file", str(f)], timeout=300
    )


@patch("scriptorium.nlm._run")
def test_artifact_commands(mock_run):
    mock_run.return_value = _FakeCompleted(stdout="queued artifact_1\n")
    create_audio("abc")
    create_slides("abc")
    create_mindmap("abc")
    create_video("abc")
    assert mock_run.call_args_list[0][0][0] == ["nlm", "audio", "create", "abc"]
    assert mock_run.call_args_list[1][0][0] == ["nlm", "slides", "create", "abc"]
    assert mock_run.call_args_list[2][0][0] == ["nlm", "mindmap", "create", "abc"]
    assert mock_run.call_args_list[3][0][0] == ["nlm", "video", "create", "abc"]


@patch("scriptorium.nlm._run")
def test_upload_timeout_raises_timeout_error(mock_run, tmp_path):
    import subprocess
    f = tmp_path / "s.md"
    f.write_text("x", encoding="utf-8")
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["nlm"], timeout=300)
    with pytest.raises(NlmTimeoutError):
        upload_source("abc", f)
