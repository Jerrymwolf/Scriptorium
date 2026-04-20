"""arXiv full-text fallback. Searches by title; returns PDF URL if found."""
from __future__ import annotations
from typing import Optional
import re
import httpx

BASE = "http://export.arxiv.org/api/query"
_PDF_LINK = re.compile(r'href="(http://arxiv\.org/pdf/[^"]+)"')


class ArxivClient:
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self._client = http_client

    async def find_pdf_by_title(self, title: str) -> Optional[str]:
        params = {"search_query": f'ti:"{title}"', "max_results": 1}
        if self._client:
            r = await self._client.get(BASE, params=params)
        else:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(BASE, params=params)
        r.raise_for_status()
        m = _PDF_LINK.search(r.text)
        return m.group(1) if m else None
