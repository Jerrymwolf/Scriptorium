"""Schema test for the plugin manifest.

Defect-fix #5 for v0.2: the manifest MUST NOT declare an ``mcpServers`` key;
v0.2 does not ship an MCP server.
"""
import json
from pathlib import Path

import pytest

MANIFEST = Path(".claude-plugin") / "plugin.json"
CLAUDE_MD = Path(".claude-plugin") / "CLAUDE.md"


def test_manifest_exists():
    assert MANIFEST.exists(), f"{MANIFEST} not found"


def test_manifest_has_required_fields():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key in ("name", "version", "description", "author"):
        assert key in data, f"missing key: {key}"
    assert data["name"] == "scriptorium"
    assert data["version"].startswith("0.2")


def test_manifest_has_no_mcp_servers_key():
    """Defect-fix #5: v0.2 ships zero MCP server, so no mcpServers block."""
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "mcpServers" not in data
    assert "mcp_servers" not in data


def test_claude_md_mentions_three_disciplines():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    for phrase in (
        "evidence-first",
        "PRISMA",
        "contradiction",
    ):
        assert phrase.lower() in text.lower(), f"missing: {phrase}"


def test_claude_md_mentions_dual_runtime():
    text = CLAUDE_MD.read_text(encoding="utf-8").lower()
    assert "claude code" in text
    assert "cowork" in text
