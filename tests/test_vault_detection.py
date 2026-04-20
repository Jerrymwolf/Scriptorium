"""§4.2 + §4.3: vault walk-up, conflict copies, path escape, symlink policy."""
from pathlib import Path

import pytest

from scriptorium.vault import (
    PathEscapeError,
    VaultConflictCopy,
    detect_vault,
    ensure_within,
)


def test_vault_detected_when_dot_obsidian_present(tmp_path):
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    review = vault / "reviews" / "caffeine-wm"
    review.mkdir(parents=True)
    res = detect_vault(review)
    assert res.vault_root == vault.resolve()
    assert res.warning is None


def test_vault_none_when_missing(tmp_path):
    review = tmp_path / "no-vault" / "reviews" / "x"
    review.mkdir(parents=True)
    res = detect_vault(review)
    assert res.vault_root is None


def test_conflict_copy_triggers_warning(tmp_path):
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / ".obsidian (conflicted copy)").mkdir()
    res = detect_vault(vault / "reviews" / "x")
    (vault / "reviews" / "x").mkdir(parents=True, exist_ok=True)
    res = detect_vault(vault / "reviews" / "x")
    assert res.vault_root == vault.resolve()
    assert res.warning == "W_VAULT_CONFLICT_COPY"


def test_conflict_only_directory_is_ignored(tmp_path):
    fake = tmp_path / "fake"
    (fake / ".obsidian 2").mkdir(parents=True)
    res = detect_vault(fake / "reviews" / "x")
    (fake / "reviews" / "x").mkdir(parents=True, exist_ok=True)
    res = detect_vault(fake / "reviews" / "x")
    assert res.vault_root is None


def test_symlinked_review_resolves_to_real_vault(tmp_path):
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    real = vault / "reviews" / "caffeine-wm"
    real.mkdir(parents=True)
    link = tmp_path / "reviews-link"
    link.symlink_to(real)
    res = detect_vault(link)
    assert res.vault_root == vault.resolve()


def test_ensure_within_allows_subpath(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    inner = root / "a" / "b"
    inner.mkdir(parents=True)
    ensure_within(inner, root)


def test_ensure_within_rejects_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(PathEscapeError):
        ensure_within(other, root)
