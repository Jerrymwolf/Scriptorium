"""Lint rules for overview.md (§8.2-§8.4)."""
from __future__ import annotations

import re


REQUIRED_SECTIONS = [
    "TL;DR",
    "Scope & exclusions",
    "Most-cited works in this corpus",
    "Current findings",
    "Contradictions in brief",
    "Recent work in this corpus (last 5 years)",
    "Methods represented in this corpus",
    "Gaps in this corpus",
    "Reading list",
]

_PROVENANCE_REQUIRED = {
    "section", "contributing_papers", "derived_from", "generation_timestamp",
}

_PAPER_LOCATOR = re.compile(r"\[\[[A-Za-z0-9_.\-]+#[^\]]+\]\]|\[[A-Za-z0-9_.\-]+:[^\]]+\]")
_SYNTH_MARKER = re.compile(r"<!--\s*synthesis\s*-->")


class OverviewLintError(Exception):
    pass


def lint_overview(text: str) -> None:
    headings = [m.group(1) for m in re.finditer(r"^##\s+(.+)$", text, re.M)]
    if headings != REQUIRED_SECTIONS:
        raise OverviewLintError(
            f"overview sections mismatch. Expected {REQUIRED_SECTIONS}; got {headings}."
        )

    sections = re.split(r"^##\s+.+$", text, flags=re.M)[1:]
    for name, body in zip(REQUIRED_SECTIONS, sections):
        _check_provenance(name, body)
        _check_citation_classes(name, body)


def _check_provenance(name: str, body: str) -> None:
    m = re.search(r"<!--\s*provenance:(.*?)-->", body, re.S)
    if not m:
        raise OverviewLintError(f"section {name!r}: missing provenance block")
    block = m.group(1)
    keys = {
        ln.split(":", 1)[0].strip()
        for ln in block.strip().splitlines()
        if ":" in ln
    }
    missing = _PROVENANCE_REQUIRED - keys
    if missing:
        raise OverviewLintError(
            f"section {name!r}: provenance missing {sorted(missing)}"
        )


def _check_citation_classes(name: str, body: str) -> None:
    cleaned = _strip_provenance(body)
    # Split on sentence-ending punctuation followed by whitespace,
    # but NOT when that whitespace immediately precedes an HTML comment.
    raw_sentences = re.split(r"(?<=[.!?])\s+(?!<!--)", cleaned)
    # Merge any trailing HTML-comment-only fragments back onto the previous sentence.
    merged: list[str] = []
    for s in raw_sentences:
        s = s.strip()
        if not s:
            continue
        # If this token is purely an HTML comment (no real text before it),
        # attach it to the previous sentence so the marker applies to it.
        if merged and re.fullmatch(r"<!--.*?-->", s, re.S):
            merged[-1] = merged[-1] + " " + s
        else:
            merged.append(s)

    for s in merged:
        has_locator = bool(_PAPER_LOCATOR.search(s))
        has_synth = bool(_SYNTH_MARKER.search(s))
        if has_locator and has_synth:
            raise OverviewLintError(
                f"section {name!r}: synthesis marker cannot appear with a paper locator: {s!r}"
            )
        if not has_locator and not has_synth:
            raise OverviewLintError(
                f"section {name!r}: sentence without locator or synthesis marker: {s!r}"
            )


def _strip_provenance(body: str) -> str:
    return re.sub(r"<!--\s*provenance:.*?-->", "", body, flags=re.S)
