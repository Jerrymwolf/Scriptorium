"""Layer A / T03: phase-state.json contract.

Covers schema, transitions, future-version rejection, signature
invalidation, atomic writes, and override semantics per plan §6.1–§6.2.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from scriptorium import phase_state
from scriptorium.errors import ScriptoriumError
from scriptorium.lock import ReviewLockHeld
from scriptorium.paths import ReviewPaths


CANONICAL_PHASES = [
    "scoping",
    "search",
    "screening",
    "extraction",
    "synthesis",
    "contradiction",
    "audit",
]


# --- ReviewPaths wiring ----------------------------------------------------


def test_review_paths_phase_state_property(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    assert paths.phase_state == review_dir / ".scriptorium" / "phase-state.json"


# --- init / read round-trip ------------------------------------------------


def test_init_creates_file_with_all_seven_phases_pending(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    state = phase_state.init(paths)

    assert paths.phase_state.exists()
    assert state["version"] == "0.4.0"
    assert set(state["phases"].keys()) == set(CANONICAL_PHASES)
    for name in CANONICAL_PHASES:
        entry = state["phases"][name]
        assert entry["status"] == "pending"
        assert entry["artifact_path"] is None
        assert entry["verified_at"] is None
        assert entry["verifier_signature"] is None
        assert entry["override"] is None


def test_read_round_trips_after_init(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    written = phase_state.init(paths)
    read_back = phase_state.read(paths)
    assert read_back == written


def test_read_on_missing_file_auto_inits(review_dir: Path) -> None:
    """`read()` on an absent file silently initializes (documented behavior)."""
    paths = ReviewPaths(root=review_dir)
    assert not paths.phase_state.exists()
    state = phase_state.read(paths)
    assert paths.phase_state.exists()
    assert set(state["phases"].keys()) == set(CANONICAL_PHASES)


# --- set_phase basic semantics ---------------------------------------------


def test_set_phase_running_no_signature_required(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)
    state = phase_state.set_phase(paths, "scoping", "running")
    assert state["phases"]["scoping"]["status"] == "running"
    assert state["phases"]["scoping"]["verified_at"] is None
    assert state["phases"]["scoping"]["verifier_signature"] is None


def test_set_phase_complete_requires_signature_and_verified_at(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)
    artifact = review_dir / "scope.json"
    artifact.write_text("{}", encoding="utf-8")
    sig = phase_state.verifier_signature_for(artifact)

    # Both fields supplied → complete works.
    state = phase_state.set_phase(
        paths,
        "scoping",
        "complete",
        artifact_path=str(artifact),
        verifier_signature=sig,
        verified_at="2026-04-26T00:00:00Z",
    )
    assert state["phases"]["scoping"]["status"] == "complete"
    assert state["phases"]["scoping"]["verifier_signature"] == sig
    assert state["phases"]["scoping"]["verified_at"] == "2026-04-26T00:00:00Z"
    assert state["phases"]["scoping"]["artifact_path"] == str(artifact)


def test_set_phase_complete_without_signature_raises(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)
    with pytest.raises(ScriptoriumError) as excinfo:
        phase_state.set_phase(paths, "scoping", "complete", verified_at="2026-04-26T00:00:00Z")
    assert excinfo.value.symbol == "E_PHASE_STATE_INVALID"


def test_set_phase_complete_default_verified_at_used_when_signature_present(
    review_dir: Path,
) -> None:
    """When verifier_signature is supplied but verified_at is None, the helper
    fills in a UTC `Z` timestamp so callers don't need to compute it. The
    on-disk artifact ends up with both fields non-null per §6.1."""
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)
    valid_sig = "sha256:" + "a" * 64
    state = phase_state.set_phase(
        paths, "scoping", "complete", verifier_signature=valid_sig
    )
    ts = state["phases"]["scoping"]["verified_at"]
    assert ts is not None and ts.endswith("Z")
    assert state["phases"]["scoping"]["verifier_signature"] == valid_sig


def test_set_phase_unknown_phase_raises(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)
    with pytest.raises(ScriptoriumError) as excinfo:
        phase_state.set_phase(paths, "not-a-phase", "running")
    assert excinfo.value.symbol == "E_PHASE_STATE_INVALID"


def test_set_phase_unknown_status_raises(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)
    with pytest.raises(ScriptoriumError) as excinfo:
        phase_state.set_phase(paths, "scoping", "bogus")
    assert excinfo.value.symbol == "E_PHASE_STATE_INVALID"


# --- override semantics ----------------------------------------------------


def test_override_phase_writes_reason_and_ts(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)
    state = phase_state.override_phase(
        paths, "screening", reason="manual sign-off", actor="jerry"
    )
    entry = state["phases"]["screening"]
    assert entry["status"] == "overridden"
    assert entry["override"]["reason"] == "manual sign-off"
    assert entry["override"]["actor"] == "jerry"
    assert entry["override"]["ts"].endswith("Z")


def test_override_phase_accepts_explicit_ts(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)
    state = phase_state.override_phase(
        paths, "screening", reason="x", actor="jerry", ts="2026-01-01T00:00:00Z"
    )
    assert state["phases"]["screening"]["override"]["ts"] == "2026-01-01T00:00:00Z"


def test_override_phase_unknown_phase_raises(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)
    with pytest.raises(ScriptoriumError) as excinfo:
        phase_state.override_phase(paths, "not-a-phase", reason="x", actor="y")
    assert excinfo.value.symbol == "E_PHASE_STATE_INVALID"


# --- future-version rejection ----------------------------------------------


def test_future_version_raises(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)
    bad = json.loads(paths.phase_state.read_text(encoding="utf-8"))
    bad["version"] = "0.5.0"
    paths.phase_state.write_text(
        json.dumps(bad, ensure_ascii=False), encoding="utf-8"
    )
    with pytest.raises(ScriptoriumError) as excinfo:
        phase_state.read(paths)
    assert excinfo.value.symbol == "E_PHASE_STATE_VERSION_NEWER"


def test_corrupt_file_raises(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    paths.phase_state.parent.mkdir(parents=True, exist_ok=True)
    paths.phase_state.write_text("not json {", encoding="utf-8")
    with pytest.raises(ScriptoriumError) as excinfo:
        phase_state.read(paths)
    assert excinfo.value.symbol == "E_PHASE_STATE_CORRUPT"


# --- verifier_signature_for ------------------------------------------------


def test_verifier_signature_for_returns_sha256_format(tmp_path: Path) -> None:
    f = tmp_path / "x.md"
    f.write_text("hello", encoding="utf-8")
    sig = phase_state.verifier_signature_for(f)
    assert sig.startswith("sha256:")
    # SHA-256 hex is 64 chars.
    assert len(sig.split(":", 1)[1]) == 64


def test_verifier_signature_for_changes_with_content(tmp_path: Path) -> None:
    f = tmp_path / "x.md"
    f.write_text("hello", encoding="utf-8")
    sig1 = phase_state.verifier_signature_for(f)
    f.write_text("hello world", encoding="utf-8")
    sig2 = phase_state.verifier_signature_for(f)
    assert sig1 != sig2


def test_verifier_signature_for_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        phase_state.verifier_signature_for(tmp_path / "missing.md")


# --- signature invalidation ------------------------------------------------


def test_artifact_mutation_downgrades_complete_to_running(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)

    artifact = review_dir / "synthesis.md"
    artifact.write_text("# v1\n", encoding="utf-8")
    sig = phase_state.verifier_signature_for(artifact)

    phase_state.set_phase(
        paths,
        "synthesis",
        "complete",
        artifact_path=str(artifact),
        verifier_signature=sig,
        verified_at="2026-04-26T00:00:00Z",
    )

    # Mutate the artifact after verification.
    artifact.write_text("# v2\n", encoding="utf-8")

    state = phase_state.read(paths)
    entry = state["phases"]["synthesis"]
    assert entry["status"] == "running"
    assert entry["verified_at"] is None
    assert entry["verifier_signature"] is None
    # artifact_path should be retained so callers know which file to re-verify.
    assert entry["artifact_path"] == str(artifact)


def test_unchanged_artifact_keeps_complete(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)

    artifact = review_dir / "synthesis.md"
    artifact.write_text("# v1\n", encoding="utf-8")
    sig = phase_state.verifier_signature_for(artifact)
    phase_state.set_phase(
        paths,
        "synthesis",
        "complete",
        artifact_path=str(artifact),
        verifier_signature=sig,
        verified_at="2026-04-26T00:00:00Z",
    )
    state = phase_state.read(paths)
    assert state["phases"]["synthesis"]["status"] == "complete"
    assert state["phases"]["synthesis"]["verifier_signature"] == sig


def test_artifact_deleted_downgrades_complete_to_running(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)

    artifact = review_dir / "synthesis.md"
    artifact.write_text("# v1\n", encoding="utf-8")
    sig = phase_state.verifier_signature_for(artifact)
    phase_state.set_phase(
        paths,
        "synthesis",
        "complete",
        artifact_path=str(artifact),
        verifier_signature=sig,
        verified_at="2026-04-26T00:00:00Z",
    )

    artifact.unlink()
    state = phase_state.read(paths)
    assert state["phases"]["synthesis"]["status"] == "running"
    assert state["phases"]["synthesis"]["verifier_signature"] is None


# --- atomic / lock behavior ------------------------------------------------


def test_concurrent_writes_never_produce_partial_json(review_dir: Path) -> None:
    """Hammer set_phase from multiple threads; the file must always be valid
    JSON when re-read between writes."""
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)

    errors: list[Exception] = []

    def writer(phase: str, status: str) -> None:
        try:
            for _ in range(20):
                try:
                    phase_state.set_phase(paths, phase, status)
                except (ScriptoriumError, ReviewLockHeld):
                    # Lock contention is expected; we only care that no torn
                    # JSON is produced.
                    pass
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [
        threading.Thread(target=writer, args=("scoping", "running")),
        threading.Thread(target=writer, args=("search", "running")),
        threading.Thread(target=writer, args=("screening", "running")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    # File must always parse, even after the storm.
    parsed = json.loads(paths.phase_state.read_text(encoding="utf-8"))
    assert parsed["version"] == "0.4.0"
    assert set(parsed["phases"].keys()) == set(CANONICAL_PHASES)


def test_no_tmp_file_left_behind_after_set_phase(review_dir: Path) -> None:
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)
    phase_state.set_phase(paths, "scoping", "running")
    leftovers = list(paths.scriptorium_dir.glob("phase-state.json.tmp*"))
    assert leftovers == []


# --- storage re-export -----------------------------------------------------


def test_phase_state_reexported_from_storage() -> None:
    from scriptorium.storage import phase_state as ps_via_storage

    assert ps_via_storage is phase_state


# --- code-review fixes (I1–I5) ---------------------------------------------


def test_corrupt_phase_entry_raises_e_phase_state_corrupt(review_dir: Path) -> None:
    """I1: malformed per-phase entries (None, str, dict missing keys) must
    surface as ``E_PHASE_STATE_CORRUPT`` from ``read()``, not crash deep in
    the invalidation loop with ``AttributeError``.
    """
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)

    # Case A: phase value is None.
    raw = json.loads(paths.phase_state.read_text(encoding="utf-8"))
    raw["phases"]["scoping"] = None
    paths.phase_state.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ScriptoriumError) as excinfo:
        phase_state.read(paths)
    assert excinfo.value.symbol == "E_PHASE_STATE_CORRUPT"

    # Case B: phase value is a string.
    raw = json.loads(paths.phase_state.read_text(encoding="utf-8"))
    raw["phases"]["scoping"] = "not-a-dict"
    paths.phase_state.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ScriptoriumError) as excinfo:
        phase_state.read(paths)
    assert excinfo.value.symbol == "E_PHASE_STATE_CORRUPT"

    # Case C: phase value is a dict but missing one of the five required keys.
    raw = json.loads(paths.phase_state.read_text(encoding="utf-8"))
    raw["phases"]["scoping"] = {
        "status": "pending",
        "artifact_path": None,
        "verified_at": None,
        # missing "verifier_signature"
        "override": None,
    }
    paths.phase_state.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ScriptoriumError) as excinfo:
        phase_state.read(paths)
    assert excinfo.value.symbol == "E_PHASE_STATE_CORRUPT"


def test_override_clears_stale_verifier_signature(review_dir: Path) -> None:
    """I2: overriding a previously-`complete` phase must clear the stale
    ``verifier_signature`` and ``verified_at`` so the entry doesn't falsely
    advertise "verified AND overridden". ``artifact_path`` is preserved so
    downstream tooling knows what the override applied to.
    """
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)

    artifact = review_dir / "synthesis.md"
    artifact.write_text("# v1\n", encoding="utf-8")
    sig = phase_state.verifier_signature_for(artifact)
    phase_state.set_phase(
        paths,
        "synthesis",
        "complete",
        artifact_path=str(artifact),
        verifier_signature=sig,
        verified_at="2026-04-26T00:00:00Z",
    )

    phase_state.override_phase(
        paths, "synthesis", reason="manual sign-off", actor="jerry"
    )

    state = phase_state.read(paths)
    entry = state["phases"]["synthesis"]
    assert entry["status"] == "overridden"
    assert entry["verifier_signature"] is None
    assert entry["verified_at"] is None
    assert entry["override"]["reason"] == "manual sign-off"
    assert entry["override"]["actor"] == "jerry"
    # artifact_path preserved so downstream knows what was overridden.
    assert entry["artifact_path"] == str(artifact)


def test_set_phase_complete_rejects_malformed_signature(review_dir: Path) -> None:
    """I3: ``set_phase(..., complete, verifier_signature=...)`` must reject
    anything that isn't ``sha256:<64 lowercase hex>``. Truthy garbage like
    ``"abc"`` would persist to disk and force perpetual silent downgrades.
    """
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)

    bad_sigs = [
        "abc",
        "sha256:short",
        "SHA256:" + "a" * 64,  # uppercase prefix
        "sha256:" + "g" * 64,  # non-hex char
    ]
    for bad in bad_sigs:
        with pytest.raises(ScriptoriumError) as excinfo:
            phase_state.set_phase(
                paths,
                "scoping",
                "complete",
                verifier_signature=bad,
            )
        assert excinfo.value.symbol == "E_PHASE_STATE_INVALID", (
            f"signature {bad!r} should have raised E_PHASE_STATE_INVALID, "
            f"got symbol={excinfo.value.symbol!r}"
        )


def test_relative_artifact_path_resolved_to_review_root(
    review_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """I4: a relative ``artifact_path`` passed to ``set_phase`` must be
    resolved against the review root at write time, so subsequent reads
    from a different cwd don't spuriously invalidate the signature.
    """
    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)

    artifact = paths.synthesis  # /<review>/synthesis.md
    artifact.write_text("# v1\n", encoding="utf-8")
    sig = phase_state.verifier_signature_for(artifact)

    # Caller passes a *relative* artifact_path — common footgun.
    phase_state.set_phase(
        paths,
        "synthesis",
        "complete",
        artifact_path="synthesis.md",
        verifier_signature=sig,
        verified_at="2026-04-26T00:00:00Z",
    )

    # Read from a *different* cwd. The invalidation check must operate
    # on the absolute path stored on disk, not resolve "synthesis.md"
    # against the reader's cwd.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    state = phase_state.read(paths)
    entry = state["phases"]["synthesis"]
    assert entry["status"] == "complete"  # NOT downgraded
    assert entry["artifact_path"] == str(paths.synthesis.resolve())


def test_read_does_not_raise_on_lock_contention(review_dir: Path) -> None:
    """I5: ``read()`` must tolerate ``ReviewLockHeld`` when the in-memory
    invalidation tries to persist itself. The downgraded state is correct
    in memory regardless; the next reader will re-derive it from the
    artifact bytes if the persistence write was skipped.
    """
    from scriptorium.lock import ReviewLock

    paths = ReviewPaths(root=review_dir)
    phase_state.init(paths)

    artifact = review_dir / "synthesis.md"
    artifact.write_text("# v1\n", encoding="utf-8")
    sig = phase_state.verifier_signature_for(artifact)
    phase_state.set_phase(
        paths,
        "synthesis",
        "complete",
        artifact_path=str(artifact),
        verifier_signature=sig,
        verified_at="2026-04-26T00:00:00Z",
    )

    # Mutate the artifact so read() will want to invalidate + persist.
    artifact.write_text("# v2 mutated\n", encoding="utf-8")

    # Hold the lock externally; read() must NOT raise ReviewLockHeld.
    with ReviewLock(paths.lock):
        state = phase_state.read(paths)

    entry = state["phases"]["synthesis"]
    assert entry["status"] == "running"  # in-memory invalidation still applied
    assert entry["verifier_signature"] is None
    assert entry["verified_at"] is None
