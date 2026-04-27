"""§13.2 stale-command scan: forbidden nlm shapes must be absent everywhere."""
from pathlib import Path


FORBIDDEN = [
    "nlm auth login",
    "nlm studio create",
    "nlm source upload",
    "--confirm",
]

ALLOWED_WITH_CONFIRM = {"docs/publishing-notebooklm.md"}


def test_no_forbidden_tokens_in_plugin_surface():
    repo = Path(__file__).resolve().parent.parent
    targets = list((repo / ".claude-plugin").rglob("*.md"))
    targets += list((repo / "docs").rglob("*.md")) if (repo / "docs").is_dir() else []
    problems: list[str] = []
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for bad in FORBIDDEN:
            if bad in text:
                rel = str(path.relative_to(repo))
                if rel in ALLOWED_WITH_CONFIRM and bad == "--confirm":
                    continue
                problems.append(f"{rel}: {bad!r}")
    assert problems == [], f"stale nlm tokens: {problems}"


def test_running_lit_review_dispatches_to_lit_scoping():
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    txt = (repo / "skills" / "running-lit-review" / "SKILL.md").read_text()
    assert "lit-scoping" in txt, "running-lit-review does not invoke lit-scoping"
    assert "Inputs you need before starting" not in txt, "old flat intake block still present"


def test_lit_searching_requires_scope_json():
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    txt = (repo / "skills" / "lit-searching" / "SKILL.md").read_text()
    assert "scope.json" in txt, "lit-searching does not read scope.json"
    assert "lit-scoping" in txt, "lit-searching does not mention auto-trigger"


def test_using_scriptorium_mentions_lit_scoping():
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    txt = (repo / "skills" / "using-scriptorium" / "SKILL.md").read_text()
    assert "lit-scoping" in txt


def test_verified_commands_appear_in_skills():
    repo = Path(__file__).resolve().parent.parent
    skills = (repo / "skills" / "publishing-to-notebooklm"
              / "SKILL.md").read_text(encoding="utf-8")
    for cmd in ("nlm doctor", "nlm notebook create", "nlm source add",
                "nlm audio create", "nlm slides create",
                "nlm mindmap create", "nlm video create", "nlm login"):
        assert cmd in skills, f"missing verified command: {cmd}"


# ---------------------------------------------------------------------------
# T08 — defensive skill-router fallback
#
# T01 (Phase 0 / test_layer_a_runtime_parity.py) graded the Cowork MCP
# `instructions` cadence as "pass". Per the v0.4 plan, that flips T08 from
# REQUIRED to DEFENSIVE. The user has explicitly directed: keep a thin
# fallback layer for resilience, but with defensive (not mandatory) tone.
#
# These tests pin:
#   1. the fallback is present in each of the 5 affected skills
#   2. the wording is byte-identical across all 5 skills
#   3. the fallback appears early (first ~1200 bytes — before any H2)
#   4. the fallback's existence is locked to T01's grade
#   5. the wording uses defensive tone, not mandatory tone
#   6. the wording names all three disciplines verbatim
#   7. the wording names both injection paths (CC SessionStart, Cowork
#      MCP instructions field)
#   8. the wording references `using-scriptorium` in backticks
# ---------------------------------------------------------------------------

T08_AFFECTED_SKILLS = (
    "running-lit-review",
    "lit-searching",
    "lit-screening",
    "lit-extracting",
    "lit-synthesizing",
)

T08_FALLBACK_LINE = (
    "**Defensive fallback (fire `using-scriptorium` first):** If the "
    "three-discipline preamble (Evidence-first claims / PRISMA audit "
    "trail / Contradiction surfacing) is not already loaded for this "
    "session, invoke `using-scriptorium` before continuing. Primary "
    "injection runs via the Claude Code `SessionStart` hook and the "
    "Cowork MCP `instructions` field — this fallback covers the rare "
    "case where neither fired."
)


def _t08_skill_path(skill_name: str):
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    return repo / "skills" / skill_name / "SKILL.md"


def _t08_extract_fallback_block(text: str) -> str:
    """Return the single line that begins with the Defensive fallback marker.

    The fallback is a single self-contained block (one bolded label + at
    most two sentences). In markdown that lives on a single logical line.
    """
    marker = "**Defensive fallback"
    for line in text.splitlines():
        if marker in line:
            return line
    raise AssertionError(f"no line containing {marker!r} found")


def test_t08_fallback_present_in_all_affected_skills():
    for skill in T08_AFFECTED_SKILLS:
        text = _t08_skill_path(skill).read_text(encoding="utf-8")
        assert T08_FALLBACK_LINE in text, (
            f"{skill}/SKILL.md missing T08 defensive fallback line"
        )


