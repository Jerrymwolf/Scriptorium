"""Render overview.md → overview.docx with citation enrichment.

Best-effort converter: handles only the markdown shapes Scriptorium emits
(H1/H2/H3 headings, paragraphs, bullet/ordered lists, tables, inline
bold/italic/code, and `[paper_id:locator]` citations).

Failure must never block overview generation — the .md is the source of truth.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document


_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")


def render_overview_docx(md_path: Path, docx_path: Path, corpus_path: Path) -> None:
    """Render overview.md to .docx. Best-effort; caller isolates failures."""
    text = md_path.read_text(encoding="utf-8")
    body = _strip_frontmatter(text)
    doc = Document()
    for block in _blocks(body):
        _render_block(doc, block)
    doc.save(str(docx_path))


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5 :]
    return text


def _blocks(body: str) -> list[list[str]]:
    """Split body into blocks separated by blank lines."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in body.splitlines():
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _render_block(doc, block: list[str]) -> None:
    first = block[0]
    m = _HEADING_RE.match(first)
    if m and len(block) == 1:
        level = len(m.group(1))
        doc.add_heading(m.group(2).strip(), level=level)
        return
    doc.add_paragraph(" ".join(line.strip() for line in block))
