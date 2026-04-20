"""Common Paper schema + adapter base + DOI normalization."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Paper:
    paper_id: str
    source: str
    title: str
    authors: list[str]
    year: Optional[int]
    doi: Optional[str] = None
    abstract: Optional[str] = None
    venue: Optional[str] = None
    open_access_url: Optional[str] = None
    raw: dict = field(default_factory=dict)

def normalize_doi(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = raw.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s or None

class SourceAdapter(ABC):
    """Common interface for all search backends."""
    name: str

    @abstractmethod
    async def search(self, query: str, limit: int = 50) -> list[Paper]: ...

    @abstractmethod
    async def fetch_by_doi(self, doi: str) -> Optional[Paper]: ...
