"""§5.3 audit.jsonl schema: status enum, UTC Z timestamps, corruption recovery."""
import json
from pathlib import Path

import pytest

from scriptorium.paths import ReviewPaths
from scriptorium.storage.audit import (
    AuditCorruptError,
    AuditEntry,
    append_audit,
    load_audit,
)


def _paths(tmp_path) -> ReviewPaths:
    return ReviewPaths(root=tmp_path)


def test_append_has_status_default_success(tmp_path):
    paths = _paths(tmp_path)
    append_audit(
        paths, AuditEntry(phase="publishing", action="notebook.create", details={})
    )
    rows = [
        json.loads(line)
        for line in paths.audit_jsonl.read_text(encoding="utf-8").splitlines()
    ]
    assert rows[0]["status"] == "success"


def test_timestamp_is_iso_utc_z(tmp_path):
    paths = _paths(tmp_path)
    append_audit(paths, AuditEntry(phase="search", action="doi.fetch"))
    row = json.loads(paths.audit_jsonl.read_text(encoding="utf-8").splitlines()[0])
    assert row["timestamp"].endswith("Z")


def test_rejects_invalid_status(tmp_path):
    paths = _paths(tmp_path)
    with pytest.raises(ValueError):
        AuditEntry(phase="publishing", action="x", status="rejected")


def test_corrupt_jsonl_raises_and_preserves_file(tmp_path):
    paths = _paths(tmp_path)
    paths.audit_dir.mkdir(parents=True, exist_ok=True)
    paths.audit_jsonl.write_text("{not valid json\n", encoding="utf-8")
    with pytest.raises(AuditCorruptError):
        load_audit(paths)
    # File is preserved verbatim.
    assert paths.audit_jsonl.read_text(encoding="utf-8") == "{not valid json\n"


def test_append_after_corruption_uses_recovery_file(tmp_path):
    paths = _paths(tmp_path)
    paths.audit_dir.mkdir(parents=True, exist_ok=True)
    paths.audit_jsonl.write_text("{not valid json\n", encoding="utf-8")
    append_audit(
        paths,
        AuditEntry(phase="publishing", action="notebook.create"),
        allow_recovery=True,
    )
    matches = list(Path(tmp_path).glob("audit.recovery.*.jsonl"))
    assert len(matches) == 1
    row = json.loads(matches[0].read_text(encoding="utf-8").splitlines()[0])
    assert row["phase"] == "publishing"
