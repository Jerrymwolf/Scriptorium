"""Rules-based screening filter. LLM-driven relevance happens in skills, not here."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from scriptorium.sources.base import Paper


@dataclass
class ScreenCriteria:
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    languages: list[str] = field(default_factory=list)
    must_include: list[str] = field(default_factory=list)
    must_exclude: list[str] = field(default_factory=list)


@dataclass
class ScreenResult:
    keep: bool
    reason: str


def _haystack(p: Paper) -> str:
    return f"{p.title} {p.abstract or ''}".lower()


def screen(paper: Paper, c: ScreenCriteria) -> ScreenResult:
    if c.year_min is not None and (paper.year is None or paper.year < c.year_min):
        return ScreenResult(False, f"year<{c.year_min}")
    if c.year_max is not None and (paper.year is not None and paper.year > c.year_max):
        return ScreenResult(False, f"year>{c.year_max}")
    if c.languages:
        lang = (paper.raw or {}).get("language", "en")
        if lang not in c.languages:
            return ScreenResult(False, f"language={lang}")
    hs = _haystack(paper)
    for kw in c.must_include:
        if kw.lower() not in hs:
            return ScreenResult(False, f"must_include missing: {kw}")
    for kw in c.must_exclude:
        if kw.lower() in hs:
            return ScreenResult(False, f"must_exclude hit: {kw}")
    return ScreenResult(True, "all criteria pass")
