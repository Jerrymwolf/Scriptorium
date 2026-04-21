"""§8.2-§8.4: overview lint — 9 sections, class discipline, provenance."""
import pytest
from scriptorium.overview.linter import OverviewLintError, lint_overview


NINE = [
    "TL;DR", "Scope & exclusions", "Most-cited works in this corpus",
    "Current findings", "Contradictions in brief",
    "Recent work in this corpus (last 5 years)",
    "Methods represented in this corpus", "Gaps in this corpus", "Reading list",
]


def _sections(bodies: list[str]) -> str:
    out = []
    for name, body in zip(NINE, bodies):
        out.append(f"## {name}\n\n{body}\n\n"
                   "<!-- provenance:\n"
                   f"  section: {name.lower().replace(' ', '-')}\n"
                   "  contributing_papers: [nehlig2010]\n"
                   "  derived_from: synthesis.md\n"
                   "  generation_timestamp: 2026-04-20T14:32:08Z\n"
                   "-->")
    return "\n".join(out)


def test_valid_overview_passes():
    body = _sections(["A [[nehlig2010#p-4]]."] * 9)
    lint_overview(body)


def test_missing_section_fails():
    body = "## TL;DR\n\nA [[nehlig2010#p-4]].\n\n"
    with pytest.raises(OverviewLintError):
        lint_overview(body)


def test_section_order_enforced():
    bodies = ["A [[x#p-1]]."] * 9
    text = _sections(bodies)
    swapped = text.replace("## TL;DR", "## TLDR_BAD")
    with pytest.raises(OverviewLintError):
        lint_overview(swapped)


def test_paper_claim_without_locator_rejected():
    body = _sections(["A claim about caffeine."] + ["[[p#p-1]]"] * 8)
    with pytest.raises(OverviewLintError):
        lint_overview(body)


def test_synthesis_sentence_needs_marker():
    body = _sections(["Overall it is good."] + ["[[p#p-1]]"] * 8)
    with pytest.raises(OverviewLintError):
        lint_overview(body)


def test_synthesis_marker_without_locator_ok():
    body = _sections(
        ["Overall it is good. <!-- synthesis -->"] + ["[[p#p-1]]"] * 8
    )
    lint_overview(body)


def test_synthesis_marker_with_locator_rejected():
    body = _sections(
        ["Overall it is good. <!-- synthesis --> [[p#p-1]]"] + ["[[p#p-1]]"] * 8
    )
    with pytest.raises(OverviewLintError):
        lint_overview(body)