def test_t08_fallback_wording_is_byte_identical_across_skills():
    blocks = []
    for skill in T08_AFFECTED_SKILLS:
        text = _t08_skill_path(skill).read_text(encoding="utf-8")
        blocks.append((skill, _t08_extract_fallback_block(text)))
    first_skill, first_block = blocks[0]
    for skill, block in blocks[1:]:
        assert block == first_block, (
            f"fallback wording drift: {first_skill} vs {skill}\n"
            f"  {first_skill}: {first_block!r}\n"
            f"  {skill}: {block!r}"
        )


def test_t08_fallback_appears_early():
    """Fallback must precede every `## ` H2 section header and live in the
    first ~1200 bytes of each skill (after frontmatter + H1)."""
    marker = "**Defensive fallback"
    for skill in T08_AFFECTED_SKILLS:
        text = _t08_skill_path(skill).read_text(encoding="utf-8")
        idx = text.find(marker)
        assert idx != -1, f"{skill}: fallback marker not found"
        assert idx <= 1200, (
            f"{skill}: fallback at byte {idx} > 1200; should appear before"
            " the first H2 section"
        )
        # First H2 (line starting with "## ") must come AFTER the fallback.
        first_h2 = text.find("\n## ")
        assert first_h2 == -1 or first_h2 > idx, (
            f"{skill}: an H2 section appears before the fallback line"
        )


def test_t08_fallback_status_is_defensive_per_t01():
    from tests.test_layer_a_runtime_parity import (
        COWORK_MCP_INSTRUCTION_CADENCE,
        T08_FALLBACK_STATUS,
    )
    assert COWORK_MCP_INSTRUCTION_CADENCE == "pass", (
        "T01 cadence grade flipped — re-evaluate whether the T08 fallback "
        "should be promoted from defensive to required."
    )
    assert T08_FALLBACK_STATUS == "defensive", (
        "T08_FALLBACK_STATUS no longer 'defensive'; current fallback wording "
        "is sized for the defensive grade."
    )


def test_t08_fallback_uses_defensive_tone():
    defensive_markers = ("Defensive fallback", "not already loaded")
    forbidden_mandatory = ("MUST fire", "REQUIRED")
    for skill in T08_AFFECTED_SKILLS:
        text = _t08_skill_path(skill).read_text(encoding="utf-8")
        block = _t08_extract_fallback_block(text)
        for marker in defensive_markers:
            assert marker in block, (
                f"{skill}: fallback missing defensive marker {marker!r}"
            )
        for bad in forbidden_mandatory:
            assert bad not in block, (
                f"{skill}: fallback contains mandatory-tone token {bad!r}; "
                "T08 is graded defensive, wording must stay defensive"
            )


def test_t08_fallback_names_three_disciplines():
    disciplines = (
        "Evidence-first claims",
        "PRISMA audit trail",
        "Contradiction surfacing",
    )
    for skill in T08_AFFECTED_SKILLS:
        block = _t08_extract_fallback_block(
            _t08_skill_path(skill).read_text(encoding="utf-8")
        )
        for d in disciplines:
            assert d in block, (
                f"{skill}: fallback does not name discipline {d!r} verbatim"
            )


def test_t08_fallback_names_both_injection_paths():
    for skill in T08_AFFECTED_SKILLS:
        block = _t08_extract_fallback_block(
            _t08_skill_path(skill).read_text(encoding="utf-8")
        )
        assert "SessionStart" in block, (
            f"{skill}: fallback does not name the Claude Code SessionStart "
            "hook injection path"
        )
        assert "instructions" in block, (
            f"{skill}: fallback does not name the Cowork MCP `instructions` "
            "field injection path"
        )


def test_t08_fallback_references_using_scriptorium():
    for skill in T08_AFFECTED_SKILLS:
        block = _t08_extract_fallback_block(
            _t08_skill_path(skill).read_text(encoding="utf-8")
        )
        assert "`using-scriptorium`" in block, (
            f"{skill}: fallback does not reference `using-scriptorium` in "
            "backticks"
        )


