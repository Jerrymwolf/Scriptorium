"""Layer A / T09: HARD-GATE blocks in phase-critical skills.

T09 promotes the existing soft preconditions in `lit-searching`,
`lit-extracting`, `lit-synthesizing`, and `running-lit-review` into
machine-greppable HARD-GATE blocks, and adds a new gate-only skill
`lit-publishing/` that enforces phase-state preconditions before handing
off to the runtime-mechanics skill `publishing-to-notebooklm`.

These tests pin:

1. `skills/lit-publishing/SKILL.md` exists, has the right frontmatter,
   and copies the byte-identical defensive-fallback paragraph from the
   other entry-point skills.
2. Every protected skill (the 4 modified + new lit-publishing) carries
   the literal `HARD-GATE` token at least once.
3. Each protected skill names the exact artifact path / phase-state
   field it reads.
4. Each protected skill names a STOP-style refusal verb AND points the
   reader at the next skill to fire when the gate trips.
5. Each protected skill states what advisory mode looks like under
   `enforce_v04=false`. The orchestrator's advisory wording must be
   meaningfully different from the per-phase skills' (it CONTINUES the
   pipeline; the per-phase skills require explicit acknowledgement).
6. lit-publishing/SKILL.md carries a Phase-5 forward-reference about
   reviewer state.
7. lit-publishing/SKILL.md hands off to publishing-to-notebooklm with
   an explicit hand-off verb.
8. running-lit-review/SKILL.md still references `lit-publishing` (this
   was already valid as a forward-reference; T09 makes it real).

The architectural decision (gate-only `lit-publishing` vs runtime
`publishing-to-notebooklm`) is documented in the v0.4 plan §T09 brief.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = REPO_ROOT / "skills"

# The five skills that carry a HARD-GATE block after T09.
PROTECTED_SKILLS = (
    "lit-searching",
    "lit-extracting",
    "lit-synthesizing",
    "running-lit-review",
    "lit-publishing",
)

# Byte-identical defensive fallback line — copied verbatim from
# tests/test_command_skill_content.py (T08). lit-publishing must carry
# the same line, byte-for-byte, so it lines up with the other entry
# skills.
DEFENSIVE_FALLBACK_LINE = (
    "**Defensive fallback (fire `using-scriptorium` first):** If the "
    "three-discipline preamble (Evidence-first claims / PRISMA audit "
    "trail / Contradiction surfacing) is not already loaded for this "
    "session, invoke `using-scriptorium` before continuing. Primary "
    "injection runs via the Claude Code `SessionStart` hook and the "
    "Cowork MCP `instructions` field — this fallback covers the rare "
    "case where neither fired."
)


def _skill_text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# A. lit-publishing/ exists and is shaped correctly
# ---------------------------------------------------------------------------


def test_lit_publishing_skill_file_exists():
    assert (SKILLS / "lit-publishing" / "SKILL.md").is_file(), (
        "T09 creates a NEW gate-only skill at skills/lit-publishing/SKILL.md"
    )


def test_lit_publishing_frontmatter_names_the_skill():
    text = _skill_text("lit-publishing")
    assert text.startswith("---\n"), "SKILL.md must open with YAML frontmatter"
    # Must declare itself as `lit-publishing` and reference its gate role
    # in the description so it auto-fires in the right phase.
    assert "name: lit-publishing\n" in text, (
        "frontmatter must contain `name: lit-publishing`"
    )
    # description must mention 'gate' or 'precondition' so the skill's
    # role (gate, not mechanics) is legible at a glance.
    desc_window = text.split("---\n", 2)[1].lower()
    assert "gate" in desc_window or "precondition" in desc_window, (
        "lit-publishing description must name its gate / precondition role"
    )


def test_lit_publishing_carries_byte_identical_defensive_fallback():
    text = _skill_text("lit-publishing")
    assert DEFENSIVE_FALLBACK_LINE in text, (
        "lit-publishing/SKILL.md must carry the byte-identical defensive "
        "fallback line used by the other entry-point skills"
    )


# ---------------------------------------------------------------------------
# B. HARD-GATE marker present in every protected skill
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill", PROTECTED_SKILLS)
def test_hard_gate_marker_present(skill: str):
    text = _skill_text(skill)
    assert "HARD-GATE" in text, (
        f"{skill}/SKILL.md must contain the literal token `HARD-GATE` "
        "(used by reviewers and tooling to find the gate block)"
    )


# ---------------------------------------------------------------------------
# C. Each gate names the artifact / phase-state field it reads
# ---------------------------------------------------------------------------

# Per the T09 brief table (plan §T09):
#
#   skill              | reads
#   -------------------|---------------------------------------------------
#   lit-searching      | scope.json AND phase-state.json::scoping.status
#   lit-extracting     | phase-state.json::screening.status AND corpus.jsonl
#   lit-synthesizing   | phase-state.json::extraction.status AND evidence.jsonl
#   running-lit-review | (orchestrator-level — surfaces per-phase failures)
#   lit-publishing     | phase-state.json::synthesis.status AND
#                      | phase-state.json::contradiction.status
#
# The orchestrator naturally references multiple phase-state fields so we
# just require it to mention `phase-state.json` and `HARD-GATE` together.

GATE_REQUIRED_TOKENS = {
    "lit-searching": ("scope.json", "phase-state.json", "scoping.status"),
    "lit-extracting": ("phase-state.json", "screening.status", "corpus.jsonl"),
    "lit-synthesizing": ("phase-state.json", "extraction.status", "evidence.jsonl"),
    "running-lit-review": ("phase-state.json",),
    "lit-publishing": ("phase-state.json", "synthesis.status", "contradiction.status"),
}


@pytest.mark.parametrize(
    "skill,tokens",
    [(s, GATE_REQUIRED_TOKENS[s]) for s in PROTECTED_SKILLS],
)
def test_hard_gate_names_artifact_or_phase_state_field(
    skill: str, tokens: tuple[str, ...]
):
    text = _skill_text(skill)
    missing = [t for t in tokens if t not in text]
    assert not missing, (
        f"{skill}/SKILL.md gate must name {tokens}; missing: {missing}"
    )


# ---------------------------------------------------------------------------
# D. Each gate names a refusal condition AND the next skill to fire
# ---------------------------------------------------------------------------

# Pin a canonical refusal verb per skill. We pick `STOP` for the gate
# blocks so the language is consistent (and different from the
# orchestrator, which surfaces failures without `STOP` of its own).
GATE_REFUSAL_VERBS = {
    "lit-searching": "STOP",
    "lit-extracting": "STOP",
    "lit-synthesizing": "STOP",
    "running-lit-review": "halt",  # orchestrator halts the pipeline
    "lit-publishing": "STOP",
}

# Skill the gate redirects the user to fire when it refuses.
GATE_REDIRECT_TARGETS = {
    "lit-searching": "lit-scoping",
    "lit-extracting": "lit-screening",
    "lit-synthesizing": "lit-extracting",
    "running-lit-review": "lit-scoping",  # orchestrator opens with scoping
    "lit-publishing": "lit-synthesizing",  # primary redirect
}


@pytest.mark.parametrize(
    "skill,verb", list(GATE_REFUSAL_VERBS.items())
)
def test_hard_gate_names_refusal_verb(skill: str, verb: str):
    text = _skill_text(skill)
    assert verb in text, (
        f"{skill}/SKILL.md gate must use the canonical refusal verb {verb!r}"
    )


@pytest.mark.parametrize(
    "skill,target", list(GATE_REDIRECT_TARGETS.items())
)
def test_hard_gate_redirects_to_next_skill(skill: str, target: str):
    text = _skill_text(skill)
    assert target in text, (
        f"{skill}/SKILL.md gate must direct the reader to fire {target!r}"
    )


def test_lit_publishing_gate_names_both_redirect_targets():
    """lit-publishing has two preconditions (synthesis + contradiction);
    the gate should point at BOTH `lit-synthesizing` and
    `lit-contradiction-check` so the user knows which one to fire."""
    text = _skill_text("lit-publishing")
    assert "lit-synthesizing" in text
    assert "lit-contradiction-check" in text


# ---------------------------------------------------------------------------
# E. Advisory-mode wording present, with intentional asymmetry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill", PROTECTED_SKILLS)
def test_advisory_mode_named(skill: str):
    text = _skill_text(skill)
    assert "enforce_v04=false" in text, (
        f"{skill}/SKILL.md must name the `enforce_v04=false` advisory mode "
        "explicitly"
    )
    # Either 'advisory' or 'warn' is acceptable as the operating verb.
    text_lower = text.lower()
    assert "advisory" in text_lower or "warn" in text_lower, (
        f"{skill}/SKILL.md must describe advisory/warn behavior under "
        "enforce_v04=false"
    )


def test_orchestrator_advisory_continues_pipeline():
    """running-lit-review's advisory wording must say it CONTINUES the
    pipeline — that's the orchestrator-only behavior the brief calls out."""
    text = _skill_text("running-lit-review")
    text_lower = text.lower()
    # We allow either 'continue' or 'continues' or 'continue the pipeline'
    # — pick whichever reads best in prose; pin the verb root.
    assert "continue" in text_lower, (
        "running-lit-review must state advisory mode CONTINUES the pipeline"
    )


