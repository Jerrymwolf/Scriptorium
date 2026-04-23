"""Contract test: the scope_approved audit entry has the expected shape."""
from __future__ import annotations

import io
import json
from pathlib import Path

from scriptorium.cli import main


def _run(argv, cwd: Path):
    out, err = io.StringIO(), io.StringIO()
    rc = main(argv, cwd=cwd, stdout=out, stderr=err, stdin=io.StringIO())
    return rc, out.getvalue(), err.getvalue()


def test_scope_approved_audit_entry_shape(tmp_path: Path):
    details = {
        "scope_version": 1,
        "dimensions_resolved_via_inference": ["research_question", "fields"],
        "dimensions_resolved_via_question": ["purpose", "year_range"],
        "tier3_dimensions_selected": ["conceptual_frame"],
        "soft_warnings_acknowledged": [],
        "revision_cycles": 1,
    }
    rc, out, err = _run(
        [
            "audit", "append",
            "--phase", "scoping",
            "--action", "scope_approved",
            "--details", json.dumps(details),
        ],
        cwd=tmp_path,
    )
    assert rc == 0, err

    entries = [
        json.loads(line)
        for line in (tmp_path / "audit" / "audit.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(entries) == 1
    e = entries[0]
    assert e["phase"] == "scoping"
    assert e["action"] == "scope_approved"
    assert e["status"] == "success"
    assert e["details"]["scope_version"] == 1
    assert "revision_cycles" in e["details"]