# ---------------------------------------------------------------------------
# T10 — red-flag tables and runtime-honesty wording
#
# T10 adds two additive artifacts to four phase skills (lit-screening,
# lit-contradiction-check, lit-extracting, lit-synthesizing):
#
#   1. A `## Red flags — do NOT` section (canonical header borrowed from
#      `using-scriptorium/INJECTION.md`) containing skill-specific
#      "Do NOT ..." bullets — closing safety net before hand-off.
#   2. The `⚠` Unicode warning marker in the Cowork (degraded-path)
#      section, with explicit naming of the degraded mode and what is
#      lost — never implied parity with CC.
#
# These tests pin:
#   - the exact red-flag header bytes appear in all four skills
#   - lit-synthesizing's old `## What not to do` header is GONE
#     (renamed to the canonical header for cross-skill consistency)
#   - each skill carries at least 3 "Do NOT ..." bullets in its red-flag
#     list
#   - per-skill discipline-critical red flags are present (audit-append
#     for screening/extracting, evidence fabrication for extracting/
#     synthesizing, contradiction-suppression for contradiction-check
#     and synthesizing)
#   - the `⚠` marker appears at least once in each Cowork section
#   - each Cowork section names a degraded-mode label and what is lost
#   - the red-flag section sits AFTER the workflow body and BEFORE the
#     hand-off section in each skill
#   - additivity: the T08 fallback line and T09 HARD-GATE blocks remain
#     byte-identical
#   - additivity: the existing `## v0.3 additions` blocks remain
# ---------------------------------------------------------------------------

T10_RED_FLAG_SKILLS = (
    "lit-screening",
    "lit-contradiction-check",
    "lit-extracting",
    "lit-synthesizing",
)

T10_RED_FLAG_HEADER = "## Red flags — do NOT"

# Skills that have a Cowork-path section (a degraded path that must
# carry the ⚠ marker after T10). All four affected skills have one.
T10_COWORK_SKILLS = T10_RED_FLAG_SKILLS

# T09 HARD-GATE blocks that must remain byte-identical after T10. Pulled
# from the on-disk skills at T09 commit 94c80a6 — used for additivity.
T09_HARD_GATE_EXTRACTING = (
    "## HARD-GATE — screening must be complete and corpus must have kept rows\n"
    "\n"
    "`lit-extracting` reads two signals at startup before fetching any full text:\n"
    "\n"
    "- `<review_root>/.scriptorium/phase-state.json::phases.screening.status`"
    ' — must be `"complete"`.\n'
    "- `<review_root>/corpus.jsonl` — must contain at least one row at "
    '`status: "kept"`.'
)

T09_HARD_GATE_SYNTHESIZING = (
    "## HARD-GATE — extraction must be complete and evidence.jsonl must have rows\n"
    "\n"
    "`lit-synthesizing` reads two signals at startup before drafting any prose:\n"
    "\n"
    "- `<review_root>/.scriptorium/phase-state.json::phases.extraction.status`"
    ' — must be `"complete"`.\n'
    "- `<review_root>/evidence.jsonl` — must exist and contain at least one row."
)


def _t10_skill_path(skill_name: str):
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    return repo / "skills" / skill_name / "SKILL.md"


def _t10_extract_red_flag_block(text: str) -> str:
    """Return everything from the Red-flag header through the next H2.

    Includes the header line and every line up to (but not including)
    the next `## ` H2 — that's the bullet block we want to test.
    """
    marker = T10_RED_FLAG_HEADER
    idx = text.find(marker)
    if idx == -1:
        raise AssertionError(f"no {marker!r} header found")
    rest = text[idx:]
    # Find the next H2 after the header line itself.
    next_h2 = rest.find("\n## ", len(marker))
    if next_h2 == -1:
        return rest
    return rest[:next_h2]


# --- Red-flag header presence and rename ---------------------------------


def test_t10_red_flag_header_present_in_all_four_skills():
    for skill in T10_RED_FLAG_SKILLS:
        text = _t10_skill_path(skill).read_text(encoding="utf-8")
        assert T10_RED_FLAG_HEADER in text, (
            f"{skill}/SKILL.md missing canonical red-flag header "
            f"{T10_RED_FLAG_HEADER!r}"
        )


def test_t10_lit_synthesizing_old_header_is_gone():
    """lit-synthesizing previously had `## What not to do`; T10 renames
    it to the canonical `## Red flags — do NOT` header so the wording is
    consistent across the four phase skills. This pins the rename."""
    text = _t10_skill_path("lit-synthesizing").read_text(encoding="utf-8")
    assert "## What not to do" not in text, (
        "lit-synthesizing/SKILL.md still has the old `## What not to do` "
        "header — T10 renames it to the canonical "
        f"{T10_RED_FLAG_HEADER!r}"
    )


# --- Red-flag bullet content -------------------------------------------------


