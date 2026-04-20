"""Config dataclass must contain every §3.2 key with the right default/type."""
from dataclasses import fields
import pytest

from scriptorium.config import Config


EXPECTED: dict[str, tuple[type | tuple, object]] = {
    "default_model": (str, "opus"),
    "review_dir": (str, "literature_review"),
    "evidence_required": (bool, True),
    "sources_enabled": (list, ["openalex", "semantic_scholar"]),
    "notebook_id": (str, ""),
    "unpaywall_email": (str, ""),
    "openalex_email": (str, ""),
    "semantic_scholar_api_key": (str, ""),
    "default_backend": (str, "openalex"),
    "languages": (list, ["en"]),
    "obsidian_vault": (str, ""),
    "notebooklm_enabled": (bool, False),
    "notebooklm_prompt": (bool, True),
}


@pytest.mark.parametrize("name,spec", list(EXPECTED.items()))
def test_field_default(name, spec):
    expected_type, expected_default = spec
    cfg = Config()
    assert hasattr(cfg, name), f"Config is missing field {name}"
    value = getattr(cfg, name)
    if expected_type is list:
        assert isinstance(value, list)
        assert value == expected_default
    else:
        assert isinstance(value, expected_type)
        assert value == expected_default


def test_no_unexpected_fields():
    names = {f.name for f in fields(Config)}
    assert names == set(EXPECTED), (
        f"Unexpected Config fields: {names ^ set(EXPECTED)}"
    )
