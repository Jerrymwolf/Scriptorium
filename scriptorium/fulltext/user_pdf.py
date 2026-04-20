"""Register user-dropped PDFs into the review's pdfs/ cache."""
from __future__ import annotations
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from scriptorium.paths import ReviewPaths


@dataclass
class PdfRecord:
    paper_id: str
    cached_path: Path
    sha256: str


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _cached_name(paper_id: str, sha: str) -> str:
    return f"{paper_id}__{sha[:12]}.pdf"


def register_user_pdf(paths: ReviewPaths, src: Path, paper_id: str) -> PdfRecord:
    paths.pdfs.mkdir(parents=True, exist_ok=True)
    sha = _sha256(src)
    dest = paths.pdfs / _cached_name(paper_id, sha)
    if not dest.exists():
        shutil.copy2(src, dest)
    return PdfRecord(paper_id=paper_id, cached_path=dest, sha256=sha)


def find_registered_pdf(paths: ReviewPaths, paper_id: str) -> Optional[Path]:
    if not paths.pdfs.exists():
        return None
    for p in paths.pdfs.iterdir():
        if p.name.startswith(f"{paper_id}__") and p.suffix.lower() == ".pdf":
            return p
    return None
