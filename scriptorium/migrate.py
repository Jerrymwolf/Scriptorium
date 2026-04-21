"""Review migration (§10.1)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

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
        scriptorium_version="0.3.0",
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
