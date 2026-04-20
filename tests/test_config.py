import pytest
import tomllib
from scriptorium.config import (
    Config,
    load_config,
    save_config,
    save_config_from_kv,
)


def test_load_config_defaults_when_missing(tmp_path):
    path = tmp_path / "config.toml"
    cfg = load_config(path)
    assert cfg == Config()


def test_roundtrip_save_and_load(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(
        default_model="haiku",
        evidence_required=False,
        sources_enabled=["openalex"],
    )
    save_config(path, cfg)
    loaded = load_config(path)
    assert loaded == cfg


def test_save_config_from_kv_coerces_types(tmp_path):
    path = tmp_path / "config.toml"
    save_config(path, Config())
    save_config_from_kv(path, "evidence_required", "false")
    save_config_from_kv(
        path, "sources_enabled", "openalex, semantic_scholar, pubmed"
    )
    cfg = load_config(path)
    assert cfg.evidence_required is False
    assert cfg.sources_enabled == ["openalex", "semantic_scholar", "pubmed"]


def test_save_config_from_kv_rejects_unknown_key(tmp_path):
    path = tmp_path / "config.toml"
    save_config(path, Config())
    with pytest.raises(KeyError):
        save_config_from_kv(path, "nope_not_a_field", "whatever")


def test_save_config_from_kv_rejects_bad_bool(tmp_path):
    path = tmp_path / "config.toml"
    save_config(path, Config())
    with pytest.raises(ValueError):
        save_config_from_kv(path, "evidence_required", "maybe")


def test_save_config_from_kv_is_injection_safe(tmp_path):
    """Defect-fix #3: malicious values must be stored as literal data.

    The payload tries to break out of the TOML string and inject a new key
    (``evil_key``). If the writer forgets to escape quotes and newlines,
    tomllib will parse a second top-level key. We assert that does NOT happen:
    the payload is round-tripped byte-for-byte as the value of
    ``default_model``, and no ``evil_key`` appears at any level of the parsed
    TOML document.
    """
    path = tmp_path / "config.toml"
    save_config(path, Config())
    payload = 'opus"\nevil_key = "stolen'
    save_config_from_kv(path, "default_model", payload)

    cfg = load_config(path)
    assert cfg.default_model == payload

    raw = path.read_text(encoding="utf-8")
    data = tomllib.loads(raw)
    assert "evil_key" not in data
    assert "evil_key" not in data.get("scriptorium", {})
    assert data["scriptorium"]["default_model"] == payload


def test_save_config_from_kv_escapes_del_character(tmp_path):
    path = tmp_path / "config.toml"
    save_config(path, Config())
    payload = "value\x7fwith-del"
    save_config_from_kv(path, "default_model", payload)
    cfg = load_config(path)
    assert cfg.default_model == payload
