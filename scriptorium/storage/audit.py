"""PRISMA-style audit trail. Markdown for humans, JSONL for tools."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from typing import Any
from scriptorium.paths import ReviewPaths


@dataclass
class AuditEntry:
    phase: str
    action: str
    details: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def append_audit(paths: ReviewPaths, entry: AuditEntry) -> None:
    paths.audit_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with paths.audit_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    _append_markdown(paths, entry)


def _append_markdown(paths: ReviewPaths, entry: AuditEntry) -> None:
    if not paths.audit_md.exists():
        paths.audit_md.write_text("# PRISMA Audit Trail\n\n")
    lines = [f"### {entry.ts} — {entry.phase} / `{entry.action}`\n"]
    for k, v in entry.details.items():
        lines.append(f"- **{k}:** {v}\n")
    lines.append("\n")
    with paths.audit_md.open("a", encoding="utf-8") as f:
        f.write("".join(lines))


def load_audit(paths: ReviewPaths) -> list[AuditEntry]:
    if not paths.audit_jsonl.exists():
        return []
    out: list[AuditEntry] = []
    with paths.audit_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(AuditEntry(**json.loads(line)))
    return out
