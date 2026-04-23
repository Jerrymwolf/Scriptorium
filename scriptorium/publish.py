"""`scriptorium publish` flow (§9)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from scriptorium import nlm as nlm  # noqa: F401 — rebindable for tests
from scriptorium.storage.audit import AuditEntry, append_audit
from scriptorium.paths import ReviewPaths


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
    paths = ReviewPaths(root=review_dir)
    out: list[Path] = []
    prose_map = {
        "overview": paths.overview,
        "synthesis": paths.synthesis,
        "contradictions": paths.contradictions,
        "evidence": paths.evidence,
    }
    for token in ("overview", "synthesis", "contradictions", "evidence"):
        if token in sources:
            p = prose_map[token]
            if p.exists():
                out.append(p)
    if "pdfs" in sources:
        pdfs_dir = paths.pdfs
        if pdfs_dir.is_dir():
            for pdf in sorted(pdfs_dir.glob("*.pdf")):
                if pdf.is_symlink():
                    continue
                if pdf.is_file():
                    out.append(pdf)
    if "stubs" in sources:
        papers_dir = paths.papers
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


REQUIRED_SOURCE_KEYS: tuple[str, ...] = (
    "overview",
    "synthesis",
    "contradictions",
    "evidence",
)


def ensure_required_files(*, review_dir: Path, sources: tuple[str, ...]) -> None:
    paths = ReviewPaths(root=review_dir)
    prose_map = {
        "overview": paths.overview,
        "synthesis": paths.synthesis,
        "contradictions": paths.contradictions,
        "evidence": paths.evidence,
    }
    missing: list[str] = []
    for token in sources:
        p = prose_map.get(token)
        if p is not None and not p.exists():
            missing.append(p.name)
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


def run_publish(args: PublishArgs, *, now_iso: str, partial_state: Optional[dict] = None) -> PublishOutcome:
    if partial_state is not None:
        state = partial_state
    else:
        state = {}
    state.setdefault("uploaded_names", [])
    state.setdefault("notebook_id", None)
    state.setdefault("notebook_url", None)

    ensure_required_files(review_dir=args.review_dir, sources=args.sources)

    try:
        nlm.doctor()
    except Exception as e:
        from scriptorium.nlm import NlmTimeoutError as _NlmTimeoutError
        if isinstance(e, _NlmTimeoutError):
            raise
        raise PublishError(
            "nlm CLI not found or not authenticated. Install with "
            "'uv tool install notebooklm-mcp-cli' and run 'nlm login'. "
            "See docs/publishing-notebooklm.md for full setup.",
            symbol="E_NLM_UNAVAILABLE",
        ) from e

    try:
        created = nlm.create_notebook(args.notebook)
    except Exception as e:
        from scriptorium.nlm import NlmTimeoutError as _NlmTimeoutError
        if isinstance(e, _NlmTimeoutError):
            raise
        stderr_val = getattr(e, "stderr", "")
        rc_val = getattr(e, "returncode", "?")
        raise PublishError(
            f"failed to create NotebookLM notebook ({rc_val}). nlm output: "
            f"{stderr_val}. See docs/publishing-notebooklm.md#troubleshooting.",
            symbol="E_NLM_CREATE",
        ) from e

    state["notebook_id"] = created.notebook_id
    state["notebook_url"] = created.notebook_url

    source_files = collect_source_files(review_dir=args.review_dir, sources=args.sources)
    uploaded: list[str] = []
    warnings: list[str] = []
    for i, path in enumerate(source_files):
        try:
            nlm.upload_source(created.notebook_id, path)
        except Exception as e:
            stderr_val = getattr(e, "stderr", "")
            rc_val = getattr(e, "returncode", "?")
            state["failing_command"] = f"nlm source add {created.notebook_id} --file {path}"
            state["exit_code"] = getattr(e, "returncode", None)
            state["stderr"] = str(getattr(e, "stderr", e))
            raise PublishError(
                f"upload failed for {path.name} ({rc_val}). {len(uploaded)} "
                f"sources uploaded successfully before failure. Notebook "
                f"{created.notebook_id} exists in partial state at "
                f"{created.notebook_url}. See audit.md for details.",
                symbol="E_NLM_UPLOAD",
            ) from e
        uploaded.append(path.name)
        state["uploaded_names"].append(path.name)
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


def has_prior_publish(audit_md: Path, notebook_name: str) -> bool:
    """Return True iff audit.md records a prior publish to `notebook_name`."""
    if not audit_md.exists():
        return False
    text = audit_md.read_text(encoding="utf-8")
    marker = f'**Notebook:** "{notebook_name}"'
    return marker in text


def append_publish_audit(
    *,
    review_dir: Path,
    outcome: "PublishOutcome",
    attempted_sources: list[Path],
    status: str,
    triggered_by: str,
    generate_flag: Optional[str],
    notebook_name: str,
) -> None:
    paths = ReviewPaths(root=review_dir)
    uploaded = [{"name": p.name, "size": p.stat().st_size} for p in attempted_sources if p.name in outcome.uploaded_sources]
    details = {
        "notebook_name": notebook_name,
        "notebook_id": outcome.notebook_id,
        "notebook_url": outcome.notebook_url,
        "triggered_by": triggered_by,
        "attempted_sources": [{"name": p.name, "size": p.stat().st_size} for p in attempted_sources],
        "uploaded_sources": uploaded,
        "uploaded_total_bytes": sum(u["size"] for u in uploaded),
        "artifact_ids": outcome.artifact_ids,
        "generate": generate_flag,
    }
    append_audit(paths, AuditEntry(phase="publishing", action="notebook.publish", status=status, details=details))
    _append_publish_md(paths.audit_md, outcome, attempted_sources, status, notebook_name)


def _append_publish_md(audit_md: Path, outcome: "PublishOutcome", attempted: list[Path], status: str, notebook_name: str) -> None:
    from datetime import datetime, timezone
    if not audit_md.exists():
        audit_md.write_text("# PRISMA Audit Trail\n\n")
    text = audit_md.read_text(encoding="utf-8")
    if "## Publishing" not in text:
        audit_md.write_text(text + "## Publishing\n\n", encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    lines = [
        f"\n### {now} — NotebookLM\n",
        f"**Status:** {status}",
        f'**Notebook:** "{notebook_name}" (id: `{outcome.notebook_id}`)',
        f"**URL:** {outcome.notebook_url}",
        "",
    ]
    with audit_md.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def append_partial_audit(
    *,
    review_dir: Path,
    attempted_sources: list[Path],
    uploaded_names: list[str],
    notebook_id: Optional[str],
    notebook_url: Optional[str],
    notebook_name: Optional[str],
    failing_command: str,
    exit_code: Optional[int],
    stderr_truncated: str,
    symbol: str,
) -> None:
    paths = ReviewPaths(root=review_dir)
    details = {
        "notebook_name": notebook_name,
        "notebook_id": notebook_id,
        "notebook_url": notebook_url,
        "attempted_sources": [{"name": str(p.relative_to(review_dir))} for p in attempted_sources],
        "uploaded_sources": [{"name": n} for n in uploaded_names],
        "failing_command": failing_command,
        "captured_exit_code": exit_code,
        "captured_stderr": stderr_truncated[:4096],
        "symbol": symbol,
    }
    append_audit(paths, AuditEntry(phase="publishing", action="notebook.publish.partial", status="partial", details=details))
