# tests/test_docs_cowork_smoke.py
"""Content test for the Cowork smoke checklist."""
from pathlib import Path

DOC = Path("docs/cowork-smoke.md")


def test_doc_exists():
    assert DOC.exists()


def test_all_four_connectors_covered():
    text = DOC.read_text(encoding="utf-8")
    for connector in (
        "Consensus",
        "Scholar Gateway",
        "PubMed",
        "NotebookLM",
    ):
        assert connector in text, f"missing connector row: {connector}"


def test_mcp_tool_names_present():
    text = DOC.read_text(encoding="utf-8")
    for tool in (
        "mcp__claude_ai_Consensus__search",
        "mcp__claude_ai_Scholar_Gateway__semanticSearch",
        "mcp__claude_ai_PubMed__search_articles",
        "mcp__notebooklm-mcp__notebook_create",
    ):
        assert tool in text, f"missing probe: {tool}"


def test_degraded_mode_discussed():
    text = DOC.read_text(encoding="utf-8").lower()
    assert "degraded" in text or "degradation" in text
    assert "webfetch" in text or "openalex" in text


def test_state_fallback_chain_present():
    text = DOC.read_text(encoding="utf-8")
    assert "NotebookLM" in text
    assert "Drive" in text
    assert "Notion" in text
    assert "session-only" in text


def test_runtime_probe_verification_step_present():
    text = DOC.read_text(encoding="utf-8").lower()
    assert "runtime probe" in text
    assert "using-scriptorium" in text


def test_consensus_fencing_rule_callout():
    text = DOC.read_text(encoding="utf-8")
    assert "[paper_id:locator]" in text
    assert "[1]" in text or "numbered" in text.lower()
