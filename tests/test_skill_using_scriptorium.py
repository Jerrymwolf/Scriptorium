"""T07 — Content invariants for skills/using-scriptorium/SKILL.md.

The router skill must (1) make the runtime probe its explicit FIRST step,
(2) name every degraded mode honestly with a visible warning marker, and
(3) keep the three disciplines + nine phase-skill routes intact.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "skills" / "using-scriptorium" / "SKILL.md"


@pytest.fixture(scope="module")
def text() -> str:
    return SKILL.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# A. File exists + frontmatter intact
# ---------------------------------------------------------------------------


def test_skill_exists():
    assert SKILL.exists(), f"missing {SKILL}"


def test_frontmatter_names_the_skill(text: str):
    assert text.startswith("---\nname: using-scriptorium\n"), (
        "SKILL.md must open with `---\\nname: using-scriptorium\\n`"
    )
    # description: line must mention runtime/probe/dispatch in some form so
    # the skill auto-fires when a literature review is mentioned.
    desc_match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
    assert desc_match, "description: line missing from frontmatter"
    desc = desc_match.group(1).lower()
    assert any(tok in desc for tok in ("probe", "runtime", "dispatch")), (
        f"description: must mention runtime/probe/dispatch; got {desc!r}"
    )


# ---------------------------------------------------------------------------
# B. Runtime probe is explicit AND comes first
# ---------------------------------------------------------------------------


def test_runtime_probe_is_explicit_marker_present(text: str):
    """A clearly named heading must introduce the probe — not buried prose."""
    # Accept any of: "Step 1", "First branch", "Runtime detection",
    # "Step 1: Runtime", as the probe-section marker.
    marker_re = re.compile(
        r"(Step\s*1[:\s]|First\s+branch|Runtime\s+detection)",
        re.IGNORECASE,
    )
    assert marker_re.search(text), (
        "no explicit runtime-probe marker found "
        "(expected 'Step 1', 'First branch', or 'Runtime detection')"
    )


def test_runtime_probe_appears_before_skill_routing(text: str):
    """The probe section must come before any phase-skill name."""
    marker_re = re.compile(
        r"(Step\s*1[:\s]|First\s+branch|Runtime\s+detection)",
        re.IGNORECASE,
    )
    m = marker_re.search(text)
    assert m, "runtime probe marker missing"
    probe_idx = m.start()

    phase_skills = [
        "lit-searching", "lit-screening", "lit-extracting",
        "lit-synthesizing", "lit-contradiction-check", "lit-audit-trail",
        "publishing-to-notebooklm", "running-lit-review",
    ]
    for skill_name in phase_skills:
        first_mention = text.find(skill_name)
        if first_mention == -1:
            continue  # caught by the per-skill test below
        assert probe_idx < first_mention, (
            f"runtime-probe marker (offset {probe_idx}) must precede first "
            f"mention of {skill_name!r} (offset {first_mention})"
        )


def test_runtime_probe_sets_session_state_variables(text: str):
    """Probe must set RUNTIME, STATE_BACKEND, SEARCH_TOOLS explicitly."""
    for var in ("RUNTIME", "STATE_BACKEND", "SEARCH_TOOLS"):
        assert var in text, f"probe must set session-state variable {var}"


def test_runtime_probe_lists_concrete_tool_names(text: str):
    """Probe must reference the actual tool/CLI names it inspects."""
    for tool in (
        "scriptorium version",
        "mcp__claude_ai_Consensus__search",
        "mcp__claude_ai_Scholar_Gateway__semanticSearch",
        "mcp__claude_ai_PubMed__search_articles",
        "mcp__notebooklm-mcp__notebook_create",
    ):
        assert tool in text, f"missing probe reference: {tool}"


# ---------------------------------------------------------------------------
# C. Both runtimes named and distinguished
# ---------------------------------------------------------------------------


def test_both_runtimes_named(text: str):
    assert "Claude Code" in text or " CC " in text or "(CC)" in text, (
        "skill must mention Claude Code (or CC)"
    )
    assert "Cowork" in text, "skill must mention Cowork"


# ---------------------------------------------------------------------------
# D. Capability table present (markdown table with both runtimes)
# ---------------------------------------------------------------------------


def test_capability_table_present(text: str):
    # A markdown table delimiter row plus both runtime names somewhere.
    assert "|---|" in text, "no markdown table delimiter found"
    assert "Claude Code" in text and "Cowork" in text


def test_capability_table_legacy_rows_preserved(text: str):
    # These three rows are load-bearing references for downstream skills;
    # rewrite must keep them verbatim.
    for row in (
        "| Skills (SKILL.md + description match) | ✓ | ✓ (only portable surface) |",
        "| Slash commands (`/lit-review`) | ✓ | ✗ — natural-language fires skill |",
        "| State home | disk | NotebookLM → Drive → Notion → session-only |",
    ):
        assert row in text, f"missing capability-table row: {row!r}"


# ---------------------------------------------------------------------------
# E. Three disciplines preserved (each by name)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    ["Evidence-first", "PRISMA audit", "Contradiction surfacing"],
)
def test_three_disciplines_named(text: str, phrase: str):
    assert phrase in text, f"missing discipline phrase: {phrase!r}"


# ---------------------------------------------------------------------------
# F. All nine phase skills referenced by name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "skill_name",
    [
        "lit-scoping",
        "lit-searching",
        "lit-screening",
        "lit-extracting",
        "lit-synthesizing",
        "lit-contradiction-check",
        "lit-audit-trail",
        "publishing-to-notebooklm",
        "running-lit-review",
    ],
)
def test_phase_skill_referenced(text: str, skill_name: str):
    assert skill_name in text, f"missing phase-skill reference: {skill_name}"


def test_does_not_route_to_renamed_lit_publishing(text: str):
    """v0.3 renamed lit-publishing → publishing-to-notebooklm. Must not regress."""
    # We allow 'publishing-to-notebooklm' (the canonical name); we forbid
    # the bare 'lit-publishing' token. Check by ensuring every occurrence
    # of 'lit-publishing' is actually 'publishing-to-notebooklm'.
    assert "lit-publishing" not in text, (
        "skill must route to `publishing-to-notebooklm` (v0.3 canonical), "
        "not the deprecated `lit-publishing`"
    )


# ---------------------------------------------------------------------------
# G. Degraded paths named honestly + warning marker
# ---------------------------------------------------------------------------


# Phrase pinned in the SKILL.md → token used in its warning callout.
DEGRADED_CASES = [
    ("session-only", "session-only state in Cowork"),
    ("CLI missing", "CC without scriptorium CLI on PATH"),
    ("no platform search", "Cowork without Consensus/Scholar/PubMed"),
    ("no full-text retrieval", "no full-text retrieval available"),
]


@pytest.mark.parametrize("phrase,description", DEGRADED_CASES)
def test_degraded_path_named(text: str, phrase: str, description: str):
    assert phrase in text, (
        f"missing honest naming for degraded mode "
        f"({description}): expected substring {phrase!r}"
    )


def test_degraded_paths_carry_warning_markers(text: str):
    """Each degraded phrase must sit near a warning marker (warn/tell/⚠/WARNING)."""
    warning_markers = ("warn the user", "tell the user", "⚠", "WARNING")
    # We require at least one warning marker to appear in the SKILL text;
    # and we require the marker(s) to appear in the same broad section as
    # the degraded-mode phrases. Easiest robust check: any marker present,
    # AND the first warning-marker offset and the first degraded-mode
    # offset must be within 3000 chars of each other.
    marker_offsets = [
        text.find(m) for m in warning_markers if m in text
    ]
    assert marker_offsets, (
        "no warning marker found "
        f"(expected one of: {warning_markers})"
    )
    deg_offsets = [text.find(p) for p, _ in DEGRADED_CASES if p in text]
    assert deg_offsets, "no degraded-mode phrases found"
    # At least one warning marker must be within 3000 chars of at least
    # one degraded-mode phrase.
    near = any(
        abs(m - d) <= 3000
        for m in marker_offsets
        for d in deg_offsets
    )
    assert near, (
        "warning markers exist but none sit within 3000 chars of a "
        "degraded-mode phrase; rewrite so the warning is co-located"
    )


# ---------------------------------------------------------------------------
# H. Routes to phase-appropriate skill (explicit dispatch instruction)
# ---------------------------------------------------------------------------


def test_explicit_dispatch_instruction_present(text: str):
    """Some imperative dispatch phrase must connect probe → phase skill."""
    dispatch_re = re.compile(
        r"(hand off to|fire(?:\s+the)?|dispatch to|route to)",
        re.IGNORECASE,
    )
    assert dispatch_re.search(text), (
        "no dispatch instruction found "
        "(expected one of: 'hand off to', 'fire', 'dispatch to', 'route to')"
    )


# ---------------------------------------------------------------------------
# I. No silent-inference language
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden",
    [
        "assume the runtime",
        "guess the runtime",
        "infer the runtime silently",
    ],
)
def test_no_silent_inference_language(text: str, forbidden: str):
    assert forbidden.lower() not in text.lower(), (
        f"skill must probe, not infer; forbidden phrase {forbidden!r} present"
    )


# ---------------------------------------------------------------------------
# J. References INJECTION.md (or the discipline contract it carries)
# ---------------------------------------------------------------------------


def test_references_injection_md(text: str):
    """SKILL.md should point at INJECTION.md (which T06 just landed)."""
    assert "INJECTION.md" in text, (
        "SKILL.md must reference INJECTION.md so a reader knows where the "
        "discipline contract lives (and why it's not duplicated here)"
    )


# ---------------------------------------------------------------------------
# Legacy invariants worth preserving from the pre-T07 test
# ---------------------------------------------------------------------------


def test_state_adapter_mapping_is_verbatim(text: str):
    for line in (
        "review root → `cwd` → one notebook → one folder → one page",
        "`corpus.jsonl` → file → note titled `corpus` → `corpus.jsonl` file → child page `Corpus`",
        "`evidence.jsonl` → file → note titled `evidence` → `evidence.jsonl` file → child page `Evidence`",
    ):
        assert line in text, f"missing state-adapter line: {line}"
