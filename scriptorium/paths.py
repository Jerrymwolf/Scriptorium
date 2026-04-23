"""Per-review path resolution and canonical file names.

v0.3 extends v0.2's `ReviewPaths` with overview, contradictions, paper stubs,
references export, and a review lock. Resolution follows §4.1 of the design
spec: absolute path is respected; relative path is joined against `vault_root`
when set, otherwise against the cwd; `SCRIPTORIUM_REVIEW_DIR` is the fallback
when `explicit` is None.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ReviewPaths:
    root: Path

    # Prose deliverables (root)
    @property
    def overview(self) -> Path:
        return self.root / "overview.md"

    @property
    def overview_docx(self) -> Path:
        return self.root / "overview.docx"

    @property
    def synthesis(self) -> Path:
        return self.root / "synthesis.md"

    @property
    def contradictions(self) -> Path:
        return self.root / "contradictions.md"

    @property
    def scope(self) -> Path:
        return self.root / "scope.json"

    @property
    def references_bib(self) -> Path:
        return self.root / "references.bib"

    # Sources bucket
    @property
    def sources_dir(self) -> Path:
        return self.root / "sources"

    @property
    def pdfs(self) -> Path:
        return self.sources_dir / "pdfs"

    @property
    def papers(self) -> Path:
        return self.sources_dir / "papers"

    # Data bucket
    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def evidence(self) -> Path:
        return self.data_dir / "evidence.jsonl"

    @property
    def corpus(self) -> Path:
        return self.data_dir / "corpus.jsonl"

    @property
    def extracts(self) -> Path:
        return self.data_dir / "extracts"

    # Audit bucket
    @property
    def audit_dir(self) -> Path:
        return self.root / "audit"

    @property
    def audit_md(self) -> Path:
        return self.audit_dir / "audit.md"

    @property
    def audit_jsonl(self) -> Path:
        return self.audit_dir / "audit.jsonl"

    @property
    def overview_archive(self) -> Path:
        return self.audit_dir / "overview-archive"

    # Internal state
    @property
    def scriptorium_dir(self) -> Path:
        return self.root / ".scriptorium"

    @property
    def lock(self) -> Path:
        return self.scriptorium_dir / "lock"

    # Retained for backwards API — remove if no callers.
    @property
    def bib(self) -> Path:
        return self.sources_dir / "bib"

    @property
    def outputs(self) -> Path:
        return self.root / "outputs"


def resolve_review_dir(
    explicit: Optional[Path] = None,
    *,
    vault_root: Optional[Path] = None,
    cwd: Optional[Path] = None,
    create: bool = False,
) -> ReviewPaths:
    """Resolve the review directory per §4.1.

    - Absolute `explicit` is used as-is (after resolve).
    - Relative `explicit` joins to `vault_root` when given, else `cwd`.
    - No `explicit` falls back to `SCRIPTORIUM_REVIEW_DIR` then `cwd`.
    """
    base_cwd = Path(cwd) if cwd is not None else Path.cwd()

    if explicit is not None:
        p = Path(explicit)
        if p.is_absolute():
            root = p.resolve(strict=False)
        elif vault_root is not None:
            root = (Path(vault_root) / p).resolve(strict=False)
        else:
            root = (base_cwd / p).resolve(strict=False)
    else:
        env = os.environ.get("SCRIPTORIUM_REVIEW_DIR")
        root = Path(env).resolve(strict=False) if env else base_cwd.resolve(strict=False)

    if create:
        for sub in (
            "sources/pdfs",
            "sources/papers",
            "data/extracts",
            "audit/overview-archive",
            ".scriptorium",
        ):
            (root / sub).mkdir(parents=True, exist_ok=True)
    return ReviewPaths(root=root)