@pytest.mark.parametrize(
    "skill",
    ["lit-searching", "lit-extracting", "lit-synthesizing", "lit-publishing"],
)
def test_per_phase_advisory_requires_acknowledgement(skill: str):
    """The per-phase skills' advisory wording must say it requires
    explicit acknowledgement — different from the orchestrator's
    'continue the pipeline' behavior."""
    text = _skill_text(skill).lower()
    assert "acknowledg" in text, (
        f"{skill}/SKILL.md advisory wording must require explicit "
        "acknowledgement (look for the root 'acknowledg')"
    )


# ---------------------------------------------------------------------------
# F. lit-publishing — Phase 5 forward-reference about reviewer state
# ---------------------------------------------------------------------------


def test_lit_publishing_phase5_forward_reference():
    text = _skill_text("lit-publishing")
    # Phase 5 is the upcoming reviewer phase. The brief requires this
    # SKILL.md to forward-reference it so when Phase 5 lands, the gate
    # extends to verifier_signature without surprising the reader.
    assert "Phase 5" in text, (
        "lit-publishing must mention `Phase 5` in a forward-reference"
    )
    assert "reviewer" in text.lower(), (
        "lit-publishing forward-reference must name the reviewer role"
    )
    # Some signal that the gate gets stricter when Phase 5 lands.
    text_lower = text.lower()
    has_signal = (
        "once phase 5 lands" in text_lower
        or "forward-reference" in text_lower
        or "when phase 5" in text_lower
    )
    assert has_signal, (
        "lit-publishing must signal that the gate STRICTENS when Phase 5 "
        "lands (e.g. 'once Phase 5 lands' or 'forward-reference')"
    )


