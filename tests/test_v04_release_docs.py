"""Release-doc and version-metadata guards for v0.4.0.

Pinned at the v0.4 release surface so a fresh agent who tags 0.4.0 cannot
silently leave a doc, manifest, or version string at 0.3.x. Supersedes
``tests/test_version_v03.py``.
"""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from scriptorium import __version__

ROOT = Path(__file__).resolve().parent.parent
RELEASE = "0.4.0"


# --- version parity across every release surface ----------------------------


def test_package_version_is_v04():
    assert __version__ == RELEASE


def test_pyproject_version_is_v04():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "scriptorium-cli"
    assert data["project"]["version"] == RELEASE


def test_plugin_manifest_version_is_v04():
    manifest = json.loads(
        (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == RELEASE


def test_marketplace_metadata_and_plugin_version_is_v04():
    data = json.loads(
        (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    assert data["metadata"]["version"] == RELEASE
    plugin_entry = next(p for p in data["plugins"] if p["name"] == "scriptorium")
    assert plugin_entry["version"] == RELEASE


# --- CHANGELOG -------------------------------------------------------------


def test_changelog_has_v04_section_with_date():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    # Header must be `## 0.4.0 — YYYY-MM-DD` (em-dash, ISO date).
    assert re.search(r"^## 0\.4\.0 — \d{4}-\d{2}-\d{2}\b", text, re.MULTILINE), (
        "CHANGELOG.md must have a `## 0.4.0 — YYYY-MM-DD` section header"
    )


def test_changelog_v04_section_names_layers_and_migration():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    # Slice out the 0.4.0 section so we don't accidentally pass on an older entry.
    match = re.search(
        r"^## 0\.4\.0[^\n]*\n(.*?)(?=^## \d|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match, "0.4.0 section must precede prior version sections"
    section = match.group(1).lower()
    for phrase in (
        "layer a",
        "layer b",
        "enforce_v04",
        "migrate-review",
        "phase-state",
    ):
        assert phrase in section, f"0.4.0 changelog must reference {phrase!r}"


def test_changelog_unreleased_section_is_empty_or_absent():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(
        r"^## Unreleased\n(.*?)(?=^## \d|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return  # absent is fine
    body = match.group(1).strip()
    # Either empty or a one-line placeholder; reject leftover content that
    # should have moved into the 0.4.0 section.
    assert len(body) <= 80, (
        "Unreleased section must be empty after a release tag — "
        "move pending notes into 0.4.0 or back into Unreleased after the bump"
    )


# --- v0.4 release notes ----------------------------------------------------


def _release_notes() -> str:
    path = ROOT / "docs" / "v0.4-release-notes.md"
    assert path.exists(), "docs/v0.4-release-notes.md is required for the v0.4 release"
    return path.read_text(encoding="utf-8")


def test_release_notes_pin_version_and_disciplines():
    text = _release_notes()
    assert RELEASE in text, "release notes must name 0.4.0"
    lower = text.lower()
    for discipline in ("evidence-first", "prisma", "contradiction"):
        assert discipline in lower, f"release notes must preserve {discipline!r}"


def test_release_notes_describe_layer_a_and_layer_b():
    lower = _release_notes().lower()
    for phrase in (
        "layer a",
        "layer b",
        "session injection",
        "hard-gate",
        "phase-state",
        "verification",
        "extraction",
        "reviewer",
        "override",
    ):
        assert phrase in lower, f"release notes must describe {phrase!r}"


def test_release_notes_describe_migration_and_advisory_rollout():
    lower = _release_notes().lower()
    for phrase in (
        "enforce_v04",
        "advisory",
        "migrate-review",
    ):
        assert phrase in lower, f"release notes must describe {phrase!r}"


def test_release_notes_name_both_runtimes():
    lower = _release_notes().lower()
    assert "claude code" in lower
    assert "cowork" in lower


# --- cowork smoke matrix carries Layer B runtime rows ----------------------


def _smoke() -> str:
    return (ROOT / "docs" / "cowork-smoke.md").read_text(encoding="utf-8")


def test_smoke_matrix_has_extraction_backend_rows():
    text = _smoke()
    for literal in ("ISOLATION_BACKEND", "`mcp`", "`notebooklm`", "sequential"):
        assert literal in text, f"cowork-smoke.md must name extraction literal {literal!r}"


def test_smoke_matrix_has_reviewer_branch_rows():
    text = _smoke()
    for literal in (
        "REVIEWER_BRANCH",
        "inline_degraded",
        "cowork.reviewer_branch",
        "finalize_synthesis_reviewers",
    ):
        assert literal in text, f"cowork-smoke.md must name reviewer-branch literal {literal!r}"
