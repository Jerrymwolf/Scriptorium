"""`scriptorium publish` flow (§9)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from scriptorium import nlm as nlm  # noqa: F401 — rebindable for tests


VALID_SOURCE_TOKENS = ("overview", "synthesis", "contradictions", "evidence", "pdfs", "stubs")
DEFAULT_SOURCES = ("overview", "synthesis", "contradictions", "evidence", "pdfs")


class PublishUsageError(Exception):
    def __init__(self, message: str, *, symbol: str):
        super().__init__(message)
        self.symbol = symbol


class PublishError(Exception):
    def __init__(self, message: str, *, symbol: str):
        super().__init__(message)
        self.symbol = symbol


@dataclass(frozen=True)
class PublishArgs:
    review_dir: Path
    notebook: Optional[str]
    generate: Optional[str]
    sources: tuple[str, ...]
    yes: bool
    json_mode: bool


@dataclass
class PublishOutcome:
    notebook_id: str
    notebook_url: str
    uploaded_sources: list[str]
    artifact_ids: dict[str, str]
    warnings: list[str]

    def to_json_dict(self) -> dict:
        return {
            "notebook_id": self.notebook_id,
            "notebook_url": self.notebook_url,
            "uploaded_sources": self.uploaded_sources,
            "artifact_ids": self.artifact_ids,
            "warnings": self.warnings,
        }


def parse_sources(raw: Optional[str]) -> tuple[str, ...]:
    if raw is None:
        return DEFAULT_SOURCES
    tokens = [t.strip() for t in raw.split(",")]
    tokens = [t for t in tokens if t]
    if not tokens:
        raise PublishUsageError(
            "--sources contained no valid tokens. Valid values: "
            "overview, synthesis, contradictions, evidence, pdfs, stubs.",
            symbol="E_SOURCES",
        )
    unknown = [t for t in tokens if t not in VALID_SOURCE_TOKENS]
    if unknown:
        raise PublishUsageError(
            f"--sources contained unknown token {unknown[0]!r}. Valid values: "
            "overview, synthesis, contradictions, evidence, pdfs, stubs.",
            symbol="E_SOURCES",
        )
    return tuple(tokens)


_WORD = re.compile(r"[A-Za-z0-9]+")


def derive_notebook_name(review_slug: str) -> str:
    words = _WORD.findall(review_slug or "")
    if not words:
        raise ValueError(
            f"cannot derive notebook name from {review_slug!r}. "
            "Pass --notebook \"<name>\" explicitly."
        )
    return " ".join(w.capitalize() for w in words)


def build_publish_args(
    *,
    review_dir: Path,
    notebook: Optional[str],
    generate: Optional[str],
    sources_raw: Optional[str],
    yes: bool,
    json_mode: bool,
) -> PublishArgs:
    sources = parse_sources(sources_raw)
    name = notebook if notebook else derive_notebook_name(review_dir.name)
    return PublishArgs(
        review_dir=Path(review_dir),
        notebook=name,
        generate=generate,
        sources=sources,
        yes=yes,
        json_mode=json_mode,
    )


COWORK_BLOCK_TEMPLATE = """\
Publishing to NotebookLM requires local shell access, which Cowork doesn't grant.
Two options:

1. Run `scriptorium publish` from Claude Code or your terminal instead. The review
   is already in your vault (or Drive/Notion per your setup); any surface with
   local shell access can publish it.

2. Upload manually:
   a. Open https://notebooklm.google.com and create a new notebook named
      "{notebook_name}".
   b. Upload these files as sources:
{file_list}
   c. Use the Studio panel to generate your artifact of choice.

