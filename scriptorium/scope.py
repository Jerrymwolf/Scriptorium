"""scope.json v1 — scoping artifact schema, validation, and I/O.

See docs/superpowers/specs/2026-04-23-lit-scoping-design.md for the full
contract. The schema version is an integer; bump it when fields change
shape in a way existing files can't satisfy.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1

VALID_PURPOSES = {"dissertation", "grant", "narrative", "systematic", "scoping"}
VALID_METHODOLOGIES = {"any", "qualitative", "quantitative", "RCT", "mixed"}
VALID_PUB_TYPES = {"peer-reviewed", "preprints", "grey", "dissertations"}
VALID_DEPTHS = {"exhaustive", "representative"}
VALID_PARADIGMS = {"positivist", "interpretivist", "critical", "pragmatist"}


class ScopeValidationError(ValueError):
    """Raised when a scope dict fails v1 schema validation."""


@dataclass
class AnchorPaper:
    raw: str
    doi: str | None = None
    resolved: bool = False


@dataclass
class Scope:
    research_question: str
    purpose: str
    fields: list[str]
    methodology: str
    year_range: list[int | None]
    corpus_target: int | str
    publication_types: list[str]
    depth: str
    known_gaps_focus: bool
    population: str | None = None
    conceptual_frame: str | None = None
    anchor_papers: list[AnchorPaper] = field(default_factory=list)
    output_intent: str | None = None
    paradigm: str | None = None
    soft_warnings: list[str] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION
    created_at: str = ""


def _utc_z_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def validate_scope_dict(data: dict) -> None:
    """Raise ScopeValidationError if data does not conform to v1."""
    raise NotImplementedError


def load_scope(path: Path) -> Scope:
    raise NotImplementedError


def save_scope(path: Path, scope: Scope) -> None:
    raise NotImplementedError
