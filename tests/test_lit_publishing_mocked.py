# tests/test_lit_publishing_mocked.py
"""Behavioral content test for lit-publishing skill."""
from pathlib import Path

SKILL = Path(".claude-plugin/skills/lit-publishing/SKILL.md")


def test_skill_exists():
    assert SKILL.exists()


def test_every_studio_tool_named():
    text = SKILL.read_text(encoding="utf-8")
    for tool in (
        "mcp__notebooklm-mcp__studio_create",
        "mcp__notebooklm-mcp__studio_status",
        "mcp__notebooklm-mcp__download_artifact",
    ):
        assert tool in text, f"missing tool: {tool}"


def test_all_four_artifact_types_documented():
    text = SKILL.read_text(encoding="utf-8")
    for kind in ('"audio"', '"slides"', '"infographic"', '"video"'):
        assert kind in text, f"missing artifact_type: {kind}"


def test_poll_loop_described():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "poll" in text
    assert "complete" in text
    assert "studio_status" in text


def test_download_step_follows_completion():
    text = SKILL.read_text(encoding="utf-8")
    status_idx = text.find("studio_status")
    download_idx = text.find("download_artifact")
    assert status_idx != -1 and download_idx != -1
    assert download_idx > status_idx


def test_audit_entry_per_artifact():
    text = SKILL.read_text(encoding="utf-8")
    assert "scriptorium audit append" in text
    assert "--phase publishing" in text
    assert "studio.created" in text


def test_quota_failure_handled_explicitly():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "quota" in text
    assert "stop" in text or "refuse" in text


def test_cite_check_is_a_precondition():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "verify" in text or "cite-check" in text
    assert "contradiction" in text


def test_default_recommendation_is_audio():
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "audio" in text
    assert "default" in text or "just audio" in text or "cheapest" in text


def test_cost_order_communicated():
    text = SKILL.read_text(encoding="utf-8").lower()
    for pair_marker in ("audio", "video"):
        assert pair_marker in text
    assert "<" in text or "cost" in text or "cheaper" in text