# ---------------------------------------------------------------------------
# G. lit-publishing hands off to publishing-to-notebooklm
# ---------------------------------------------------------------------------


def test_lit_publishing_hands_off_to_publishing_to_notebooklm():
    text = _skill_text("lit-publishing")
    assert "publishing-to-notebooklm" in text, (
        "lit-publishing must reference the runtime-mechanics skill "
        "`publishing-to-notebooklm` by name"
    )
    # Hand-off verb of some kind — pick from the canonical set used by
    # the other skills.
    handoff_verbs = ("hand off", "hands off", "hand-off", "fire", "dispatch")
    text_lower = text.lower()
    assert any(v in text_lower for v in handoff_verbs), (
        "lit-publishing must use an explicit hand-off verb when pointing "
        f"at publishing-to-notebooklm (one of: {handoff_verbs})"
    )


# ---------------------------------------------------------------------------
# H. running-lit-review still references lit-publishing
# ---------------------------------------------------------------------------


def test_running_lit_review_references_lit_publishing():
    """The existing `tests/test_skill_running_lit_review.py::test_names_every_phase_skill_in_order`
    pins this; we duplicate the assertion here so the T09 test file is
    self-contained."""
    text = _skill_text("running-lit-review")
    assert "lit-publishing" in text, (
        "running-lit-review must still reference `lit-publishing` (the "
        "publishing phase entry point), now that it actually exists"
    )
