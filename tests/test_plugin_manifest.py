"""Schema tests for the plugin manifest and marketplace manifest."""
import json
from pathlib import Path

MANIFEST = Path(".claude-plugin") / "plugin.json"
MARKETPLACE = Path(".claude-plugin") / "marketplace.json"
CLAUDE_MD = Path("CLAUDE.md")


def test_manifest_exists():
    assert MANIFEST.exists(), f"{MANIFEST} not found"


def test_manifest_has_required_fields():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key in ("name", "version", "description", "author"):
        assert key in data, f"missing key: {key}"
    assert data["name"] == "scriptorium"
    assert data["version"].startswith("0.4")


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


# --- marketplace.json guardrails ---

def test_marketplace_exists_in_claude_plugin():
    assert MARKETPLACE.exists(), ".claude-plugin/marketplace.json missing — plugin won't be discoverable"


def test_no_root_level_marketplace_json():
    assert not Path("marketplace.json").exists(), \
        "marketplace.json must live in .claude-plugin/, not at repo root"


def test_marketplace_name_matches_registration_key():
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    assert data["name"] == "Jerrymwolf-Scriptorium", \
        "marketplace name must match extraKnownMarketplaces key exactly"


def test_marketplace_has_scriptorium_plugin():
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    names = [p["name"] for p in data.get("plugins", [])]
    assert "scriptorium" in names, "marketplace.json must list a plugin named 'scriptorium'"


def test_marketplace_plugin_source_is_flat():
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    plugin = next(p for p in data["plugins"] if p["name"] == "scriptorium")
    assert plugin["source"] == "./", "plugin source must be './' for flat repo layout"


def test_homepage_url_case():
    """Prevent silent regression: wrong case breaks GitHub redirect and confuses users."""
    plugin_data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    marketplace_data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    for url in (
        plugin_data.get("homepage", ""),
        marketplace_data.get("metadata", {}).get("homepage", ""),
    ):
        if url:
            assert "Jerrymwolf/Scriptorium" in url, \
                f"homepage URL has wrong case in: {url!r} — must be 'Jerrymwolf/Scriptorium'"


def test_version_parity():
    plugin_data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    marketplace_data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    plugin_ver = plugin_data["version"]
    marketplace_ver = marketplace_data.get("metadata", {}).get("version", "")
    marketplace_plugin_ver = next(
        p.get("version", "") for p in marketplace_data["plugins"] if p["name"] == "scriptorium"
    )
    assert plugin_ver == marketplace_ver == marketplace_plugin_ver, (
        f"Version mismatch: plugin.json={plugin_ver!r}, "
        f"marketplace metadata={marketplace_ver!r}, "
        f"marketplace plugin entry={marketplace_plugin_ver!r}"
    )
