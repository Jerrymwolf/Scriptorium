"""Contract test for skills/lit-scoping/SKILL.md."""
from __future__ import annotations

from pathlib import Path

import pytest


SKILL_PATH = (
    Path(__file__).resolve().parent.parent
    / "skills" / "lit-scoping" / "SKILL.md"
)


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_skill_file_exists():
    assert SKILL_PATH.exists(), f"missing {SKILL_PATH}"


def test_frontmatter_name_matches(skill_text: str):
    assert "name: lit-scoping" in skill_text


def test_runtime_probe_directive(skill_text: str):
    assert "Fire `using-scriptorium` first" in skill_text


def test_mentions_all_tier1_dimensions(skill_text: str):
    for dim in ("Research question", "Purpose", "Disciplinary home"):
        assert dim in skill_text, f"missing Tier 1 dim: {dim}"


def test_mentions_all_tier2_dimensions(skill_text: str):
    for dim in (
        "Population", "Methodology", "Year range",
        "Corpus target", "Publication types", "Depth",
    ):
        assert dim in skill_text, f"missing Tier 2 dim: {dim}"


def test_mentions_tier3_menu_letters(skill_text: str):
    for letter in ("A. Conceptual frame", "B. Prior anchors",
                   "C. Output intent", "D. Known gaps", "E. Research paradigm"):
        assert letter in skill_text, f"missing Tier 3 menu item: {letter}"


def test_vagueness_threshold_is_four(skill_text: str):
    assert "< 4 resolved" in skill_text


def test_cli_invocations_present(skill_text: str):
    assert "scriptorium verify --scope" in skill_text
    assert "scriptorium audit append --phase scoping --action scope_approved" in skill_text


def test_recap_contains_all_required_fields(skill_text: str):
    for label in (
        "Research question:", "Purpose:", "Field(s):", "Population:",
        "Methodology:", "Year range:", "Corpus target:",
        "Publication types:", "Depth:",
    ):
        assert label in skill_text, f"recap missing label: {label}"


def test_approval_prompt_grammar(skill_text: str):
    assert "approve / revise <dimension> / start over" in skill_text


def test_cowork_note_present(skill_text: str):
    assert "Running in Cowork" in skill_text


def test_three_revision_cycles_policy(skill_text: str):
    assert "3 revision cycles" in skill_text


def test_never_do_section_present(skill_text: str):
    assert "What you must never do" in skill_text
