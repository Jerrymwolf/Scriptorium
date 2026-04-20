"""Single-writer review lock (`<review-dir>/.scriptorium.lock`).

The lock is a plain sentinel file containing the PID of the holder. v0.3
does not attempt to break stale locks automatically; the canonical error
message tells the user to remove the file after confirming no process is
writing.
"""
from __future__ import annotations

import os
from pathlib import Path
from types import TracebackType
from typing import Optional, Type


class ReviewLockHeld(Exception):
    """Another Scriptorium run holds the review lock (E_LOCKED)."""


class ReviewLock:
    """Context manager that writes a PID sentinel file on enter and removes it on exit."""

    def __init__(self, path: Path):
        self._path = Path(path)

    def __enter__(self) -> "ReviewLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(
                self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
        except FileExistsError as e:
            raise ReviewLockHeld(
                f"review is locked by another Scriptorium run at {self._path}. "
                "If no run is active, remove the stale lock after verifying "
                "no process is writing."
            ) from e
        try:
            os.write(fd, f"{os.getpid()}\n".encode("utf-8"))
        finally:
            os.close(fd)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
