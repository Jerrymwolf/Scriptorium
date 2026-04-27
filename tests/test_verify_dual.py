"""Dual-runtime verification surfaces.

Two test groups live in this file:

A. Evidence-gate citation forms — pin that the verifier accepts the
   inline `[paper_id:locator]` form *and* the wikilink `[[paper_id#locator]]`
   form. (Pre-existing.)

B. T11 — `verification-before-completion-scriptorium` skill content.
   The skill is a Scriptorium-flavored variant of the parent
   `superpowers:verification-before-completion` skill. It fires whenever
   Claude Code is about to claim a phase is complete or transition, and
   it forbids generic-optimism wording in favor of fresh
   `scriptorium verify` / `phase show` output (or the Cowork MCP
   equivalents). The "dual" in this file name is the dual-runtime (CC CLI
   + Cowork MCP) verification surface that the skill must name explicitly
   in both columns.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from scriptorium.paths import ReviewPaths
from scriptorium.reasoning.verify_citations import verify_synthesis
from scriptorium.storage.evidence import EvidenceEntry, append_evidence


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "verification-before-completion-scriptorium"
SKILL_FILE = SKILL_DIR / "SKILL.md"


# ---------------------------------------------------------------------------
# A. Evidence-gate citation-form parity (pre-existing)
# ---------------------------------------------------------------------------


def test_mixed_forms_both_supported(tmp_path):
    paths = ReviewPaths(root=tmp_path)
    append_evidence(paths, EvidenceEntry(
        paper_id="nehlig2010",
        locator="page:4",
        claim="caffeine helps",
        quote="helps",
        direction="positive",
        concept="wm",
    ))
    text = (
        "Caffeine helps working memory [nehlig2010:page:4]. "
        "Corroborated elsewhere [[nehlig2010#p-4]]."
    )
    report = verify_synthesis(text, paths)
    assert report.ok, report


# ---------------------------------------------------------------------------
# B. T11 — verification-before-completion-scriptorium skill content
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_FILE.read_text(encoding="utf-8")


# --- B1. File exists and is shaped like a skill --------------------------


def test_t11_skill_file_exists():
    assert SKILL_FILE.is_file(), (
        "T11 creates skills/verification-before-completion-scriptorium/SKILL.md"
    )


def test_t11_frontmatter_names_the_skill(skill_text: str):
    assert skill_text.startswith("---\n"), (
        "SKILL.md must open with YAML frontmatter"
    )
    # name: must match the directory name verbatim
    assert "name: verification-before-completion-scriptorium\n" in skill_text, (
        "frontmatter must contain `name: verification-before-completion-scriptorium`"
    )
    # description: line must be present and reference the trigger
    desc_match = re.search(r"^description:\s*(.+)$", skill_text, re.MULTILINE)
    assert desc_match, "description: line missing from frontmatter"
    desc = desc_match.group(1).lower()
    # Description must reference completion/phase/verify so the skill
    # auto-fires when Claude is about to make a phase-completion claim.
    assert any(tok in desc for tok in ("phase", "complete", "verify")), (
        f"description must reference phase/complete/verify; got {desc!r}"
    )


# --- B2. CLI gates: all four named verbatim ------------------------------


@pytest.mark.parametrize("gate", ["scope", "synthesis", "publish", "overview"])
def test_t11_names_all_four_cli_gates(skill_text: str, gate: str):
    """The skill must name every `--gate` value Scriptorium ships, so a
    reader knows which command applies to which phase claim."""
    assert gate in skill_text, (
        f"skill must name the `scriptorium verify --gate {gate}` value"
    )


# --- B3. Both runtimes' verification surfaces explicit -------------------


def test_t11_names_cc_verify_command(skill_text: str):
    assert "scriptorium verify" in skill_text, (
        "skill must name the CC verification command `scriptorium verify`"
    )


def test_t11_names_cc_phase_show_command(skill_text: str):
    assert "scriptorium phase show" in skill_text, (
        "skill must name the CC `scriptorium phase show` command"
    )


def test_t11_names_cowork_mcp_verify_tool(skill_text: str):
    """The skill must name the Cowork MCP `verify` tool explicitly so the
    dual-runtime contract is legible. Pairing with the CC command, not as
    a footnote."""
    # Either `MCP `verify`` or `verify` MCP tool — accept either phrasing
    # but require the substring to appear and the word "MCP" to be near it.
    text_lower = skill_text.lower()
    assert "mcp" in text_lower, "skill must mention MCP (Cowork surface)"
    # The literal string `verify` must appear paired with MCP wording.
    assert "verify" in skill_text
    # And we want a Cowork pairing — accept any of these:
    cowork_pairings = (
        "cowork: ",
        "cowork mcp",
        "mcp `verify`",
        "mcp verify",
        "`verify` tool",
    )
    assert any(p in text_lower for p in cowork_pairings), (
        f"skill must explicitly pair the CC command with a Cowork MCP "
        f"surface; expected one of: {cowork_pairings}"
    )


def test_t11_names_cowork_mcp_phase_show_tool(skill_text: str):
    assert "phase_show" in skill_text, (
        "skill must name the Cowork MCP `phase_show` tool (the Cowork "
        "equivalent of `scriptorium phase show`)"
    )


# --- B4. Phase-state evidence fields named -------------------------------


def test_t11_names_phase_state_file(skill_text: str):
    assert "phase-state.json" in skill_text, (
        "skill must reference `phase-state.json` (the load-bearing artifact)"
    )


def test_t11_names_verifier_signature_field(skill_text: str):
    assert "verifier_signature" in skill_text, (
        "skill must reference the `verifier_signature` phase-state field — "
        "this is what proves a phase is actually complete"
    )


def test_t11_names_verified_at_field(skill_text: str):
    assert "verified_at" in skill_text, (
        "skill must reference the `verified_at` phase-state field"
    )


# --- B5. Auto-downgrade behavior named -----------------------------------


def test_t11_names_auto_downgrade_behavior(skill_text: str):
    """If the protected artifact's hash changes after verification,
    `complete` auto-downgrades to `running`. The skill must name this
    behavior so a reader knows why stale verification fails."""
    text_lower = skill_text.lower()
    # Look for the artifact-change → status-change wording.
    has_signal = (
        ("downgrade" in text_lower and "running" in text_lower)
        or ("complete" in text_lower and "running" in text_lower
            and "artifact" in text_lower)
        or ("hash" in text_lower and "complete" in text_lower
            and "running" in text_lower)
    )
    assert has_signal, (
        "skill must name the auto-downgrade (`complete` -> `running` on "
        "artifact change); look for 'downgrade' / 'artifact' / 'hash' "
        "near 'complete' and 'running'"
    )


# --- B6. Reviewer-pass forward-reference (Phase 5) -----------------------


def test_t11_names_reviewer_pass_requirement(skill_text: str):
    """Synthesis-phase completion in Phase 5+ requires reviewer-pass
    JSON for both `cite` and `contradiction` reviewers. The skill must
    forward-reference this so it doesn't need re-editing later."""
    text_lower = skill_text.lower()
    assert "reviewer" in text_lower, (
        "skill must name the reviewer requirement for synthesis completion"
    )
    # Both reviewer kinds must be named — they're the two-reviewer
    # contract from plan §6.3.
    assert "cite" in text_lower
    assert "contradiction" in text_lower


