"""OpenAlex adapter. Default backend; no key required."""
from __future__ import annotations
from typing import Optional
import httpx
from scriptorium.sources.base import SourceAdapter, Paper, normalize_doi

BASE = "https://api.openalex.org"

class OpenAlexAdapter(SourceAdapter):
    name = "openalex"

    def __init__(self, mailto: str = "", http_client: Optional[httpx.AsyncClient] = None):
        self.mailto = mailto
        self._client = http_client

    async def _get(self, url: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        if self.mailto:
            params["mailto"] = self.mailto
        if self._client:
            r = await self._client.get(url, params=params)
        else:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(url, params=params)
        r.raise_for_status()
        return r.json()

    async def search(self, query: str, limit: int = 50) -> list[Paper]:
        data = await self._get(f"{BASE}/works", {"search": query, "per-page": min(limit, 200)})
        return [self._to_paper(w) for w in data.get("results", [])]

    async def fetch_by_doi(self, doi: str) -> Optional[Paper]:
        try:
            data = await self._get(f"{BASE}/works/doi:{doi}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        return self._to_paper(data)

    def _to_paper(self, w: dict) -> Paper:
        oa_id = w.get("id", "").rsplit("/", 1)[-1]
        authors = [a["author"]["display_name"] for a in w.get("authorships", [])]
        venue = (w.get("host_venue") or {}).get("display_name")
        oa_url = (w.get("open_access") or {}).get("oa_url")
        abstract = _decode_inverted_index(w.get("abstract_inverted_index"))
        return Paper(
            paper_id=oa_id,
            source=self.name,
            title=w.get("title") or "",
            authors=authors,
            year=w.get("publication_year"),
            doi=normalize_doi(w.get("doi")),
            abstract=abstract,
            venue=venue,
            open_access_url=oa_url,
            raw=w,
        )

def _decode_inverted_index(idx: dict | None) -> Optional[str]:
    if not idx:
        return None
    positions: list[tuple[int, str]] = []
    for word, locs in idx.items():
        for loc in locs:
            positions.append((loc, word))
    positions.sort()
    return " ".join(w for _, w in positions)
