"""Exit codes and canonical error class for Scriptorium v0.3.

The symbols here are the contract referenced by §11 of the design spec.
Every non-zero code is unique. `ScriptoriumError.symbol` carries the
symbolic name; `exit_code` is the integer returned by `scriptorium` on
unhandled error.
"""
from __future__ import annotations


EXIT_CODES: dict[str, int] = {
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


class ScriptoriumError(Exception):
    """A user-visible Scriptorium error carrying a §11 symbol."""

    def __init__(self, message: str, *, symbol: str) -> None:
        if symbol not in EXIT_CODES:
            raise KeyError(f"Unknown exit-code symbol: {symbol!r}")
        super().__init__(message)
        self.symbol = symbol
        self.exit_code = EXIT_CODES[symbol]
