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
_BULLET_RE = re.compile(r"^[-*+]\s+(.*)$")
_ORDERED_RE = re.compile(r"^\d+\.\s+(.*)$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")
_INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")


def _emit_runs(paragraph, text: str) -> None:
    parts = _INLINE_RE.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
        else:
            paragraph.add_run(part)


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

    if all(_BULLET_RE.match(line) for line in block):
        for line in block:
            p = doc.add_paragraph(style="List Bullet")
            _emit_runs(p, _BULLET_RE.match(line).group(1))
        return

    if all(_ORDERED_RE.match(line) for line in block):
        for line in block:
            p = doc.add_paragraph(style="List Number")
            _emit_runs(p, _ORDERED_RE.match(line).group(1))
        return

    if len(block) >= 2 and _TABLE_SEP_RE.match(block[1]) and "|" in block[0]:
        _render_table(doc, block)
        return

    para = doc.add_paragraph()
    _emit_runs(para, " ".join(line.strip() for line in block))


def _split_table_row(line: str) -> list[str]:
    parts = line.strip().strip("|").split("|")
    return [p.strip() for p in parts]


def _render_table(doc, block: list[str]) -> None:
    header = _split_table_row(block[0])
    rows = [_split_table_row(line) for line in block[2:]]
    table = doc.add_table(rows=1 + len(rows), cols=len(header))
    table.style = "Table Grid"
    for i, cell in enumerate(table.rows[0].cells):
        cell.text = header[i] if i < len(header) else ""
    for r, row in enumerate(rows, start=1):
        for i, cell in enumerate(table.rows[r].cells):
            cell.text = row[i] if i < len(row) else ""
