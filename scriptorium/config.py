"""TOML-backed configuration with injection-safe KV setter (defect-fix #3).

v0.1 shelled out to a subprocess that interpolated user input into a shell
string, making it vulnerable to command injection via a crafted --value.
This module replaces that path with a pure-Python writer that:

  1. Validates the key against dataclasses.fields(Config) (unknown keys raise).
  2. Coerces the value to the field's declared type via get_origin/get_args.
  3. Writes TOML by escaping quotes, newlines, and control chars — the value
     is always *data*, never interpreted as TOML syntax.
"""

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints
import tomllib


@dataclass
class Config:
    default_model: str = "opus"
    review_dir: str = "literature_review"
    evidence_required: bool = True
    sources_enabled: list[str] = field(
        default_factory=lambda: ["openalex", "semantic_scholar"]
    )
    notebook_id: str = ""
    unpaywall_email: str = ""
    openalex_email: str = ""
    semantic_scholar_api_key: str = ""
    default_backend: str = "openalex"
    languages: list[str] = field(default_factory=lambda: ["en"])
    obsidian_vault: str = ""
    notebooklm_enabled: bool = False
    notebooklm_prompt: bool = True


def load_config(path: Path) -> Config:
    if not path.exists():
        return Config()
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    section = raw.get("scriptorium", {})
    known = {f.name for f in fields(Config)}
    kwargs = {k: v for k, v in section.items() if k in known}
    return Config(**kwargs)


def _toml_escape_str(v: str) -> str:
    """Return a TOML basic string literal with all dangerous chars escaped."""
    out: list[str] = []
    for ch in v:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def _toml_serialize(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return _toml_escape_str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_serialize(x) for x in v) + "]"
    raise TypeError(f"Unsupported TOML type: {type(v).__name__}")


def save_config(path: Path, config: Config) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[scriptorium]"]
    for f in fields(Config):
        v = getattr(config, f.name)
        lines.append(f"{f.name} = {_toml_serialize(v)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _coerce(value: str, field_type: Any) -> Any:
    """Coerce a raw string value to the declared field type."""
    origin = get_origin(field_type)
    if field_type is bool:
        low = value.lower()
        if low in ("true", "1", "yes"):
            return True
        if low in ("false", "0", "no"):
            return False
        raise ValueError(f"Cannot coerce {value!r} to bool")
    if origin is list:
        args = get_args(field_type)
        item_type = args[0] if args else str
        if item_type is not str:
            raise TypeError(
                f"Only list[str] is supported; got list[{item_type!r}]"
            )
        return [item.strip() for item in value.split(",") if item.strip()]
    if field_type is str:
        return value
    raise TypeError(f"Unsupported field type: {field_type!r}")


class ConfigCorruptError(Exception):
    """Raised when a TOML config file exists but cannot be parsed (§3.1)."""


_ENV_STRING_KEYS: dict[str, str] = {
    "SCRIPTORIUM_OBSIDIAN_VAULT": "obsidian_vault",
}


def _load_toml_safe(path: Path) -> dict:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigCorruptError(f"{path}: {e}") from e
    section = raw.get("scriptorium", {})
    if not isinstance(section, dict):
        raise ConfigCorruptError(f"{path}: [scriptorium] is not a table")
    return section


def _apply_section(cfg: Config, section: dict) -> Config:
    known = {f.name for f in fields(Config)}
    data = {**cfg.__dict__}
    for k, v in section.items():
        if k in known:
            data[k] = v
    return Config(**data)


def resolve_config(
    *,
    review_dir: Path | None,
    user_config_path: Path | None,
) -> Config:
    """Resolve a merged Config per §3.1 plus env overrides per §3.3.

    Order (later overrides earlier):
      1. Built-in defaults.
      2. <review_dir>/config.toml.
      3. <user_config_path>.
      4. Env overrides.
    """
    cfg = Config()

    if review_dir is not None:
        review_toml = Path(review_dir) / "config.toml"
        if review_toml.exists():
            cfg = _apply_section(cfg, _load_toml_safe(review_toml))

    if user_config_path is not None and user_config_path.exists():
        cfg = _apply_section(cfg, _load_toml_safe(user_config_path))

    for env_name, field_name in _ENV_STRING_KEYS.items():
        env_val = os.environ.get(env_name)
        if env_val is not None:
            setattr(cfg, field_name, env_val)

    return cfg


def default_user_config_path() -> Path:
    """Location of the user-level config (§3.1)."""
    override = os.environ.get("SCRIPTORIUM_CONFIG")
    if override:
        return Path(override)
    home = Path(os.environ.get("HOME", "")).expanduser()
    return home / ".config" / "scriptorium" / "config.toml"


def save_config_from_kv(path: Path, key: str, value: str) -> None:
    """Safe KV setter — defect-fix #3.

    Validates the key, coerces the value to the declared type, then writes
    TOML via the escaping writer. The value is data, not a command.
    """
    try:
        config = load_config(path)
    except tomllib.TOMLDecodeError as e:
        raise ConfigCorruptError(f"{path}: {e}") from e
    field_map = {f.name: f for f in fields(Config)}
    if key not in field_map:
        raise KeyError(f"Unknown config key: {key!r}")
    # Use get_type_hints() so annotations are resolved to actual types,
    # not strings (which is what field.type returns under PEP 563).
    type_hints = get_type_hints(Config)
    coerced = _coerce(value, type_hints[key])
    setattr(config, key, coerced)
    save_config(path, config)
