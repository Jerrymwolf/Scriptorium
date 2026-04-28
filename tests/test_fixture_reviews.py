"""T17 acceptance — the static review fixtures are stable and well-formed.

These tests pin the on-disk shape of:

* ``tests/fixtures/reviews/small_v04/`` — minimal v0.4-shaped review
  (phase-state.json present, all 7 phases pending, config has
  ``enforce_v04 = true``).
* ``tests/fixtures/reviews/legacy_v03/`` — pre-v0.4 review (no
  phase-state.json; v0.3-style citations).

Future tests (and Phase 6 release-doc tests) can ``copytree`` either
fixture into ``tmp_path`` and operate on it. Pinning the shape here
makes that contract explicit.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from scriptorium import phase_state
from scriptorium.paths import ReviewPaths


SMALL_V04_PATH = Path(__file__).parent / "fixtures" / "reviews" / "small_v04"
LEGACY_V03_PATH = Path(__file__).parent / "fixtures" / "reviews" / "legacy_v03"


# ---------------------------------------------------------------------------
# small_v04 — v0.4-shaped review
# ---------------------------------------------------------------------------


def test_small_v04_required_files_present() -> None:
    root = SMALL_V04_PATH
    assert root.is_dir()
    # Prose deliverables
    for name in ("overview.md", "synthesis.md", "contradictions.md"):
        f = root / name
        assert f.is_file(), f"missing {name}"
        assert f.read_text(encoding="utf-8").strip(), f"{name} is empty"
    # Data and audit
    assert (root / "data" / "evidence.jsonl").is_file()
    assert (root / "audit" / "audit.md").is_file()
    assert (root / "audit" / "audit.jsonl").is_file()
    # v0.4 marker artifacts
    assert (root / ".scriptorium" / "phase-state.json").is_file()
    assert (root / "config.toml").is_file()


def test_small_v04_phase_state_validates(tmp_path: Path) -> None:
    """Copy the fixture and let the live phase_state loader validate it."""
    dest = tmp_path / "small_v04"
    shutil.copytree(SMALL_V04_PATH, dest)
    paths = ReviewPaths(root=dest)
    state = phase_state.read(paths)
    assert state["version"] == "0.4.0"
    expected = {
        "scoping",
        "search",
        "screening",
        "extraction",
        "synthesis",
        "contradiction",
        "audit",
    }
    assert set(state["phases"].keys()) == expected
    for entry in state["phases"].values():
        assert entry["status"] == "pending"


def test_small_v04_config_has_enforce_v04_true() -> None:
    cfg = (SMALL_V04_PATH / "config.toml").read_text(encoding="utf-8")
    assert "enforce_v04 = true" in cfg


def test_small_v04_evidence_jsonl_is_well_formed() -> None:
    rows = [
        json.loads(line)
        for line in (SMALL_V04_PATH / "data" / "evidence.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert rows, "evidence.jsonl must have at least one row"
    for row in rows:
        for required in (
            "paper_id",
            "locator",
            "claim",
            "quote",
            "direction",
            "concept",
        ):
            assert required in row, f"evidence row missing {required!r}"


# ---------------------------------------------------------------------------
# legacy_v03 — pre-v0.4 review
# ---------------------------------------------------------------------------


def test_legacy_v03_has_no_phase_state() -> None:
    """The whole point of legacy_v03 is the absence of phase-state.json."""
    assert not (LEGACY_V03_PATH / ".scriptorium" / "phase-state.json").exists()
    assert not (LEGACY_V03_PATH / ".scriptorium").exists()


def test_legacy_v03_required_files_present() -> None:
    root = LEGACY_V03_PATH
    assert root.is_dir()
    assert (root / "synthesis.md").is_file()
    assert (root / "contradictions.md").is_file()
    assert (root / "audit" / "audit.md").is_file()
    # v0.3 puts evidence.jsonl at the review root, not under data/.
    assert (root / "evidence.jsonl").is_file()
    assert not (root / "data").exists()


def test_legacy_v03_uses_v03_citation_format() -> None:
    text = (LEGACY_V03_PATH / "synthesis.md").read_text(encoding="utf-8")
    # v0.3 format: [paper_id:page:N], not [[paper_id#p-N]].
    assert "[nehlig2010:page:4]" in text
    assert "[[nehlig2010#p-4]]" not in text


def test_legacy_v03_loads_in_advisory_mode(tmp_path: Path) -> None:
    """Copy the fixture and confirm phase_state.read() auto-inits on missing."""
    dest = tmp_path / "legacy_v03"
    shutil.copytree(LEGACY_V03_PATH, dest)
    paths = ReviewPaths(root=dest)
    # Auto-init on read (T03 contract).
    state = phase_state.read(paths)
    assert state["version"] == "0.4.0"
    for entry in state["phases"].values():
        assert entry["status"] == "pending"
