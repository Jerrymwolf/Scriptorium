"""Layered config resolution per §3.1 and env overrides per §3.3."""
import os
from pathlib import Path

import pytest

from scriptorium.config import (
    Config,
    ConfigCorruptError,
    resolve_config,
)


def _write_toml(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_defaults_when_no_files(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_REVIEW_DIR", raising=False)
    monkeypatch.delenv("SCRIPTORIUM_CONFIG", raising=False)
    monkeypatch.delenv("SCRIPTORIUM_OBSIDIAN_VAULT", raising=False)
    cfg = resolve_config(review_dir=tmp_path, user_config_path=tmp_path / "nope.toml")
    assert cfg == Config()


def test_review_local_overrides_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_OBSIDIAN_VAULT", raising=False)
    _write_toml(
        tmp_path / "config.toml",
        '[scriptorium]\nunpaywall_email = "review@example.com"\n',
    )
    cfg = resolve_config(review_dir=tmp_path, user_config_path=tmp_path / "user.toml")
    assert cfg.unpaywall_email == "review@example.com"


def test_user_config_overrides_review_local(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_OBSIDIAN_VAULT", raising=False)
    _write_toml(
        tmp_path / "config.toml",
        '[scriptorium]\nunpaywall_email = "review@example.com"\n',
    )
    user = tmp_path / "user.toml"
    _write_toml(user, '[scriptorium]\nunpaywall_email = "user@example.com"\n')
    cfg = resolve_config(review_dir=tmp_path, user_config_path=user)
    assert cfg.unpaywall_email == "user@example.com"


def test_env_overrides_user_config(tmp_path, monkeypatch):
    user = tmp_path / "user.toml"
    _write_toml(user, '[scriptorium]\nobsidian_vault = "/from/user"\n')
    monkeypatch.setenv("SCRIPTORIUM_OBSIDIAN_VAULT", "/from/env")
    cfg = resolve_config(review_dir=tmp_path, user_config_path=user)
    assert cfg.obsidian_vault == "/from/env"


def test_unknown_key_in_toml_is_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_OBSIDIAN_VAULT", raising=False)
    _write_toml(
        tmp_path / "config.toml",
        '[scriptorium]\nnot_a_key = "x"\nunpaywall_email = "ok@example.com"\n',
    )
    cfg = resolve_config(review_dir=tmp_path, user_config_path=tmp_path / "user.toml")
    assert cfg.unpaywall_email == "ok@example.com"


def test_corrupted_toml_raises_config_corrupt(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_OBSIDIAN_VAULT", raising=False)
    _write_toml(tmp_path / "config.toml", "this is = not = valid = toml\n[[[")
    with pytest.raises(ConfigCorruptError):
        resolve_config(review_dir=tmp_path, user_config_path=tmp_path / "user.toml")


def test_cowork_env_flag_sets_cowork_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTORIUM_COWORK", "1")
    from scriptorium.cowork import is_cowork_mode
    assert is_cowork_mode() is True
    monkeypatch.setenv("SCRIPTORIUM_COWORK", "no")
    assert is_cowork_mode() is False


def test_force_cowork_alias(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIPTORIUM_COWORK", raising=False)
    monkeypatch.setenv("SCRIPTORIUM_FORCE_COWORK", "yes")
    from scriptorium.cowork import is_cowork_mode
    assert is_cowork_mode() is True
