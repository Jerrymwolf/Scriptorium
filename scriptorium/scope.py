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
    required_keys = {
        "schema_version", "created_at", "research_question", "purpose",
        "fields", "population", "methodology", "year_range", "corpus_target",
        "publication_types", "depth", "conceptual_frame", "anchor_papers",
        "output_intent", "known_gaps_focus", "paradigm", "soft_warnings",
    }
    missing = required_keys - data.keys()
    if missing:
        raise ScopeValidationError(f"missing required fields: {sorted(missing)}")

    if data["schema_version"] != SCHEMA_VERSION:
        raise ScopeValidationError(
            f"schema_version must be {SCHEMA_VERSION}, got {data['schema_version']!r}"
        )

    rq = data["research_question"]
    if not isinstance(rq, str) or not rq.strip():
        raise ScopeValidationError("research_question must be a non-empty string")

    if data["purpose"] not in VALID_PURPOSES:
        raise ScopeValidationError(
            f"purpose must be one of {sorted(VALID_PURPOSES)}, got {data['purpose']!r}"
        )

    fields_ = data["fields"]
    if not isinstance(fields_, list) or not fields_:
        raise ScopeValidationError("fields must be a non-empty list of strings")
    if not all(isinstance(f, str) and f.strip() for f in fields_):
        raise ScopeValidationError("fields entries must be non-empty strings")

    if data["methodology"] not in VALID_METHODOLOGIES:
        raise ScopeValidationError(
            f"methodology must be one of {sorted(VALID_METHODOLOGIES)}, "
            f"got {data['methodology']!r}"
        )

    yr = data["year_range"]
    if not (isinstance(yr, list) and len(yr) == 2):
        raise ScopeValidationError("year_range must be a 2-element list")
    for v in yr:
        if v is not None and not isinstance(v, int):
            raise ScopeValidationError("year_range entries must be int or null")

    ct = data["corpus_target"]
    if ct == "exhaustive":
        pass
    elif isinstance(ct, int) and ct > 0:
        pass
    else:
        raise ScopeValidationError(
            "corpus_target must be a positive int or the string 'exhaustive'"
        )

    pts = data["publication_types"]
    if not isinstance(pts, list) or not pts:
        raise ScopeValidationError("publication_types must be a non-empty list")
    for t in pts:
        if t not in VALID_PUB_TYPES:
            raise ScopeValidationError(
                f"publication_types entry {t!r} not in {sorted(VALID_PUB_TYPES)}"
            )

    if data["depth"] not in VALID_DEPTHS:
        raise ScopeValidationError(
            f"depth must be one of {sorted(VALID_DEPTHS)}, got {data['depth']!r}"
        )

    p = data["paradigm"]
    if p is not None and p not in VALID_PARADIGMS:
        raise ScopeValidationError(
            f"paradigm must be null or one of {sorted(VALID_PARADIGMS)}, got {p!r}"
        )

    if not isinstance(data["known_gaps_focus"], bool):
        raise ScopeValidationError("known_gaps_focus must be a boolean")

    for i, a in enumerate(data["anchor_papers"]):
        if not isinstance(a, dict) or "raw" not in a or not a["raw"]:
            raise ScopeValidationError(
                f"anchor_papers[{i}] must be an object with non-empty 'raw'"
            )


def _scope_to_dict(scope: Scope) -> dict:
    return asdict(scope)


def _scope_from_dict(data: dict) -> Scope:
    anchors = [AnchorPaper(**a) for a in data.get("anchor_papers", [])]
    return Scope(**{**data, "anchor_papers": anchors})


def save_scope(path: Path, scope: Scope) -> None:
    """Validate and write scope.json atomically.

    created_at is populated if empty. The file is written via a temp file
    and renamed to avoid torn writes.
    """
    if not scope.created_at:
        scope.created_at = _utc_z_now()
    data = _scope_to_dict(scope)
    validate_scope_dict(data)  # raises before any write
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def load_scope(path: Path) -> Scope:
    """Read and validate scope.json."""
    text = path.read_text(encoding="utf-8")  # FileNotFoundError propagates
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ScopeValidationError(f"invalid JSON in {path}: {e}") from e
    validate_scope_dict(data)
    return _scope_from_dict(data)
