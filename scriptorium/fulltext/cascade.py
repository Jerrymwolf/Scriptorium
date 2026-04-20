"""Full-text cascade: user_pdf → unpaywall → arxiv → pmc → abstract_only."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol
import httpx
from scriptorium.paths import ReviewPaths
from scriptorium.sources.base import Paper
from scriptorium.fulltext.user_pdf import find_registered_pdf
from scriptorium.fulltext.pdf_text import extract_pages


class Downloader(Protocol):
    async def download(self, url: str, dest: Path) -> Path: ...


class HttpxDownloader:
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self._client = http_client

    async def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self._client:
            r = await self._client.get(url, follow_redirects=True)
        else:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
                r = await c.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return dest


@dataclass
class FulltextResult:
    paper_id: str
    source: str                # "user_pdf" | "unpaywall" | "arxiv" | "pmc" | "abstract_only"
    pdf_path: Optional[Path]
    text: Optional[str]
    pages: list[str]


async def resolve_fulltext(
    paths: ReviewPaths,
    paper: Paper,
    *,
    unpaywall,
    arxiv,
    pmc,
    downloader: Downloader,
) -> FulltextResult:
    user = find_registered_pdf(paths, paper.paper_id)
    if user:
        return _from_pdf(paper.paper_id, "user_pdf", user)

    if paper.doi:
        url = await unpaywall.find_pdf(paper.doi)
        if url:
            dest = paths.pdfs / f"{paper.paper_id}__unpaywall.pdf"
            await downloader.download(url, dest)
            return _from_pdf(paper.paper_id, "unpaywall", dest)

    if paper.title:
        url = await arxiv.find_pdf_by_title(paper.title)
        if url:
            dest = paths.pdfs / f"{paper.paper_id}__arxiv.pdf"
            await downloader.download(url, dest)
            return _from_pdf(paper.paper_id, "arxiv", dest)

    pmcid = (paper.raw or {}).get("pmcid")
    if pmcid:
        url = await pmc.find_pdf(pmcid)
        if url:
            dest = paths.pdfs / f"{paper.paper_id}__pmc.pdf"
            await downloader.download(url, dest)
            return _from_pdf(paper.paper_id, "pmc", dest)

    return FulltextResult(
        paper_id=paper.paper_id, source="abstract_only",
        pdf_path=None, text=paper.abstract or "", pages=[],
    )


def _from_pdf(paper_id: str, source: str, pdf: Path) -> FulltextResult:
    pages = extract_pages(pdf)
    return FulltextResult(
        paper_id=paper_id, source=source, pdf_path=pdf,
        text="\n".join(pages), pages=pages,
    )
