import shutil
from pathlib import Path
import pytest
from scriptorium.paths import resolve_review_dir
from scriptorium.sources.base import Paper
from scriptorium.fulltext.cascade import resolve_fulltext, FulltextResult
from scriptorium.fulltext.user_pdf import register_user_pdf

FIXTURES = Path(__file__).parent / "fixtures"


class StubUnpaywall:
    def __init__(self, url):
        self.url = url
    async def find_pdf(self, doi):
        return self.url


class StubArxiv:
    def __init__(self, url):
        self.url = url
    async def find_pdf_by_title(self, title):
        return self.url


class StubPMC:
    def __init__(self, url):
        self.url = url
    async def find_pdf(self, pmcid):
        return self.url


class StubDownloader:
    def __init__(self, dest_template):
        self.dest_template = dest_template
        self.calls = []
    async def download(self, url, dest):
        self.calls.append(url)
        shutil.copy2(FIXTURES / "pdfs" / "multi.pdf", dest)
        return dest


@pytest.mark.asyncio
async def test_cascade_uses_user_pdf_first(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    register_user_pdf(paths, FIXTURES / "pdfs" / "multi.pdf", paper_id="W1")
    paper = Paper(paper_id="W1", source="openalex", title="t", authors=[], year=2020, doi="10.1/abc")
    res = await resolve_fulltext(
        paths, paper,
        unpaywall=StubUnpaywall("never_called"),
        arxiv=StubArxiv("never_called"),
        pmc=StubPMC("never_called"),
        downloader=StubDownloader("never"),
    )
    assert res.source == "user_pdf"
    assert res.pdf_path is not None and res.pdf_path.exists()


@pytest.mark.asyncio
async def test_cascade_falls_through_to_unpaywall(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    paper = Paper(paper_id="W2", source="openalex", title="t", authors=[], year=2020, doi="10.1/abc")
    dl = StubDownloader("dl")
    res = await resolve_fulltext(
        paths, paper,
        unpaywall=StubUnpaywall("https://x.example/u.pdf"),
        arxiv=StubArxiv(None),
        pmc=StubPMC(None),
        downloader=dl,
    )
    assert res.source == "unpaywall"
    assert dl.calls == ["https://x.example/u.pdf"]


@pytest.mark.asyncio
async def test_cascade_returns_abstract_only_when_nothing_works(review_dir):
    paths = resolve_review_dir(explicit=review_dir)
    paper = Paper(paper_id="W3", source="openalex", title="t", authors=[], year=2020,
                  doi=None, abstract="An abstract paragraph.")
    res = await resolve_fulltext(
        paths, paper,
        unpaywall=StubUnpaywall(None),
        arxiv=StubArxiv(None),
        pmc=StubPMC(None),
        downloader=StubDownloader("never"),
    )
    assert res.source == "abstract_only"
    assert res.pdf_path is None
    assert res.text and "abstract paragraph" in res.text.lower()
