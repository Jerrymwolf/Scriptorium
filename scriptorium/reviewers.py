"""Reviewer output validation for Scriptorium v0.4 (T04 minimal surface).

This module exposes only ``validate_reviewer_output`` and its supporting
constants. T14 will extend this module with ``append_reviewer_output``,
``finalize_synthesis_phase``, and agent-prompt logic.

§6.3 Reviewer output schema::

    {
      "reviewer": "cite|contradiction",
      "runtime": "claude_code|cowork",
      "verdict": "pass|fail|skipped",
      "summary": "string",
      "findings": [ ... ],
      "synthesis_sha256": "sha256:<64 hex>",
      "reviewer_prompt_sha256": "sha256:<64 hex>",
      "created_at": "ISO-8601"
    }

Rules:
- ``reviewer`` must be exactly one of ``cite``, ``contradiction``.
- ``runtime`` must be exactly one of ``claude_code``, ``cowork``.
- ``verdict=pass`` may have empty ``findings``.
- ``verdict=fail`` must have at least one finding.
- ``skipped`` is allowed with empty findings.
- Both hash fields must match ``sha256:<64 lowercase hex>``.
- The payload is invalid if required hashes are missing.
"""
from __future__ import annotations

import re
from typing import Any

from scriptorium.errors import ScriptoriumError
from scriptorium.phase_state import SHA256_SIG_RE


_VALID_REVIEWERS = frozenset({"cite", "contradiction"})
_VALID_RUNTIMES = frozenset({"claude_code", "cowork"})
_VALID_VERDICTS = frozenset({"pass", "fail", "skipped"})
_VALID_FINDING_KINDS = frozenset(
    {"unsupported_claim", "bad_locator", "missed_contradiction", "other"}
)

_REQUIRED_FIELDS = (
    "reviewer",
    "runtime",
    "verdict",
    "summary",
    "findings",
    "synthesis_sha256",
    "reviewer_prompt_sha256",
    "created_at",
)


def validate_reviewer_output(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a reviewer output payload against the §6.3 schema.

    Returns the payload unchanged on success.
    Raises :class:`~scriptorium.errors.ScriptoriumError` with symbol
    ``E_REVIEWER_INVALID`` on any schema violation.
    """
    def _fail(msg: str) -> None:
        raise ScriptoriumError(msg, symbol="E_REVIEWER_INVALID")

    if not isinstance(payload, dict):
        _fail("reviewer output must be a JSON object")

    # Check required top-level fields are present.
    for field in _REQUIRED_FIELDS:
        if field not in payload:
            _fail(f"missing required field: {field!r}")

    reviewer = payload["reviewer"]
    if reviewer not in _VALID_REVIEWERS:
        _fail(
            f"reviewer must be one of {sorted(_VALID_REVIEWERS)}, "
            f"got {reviewer!r}"
        )

    runtime = payload["runtime"]
    if runtime not in _VALID_RUNTIMES:
        _fail(
            f"runtime must be one of {sorted(_VALID_RUNTIMES)}, "
            f"got {runtime!r}"
        )

    verdict = payload["verdict"]
    if verdict not in _VALID_VERDICTS:
        _fail(
            f"verdict must be one of {sorted(_VALID_VERDICTS)}, "
            f"got {verdict!r}"
        )

    findings = payload["findings"]
    if not isinstance(findings, list):
        _fail("findings must be a JSON array")

    if verdict == "fail" and len(findings) == 0:
        _fail("verdict=fail requires at least one finding")

    # Validate individual finding objects.
    for idx, finding in enumerate(findings):
        if not isinstance(finding, dict):
            _fail(f"findings[{idx}] must be a JSON object")
        if "kind" not in finding:
            _fail(f"findings[{idx}] missing required field 'kind'")
        kind = finding["kind"]
        if kind not in _VALID_FINDING_KINDS:
            _fail(
                f"findings[{idx}].kind must be one of "
                f"{sorted(_VALID_FINDING_KINDS)}, got {kind!r}"
            )
        for str_field in ("paper_id", "locator", "detail"):
            if str_field in finding and not isinstance(finding[str_field], str):
                _fail(
                    f"findings[{idx}].{str_field} must be a string"
                )

    # Validate hash fields.
    for hash_field in ("synthesis_sha256", "reviewer_prompt_sha256"):
        value = payload[hash_field]
        if not isinstance(value, str):
            _fail(f"{hash_field!r} must be a string")
        if not SHA256_SIG_RE.fullmatch(value):
            _fail(
                f"{hash_field!r} must match 'sha256:<64 lowercase hex>', "
                f"got {value!r}"
            )

    return payload
