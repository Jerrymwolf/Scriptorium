"""Regenerate the small_v04 audit fixture pair via the live writer (I1+I2 fidelity)."""
from __future__ import annotations

from pathlib import Path

from scriptorium.paths import ReviewPaths
from scriptorium.storage.audit import AuditEntry, append_audit


FIXTURE_ROOT = (
    Path(__file__).resolve().parent.parent
    / "tests" / "fixtures" / "reviews" / "small_v04"
)


def main() -> None:
    audit_dir = FIXTURE_ROOT / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "audit.md").unlink(missing_ok=True)
    (audit_dir / "audit.jsonl").unlink(missing_ok=True)
    paths = ReviewPaths(root=FIXTURE_ROOT)
    append_audit(paths, AuditEntry(
        phase="setup", action="review.init",
        timestamp="2026-04-26T00:00:00Z",
        details={"version": "0.4.0"},
    ))
    append_audit(paths, AuditEntry(
        phase="synthesis", action="synthesis.complete",
        timestamp="2026-04-26T00:01:00Z",
        details={"claims": 1},
    ))


if __name__ == "__main__":
    main()
