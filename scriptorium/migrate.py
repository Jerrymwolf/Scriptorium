"""Review migration (§10.1) plus v0.4 phase-state backfill (§10, T05)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scriptorium import phase_state
from scriptorium.errors import ScriptoriumError
from scriptorium.frontmatter import (
    ReviewArtifactFrontmatter, read_frontmatter, strip_frontmatter, write_frontmatter,
)
from scriptorium.lock import ReviewLock
from scriptorium.obsidian.queries import write_query_file
from scriptorium.paths import ReviewPaths
from scriptorium.storage.audit import AuditEntry, append_audit


_LEGACY = re.compile(r"\[([A-Za-z0-9_.\-]+):page:(\d+)\]")


@dataclass
class MigrationResult:
    changed_files: list[str]
    skipped_files: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "changed_files": self.changed_files,
            "skipped_files": self.skipped_files,
            "warnings": self.warnings,
        }


def _convert_legacy_citations(text: str) -> str:
    return _LEGACY.sub(lambda m: f"[[{m.group(1)}#p-{m.group(2)}]]", text)


def _has_frontmatter(text: str) -> bool:
    return text.startswith("---\n")


def _ensure_frontmatter(
    path: Path, *, review_id: str, review_type: str,
) -> bool:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if _has_frontmatter(text):
        return False
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    fm = ReviewArtifactFrontmatter(
        schema_version="scriptorium.review_file.v1",
        scriptorium_version="0.3.1",
        review_id=review_id,
        review_type=review_type,
        created_at=now,
        updated_at=now,
        research_question="",
        cite_discipline="locator",
    )
    path.write_text(write_frontmatter(fm.to_dict(), body=text), encoding="utf-8")
    return True


def migrate_review(review_paths: ReviewPaths, *, dry_run: bool) -> MigrationResult:
    changed: list[str] = []
    skipped: list[str] = []
    warnings: list[str] = []

    required = [review_paths.synthesis, review_paths.audit_md, review_paths.evidence]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        raise ScriptoriumError(
            f"review directory is incomplete: expected {missing} at "
            f"{review_paths.root}. Run /lit-review to completion before migration.",
            symbol="E_REVIEW_INCOMPLETE",
        )

    def _maybe_convert(p: Path) -> None:
        if not p.exists():
            skipped.append(p.name)
            return
        original = p.read_text(encoding="utf-8")
        converted = _convert_legacy_citations(original)
        if converted != original:
            if not dry_run:
                p.write_text(converted, encoding="utf-8")
            changed.append(p.name)

    with ReviewLock(review_paths.lock):
        for p in (review_paths.synthesis, review_paths.contradictions):
            _maybe_convert(p)

        for p, t in [
            (review_paths.synthesis, "synthesis"),
            (review_paths.contradictions, "contradictions"),
            (review_paths.audit_md, "audit"),
        ]:
            if p.exists() and not _has_frontmatter(p.read_text(encoding="utf-8")):
                if not dry_run:
                    _ensure_frontmatter(p, review_id=review_paths.root.name, review_type=t)
                if p.name not in changed:
                    changed.append(p.name)

        queries = (review_paths.root.parent.parent / "scriptorium-queries.md") \
            if (review_paths.root.parent.parent / ".obsidian").is_dir() \
            else (review_paths.root / "scriptorium-queries.md")
        if not queries.exists() and not dry_run:
            write_query_file(queries)
            changed.append("scriptorium-queries.md")
        elif not queries.exists() and dry_run:
            changed.append("scriptorium-queries.md")

        if not dry_run:
            append_audit(
                review_paths,
                AuditEntry(
                    phase="migration", action="migrate-review",
                    status="success", details={"changed_files": changed},
                ),
            )

    return MigrationResult(changed_files=changed, skipped_files=skipped, warnings=warnings)


# ---------------------------------------------------------------------------
# v0.4 phase-state backfill (§10, T05)
# ---------------------------------------------------------------------------


# Phase → ReviewPaths attribute. screening has no canonical v0.3 artifact, so
# it stays pending after backfill.
_PHASE_ARTIFACT_ATTR: tuple[tuple[str, str], ...] = (
    ("scoping", "scope"),
    ("search", "corpus"),
    ("extraction", "evidence"),
    ("synthesis", "synthesis"),
    ("contradiction", "contradictions"),
    ("audit", "audit_md"),
)


def _present_and_nonempty(p: Path) -> bool:
    """A backfill-eligible artifact: file exists and has size > 0 bytes."""
    try:
        return p.exists() and p.stat().st_size > 0
    # Any inspection failure (perms, broken symlink, race) → treat as ineligible
    # rather than aborting the whole backfill. Tolerance is correct here.
    except OSError:
        return False


def _phases_eligible_for_backfill(
    review_paths: ReviewPaths,
) -> list[tuple[str, Path]]:
    """Return ``[(phase, artifact_path)]`` for each phase whose artifact is
    present and non-empty. Order matches :data:`_PHASE_ARTIFACT_ATTR`.
    """
    eligible: list[tuple[str, Path]] = []
    for phase, attr in _PHASE_ARTIFACT_ATTR:
        artifact = getattr(review_paths, attr)
        if _present_and_nonempty(artifact):
            eligible.append((phase, artifact))
    return eligible


def backfill_phase_state_v04(
    review_paths: ReviewPaths, *, dry_run: bool
) -> list[str]:
    """Backfill ``phase-state.json`` from existing review artifacts (§10).

    Rules:

    * If ``phase-state.json`` doesn't exist, initialise it (7 pending phases).
    * For each canonical phase whose artifact is present and non-empty, and
      whose current status is ``pending``, set status to ``running`` with
      ``artifact_path`` set to the absolute artifact path.
    * Phases already in any non-pending status are left untouched
      (idempotence — never downgrade user state).
    * Never set status to ``complete`` — legacy reviews have no v0.4
      verifier signature, so the honest status for a present artifact is
      ``running``.
    * On dry-run, no writes occur; the returned list still reports which
      phases would be upgraded.
    * On real run, a single audit row is appended documenting the backfill.

    Returns the list of phase names that were (or would be) upgraded from
    ``pending`` to ``running`` in this call.
    """
    eligible = _phases_eligible_for_backfill(review_paths)

    if dry_run:
        # We need the *current* phase-state contents to decide which phases
        # would actually be upgraded (some may already be non-pending).
        if review_paths.phase_state.exists():
            current = phase_state.read(review_paths)
            return [
                name
                for name, _artifact in eligible
                if current["phases"].get(name, {}).get("status") == "pending"
            ]
        # No phase-state.json yet → all eligible phases would be upgraded.
        return [name for name, _artifact in eligible]

    # Real run: ensure phase-state exists, then upgrade pending → running for
    # each eligible phase. M2: capture init's return value to avoid a
    # redundant read() of the file we just wrote.
    if not review_paths.phase_state.exists():
        state = phase_state.init(review_paths)
    else:
        state = phase_state.read(review_paths)

    upgraded: list[str] = []
    current_phase: Optional[str] = None
    try:
        for name, artifact in eligible:
            current_phase = name
            entry = state["phases"].get(name, {})
            if entry.get("status") != "pending":
                continue  # idempotent — never downgrade user state
            phase_state.set_phase(
                review_paths,
                name,
                "running",
                artifact_path=str(artifact.resolve()),
            )
            upgraded.append(name)
    except Exception as e:
        # Mid-loop failure: some phases may already be on disk. Emit a
        # ``partial`` audit row so forensic debugging is possible, then
        # re-raise so the CLI surfaces the error to the user.
        append_audit(
            review_paths,
            AuditEntry(
                phase="migration",
                action="backfill-phase-state-v0.4",
                status="partial",
                details={
                    "upgraded_phases": upgraded,
                    "failed_phase": current_phase,
                    "error": str(e),
                },
            ),
        )
        raise

    # I2: no upgrades → no audit row. Every audit row should be meaningful;
    # do NOT restore an unconditional append "to be safe."
    if upgraded:
        append_audit(
            review_paths,
            AuditEntry(
                phase="migration",
                action="backfill-phase-state-v0.4",
                status="success",
                details={"upgraded_phases": upgraded},
            ),
        )
    return upgraded
