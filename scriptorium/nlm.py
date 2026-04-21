"""Thin wrapper over the verified `nlm` CLI (§0.2).

Every call goes through `_run` so tests can patch a single seam. Output
parsing is limited to the two fields v0.3 needs from `nlm notebook create`:
the notebook id and URL.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence


DEFAULT_TIMEOUT_SECONDS = 300
DOCTOR_TIMEOUT_SECONDS = 60


class NlmUnavailableError(Exception):
    """`nlm` is missing or `nlm doctor` reports failure."""


class NlmTimeoutError(Exception):
    """An `nlm` subprocess timed out."""


class NlmCommandError(Exception):
    """Generic `nlm` command failure."""

    def __init__(self, message: str, *, returncode: int, stderr: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


@dataclass
class NlmResult:
    stdout: str
    stderr: str
    returncode: int


@dataclass
class NotebookCreated:
    notebook_id: str
    notebook_url: str
    stdout: str


def _run(cmd: Sequence[str], *, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(cmd),
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _invoke(cmd: Sequence[str], *, timeout: int) -> NlmResult:
    try:
        cp = _run(cmd, timeout=timeout)
    except FileNotFoundError as e:
        raise NlmUnavailableError(f"nlm not on PATH: {cmd[0]}") from e
    except subprocess.TimeoutExpired as e:
        raise NlmTimeoutError(f"timed out: {' '.join(cmd)}") from e
    return NlmResult(stdout=cp.stdout or "", stderr=cp.stderr or "", returncode=cp.returncode)


def doctor() -> NlmResult:
    res = _invoke(["nlm", "doctor"], timeout=DOCTOR_TIMEOUT_SECONDS)
    if res.returncode != 0:
        raise NlmUnavailableError(res.stderr or res.stdout or "nlm doctor failed")
    return res


_ID_RE = re.compile(r"id[:\s]+([A-Za-z0-9_\-]+)", re.IGNORECASE)
_URL_RE = re.compile(r"(https?://\S+)")


def create_notebook(title: str) -> NotebookCreated:
    res = _invoke(
        ["nlm", "notebook", "create", title], timeout=DEFAULT_TIMEOUT_SECONDS
    )
    if res.returncode != 0:
        raise NlmCommandError(
            f"nlm notebook create failed",
            returncode=res.returncode, stderr=res.stderr,
        )
    id_match = _ID_RE.search(res.stdout)
    url_match = _URL_RE.search(res.stdout)
    if not id_match or not url_match:
        raise NlmCommandError(
            f"could not parse notebook id/url from nlm output: {res.stdout!r}",
            returncode=res.returncode, stderr=res.stderr,
        )
    return NotebookCreated(
        notebook_id=id_match.group(1),
        notebook_url=url_match.group(1),
        stdout=res.stdout,
    )


def upload_source(notebook_id: str, path: Path) -> NlmResult:
    res = _invoke(
        ["nlm", "source", "add", notebook_id, "--file", str(path)],
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    if res.returncode != 0:
        raise NlmCommandError(
            f"nlm source add failed for {path}",
            returncode=res.returncode, stderr=res.stderr,
        )
    return res


def _artifact(kind: str, notebook_id: str) -> NlmResult:
    res = _invoke(
        ["nlm", kind, "create", notebook_id], timeout=DEFAULT_TIMEOUT_SECONDS
    )
    if res.returncode != 0:
        raise NlmCommandError(
            f"nlm {kind} create failed",
            returncode=res.returncode, stderr=res.stderr,
        )
    return res


def create_audio(notebook_id: str) -> NlmResult:
    return _artifact("audio", notebook_id)


def create_slides(notebook_id: str) -> NlmResult:
    return _artifact("slides", notebook_id)


def create_mindmap(notebook_id: str) -> NlmResult:
    return _artifact("mindmap", notebook_id)


def create_video(notebook_id: str) -> NlmResult:
    return _artifact("video", notebook_id)
