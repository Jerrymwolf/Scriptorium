"""Tests for scriptorium.scope — scope.json v1 schema."""
from __future__ import annotations

import json
from pathlib import Path

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
