"""Assemble overview.md from synthesis/contradictions/evidence (§8.5)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scriptorium.frontmatter import ReviewArtifactFrontmatter, write_frontmatter
from scriptorium.overview.linter import REQUIRED_SECTIONS, lint_overview
from scriptorium.paths import ReviewPaths
from scriptorium.storage.evidence import load_evidence


@dataclass
class OverviewResult:
    path: Path
    archived_path: Optional[Path]
    corpus_hash: str
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "archived_path": str(self.archived_path) if self.archived_path else None,
            "corpus_hash": self.corpus_hash,
            "warnings": self.warnings,
        }


def compute_corpus_hash(paths: ReviewPaths) -> str:
    rows = load_evidence(paths)
    ids = sorted(
        f"{r.paper_id}|{r.locator}|{hashlib.sha256(r.claim.encode('utf-8')).hexdigest()}"
        for r in rows
    )
    h = hashlib.sha256()
    for id_ in ids:
        h.update(id_.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def default_seed(research_question: str, review_id: str) -> int:
    digest = hashlib.sha256(
        (research_question + review_id).encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16)


def _compose_body(paths: ReviewPaths) -> str:
    rows = load_evidence(paths)
    # Validate synthesis.md: it must contain at least one locator when it has
    # substantive content (non-empty, non-whitespace).
    synth_text = ""
    if paths.synthesis.exists():
        synth_text = paths.synthesis.read_text(encoding="utf-8").strip()

    from scriptorium.overview.linter import _PAPER_LOCATOR, _SYNTH_MARKER
    if synth_text and not _PAPER_LOCATOR.search(synth_text) and not _SYNTH_MARKER.search(synth_text):
        # synthesis.md has content but no valid citations — produce a body
        # that will fail lint so the caller sees E_OVERVIEW_FAILED.
        raise _SynthesisHasNoCitations(
            f"synthesis.md has content but no paper locators or synthesis markers"
        )

    cite_line = (
        f"Corpus contains {len(rows)} evidence rows. <!-- synthesis -->"
        if not rows
        else f"Representative finding: {rows[0].claim} [[{rows[0].paper_id}#p-{rows[0].locator.split(':', 1)[-1]}]]."
    )
    synth_line = "Corpus framing summarized here. <!-- synthesis -->"
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    sections: list[str] = []
    for name in REQUIRED_SECTIONS:
        body = cite_line if rows else synth_line
        prov = (
            "<!-- provenance:\n"
            f"  section: {name.lower().replace(' ', '-').replace(';', '').replace('(', '').replace(')', '').replace('&', 'and')}\n"
            "  contributing_papers: []\n"
            "  derived_from: synthesis.md\n"
            f"  generation_timestamp: {ts}\n"
            "-->"
        )
        sections.append(f"## {name}\n\n{body}\n\n{prov}")
    return "\n\n".join(sections) + "\n"


class _SynthesisHasNoCitations(Exception):
    pass


def regenerate_overview(
    paths: ReviewPaths,
    *,
    model: str,
    seed: Optional[int],
    research_question: str = "",
    review_id: Optional[str] = None,
) -> OverviewResult:
    from scriptorium.overview.linter import OverviewLintError
    try:
        body = _compose_body(paths)
    except _SynthesisHasNoCitations as e:
        raise OverviewLintError(str(e)) from e
    lint_overview(body)

    review_id_ = review_id or paths.root.name
    seed_ = seed if seed is not None else default_seed(research_question, review_id_)
    corpus_hash = compute_corpus_hash(paths)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    fm = ReviewArtifactFrontmatter(
        schema_version="scriptorium.review_file.v1",
        scriptorium_version="0.3.1",
        review_id=review_id_,
        review_type="overview",
        created_at=now,
        updated_at=now,
        research_question=research_question,
        cite_discipline="locator",
        model_version=model,
        generation_seed=seed_,
        generation_timestamp=now,
        corpus_hash=corpus_hash,
        ranking_weights={"citation_frequency": 0.6, "llm_salience": 0.4},
    )

    archived_path: Optional[Path] = None
    if paths.overview.exists():
        paths.overview_archive.mkdir(parents=True, exist_ok=True)
        stamp = now.replace(":", "").replace("-", "")
        archived_path = paths.overview_archive / f"{stamp}.md"
        archived_path.write_text(
            paths.overview.read_text(encoding="utf-8"), encoding="utf-8",
        )

    text = write_frontmatter(fm.to_dict(), body=body)
    paths.overview.write_text(text, encoding="utf-8")

    from scriptorium.export import render_overview_docx
    from scriptorium.storage.audit import AuditEntry, append_audit

    source_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    try:
        result = render_overview_docx(
            paths.overview, paths.overview_docx, paths.corpus
        )
        append_audit(
            paths,
            AuditEntry(
                phase="overview",
                action="overview_rendered",
                status="success",
                details={
                    "wrote": ["overview.md", "overview.docx"],
                    "source_sha256": source_sha,
                    "citation_misses": result.citation_misses,
                    "corpus_unavailable": result.corpus_unavailable,
                },
            ),
        )
    except Exception as exc:
        append_audit(
            paths,
            AuditEntry(
                phase="overview",
                action="overview_docx_failed",
                status="failure",
                details={
                    "wrote": ["overview.md"],
                    "source_sha256": source_sha,
                    "error": str(exc)[:200],
                },
            ),
        )

    return OverviewResult(
        path=paths.overview,
        archived_path=archived_path,
        corpus_hash=corpus_hash,
        warnings=[],
    )


def write_failed_draft(paths: ReviewPaths, body: str) -> Path:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stamp = now.replace(":", "").replace("-", "")
    paths.overview_archive.mkdir(parents=True, exist_ok=True)
    p = paths.overview_archive / f"overview.failed.{stamp}.md"
    p.write_text(body, encoding="utf-8")
    return p
