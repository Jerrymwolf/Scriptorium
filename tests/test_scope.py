"""Tests for scriptorium.scope — scope.json v1 schema."""
from __future__ import annotations

import pytest

from scriptorium.scope import (
    SCHEMA_VERSION,
    VALID_PURPOSES,
    VALID_METHODOLOGIES,
    VALID_PUB_TYPES,
    VALID_DEPTHS,
    VALID_PARADIGMS,
    Scope,
    AnchorPaper,
    ScopeValidationError,
    load_scope,
    save_scope,
    validate_scope_dict,
)


def test_schema_version_is_1():
    assert SCHEMA_VERSION == 1


def test_valid_purposes_set():
    assert VALID_PURPOSES == {
        "dissertation", "grant", "narrative", "systematic", "scoping"
    }


def test_valid_methodologies_set():
    assert VALID_METHODOLOGIES == {
        "any", "qualitative", "quantitative", "RCT", "mixed"
    }


def test_valid_publication_types_set():
    assert VALID_PUB_TYPES == {
        "peer-reviewed", "preprints", "grey", "dissertations"
    }


def test_valid_depths_set():
    assert VALID_DEPTHS == {"exhaustive", "representative"}


def test_valid_paradigms_set():
    assert VALID_PARADIGMS == {
        "positivist", "interpretivist", "critical", "pragmatist"
    }


def test_anchor_paper_defaults():
    ap = AnchorPaper(raw="Ryan & Deci 2000")
    assert ap.doi is None
    assert ap.resolved is False


def test_scope_requires_and_optional_fields():
    scope = Scope(
        research_question="Does X affect Y?",
        purpose="dissertation",
        fields=["psychology"],
        methodology="any",
        year_range=[2018, 2026],
        corpus_target=50,
        publication_types=["peer-reviewed"],
        depth="representative",
        known_gaps_focus=False,
    )
    assert scope.population is None
    assert scope.conceptual_frame is None
    assert scope.anchor_papers == []
    assert scope.output_intent is None
    assert scope.paradigm is None
    assert scope.soft_warnings == []
    assert scope.schema_version == 1
    assert scope.created_at == ""
