"""Unpaywall adapter — DOI → OA PDF URL."""
from __future__ import annotations
from typing import Optional
import httpx

BASE = "https://api.unpaywall.org/v2"


class UnpaywallClient:
    def __init__(self, email: str, http_client: Optional[httpx.AsyncClient] = None):
        if not email:
            raise ValueError("Unpaywall requires a contact email per their ToS.")
        self.email = email
        self._client = http_client

    async def find_pdf(self, doi: str) -> Optional[str]:
        params = {"email": self.email}
        url = f"{BASE}/{doi}"
        if self._client:
            r = await self._client.get(url, params=params)
        else:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(url, params=params)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        if not data.get("is_oa"):
            return None
        loc = data.get("best_oa_location") or {}
        return loc.get("url_for_pdf") or None
