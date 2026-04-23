"""§4.1 resolve_review_dir + new §2 review paths."""
from pathlib import Path

import pytest

from scriptorium.paths import ReviewPaths, resolve_review_dir


def test_absolute_path_used_verbatim(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_REVIEW_DIR", raising=False)
    paths = resolve_review_dir(explicit=tmp_path, vault_root=None, cwd=tmp_path)
    assert paths.root == tmp_path.resolve()


def test_relative_with_vault(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_REVIEW_DIR", raising=False)
    vault = tmp_path / "vault"
    (vault / "reviews" / "caffeine-wm").mkdir(parents=True)
    paths = resolve_review_dir(
        explicit=Path("reviews/caffeine-wm"),
        vault_root=vault,
        cwd=tmp_path,
    )
    assert paths.root == (vault / "reviews" / "caffeine-wm").resolve()


def test_relative_without_vault(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_REVIEW_DIR", raising=False)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    paths = resolve_review_dir(
        explicit=Path("reviews/caffeine-wm"),
        vault_root=None,
        cwd=cwd,
    )
    assert paths.root == (cwd / "reviews" / "caffeine-wm").resolve()


def test_env_fallback(tmp_path, monkeypatch):
    env_dir = tmp_path / "env-review"
    env_dir.mkdir()
    monkeypatch.setenv("SCRIPTORIUM_REVIEW_DIR", str(env_dir))
    paths = resolve_review_dir(explicit=None, vault_root=None, cwd=tmp_path)
    assert paths.root == env_dir.resolve()


def test_default_is_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_REVIEW_DIR", raising=False)
    paths = resolve_review_dir(explicit=None, vault_root=None, cwd=tmp_path)
    assert paths.root == tmp_path.resolve()


def test_new_review_paths_exposed(tmp_path):
    p = ReviewPaths(root=tmp_path)
    assert p.overview == tmp_path / "overview.md"
    assert p.contradictions == tmp_path / "contradictions.md"
    assert p.references_bib == tmp_path / "references.bib"
    assert p.papers == tmp_path / "sources" / "papers"
    assert p.lock == tmp_path / ".scriptorium" / "lock"
    assert p.overview_archive == tmp_path / "audit" / "overview-archive"
