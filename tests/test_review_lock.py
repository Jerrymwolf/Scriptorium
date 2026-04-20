"""§9.4 / §10.1: single-writer lock for publish and migrate-review."""
from pathlib import Path

import pytest

from scriptorium.lock import (
    ReviewLock,
    ReviewLockHeld,
)


def test_acquire_and_release(tmp_path):
    lock = tmp_path / ".scriptorium.lock"
    with ReviewLock(lock):
        assert lock.exists()
    assert not lock.exists()


def test_second_acquire_raises(tmp_path):
    lock = tmp_path / ".scriptorium.lock"
    with ReviewLock(lock):
        with pytest.raises(ReviewLockHeld) as exc:
            with ReviewLock(lock):
                pass
        assert str(lock) in str(exc.value)


def test_stale_lock_readable_message(tmp_path):
    lock = tmp_path / ".scriptorium.lock"
    lock.write_text("999999\n", encoding="utf-8")
    with pytest.raises(ReviewLockHeld):
        with ReviewLock(lock):
            pass
