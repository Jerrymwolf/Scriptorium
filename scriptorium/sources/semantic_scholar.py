"""Semantic Scholar adapter (opt-in)."""
from __future__ import annotations
from typing import Optional
import httpx
from scriptorium.sources.base import SourceAdapter, Paper, normalize_doi

BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS = "paperId,title,year,authors,venue,externalIds,abstract,openAccessPdf"

class SemanticScholarAdapter(SourceAdapter):
    name = "semantic_scholar"

    def __init__(self, api_key: Optional[str] = None, http_client: Optional[httpx.AsyncClient] = None):
        self.api_key = api_key
        self._client = http_client

    def _headers(self) -> dict:
        return {"x-api-key": self.api_key} if self.api_key else {}

    async def _get(self, url: str, params: dict | None = None) -> dict:
        if self._client:
            r = await self._client.get(url, params=params, headers=self._headers())
        else:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(url, params=params, headers=self._headers())
        r.raise_for_status()
        return r.json()

    async def search(self, query: str, limit: int = 50) -> list[Paper]:
        data = await self._get(
            f"{BASE}/paper/search",
            {"query": query, "limit": min(limit, 100), "fields": FIELDS},
        )
        return [self._to_paper(w) for w in data.get("data", [])]

    async def fetch_by_doi(self, doi: str) -> Optional[Paper]:
        try:
            data = await self._get(f"{BASE}/paper/DOI:{doi}", {"fields": FIELDS})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        return self._to_paper(data)

    def _to_paper(self, w: dict) -> Paper:
        ext = w.get("externalIds") or {}
        oa = w.get("openAccessPdf") or {}
        return Paper(
            paper_id=w.get("paperId") or "",
            source=self.name,
            title=w.get("title") or "",
            authors=[a.get("name", "") for a in w.get("authors") or []],
            year=w.get("year"),
            doi=normalize_doi(ext.get("DOI")),
            abstract=w.get("abstract"),
            venue=w.get("venue"),
            open_access_url=oa.get("url"),
            raw=w,
        )
