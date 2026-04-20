"""PubMed Central OA service. PMCID → PDF URL."""
from __future__ import annotations
from typing import Optional
import re
import httpx

BASE = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
_PDF_LINK = re.compile(r'format="pdf"\s+href="([^"]+)"')


class PMCClient:
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self._client = http_client

    async def find_pdf(self, pmcid: str) -> Optional[str]:
        if self._client:
            r = await self._client.get(BASE, params={"id": pmcid})
        else:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(BASE, params={"id": pmcid})
        r.raise_for_status()
        m = _PDF_LINK.search(r.text)
        return m.group(1) if m else None