# --- B7. Audit-row evidence requirement ----------------------------------


def test_t11_names_audit_evidence_requirement(skill_text: str):
    """Any phase-change claim requires a corresponding `audit.jsonl` row.
    The skill must say 'don't trust the append happened — read the row.'"""
    assert "audit.jsonl" in skill_text, (
        "skill must reference `audit.jsonl` (the row presence is the proof "
        "that an audit append actually happened)"
    )


# --- B8. Generic-optimism phrases listed as forbidden --------------------


# Floor pin: every quoted forbidden-optimism phrase the skill currently lists in
# its red-flag block. If the skill adds a new forbidden phrase, add it here too.
# These phrases must appear in a "do not say this" / red-flag context, not as
# positive guidance.
T11_FORBIDDEN_OPTIMISM_PHRASES = (
    "should pass",
    "should be complete",
    "should work",
    "looks complete",
    "looks clean",
    "looks fine",
    "phase is done",
    "synthesis is clean",
    "ready to publish",
)


@pytest.mark.parametrize("phrase", T11_FORBIDDEN_OPTIMISM_PHRASES)
def test_t11_forbids_generic_optimism_phrase(skill_text: str, phrase: str):
    """Each forbidden phrase must appear in the skill — we expect them
    to be listed as 'do not say this' patterns. Mere absence isn't
    enough; the skill must name them so a reader learns which phrases
    are not-good-enough."""
    assert phrase in skill_text, (
        f"skill must explicitly call out the forbidden optimism phrase "
        f"{phrase!r} (so a reader recognizes it next time)"
    )


