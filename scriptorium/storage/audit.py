"""PRISMA-style audit trail. v0.3 adds a `status` enum, UTC `Z` timestamps,
and corruption recovery.

Corruption policy (§5.3): a corrupted `audit.jsonl` is never truncated.
Reads raise AuditCorruptError. Writes (when `allow_recovery=True`) redirect
to a timestamped `audit.recovery.<ts>.jsonl` sibling so new audit rows are
not lost.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal

from scriptorium.paths import ReviewPaths


AuditStatus = Literal["success", "warning", "failure", "partial", "skipped"]
_ALLOWED_STATUS = {"success", "warning", "failure", "partial", "skipped"}


class AuditCorruptError(Exception):
    """Raised when an existing audit.jsonl cannot be parsed (§5.3)."""


def _utc_z_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


@dataclass
class AuditEntry:
    phase: str
    action: str
    status: AuditStatus = "success"
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_z_now)
    # Retained for v0.2 back-compat when external code passes `ts=`.
    ts: str = ""

    def __post_init__(self) -> None:
        if self.status not in _ALLOWED_STATUS:
            raise ValueError(
                f"audit status must be one of {sorted(_ALLOWED_STATUS)}, "
                f"got {self.status!r}"
            )
        if self.ts and not self.timestamp:
            self.timestamp = self.ts


def _serialize(entry: AuditEntry) -> dict:
    return {
        "timestamp": entry.timestamp,
        "phase": entry.phase,
        "action": entry.action,
        "status": entry.status,
        "details": entry.details,
    }


def _recovery_path(paths: ReviewPaths) -> Path:
    stamp = _utc_z_now().replace(":", "").replace("-", "")
    return paths.root / f"audit.recovery.{stamp}.jsonl"


def _scan_jsonl_for_corruption(path: Path) -> None:
    """Read every line; raise AuditCorruptError on any parse failure."""
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as e:
                raise AuditCorruptError(
                    f"{path}:{lineno}: {e.msg}"
                ) from e


def append_audit(
    paths: ReviewPaths,
    entry: AuditEntry,
    *,
    allow_recovery: bool = False,
) -> None:
    paths.audit_jsonl.parent.mkdir(parents=True, exist_ok=True)
    target = paths.audit_jsonl
    try:
        _scan_jsonl_for_corruption(paths.audit_jsonl)
    except AuditCorruptError:
        if not allow_recovery:
            raise
        target = _recovery_path(paths)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_serialize(entry), ensure_ascii=False) + "\n")
    _append_markdown(paths, entry)


def _append_markdown(paths: ReviewPaths, entry: AuditEntry) -> None:
    if not paths.audit_md.exists():
        paths.audit_md.write_text("# PRISMA Audit Trail\n\n")
    lines = [f"### {entry.timestamp} — {entry.phase} / `{entry.action}`\n"]
    lines.append(f"- **status:** {entry.status}\n")
    for k, v in entry.details.items():
        lines.append(f"- **{k}:** {v}\n")
    lines.append("\n")
    with paths.audit_md.open("a", encoding="utf-8") as f:
        f.write("".join(lines))


def load_audit(paths: ReviewPaths) -> list[AuditEntry]:
    if not paths.audit_jsonl.exists():
        return []
    _scan_jsonl_for_corruption(paths.audit_jsonl)
    out: list[AuditEntry] = []
    with paths.audit_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            out.append(
                AuditEntry(
                    phase=row["phase"],
                    action=row["action"],
                    status=row.get("status", "success"),
                    details=row.get("details", {}),
                    timestamp=row.get("timestamp", row.get("ts", "")),
                )
            )
    return out
