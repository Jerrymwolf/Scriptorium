"""Page-aware PDF text extraction. Returns per-page strings + locator finder."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from pypdf import PdfReader


def extract_pages(pdf: Path) -> list[str]:
    reader = PdfReader(str(pdf))
    out: list[str] = []
    for page in reader.pages:
        out.append(page.extract_text() or "")
    return out


def find_quote_locator(pages: list[str], quote: str) -> Optional[str]:
    needle = " ".join(quote.lower().split())
    for i, text in enumerate(pages, start=1):
        haystack = " ".join(text.lower().split())
        if needle in haystack:
            return f"page:{i}"
    return None
