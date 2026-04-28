"""Every §11 exit code symbol must be exported with a unique integer value."""
from scriptorium.errors import EXIT_CODES, ScriptoriumError


EXPECTED = {
    "OK": 0,
    "E_USAGE": 1,
    "E_CONFIG": 2,
    "E_VERIFY_FAILED": 3,
    "E_REVIEW_INCOMPLETE": 4,
    "E_NLM_UNAVAILABLE": 5,
    "E_NLM_CREATE": 6,
    "E_NLM_UPLOAD": 7,
    "E_NLM_ARTIFACT": 8,
    "E_TIMEOUT": 9,
    "E_SOURCES": 10,
    "E_NOTEBOOK_NAME": 11,
    "E_LOCKED": 12,
    "E_PATH_ESCAPE": 13,
    "E_CONFIG_CORRUPT": 14,
    "E_AUDIT_CORRUPT": 15,
    "E_STATE_CORRUPT": 16,
    "E_OVERVIEW_FAILED": 17,
    "E_SETUP_FAILED": 18,
    # v0.4 Layer A — phase-state contract (T03)
    "E_PHASE_STATE_VERSION_NEWER": 19,
    "E_PHASE_STATE_INVALID": 20,
    "E_PHASE_STATE_CORRUPT": 21,
    # v0.4 Layer B — reviewer output validation (T04)
    "E_REVIEWER_INVALID": 22,
    "E_NOT_IMPLEMENTED": 23,
    # v0.4 Layer B — extraction orchestration (T12)
    "E_EXTRACT_BAD_CAP": 24,
    "E_EXTRACT_NO_DISPATCHER": 25,
    "E_EXTRACT_UNKNOWN_RUNTIME": 26,
    # v0.4 Layer B — Cowork backend dispatch (T13)
    "E_EXTRACT_UNKNOWN_BACKEND": 27,
    "E_EXTRACT_NO_BACKEND": 28,
    "E_EXTRACT_PAPER_NOT_KEPT": 29,
    "E_INTERRUPTED": 130,
}


def test_exit_codes_match_spec():
    assert EXIT_CODES == EXPECTED


def test_exit_codes_are_unique():
    assert len(set(EXIT_CODES.values())) == len(EXIT_CODES)


def test_scriptorium_error_carries_symbol_and_exit_code():
    err = ScriptoriumError("boom", symbol="E_NLM_CREATE")
    assert err.symbol == "E_NLM_CREATE"
    assert err.exit_code == 6
    assert str(err) == "boom"


def test_scriptorium_error_rejects_unknown_symbol():
    import pytest
    with pytest.raises(KeyError):
        ScriptoriumError("boom", symbol="E_NOT_A_THING")