Either way, remember to note the upload in audit.md under ## Publishing; see
docs/publishing-notebooklm.md for the template.
"""


def collect_source_files(*, review_dir: Path, sources: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    mapping = {
        "overview": "overview.md",
        "synthesis": "synthesis.md",
        "contradictions": "contradictions.md",
        "evidence": "evidence.jsonl",
    }
    for token in ("overview", "synthesis", "contradictions", "evidence"):
        if token in sources:
            p = review_dir / mapping[token]
            if p.exists():
                out.append(p)
    if "pdfs" in sources:
        pdfs_dir = review_dir / "pdfs"
        if pdfs_dir.is_dir():
            for pdf in sorted(pdfs_dir.glob("*.pdf")):
                if pdf.is_symlink():
                    continue
                if pdf.is_file():
                    out.append(pdf)
    if "stubs" in sources:
        papers_dir = review_dir / "papers"
        if papers_dir.is_dir():
            for md in sorted(papers_dir.glob("*.md")):
                out.append(md)
    return out


def render_cowork_block(*, notebook_name: str, review_dir: Path, sources: tuple[str, ...]) -> str:
    entries = collect_source_files(review_dir=Path(review_dir), sources=sources)
    rel_lines = []
    for entry in entries:
        rel = entry.relative_to(Path(review_dir))
        rel_lines.append(f"      - {rel}")
    file_list = "\n".join(rel_lines) if rel_lines else "      - (no source files resolved)"
    return COWORK_BLOCK_TEMPLATE.format(notebook_name=notebook_name, file_list=file_list)


REQUIRED_SOURCE_FILES = {
    "overview": "overview.md",
    "synthesis": "synthesis.md",
    "contradictions": "contradictions.md",
    "evidence": "evidence.jsonl",
}


def ensure_required_files(*, review_dir: Path, sources: tuple[str, ...]) -> None:
    missing: list[str] = []
    for token in sources:
        fname = REQUIRED_SOURCE_FILES.get(token)
        if fname and not (review_dir / fname).exists():
            missing.append(fname)
    if missing:
        raise PublishError(
            f"review directory is incomplete: expected {missing} at "
            f"{review_dir}. Run /lit-review to completion before publishing.",
            symbol="E_REVIEW_INCOMPLETE",
        )


_ARTIFACT_DISPATCH = {
    "audio": ("audio", "create_audio"),
    "deck": ("deck", "create_slides"),
    "mindmap": ("mindmap", "create_mindmap"),
    "video": ("video", "create_video"),
}


def _artifact_for_generate_flag(flag: str) -> list[tuple[str, str]]:
    if flag == "all":
        return [_ARTIFACT_DISPATCH["audio"], _ARTIFACT_DISPATCH["deck"],
                _ARTIFACT_DISPATCH["mindmap"]]
    return [_ARTIFACT_DISPATCH[flag]]


def run_publish(args: PublishArgs, *, now_iso: str) -> PublishOutcome:
    ensure_required_files(review_dir=args.review_dir, sources=args.sources)

    try:
        nlm.doctor()
    except Exception as e:
        raise PublishError(
            "nlm CLI not found or not authenticated. Install with "
            "'uv tool install notebooklm-mcp-cli' and run 'nlm login'. "
            "See docs/publishing-notebooklm.md for full setup.",
            symbol="E_NLM_UNAVAILABLE",
        ) from e

    try:
        created = nlm.create_notebook(args.notebook)
    except Exception as e:
        stderr_val = getattr(e, "stderr", "")
        rc_val = getattr(e, "returncode", "?")
        raise PublishError(
            f"failed to create NotebookLM notebook ({rc_val}). nlm output: "
            f"{stderr_val}. See docs/publishing-notebooklm.md#troubleshooting.",
            symbol="E_NLM_CREATE",
        ) from e

    source_files = collect_source_files(review_dir=args.review_dir, sources=args.sources)
    uploaded: list[str] = []
    warnings: list[str] = []
    for i, path in enumerate(source_files):
        try:
            nlm.upload_source(created.notebook_id, path)
        except Exception as e:
            stderr_val = getattr(e, "stderr", "")
            rc_val = getattr(e, "returncode", "?")
            raise PublishError(
                f"upload failed for {path.name} ({rc_val}). {len(uploaded)} "
                f"sources uploaded successfully before failure. Notebook "
                f"{created.notebook_id} exists in partial state at "
                f"{created.notebook_url}. See audit.md for details.",
                symbol="E_NLM_UPLOAD",
            ) from e
        uploaded.append(path.name)
        if i + 1 < len(source_files):
            time.sleep(1)

    artifact_ids: dict[str, str] = {}
    if args.generate:
        for label, fn_name in _artifact_for_generate_flag(args.generate):
            fn = getattr(nlm, fn_name)
            try:
                res = fn(created.notebook_id)
            except Exception as e:
                raise PublishError(
                    f"artifact generation failed for {label}: "
                    f"{getattr(e, 'stderr', e)}.",
                    symbol="E_NLM_ARTIFACT",
                ) from e
            m = re.search(r"([A-Za-z0-9_]*artifact[A-Za-z0-9_]*)", res.stdout)
            artifact_ids[label] = m.group(1) if m else "queued"

    return PublishOutcome(
        notebook_id=created.notebook_id,
        notebook_url=created.notebook_url,
        uploaded_sources=uploaded,
        artifact_ids=artifact_ids,
        warnings=warnings,
    )
