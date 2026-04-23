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


MINIMAL_VALID = {
    "schema_version": 1,
    "created_at": "2026-04-23T10:30:00Z",
    "research_question": "Does X affect Y?",
    "purpose": "dissertation",
    "fields": ["psychology"],
    "population": None,
    "methodology": "any",
    "year_range": [2018, 2026],
    "corpus_target": 50,
    "publication_types": ["peer-reviewed"],
    "depth": "representative",
    "conceptual_frame": None,
    "anchor_papers": [],
    "output_intent": None,
    "known_gaps_focus": False,
    "paradigm": None,
    "soft_warnings": [],
}


def test_validate_minimal_valid_passes():
    validate_scope_dict(MINIMAL_VALID)  # no raise


def test_validate_missing_required_field_raises():
    data = dict(MINIMAL_VALID)
    del data["research_question"]
    with pytest.raises(ScopeValidationError, match="research_question"):
        validate_scope_dict(data)


def test_validate_empty_research_question_raises():
    data = dict(MINIMAL_VALID, research_question="   ")
    with pytest.raises(ScopeValidationError, match="research_question"):
        validate_scope_dict(data)


def test_validate_bad_purpose_raises():
    data = dict(MINIMAL_VALID, purpose="phd-thesis")
    with pytest.raises(ScopeValidationError, match="purpose"):
        validate_scope_dict(data)


def test_validate_bad_methodology_raises():
    data = dict(MINIMAL_VALID, methodology="survey")
    with pytest.raises(ScopeValidationError, match="methodology"):
        validate_scope_dict(data)


def test_validate_bad_depth_raises():
    data = dict(MINIMAL_VALID, depth="shallow")
    with pytest.raises(ScopeValidationError, match="depth"):
        validate_scope_dict(data)


def test_validate_bad_publication_type_raises():
    data = dict(MINIMAL_VALID, publication_types=["books"])
    with pytest.raises(ScopeValidationError, match="publication_types"):
        validate_scope_dict(data)


def test_validate_bad_paradigm_raises():
    data = dict(MINIMAL_VALID, paradigm="postmodern")
    with pytest.raises(ScopeValidationError, match="paradigm"):
        validate_scope_dict(data)


def test_validate_null_paradigm_allowed():
    data = dict(MINIMAL_VALID, paradigm=None)
    validate_scope_dict(data)  # no raise


def test_validate_empty_fields_list_raises():
    data = dict(MINIMAL_VALID, fields=[])
    with pytest.raises(ScopeValidationError, match="fields"):
        validate_scope_dict(data)


def test_validate_year_range_wrong_length_raises():
    data = dict(MINIMAL_VALID, year_range=[2020])
    with pytest.raises(ScopeValidationError, match="year_range"):
        validate_scope_dict(data)


def test_validate_year_range_null_null_allowed():
    data = dict(MINIMAL_VALID, year_range=[None, None])
    validate_scope_dict(data)


def test_validate_year_range_open_ended_allowed():
    data = dict(MINIMAL_VALID, year_range=[2015, None])
    validate_scope_dict(data)


def test_validate_corpus_target_exhaustive_string_allowed():
    data = dict(MINIMAL_VALID, corpus_target="exhaustive")
    validate_scope_dict(data)


def test_validate_corpus_target_negative_raises():
    data = dict(MINIMAL_VALID, corpus_target=-5)
    with pytest.raises(ScopeValidationError, match="corpus_target"):
        validate_scope_dict(data)


def test_validate_wrong_schema_version_raises():
    data = dict(MINIMAL_VALID, schema_version=2)
    with pytest.raises(ScopeValidationError, match="schema_version"):
        validate_scope_dict(data)


def test_validate_anchor_paper_missing_raw_raises():
    data = dict(MINIMAL_VALID, anchor_papers=[{"doi": None, "resolved": False}])
    with pytest.raises(ScopeValidationError, match="anchor_papers"):
        validate_scope_dict(data)
