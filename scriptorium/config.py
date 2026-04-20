"""TOML-backed configuration with injection-safe KV setter (defect-fix #3).

v0.1 shelled out to a subprocess that interpolated user input into a shell
string, making it vulnerable to command injection via a crafted --value.
This module replaces that path with a pure-Python writer that:

  1. Validates the key against dataclasses.fields(Config) (unknown keys raise).
  2. Coerces the value to the field's declared type via get_origin/get_args.
  3. Writes TOML by escaping quotes, newlines, and control chars — the value
     is always *data*, never interpreted as TOML syntax.
"""

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
        elif ord(ch) < 0x20:
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


def save_config_from_kv(path: Path, key: str, value: str) -> None:
    """Safe KV setter — defect-fix #3.

    Validates the key, coerces the value to the declared type, then writes
    TOML via the escaping writer. The value is data, not a command.
    """
    config = load_config(path)
    field_map = {f.name: f for f in fields(Config)}
    if key not in field_map:
        raise KeyError(f"Unknown config key: {key!r}")
    # Use get_type_hints() so annotations are resolved to actual types,
    # not strings (which is what field.type returns under PEP 563).
    type_hints = get_type_hints(Config)
    coerced = _coerce(value, type_hints[key])
    setattr(config, key, coerced)
    save_config(path, config)
