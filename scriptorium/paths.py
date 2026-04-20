"""Per-review path resolution. State lives next to the dissertation."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ReviewPaths:
    root: Path

    @property
    def evidence(self) -> Path:
        return self.root / "evidence.jsonl"

    @property
    def audit_md(self) -> Path:
        return self.root / "audit.md"

    @property
    def audit_jsonl(self) -> Path:
        return self.root / "audit.jsonl"

    @property
    def corpus(self) -> Path:
        return self.root / "corpus.jsonl"

    @property
    def synthesis(self) -> Path:
        return self.root / "synthesis.md"

    @property
    def pdfs(self) -> Path:
        return self.root / "pdfs"

    @property
    def extracts(self) -> Path:
        return self.root / "extracts"

    @property
    def outputs(self) -> Path:
        return self.root / "outputs"

    @property
    def bib(self) -> Path:
        return self.root / "bib"


def resolve_review_dir(
    explicit: Optional[Path] = None, create: bool = False
) -> ReviewPaths:
    if explicit is not None:
        root = Path(explicit)
    elif env := os.environ.get("SCRIPTORIUM_REVIEW_DIR"):
        root = Path(env)
    else:
        root = Path.cwd()
    if create:
        for sub in ("pdfs", "extracts", "outputs", "bib"):
            (root / sub).mkdir(parents=True, exist_ok=True)
    return ReviewPaths(root=root)
