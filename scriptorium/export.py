"""Render overview.md → overview.docx with citation enrichment.

Best-effort converter: handles only the markdown shapes Scriptorium emits
(H1/H2/H3 headings, paragraphs, bullet/ordered lists, tables, inline
bold/italic/code, and `[paper_id:locator]` citations).

Failure must never block overview generation — the .md is the source of truth.
"""
from __future__ import annotations

from pathlib import Path
