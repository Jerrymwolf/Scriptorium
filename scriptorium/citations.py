"""Cite parser that accepts v0.2 `[paper_id:locator]` and v0.3 `[[paper_id#locator]]`.

Normalization (§6.3):
  - v0.3 wikilink `[[id#p-N]]` maps to `Citation(id, "page:N")`.
  - v0.3 wikilink `[[id#<loc>]]` where `<loc>` is not `p-N` is passed through
    as the locator verbatim (so `[[id#methods]]` -> `Citation(id, "methods")`).
  - Legacy `[id:loc]` is passed through verbatim.

Both forms are used by the evidence gate: a `Citation` is resolved against
`evidence.jsonl` by exact (paper_id, locator) match.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    paper_id: str
    locator: str


_LEGACY = re.compile(r"\[([A-Za-z0-9_.\-]+):([^\]]+)\]")
_WIKI = re.compile(r"\[\[([A-Za-z0-9_.\-]+)#([^\]]+)\]\]")


def _normalize_wiki_locator(raw: str) -> str:
    m = re.fullmatch(r"p-(\d+)", raw.strip())
    if m:
        return f"page:{m.group(1)}"
    return raw.strip()


def parse_citations(text: str) -> list[Citation]:
    cites: list[Citation] = []
    for m in _WIKI.finditer(text):
        cites.append(Citation(m.group(1), _normalize_wiki_locator(m.group(2))))
    for m in _LEGACY.finditer(text):
        cites.append(Citation(m.group(1), m.group(2)))
    return cites
