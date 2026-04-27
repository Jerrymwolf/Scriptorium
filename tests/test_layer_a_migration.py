"""Layer A / T05: enforce_v04 config flag and migration backfill of phase-state.

Covers §10 of the v0.4 implementation plan:

    * ``enforce_v04`` defaults to advisory behavior.
    * Legacy reviews missing ``phase-state.json`` still open.
    * ``migrate-review --to 0.4`` backfills the artifact from existing review
      state without mutating legacy artifacts.

Tests are deterministic and avoid mocking — fixtures build minimal legacy
review directories on tmp_path and exercise the real CLI surface.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from scriptorium import phase_state
from scriptorium.cli import main
from scriptorium.config import (
    Config,
    load_config,
    save_config_from_kv,
)
from scriptorium.paths import ReviewPaths
from scriptorium.storage.audit import load_audit


# ----------------------------------------------------------------------------
# Config defaults — enforce_v04 + extraction_parallel_cap
# ----------------------------------------------------------------------------


def test_config_defaults_enforce_v04_false() -> None:
    """§10: default in 0.4.0 is ``enforce_v04=False`` (advisory rollout)."""
    cfg = Config()
    assert cfg.enforce_v04 is False


def test_config_defaults_extraction_parallel_cap_is_four() -> None:
    """T12 reads ``extraction_parallel_cap``; T05 just plants a default of 4."""
    cfg = Config()
    assert cfg.extraction_parallel_cap == 4


def test_save_config_from_kv_round_trips_enforce_v04(tmp_path: Path) -> None:
    """``save_config_from_kv`` must coerce 'true' → True and persist."""
    path = tmp_path / "config.toml"
    save_config_from_kv(path, "enforce_v04", "true")
    cfg = load_config(path)
    assert cfg.enforce_v04 is True


def test_save_config_from_kv_round_trips_extraction_parallel_cap(
    tmp_path: Path,
) -> None:
    """``save_config_from_kv`` must coerce '8' → 8 (validates int support)."""
    path = tmp_path / "config.toml"
    save_config_from_kv(path, "extraction_parallel_cap", "8")
    cfg = load_config(path)
    assert cfg.extraction_parallel_cap == 8


def test_save_config_from_kv_rejects_non_int_for_parallel_cap(
    tmp_path: Path,
) -> None:
    """Coercion must raise ValueError on garbage values for int fields."""
    path = tmp_path / "config.toml"
    with pytest.raises(ValueError):
        save_config_from_kv(path, "extraction_parallel_cap", "not-an-int")


# ----------------------------------------------------------------------------
# Legacy-review fixture helper
# ----------------------------------------------------------------------------


def _legacy_review(
    tmp_path: Path,
    *,
    pre_migrated: bool = False,
) -> Path:
    """Build a minimal legacy review directory.

    ``pre_migrated=True`` writes already-converted citations (``[[id#p-N]]``)
    so the v0.3 legacy migration path becomes a no-op for that file. This
    keeps backfill-focused tests free from the orthogonal citation rewrite.
    """
    root = tmp_path / "reviews" / "legacy-topic"
    root.mkdir(parents=True)

    if pre_migrated:
        synthesis_text = "Caffeine helps WM [[nehlig2010#p-4]].\n"
    else:
        synthesis_text = "Caffeine helps WM [nehlig2010:page:4].\n"
    (root / "synthesis.md").write_text(synthesis_text, encoding="utf-8")

    (root / "contradictions.md").write_text("# Contradictions\n", encoding="utf-8")
    (root / "audit").mkdir(parents=True)
    (root / "audit" / "audit.md").write_text(
        "# PRISMA Audit Trail\n\n", encoding="utf-8"
    )
    (root / "data").mkdir(parents=True)
    (root / "data" / "evidence.jsonl").write_text(
        json.dumps(
            {
                "paper_id": "nehlig2010",
                "locator": "page:4",
                "claim": "helps",
                "quote": "helps",
                "direction": "positive",
                "concept": "wm",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return root


# ----------------------------------------------------------------------------
# Legacy review opens in advisory mode
# ----------------------------------------------------------------------------


def test_legacy_review_without_phase_state_loads_in_advisory_mode(
    tmp_path: Path,
) -> None:
    """§10: a review missing phase-state.json must still open. ``read()``
    auto-initialises (T03 contract) and returns 7 pending phases.
    """
    root = _legacy_review(tmp_path)
    paths = ReviewPaths(root=root)

    # No phase-state.json exists yet.
    assert not paths.phase_state.exists()

    state = phase_state.read(paths)
    assert state["version"] == "0.4.0"
    assert set(state["phases"].keys()) == {
        "scoping",
        "search",
        "screening",
        "extraction",
        "synthesis",
        "contradiction",
        "audit",
    }
    for entry in state["phases"].values():
        assert entry["status"] == "pending"


# ----------------------------------------------------------------------------
# migrate-review --to 0.4 backfill
# ----------------------------------------------------------------------------


def _run_migrate_to_04(root: Path, *, dry_run: bool = False) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    argv = ["migrate-review", str(root), "--to", "0.4", "--json"]
    if dry_run:
        argv.append("--dry-run")
    rc = main(argv, stdout=out, stderr=err)
    return rc, out.getvalue(), err.getvalue()


def test_backfill_creates_phase_state_with_running_for_present_artifacts(
    tmp_path: Path,
) -> None:
    """Real backfill: phases with a present-non-empty artifact become
    ``running`` (with ``artifact_path`` set); phases without an artifact
    stay ``pending``; no phase becomes ``complete``.
    """
    root = _legacy_review(tmp_path, pre_migrated=True)
    paths = ReviewPaths(root=root)

    rc, _out, err = _run_migrate_to_04(root, dry_run=False)
    assert rc == 0, f"expected rc=0, got {rc}; stderr={err!r}"
    assert paths.phase_state.exists()

    state = json.loads(paths.phase_state.read_text(encoding="utf-8"))
    phases = state["phases"]

    # Present-and-non-empty artifacts → running with absolute artifact_path.
    for phase, artifact in (
        ("extraction", paths.evidence),
        ("synthesis", paths.synthesis),
        ("contradiction", paths.contradictions),
        ("audit", paths.audit_md),
    ):
        entry = phases[phase]
        assert entry["status"] == "running", (
            f"{phase} should be running; got {entry['status']}"
        )
        assert entry["artifact_path"] == str(artifact), (
            f"{phase} artifact_path mismatch: {entry['artifact_path']!r} "
            f"vs {str(artifact)!r}"
        )

    # No scope.json or corpus.jsonl in the legacy fixture → still pending.
    assert phases["scoping"]["status"] == "pending"
    assert phases["scoping"]["artifact_path"] is None
    assert phases["search"]["status"] == "pending"
    assert phases["search"]["artifact_path"] is None

    # screening has no canonical artifact in v0.3 → always pending.
    assert phases["screening"]["status"] == "pending"

    # No phase is complete (no v0.4 verifier signature exists yet).
    for name, entry in phases.items():
        assert entry["status"] != "complete", f"{name} should not be complete"
        assert entry["verifier_signature"] is None
        assert entry["verified_at"] is None


def test_backfill_present_scope_and_corpus_marks_running(tmp_path: Path) -> None:
    """If scope.json and corpus.jsonl ARE present, backfill upgrades scoping
    and search to ``running`` too (artifact-presence test, not a fixture
    artefact).
    """
    root = _legacy_review(tmp_path, pre_migrated=True)
    paths = ReviewPaths(root=root)
    paths.scope.write_text(json.dumps({"q": "test"}), encoding="utf-8")
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.corpus.write_text('{"id": "p1"}\n', encoding="utf-8")

    rc, _out, _err = _run_migrate_to_04(root, dry_run=False)
    assert rc == 0
    state = json.loads(paths.phase_state.read_text(encoding="utf-8"))
    assert state["phases"]["scoping"]["status"] == "running"
    assert state["phases"]["scoping"]["artifact_path"] == str(paths.scope)
    assert state["phases"]["search"]["status"] == "running"
    assert state["phases"]["search"]["artifact_path"] == str(paths.corpus)


def test_backfill_skips_empty_artifacts(tmp_path: Path) -> None:
    """An artifact file that exists but is zero bytes must NOT trigger a
    pending → running upgrade.

    We use ``evidence.jsonl`` because the legacy migration's
    ``_ensure_frontmatter`` deliberately rewrites synthesis/contradictions/
    audit, making them non-empty by the time backfill runs. ``evidence.jsonl``
    is not touched by legacy migration, so an empty file stays empty —
    a clean test of the size-based skip rule.
    """
    root = _legacy_review(tmp_path, pre_migrated=True)
    paths = ReviewPaths(root=root)
    paths.evidence.write_text("", encoding="utf-8")  # empty
    assert paths.evidence.stat().st_size == 0

    rc, _out, _err = _run_migrate_to_04(root, dry_run=False)
    assert rc == 0
    state = json.loads(paths.phase_state.read_text(encoding="utf-8"))
    assert state["phases"]["extraction"]["status"] == "pending"
    assert state["phases"]["extraction"]["artifact_path"] is None


def test_backfill_is_idempotent(tmp_path: Path) -> None:
    """Running ``migrate-review --to 0.4`` twice produces no additional
    phase-state changes after the first run. We assert on byte equality
    of phase-state.json across the two runs.
    """
    root = _legacy_review(tmp_path, pre_migrated=True)
    paths = ReviewPaths(root=root)

    rc1, _out, _err = _run_migrate_to_04(root, dry_run=False)
    assert rc1 == 0
    first_bytes = paths.phase_state.read_bytes()

    rc2, _out, _err = _run_migrate_to_04(root, dry_run=False)
    assert rc2 == 0
    second_bytes = paths.phase_state.read_bytes()

    assert first_bytes == second_bytes, (
        "phase-state.json must not change between identical migration runs"
    )


def test_backfill_does_not_mutate_legacy_artifacts(tmp_path: Path) -> None:
    """The new v0.4 backfill code path must NOT rewrite legacy artifacts.

    The pre-existing v0.3 legacy migration intentionally rewrites citations
    and adds frontmatter; that's separate behavior we don't test here. To
    isolate the *backfill* code path, we run the legacy migration first
    (without ``--to``) to settle artifacts into their post-migration form,
    snapshot, then run ``--to 0.4`` (which goes through the legacy migrate
    again — now a no-op — plus the new backfill) and assert no further drift.
    """
    root = _legacy_review(tmp_path, pre_migrated=True)
    paths = ReviewPaths(root=root)

    # Run the legacy migration alone first.
    out, err = io.StringIO(), io.StringIO()
    rc = main(
        ["migrate-review", str(root), "--json"], stdout=out, stderr=err
    )
    assert rc == 0

    # Snapshot artifact contents AFTER the legacy migration has run.
    # NOTE: audit.md is intentionally excluded — backfill appends an audit
    # row to it (per §10's "must not break the audit trail" requirement),
    # so it is expected to grow. The "no mutation" rule applies to legacy
    # *data* artifacts (synthesis, contradictions, evidence), not the audit log.
    snapshots = {
        paths.synthesis: paths.synthesis.read_bytes(),
        paths.contradictions: paths.contradictions.read_bytes(),
        paths.evidence: paths.evidence.read_bytes(),
    }

    # Now run --to 0.4. Legacy migration is a no-op the second time;
    # only the backfill should run. Backfill must not mutate artifacts.
    rc, _out, _err = _run_migrate_to_04(root, dry_run=False)
    assert rc == 0

    for path, original in snapshots.items():
        assert path.read_bytes() == original, (
            f"{path.name} was mutated by migrate-review --to 0.4 backfill"
        )


def test_backfill_never_sets_complete(tmp_path: Path) -> None:
    """No phase has a verifier_signature after backfill — legacy reviews
    have no v0.4 signatures, so honest status is at most ``running``.
    """
    root = _legacy_review(tmp_path, pre_migrated=True)
    paths = ReviewPaths(root=root)

    # Add scope + corpus so most phases get upgraded — exercising the
    # "no upgrade to complete" rule across as many phases as possible.
    paths.scope.write_text("{}", encoding="utf-8")
    paths.corpus.write_text('{"id":"p1"}\n', encoding="utf-8")

    rc, _out, _err = _run_migrate_to_04(root, dry_run=False)
    assert rc == 0

    state = json.loads(paths.phase_state.read_text(encoding="utf-8"))
    for name, entry in state["phases"].items():
        assert entry["status"] != "complete", (
            f"{name} should not be complete after backfill"
        )
        assert entry["verifier_signature"] is None, (
            f"{name} must have no verifier_signature"
        )
        assert entry["verified_at"] is None, (
            f"{name} must have no verified_at"
        )


def test_dry_run_does_not_create_phase_state(tmp_path: Path) -> None:
    """--dry-run --to 0.4 must NOT write phase-state.json. The migration
    output should still report what would be backfilled — we surface that
    via ``warnings`` in the JSON payload.
    """
    root = _legacy_review(tmp_path, pre_migrated=True)
    paths = ReviewPaths(root=root)

    rc, out, _err = _run_migrate_to_04(root, dry_run=True)
    assert rc == 0
    assert not paths.phase_state.exists(), (
        "phase-state.json must not be created on --dry-run"
    )

    payload = json.loads(out)
    # Warnings should mention which phases would be backfilled.
    joined = " ".join(payload.get("warnings", []))
    # We expect at least the 4 phases the fixture has present artifacts for.
    for phase in ("extraction", "synthesis", "contradiction", "audit"):
        assert phase in joined, (
            f"dry-run warnings should mention {phase}; got {joined!r}"
        )


def test_legacy_path_without_to_does_not_create_phase_state(
    tmp_path: Path,
) -> None:
    """``migrate-review`` WITHOUT ``--to`` is the v0.3 legacy path and must
    NOT create phase-state.json — proves backfill is opt-in via --to 0.4.
    """
    root = _legacy_review(tmp_path)
    paths = ReviewPaths(root=root)

    out, err = io.StringIO(), io.StringIO()
    rc = main(
        ["migrate-review", str(root), "--json"], stdout=out, stderr=err
    )
    assert rc == 0
    assert not paths.phase_state.exists(), (
        "legacy migrate-review (no --to) must not create phase-state.json"
    )


def test_backfill_appends_audit_row(tmp_path: Path) -> None:
    """An audit row must be appended describing the backfill. This satisfies
    the verification gate's "legacy-review handling proven not to break the
    audit trail" requirement.
    """
    root = _legacy_review(tmp_path, pre_migrated=True)
    paths = ReviewPaths(root=root)

    rc, _out, _err = _run_migrate_to_04(root, dry_run=False)
    assert rc == 0

    rows = load_audit(paths)
    backfill_rows = [
        r for r in rows if r.action == "backfill-phase-state-v0.4"
    ]
    assert len(backfill_rows) == 1, (
        f"expected exactly one backfill audit row; got {len(backfill_rows)}"
    )
    row = backfill_rows[0]
    assert row.phase == "migration"
    assert row.status == "success"
    # Details should list which phases were upgraded.
    upgraded = row.details.get("upgraded_phases") or row.details.get(
        "phases_upgraded"
    )
    assert upgraded is not None, (
        f"audit details must list upgraded phases; got {row.details!r}"
    )
    assert "synthesis" in upgraded
    assert "extraction" in upgraded
    assert "contradiction" in upgraded
    assert "audit" in upgraded


def test_backfill_does_not_downgrade_existing_running_state(
    tmp_path: Path,
) -> None:
    """Idempotence rule: if phase-state.json already exists with a phase in
    a non-pending status (e.g. user marked running externally), backfill
    must not downgrade it. Only ``pending`` phases are eligible for upgrade.
    """
    root = _legacy_review(tmp_path, pre_migrated=True)
    paths = ReviewPaths(root=root)

    # Initialise phase-state and pre-mark synthesis as overridden (a manual
    # sign-off the user did before running migrate). This must survive the
    # backfill.
    phase_state.init(paths)
    phase_state.override_phase(
        paths, "synthesis", reason="manual sign-off", actor="jerry"
    )

    rc, _out, _err = _run_migrate_to_04(root, dry_run=False)
    assert rc == 0

    state = json.loads(paths.phase_state.read_text(encoding="utf-8"))
    assert state["phases"]["synthesis"]["status"] == "overridden"
    # Other phases should still get upgraded since they were pending.
    assert state["phases"]["extraction"]["status"] == "running"
