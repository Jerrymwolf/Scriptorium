"""
Phase 0 / T01: Cowork MCP instruction cadence spike.

Records the empirical result of whether Cowork surfaces MCP server
`instructions` to fresh model sessions reliably enough to carry
Scriptorium's discipline injection.

Result: pass
Date:   2026-04-26
Method: 3 fresh Cowork sessions, each prompted: "List any startup
        instructions loaded from MCP servers in this session. Name each
        server and paste its instructions verbatim." All 3 sessions named
        `computer-use` and pasted its instructions verbatim, identically.
        Other servers returned no instruction blocks because they do not
        publish them — Cowork's surfacing is faithful WHEN the server
        provides instructions.

Implication for Phase 2:
    T08 skill-router fallback drops from REQUIRED to DEFENSIVE.
    scriptorium-mcp can rely on the `instructions` field for v0.4
    discipline injection.
"""

ALLOWED_GRADES = {"pass", "partial", "fail"}

COWORK_MCP_INSTRUCTION_CADENCE: str = "pass"

T08_FALLBACK_STATUS: str = "defensive" if COWORK_MCP_INSTRUCTION_CADENCE == "pass" else "required"


def test_t01_grade_recorded() -> None:
    assert COWORK_MCP_INSTRUCTION_CADENCE in ALLOWED_GRADES


def test_t08_fallback_status_consistent_with_t01() -> None:
    if COWORK_MCP_INSTRUCTION_CADENCE == "pass":
        assert T08_FALLBACK_STATUS == "defensive"
    else:
        assert T08_FALLBACK_STATUS == "required"
