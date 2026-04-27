"""v0.4 Layer A — per-review phase status artifact.

Implements the `phase-state.json` contract described in §6.1–§6.2 of the
v0.4 implementation plan. The artifact lives at
``<review>/.scriptorium/phase-state.json`` (the filename uses a hyphen;
this module uses an underscore).

Schema (§6.1)::

    {
      "version": "0.4.0",
      "phases": {
        "<phase>": {
          "status": "pending"|"running"|"complete"|"failed"|"overridden",
          "artifact_path": str | None,
          "verified_at":  "<UTC Z>" | None,
          "verifier_signature": "sha256:<hex>" | None,
          "override": {"reason": str, "actor": str, "ts": "<UTC Z>"} | None
        }, ...
      }
    }

Rules:

* ``complete`` requires both ``verified_at`` and ``verifier_signature``.
* If the protected artifact's contents change after verification, the next
  ``read()`` downgrades that phase from ``complete`` back to ``running``
  and clears ``verified_at`` / ``verifier_signature``. The artifact path
  is preserved so the caller knows what to re-verify.
* ``overridden`` requires ``override.reason`` and ``override.ts``.
* An unknown future ``version`` raises ``E_PHASE_STATE_VERSION_NEWER``.
* A malformed file raises ``E_PHASE_STATE_CORRUPT``.

Read-on-missing: ``read()`` silently calls ``init()`` when the artifact
does not yet exist. Green-field reviews (T03) are the common case;
legacy v0.3 migration (T05) is layered on top.

Concurrency: writes acquire the per-review lock and use a temp file plus
``os.replace`` so a partial JSON document is never visible.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from scriptorium.errors import ScriptoriumError
from scriptorium.lock import ReviewLock, ReviewLockHeld
from scriptorium.paths import ReviewPaths


SCHEMA_VERSION = "0.4.0"

# I3: a verifier_signature must look exactly like ``sha256:<64 lowercase hex>``.
# Truthy garbage like ``"abc"`` would otherwise persist to disk and force
# perpetual silent downgrades on every read.
SHA256_SIG_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

# I1: every per-phase entry must contain exactly these five keys. Anything
# else means a hand-edited or otherwise corrupted artifact, which we surface
# as ``E_PHASE_STATE_CORRUPT`` rather than letting it crash deep in the
# invalidation loop.
_REQUIRED_ENTRY_KEYS: frozenset[str] = frozenset(
    {"status", "artifact_path", "verified_at", "verifier_signature", "override"}
)

PhaseName = Literal[
    "scoping",
    "search",
    "screening",
    "extraction",
    "synthesis",
    "contradiction",
    "audit",
]
PHASES: tuple[str, ...] = (
    "scoping",
    "search",
    "screening",
    "extraction",
    "synthesis",
    "contradiction",
    "audit",
)
_ALLOWED_PHASES = frozenset(PHASES)

PhaseStatus = Literal["pending", "running", "complete", "failed", "overridden"]
_ALLOWED_STATUSES = frozenset(
    {"pending", "running", "complete", "failed", "overridden"}
)


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------


def _utc_z_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _empty_entry() -> dict[str, Any]:
    return {
        "status": "pending",
        "artifact_path": None,
        "verified_at": None,
        "verifier_signature": None,
        "override": None,
    }


def _empty_state() -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "phases": {name: _empty_entry() for name in PHASES},
    }


def _check_phase(phase: str) -> None:
    if phase not in _ALLOWED_PHASES:
        raise ScriptoriumError(
            f"unknown phase {phase!r}; allowed: {sorted(_ALLOWED_PHASES)}",
            symbol="E_PHASE_STATE_INVALID",
        )


def _check_status(status: str) -> None:
    if status not in _ALLOWED_STATUSES:
        raise ScriptoriumError(
            f"unknown status {status!r}; allowed: {sorted(_ALLOWED_STATUSES)}",
            symbol="E_PHASE_STATE_INVALID",
        )


def _compare_versions(actual: str, expected: str) -> int:
    """Return -1 if actual<expected, 0 equal, +1 if actual>expected.

    Tolerates non-semver suffixes by comparing leading int components.
    """
    def parts(v: str) -> list[int]:
        out: list[int] = []
        for chunk in v.split("."):
            digits = ""
            for ch in chunk:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            out.append(int(digits) if digits else 0)
        return out

    a, b = parts(actual), parts(expected)
    # Pad to equal length.
    while len(a) < len(b):
        a.append(0)
    while len(b) < len(a):
        b.append(0)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def _validate_loaded(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise ScriptoriumError(
            "phase-state.json root is not a JSON object",
            symbol="E_PHASE_STATE_CORRUPT",
        )
    version = state.get("version")
    if not isinstance(version, str):
        raise ScriptoriumError(
            "phase-state.json missing string `version`",
            symbol="E_PHASE_STATE_CORRUPT",
        )
    if _compare_versions(version, SCHEMA_VERSION) > 0:
        raise ScriptoriumError(
            f"phase-state.json version {version!r} is newer than this "
            f"Scriptorium ({SCHEMA_VERSION}); upgrade Scriptorium to read it.",
            symbol="E_PHASE_STATE_VERSION_NEWER",
        )
    phases = state.get("phases")
    if not isinstance(phases, dict):
        raise ScriptoriumError(
            "phase-state.json `phases` is not an object",
            symbol="E_PHASE_STATE_CORRUPT",
        )
    # I1: validate per-entry shape. Without this, malformed entries (None,
    # str, dict missing keys) crash later inside _maybe_invalidate_signatures
    # with AttributeError instead of the documented E_PHASE_STATE_CORRUPT.
    for name, entry in phases.items():
        if not isinstance(entry, dict):
            raise ScriptoriumError(
                f"phase-state.json `phases[{name!r}]` is not an object",
                symbol="E_PHASE_STATE_CORRUPT",
            )
        missing = _REQUIRED_ENTRY_KEYS - entry.keys()
        if missing:
            raise ScriptoriumError(
                f"phase-state.json `phases[{name!r}]` missing required "
                f"keys: {sorted(missing)}",
                symbol="E_PHASE_STATE_CORRUPT",
            )
    return state


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` to ``path`` atomically.

    The temp file is sibling to the target so ``os.replace`` is a same-FS
    rename. ``fsync`` ensures the bytes hit disk before the rename so a
    crash mid-write does not leave a half-flushed final file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)


def _load_raw(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ScriptoriumError(
            f"phase-state.json is not valid JSON: {e.msg}",
            symbol="E_PHASE_STATE_CORRUPT",
        ) from e
    return _validate_loaded(data)


def _maybe_invalidate_signatures(
    state: dict[str, Any], paths: ReviewPaths
) -> tuple[dict[str, Any], bool]:
    """Downgrade complete→running for any phase whose protected artifact
    has changed since verification. Returns (new_state, mutated_flag).
    """
    mutated = False
    for name in PHASES:
        entry = state["phases"].get(name)
        if not entry:
            continue
        # I1 (defensive): _validate_loaded should have already rejected
        # non-dict entries. This guard makes the loop robust if someone
        # constructs a state dict in-memory without going through load.
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "complete":
            continue
        artifact_path = entry.get("artifact_path")
        recorded_sig = entry.get("verifier_signature")
        if not artifact_path or not recorded_sig:
            # Inconsistent on disk; skip — set_phase rejects this shape on
            # write, and we don't mutate someone else's hand-edited file.
            continue
        try:
            current_sig = verifier_signature_for(Path(artifact_path))
        except FileNotFoundError:
            current_sig = None
        if current_sig != recorded_sig:
            entry["status"] = "running"
            entry["verified_at"] = None
            entry["verifier_signature"] = None
            # artifact_path is preserved so the caller can re-verify.
            mutated = True
    return state, mutated


# ----------------------------------------------------------------------------
# public API (§6.2 signatures)
# ----------------------------------------------------------------------------


def init(paths: ReviewPaths) -> dict[str, Any]:
    """Create ``phase-state.json`` with all 7 phases in ``pending`` state.

    Overwrites any existing file — callers should use :func:`read` to load
    an existing artifact. The write is atomic and serialized by the
    review lock.
    """
    state = _empty_state()
    with ReviewLock(paths.lock):
        _atomic_write(paths.phase_state, state)
    return state


def read(paths: ReviewPaths) -> dict[str, Any]:
    """Load and return the phase state.

    If the artifact does not yet exist, this calls :func:`init` and
    returns the fresh state (green-field default for T03; T05 migration
    is responsible for backfilling legacy reviews with richer content).

    On every read, any phase whose recorded ``verifier_signature`` no
    longer matches the on-disk artifact is downgraded from ``complete``
    to ``running`` and the verification fields are cleared. That
    downgrade is persisted so subsequent readers see the same state.
    """
    if not paths.phase_state.exists():
        return init(paths)
    state = _load_raw(paths.phase_state)
    state, mutated = _maybe_invalidate_signatures(state, paths)
    if mutated:
        # I5: ``read()`` is a logical read — it must not raise on writer
        # contention. The in-memory invalidation is correct regardless;
        # the next reader will re-derive it from the artifact bytes if we
        # couldn't persist the downgrade now.
        try:
            with ReviewLock(paths.lock):
                _atomic_write(paths.phase_state, state)
        except ReviewLockHeld:
            pass
    return state


def set_phase(
    paths: ReviewPaths,
    phase: str,
    status: str,
    *,
    artifact_path: str | None = None,
    verifier_signature: str | None = None,
    verified_at: str | None = None,
) -> dict[str, Any]:
    """Update a phase entry and return the new full state.

    Rules enforced here:
        * ``phase`` must be one of :data:`PHASES`.
        * ``status`` must be one of the allowed statuses.
        * ``status="complete"`` requires ``verifier_signature`` (and we'll
          fill ``verified_at`` with a UTC ``Z`` timestamp if the caller
          omits it). Both fields are then non-null on disk.
        * Verification fields are cleared for non-complete statuses unless
          the caller passes them explicitly.
    """
    _check_phase(phase)
    _check_status(status)

    if status == "complete":
        if not verifier_signature:
            raise ScriptoriumError(
                f"phase {phase!r} cannot be `complete` without "
                "`verifier_signature`",
                symbol="E_PHASE_STATE_INVALID",
            )
        # I3: enforce the documented signature shape. Without this, garbage
        # like "abc" persists to disk and forces perpetual silent downgrades
        # because the artifact's real sha256 will never match.
        if not SHA256_SIG_RE.fullmatch(verifier_signature):
            raise ScriptoriumError(
                "verifier_signature must match 'sha256:<64 lowercase hex>', "
                f"got {verifier_signature!r}",
                symbol="E_PHASE_STATE_INVALID",
            )
        if verified_at is None:
            verified_at = _utc_z_now()
    elif status == "overridden":
        # `overridden` is set via override_phase(); reject the shortcut so
        # callers don't accidentally bypass the reason/ts contract.
        raise ScriptoriumError(
            "use override_phase() to set status=`overridden`",
            symbol="E_PHASE_STATE_INVALID",
        )

    with ReviewLock(paths.lock):
        if paths.phase_state.exists():
            state = _load_raw(paths.phase_state)
        else:
            state = _empty_state()

        entry = state["phases"].setdefault(phase, _empty_entry())
        entry["status"] = status
        if artifact_path is not None:
            # I4: resolve relative paths against the review root at write
            # time so the on-disk value is always absolute. Otherwise the
            # read-time invalidation check resolves the path against the
            # *reader's* cwd, which spuriously downgrades any phase whose
            # state was read from a different cwd than it was written from.
            ap = Path(artifact_path)
            if not ap.is_absolute():
                ap = (paths.root / ap).resolve()
            entry["artifact_path"] = str(ap)
        if status == "complete":
            entry["verified_at"] = verified_at
            entry["verifier_signature"] = verifier_signature
        else:
            # Non-complete statuses do not carry verification metadata.
            # Callers can override by passing the fields explicitly.
            entry["verified_at"] = verified_at if verified_at is not None else None
            entry["verifier_signature"] = (
                verifier_signature if verifier_signature is not None else None
            )

        _atomic_write(paths.phase_state, state)
    return state


def override_phase(
    paths: ReviewPaths,
    phase: str,
    *,
    reason: str,
    actor: str,
    ts: str | None = None,
) -> dict[str, Any]:
    """Mark ``phase`` as ``overridden`` with a justification record."""
    _check_phase(phase)
    if not reason:
        raise ScriptoriumError(
            "override requires a non-empty `reason`",
            symbol="E_PHASE_STATE_INVALID",
        )
    if not actor:
        raise ScriptoriumError(
            "override requires a non-empty `actor`",
            symbol="E_PHASE_STATE_INVALID",
        )
    if ts is None:
        ts = _utc_z_now()

    with ReviewLock(paths.lock):
        if paths.phase_state.exists():
            state = _load_raw(paths.phase_state)
        else:
            state = _empty_state()
        entry = state["phases"].setdefault(phase, _empty_entry())
        entry["status"] = "overridden"
        entry["override"] = {"reason": reason, "actor": actor, "ts": ts}
        # I2: an `overridden` phase has not been *verified* — clear stale
        # verification metadata so the entry doesn't falsely advertise
        # "we verified this AND overrode it." `artifact_path` is preserved
        # so downstream tooling knows what the override applied to.
        entry["verifier_signature"] = None
        entry["verified_at"] = None
        _atomic_write(paths.phase_state, state)
    return state


def verifier_signature_for(path: Path) -> str:
    """Return ``"sha256:<hex>"`` of ``path``'s bytes.

    Raises :class:`FileNotFoundError` if the file does not exist — callers
    must guard against that explicitly so a missing artifact does not
    silently produce a sentinel signature.
    """
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return f"sha256:{digest}"