def test_t10_red_flag_block_has_minimum_bullets():
    """Each red-flag block must carry at least 3 `Do NOT ...` bullets —
    one bullet is not a list."""
    for skill in T10_RED_FLAG_SKILLS:
        text = _t10_skill_path(skill).read_text(encoding="utf-8")
        block = _t10_extract_red_flag_block(text)
        bullets = [
            line for line in block.splitlines()
            if line.startswith("- Do NOT ") or line.startswith("- DO NOT ")
        ]
        assert len(bullets) >= 3, (
            f"{skill}/SKILL.md red-flag block has only {len(bullets)} "
            f"`Do NOT ...` bullets; need at least 3"
        )


# Per-skill discipline-critical red flags. We assert presence of small
# substrings inside the red-flag block (not the whole skill) so the test
# pins the bullet's location, not just stray prose.
T10_REQUIRED_RED_FLAG_SUBSTRINGS = {
    "lit-screening": (
        "audit",          # don't skip the screening audit-append
        "reason",         # don't drop without setting reason
    ),
    "lit-contradiction-check": (
        "average",        # don't average disagreement away
        "[paper_id:locator]",  # don't write a camp without inline cites
    ),
    "lit-extracting": (
        "audit",          # don't skip the extraction audit-append
        "fabricate",      # don't fabricate locator values
    ),
    "lit-synthesizing": (
        "invent",         # don't invent paper ids/locators
        "cite-check",     # don't omit the cite-check
    ),
}


def test_t10_per_skill_required_red_flags_present():
    for skill, substrings in T10_REQUIRED_RED_FLAG_SUBSTRINGS.items():
        text = _t10_skill_path(skill).read_text(encoding="utf-8")
        block = _t10_extract_red_flag_block(text)
        missing = [s for s in substrings if s not in block]
        assert not missing, (
            f"{skill}/SKILL.md red-flag block missing required "
            f"discipline-critical substrings: {missing}"
        )


# --- Section ordering: red flags AFTER workflow, BEFORE hand-off ----------


def test_t10_red_flag_section_sits_before_handoff():
    """Red-flag section must appear AFTER the main workflow body and
    BEFORE the hand-off section so it reads as a closing safety net."""
    for skill in T10_RED_FLAG_SKILLS:
        text = _t10_skill_path(skill).read_text(encoding="utf-8")
        red_idx = text.find(T10_RED_FLAG_HEADER)
        handoff_idx = text.find("## Hand-off")
        assert red_idx != -1, f"{skill}: no red-flag header"
        assert handoff_idx != -1, f"{skill}: no `## Hand-off` header"
        assert red_idx < handoff_idx, (
            f"{skill}/SKILL.md: red-flag section at byte {red_idx} must "
            f"precede `## Hand-off` at byte {handoff_idx}"
        )


# --- Runtime-honesty: ⚠ marker in each Cowork section ---------------------


def test_t10_warning_marker_in_each_skill():
    """The ⚠ Unicode marker must appear at least once in each affected
    skill — used in the Cowork (degraded-path) section to name what is
    lost vs CC."""
    for skill in T10_COWORK_SKILLS:
        text = _t10_skill_path(skill).read_text(encoding="utf-8")
        assert "\u26a0" in text, (
            f"{skill}/SKILL.md: missing ⚠ Unicode marker (U+26A0); the "
            "Cowork section must name the degraded mode honestly"
        )


def _t10_extract_cowork_section(text: str) -> str:
    """Return the Cowork-path section body.

    Skills name the Cowork path two different ways:

    1. As an H2 — `## Workflow — Cowork` / `## Workflow — Cowork path`
       (lit-screening, lit-extracting, lit-contradiction-check). We
       slice from that H2 to the next H2.
    2. As a `**Cowork:**` bolded paragraph inside `## Runtime specifics`
       (lit-synthesizing). We slice from the `**Cowork:**` line to the
       next blank line followed by `**` or `## ` (i.e. end of paragraph).

    Both shapes count as "the Cowork section" for runtime-honesty
    purposes — they're where the ⚠ marker must live.
    """
    lines = text.splitlines(keepends=True)
    # Shape 1: H2 header containing 'Cowork'
    for i, line in enumerate(lines):
        if line.startswith("## ") and "Cowork" in line:
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("## "):
                    end = j
                    break
            return "".join(lines[i:end])
    # Shape 2: `**Cowork:**` bolded paragraph
    for i, line in enumerate(lines):
        if line.startswith("**Cowork:**"):
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("## ") or lines[j].startswith("**"):
                    end = j
                    break
            return "".join(lines[i:end])
    raise AssertionError("no Cowork section found (no H2 with 'Cowork' and no '**Cowork:**' bold paragraph)")