def test_t11_forbidden_phrases_appear_in_negative_context(skill_text: str):
    """The forbidden phrases must NOT appear as positive guidance. We
    check that each phrase sits within ~800 chars of a negative marker
    (a red-flag / do-not / forbidden / not sufficient cue). The window
    is wide enough to span the entire red-flag bullet list from any
    bullet within it."""
    negative_markers = (
        "Red flag",
        "red flag",
        "Do not",
        "do not",
        "Not Sufficient",
        "Not sufficient",
        "not sufficient",
        "Forbidden",
        "forbidden",
        "STOP",
        "Never",
        "never",
    )
    for phrase in T11_FORBIDDEN_OPTIMISM_PHRASES:
        idx = skill_text.find(phrase)
        assert idx != -1, f"forbidden phrase {phrase!r} not present"
        window_start = max(0, idx - 800)
        window_end = min(len(skill_text), idx + 800)
        window = skill_text[window_start:window_end]
        assert any(m in window for m in negative_markers), (
            f"forbidden phrase {phrase!r} must sit near a negative marker "
            f"(one of {negative_markers}); window: {window!r}"
        )


# --- B9. Common-failures table with at least 4 rows ----------------------


def test_t11_has_common_failures_table_with_4_rows(skill_text: str):
    """Mirroring the parent skill, the file must include a structured
    table mapping <claim> -> <required evidence> -> <not sufficient>.
    At least 4 data rows so the pattern reads as a list, not a sample."""
    # Find the table by its header row containing both "Claim" and
    # "Requires" — the parent skill's pattern.
    lines = skill_text.splitlines()
    table_start = None
    for i, line in enumerate(lines):
        # The header row is a `|...|` line containing 'Claim' and either
        # 'Requires' or 'Required' or 'Evidence'.
        if line.startswith("|") and "Claim" in line and (
            "Requires" in line or "Required" in line or "Evidence" in line
        ):
            table_start = i
            break
    assert table_start is not None, (
        "no common-failures table found (expected a row starting with `|` "
        "and containing 'Claim' and 'Requires'/'Required'/'Evidence')"
    )
    # The next line is the markdown delimiter `|---|---|---|`. Then data
    # rows follow until the first non-`|` line.
    delim_idx = table_start + 1
    assert lines[delim_idx].strip().startswith("|"), (
        "expected markdown delimiter row immediately after table header"
    )
    data_rows = 0
    for line in lines[delim_idx + 1:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        data_rows += 1
    assert data_rows >= 4, (
        f"common-failures table must have at least 4 data rows; "
        f"found {data_rows}"
    )


# --- B10. When-to-apply / trigger section closes the skill ---------------


def test_t11_has_when_to_apply_section(skill_text: str):
    """A 'When to apply' (or equivalent trigger) section closes the
    skill so Claude Code knows when to fire it."""
    text_lower = skill_text.lower()
    has_section = (
        "when to apply" in text_lower
        or "when to fire" in text_lower
        or "trigger" in text_lower
    )
    assert has_section, (
        "skill must close with a 'When to apply' / 'When to fire' / "
        "'Trigger' section so the trigger condition is explicit"
    )


# --- B11. References the parent superpowers skill ------------------------


def test_t11_references_parent_superpowers_skill(skill_text: str):
    """A reader should be able to find the generic version. Per the
    stylistic guidance, cite the parent skill once near the top."""
    assert "superpowers:verification-before-completion" in skill_text.lower(), (
        "expected canonical reference 'superpowers:verification-before-completion'"
        " in skill prose so a reader can find the generic version"
    )


# --- B12. Reasonable size (intent-focused, not a how-to manual) ----------


SOFT_CAP_BYTES = 8 * 1024
HARD_CAP_BYTES = 12 * 1024  # 1.5x soft — pragmatic ceiling for a discipline skill


def test_t11_skill_size_reasonable(skill_text: str):
    """B12. Skill size soft-warns at 8 KiB; hard-fails at 12 KiB.

    Discipline skills should stay scannable. The soft cap matches the parent
    `superpowers:verification-before-completion` skill's size; the hard cap
    gives prose-edit headroom without letting the file balloon."""
    size_bytes = len(skill_text.encode("utf-8"))
    line_count = skill_text.count("\n") + 1
    assert size_bytes <= HARD_CAP_BYTES, (
        f"skill is {size_bytes} bytes; hard cap is {HARD_CAP_BYTES}"
    )
    assert line_count <= 250, (
        f"skill is {line_count} lines; cap is 250"
    )
    if size_bytes > SOFT_CAP_BYTES:
        # Print a warning visible in pytest -v output without failing.
        print(
            f"\nNOTE: SKILL.md is {size_bytes} bytes (over {SOFT_CAP_BYTES}-byte"
            f" soft cap, under {HARD_CAP_BYTES}-byte hard cap)."
        )
