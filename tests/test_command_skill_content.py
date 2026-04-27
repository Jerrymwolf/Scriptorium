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
