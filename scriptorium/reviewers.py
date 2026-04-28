"""Reviewer output validation and synthesis-exit gate for Scriptorium v0.4.

T04 introduced :func:`validate_reviewer_output` (§6.3 schema). T14 extends
this module with the synthesis-exit gate:

* :func:`append_reviewer_output` — write one auditable row per reviewer
  invocation.
* :func:`finalize_synthesis_phase` — aggregate cite + contradiction
  verdicts and promote ``phases.synthesis`` to ``complete`` only when
  both verdicts are ``pass``.

The Claude Code agent prompts that produce these payloads live at
``agents/lit-cite-reviewer.md`` and ``agents/lit-contradiction-reviewer.md``.
T15 owns the Cowork branch.

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

import copy
from typing import Any

from scriptorium.errors import ScriptoriumError
from scriptorium.paths import ReviewPaths
from scriptorium.phase_state import (
    SHA256_SIG_RE,
    set_phase,
    verifier_signature_for,
)
from scriptorium.storage.audit import AuditEntry, append_audit


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


# ---------------------------------------------------------------------------
# T14 — synthesis-exit gate
# ---------------------------------------------------------------------------


# Verdict → audit-status mapping (§6.3 + audit AuditStatus enum).
# pass → success, fail → failure, skipped → skipped. The skipped row is the
# only audit row that itself signals "not run"; we want it to remain visible
# rather than collapse into a generic warning.
_VERDICT_TO_AUDIT_STATUS: dict[str, str] = {
    "pass": "success",
    "fail": "failure",
    "skipped": "skipped",
}


def append_reviewer_output(
    paths: ReviewPaths, payload: dict[str, Any]
) -> None:
    """Validate and append one reviewer output row to the audit log.

    Writes a single ``AuditEntry`` to ``audit.jsonl`` with:

      * ``phase = "synthesis"`` — the synthesis-exit gate is part of the
        synthesis phase end-state.
      * ``action = "reviewer.<reviewer>"`` — ``reviewer.cite`` or
        ``reviewer.contradiction``.
      * ``status`` mapped from ``payload["verdict"]`` via
        :data:`_VERDICT_TO_AUDIT_STATUS`.
      * ``details`` = the full validated payload (preserves verdict,
        summary, findings, hashes, runtime, timestamp).

    The full payload in ``details`` means an auditor can reconstruct the
    reviewer's exact verdict from ``audit.jsonl`` alone — no separate
    artifact file is needed. Validation runs first, so a malformed
    payload fails-fast with ``E_REVIEWER_INVALID`` and never reaches the
    audit writer.
    """
    validated = validate_reviewer_output(payload)
    reviewer = validated["reviewer"]
    verdict = validated["verdict"]
    entry = AuditEntry(
        phase="synthesis",
        action=f"reviewer.{reviewer}",
        status=_VERDICT_TO_AUDIT_STATUS[verdict],
        # deepcopy so a later caller mutating their payload object can't
        # retroactively rewrite the audit row in memory.
        details=copy.deepcopy(validated),
    )
    append_audit(paths, entry)


def finalize_synthesis_phase(
    paths: ReviewPaths,
    *,
    cite_result: dict[str, Any],
    contradiction_result: dict[str, Any],
) -> dict[str, Any]:
    """Aggregate the two reviewer verdicts and update ``phases.synthesis``.

    Steps (in order):

      1. Validate both payloads. If either is malformed, raise
         ``E_REVIEWER_INVALID`` BEFORE writing any audit row or
         mutating phase-state.
      2. Pin the slot/reviewer-name contract: ``cite_result`` must carry
         ``reviewer="cite"``; ``contradiction_result`` must carry
         ``reviewer="contradiction"``.
      3. Append two reviewer audit rows (cite first, then contradiction).
      4. Decide aggregate verdict:
           - ``synthesis_status = "complete"`` IFF both verdicts are
             ``pass``;
           - else ``synthesis_status = "running"`` (recoverable — the
             user re-drafts and re-reviews; we don't burn ``failed``
             on reviewer-fail).
      5. If ``complete``: require ``synthesis.md`` to exist (else raise
         ``E_REVIEWER_ARTIFACT_MISSING``); compute its sha256; promote
         the phase via :func:`phase_state.set_phase`.
         If ``running``: clear ``synthesis`` to running with no
         signature.
      6. Append a ``synthesis.gate`` audit row summarizing the
         aggregation.

    Returns a stable dict::

        {
          "synthesis_status": "complete" | "running",
          "phase_state": <full phase-state dict>,
          "cite_verdict": "pass" | "fail" | "skipped",
          "contradiction_verdict": "pass" | "fail" | "skipped",
        }
    """
    # Step 1 — validate fail-fast.
    cite_validated = validate_reviewer_output(cite_result)
    contra_validated = validate_reviewer_output(contradiction_result)

    # Step 2 — slot/reviewer-name contract.
    if cite_validated["reviewer"] != "cite":
        raise ScriptoriumError(
            "cite_result must carry reviewer='cite', got "
            f"{cite_validated['reviewer']!r}",
            symbol="E_REVIEWER_INVALID",
        )
    if contra_validated["reviewer"] != "contradiction":
        raise ScriptoriumError(
            "contradiction_result must carry reviewer='contradiction', got "
            f"{contra_validated['reviewer']!r}",
            symbol="E_REVIEWER_INVALID",
        )

    # Step 3 — reviewer audit rows.
    append_reviewer_output(paths, cite_validated)
    append_reviewer_output(paths, contra_validated)

    cite_verdict = cite_validated["verdict"]
    contra_verdict = contra_validated["verdict"]

    # Step 4 — aggregate verdict.
    both_pass = cite_verdict == "pass" and contra_verdict == "pass"
    synthesis_status = "complete" if both_pass else "running"

    # Step 5 — phase-state mutation.
    if synthesis_status == "complete":
        synthesis_path = paths.synthesis
        if not synthesis_path.exists():
            raise ScriptoriumError(
                f"cannot mark synthesis complete: artifact missing at "
                f"{synthesis_path}",
                symbol="E_REVIEWER_ARTIFACT_MISSING",
            )
        sig = verifier_signature_for(synthesis_path)
        state = set_phase(
            paths,
            "synthesis",
            "complete",
            artifact_path=str(synthesis_path),
            verifier_signature=sig,
        )
    else:
        state = set_phase(paths, "synthesis", "running")

    # Step 6 — gate audit row.
    gate_status = "success" if synthesis_status == "complete" else "warning"
    append_audit(
        paths,
        AuditEntry(
            phase="synthesis",
            action="synthesis.gate",
            status=gate_status,
            details={
                "cite_verdict": cite_verdict,
                "contradiction_verdict": contra_verdict,
                "result": synthesis_status,
            },
        ),
    )

    return {
        "synthesis_status": synthesis_status,
        "phase_state": state,
        "cite_verdict": cite_verdict,
        "contradiction_verdict": contra_verdict,
    }