def test_t10_cowork_section_carries_warning_marker():
    """The ⚠ marker MUST be inside the Cowork section, not buried
    elsewhere in the skill. Each Cowork section names the degraded mode
    using the `⚠ <name>: <what is lost>` format established by
    `using-scriptorium/SKILL.md` §3."""
    for skill in T10_COWORK_SKILLS:
        text = _t10_skill_path(skill).read_text(encoding="utf-8")
        cowork = _t10_extract_cowork_section(text)
        assert "\u26a0" in cowork, (
            f"{skill}/SKILL.md: ⚠ marker missing from the Cowork section"
        )


# Per-skill terms that must appear inside the Cowork section, naming
# what is lost / which capability is degraded. Substring assertions —
# the prose can vary but these load-bearing words must show up.
T10_COWORK_DEGRADATION_TERMS = {
    "lit-screening": (
        "manual",      # screener falls back to in-prose / manual evaluation
    ),
    "lit-contradiction-check": (
        "manual",      # manual grouping by concept (no `scriptorium contradictions`)
    ),
    "lit-extracting": (
        "Unpaywall",   # Unpaywall not available in Cowork
        "arXiv",       # arXiv not available in Cowork
    ),
    "lit-synthesizing": (
        "no hook",     # no PostToolUse hook in Cowork
        "scriptorium verify",  # no `scriptorium verify` in Cowork
    ),
}


def test_t10_cowork_section_names_degraded_capability():
    for skill, terms in T10_COWORK_DEGRADATION_TERMS.items():
        text = _t10_skill_path(skill).read_text(encoding="utf-8")
        cowork = _t10_extract_cowork_section(text)
        missing = [t for t in terms if t not in cowork]
        assert not missing, (
            f"{skill}/SKILL.md Cowork section must name degraded "
            f"capabilities {terms}; missing: {missing}"
        )


# --- Additivity: T08 fallback line and T09 HARD-GATE blocks unchanged ----


def test_t10_preserves_t08_fallback_in_three_affected_skills():
    """T10 is additive — the T08 defensive-fallback line in
    lit-screening, lit-extracting, and lit-synthesizing must remain
    byte-identical. (lit-contradiction-check is NOT a T08 skill, so we
    don't assert it carries the fallback.)"""
    for skill in ("lit-screening", "lit-extracting", "lit-synthesizing"):
        text = _t10_skill_path(skill).read_text(encoding="utf-8")
        assert T08_FALLBACK_LINE in text, (
            f"{skill}/SKILL.md: T10 edits broke the T08 defensive "
            "fallback line (must remain byte-identical)"
        )


def test_t10_lit_contradiction_check_has_no_t08_fallback():
    """lit-contradiction-check is NOT in the T08 affected list. Pin the
    asymmetry so a future drive-by edit doesn't grow it into one."""
    text = _t10_skill_path("lit-contradiction-check").read_text(encoding="utf-8")
    assert T08_FALLBACK_LINE not in text, (
        "lit-contradiction-check/SKILL.md should NOT carry the T08 "
        "defensive-fallback line — it is not a T08-affected skill"
    )


def test_t10_preserves_t09_hard_gate_in_lit_extracting():
    text = _t10_skill_path("lit-extracting").read_text(encoding="utf-8")
    assert T09_HARD_GATE_EXTRACTING in text, (
        "lit-extracting/SKILL.md: T10 edits broke the T09 HARD-GATE "
        "block (header + reads-list must remain byte-identical)"
    )


def test_t10_preserves_t09_hard_gate_in_lit_synthesizing():
    text = _t10_skill_path("lit-synthesizing").read_text(encoding="utf-8")
    assert T09_HARD_GATE_SYNTHESIZING in text, (
        "lit-synthesizing/SKILL.md: T10 edits broke the T09 HARD-GATE "
        "block (header + reads-list must remain byte-identical)"
    )


def test_t10_preserves_v03_additions_blocks():
    """Three of the four T10-affected skills carry a `## v0.3 additions`
    block (lit-contradiction-check, lit-extracting, lit-synthesizing).
    Pin that they remain after T10 — the trailing v0.3 paragraphs are
    not swept away by the new red-flag section."""
    for skill in (
        "lit-contradiction-check",
        "lit-extracting",
        "lit-synthesizing",
    ):
        text = _t10_skill_path(skill).read_text(encoding="utf-8")
        assert "## v0.3 additions" in text, (
            f"{skill}/SKILL.md: T10 edits removed the `## v0.3 additions` "
            "block (must remain present)"
        )
