# tests/test_arxiv.py
import respx, httpx, pytest
from pathlib import Path
from scriptorium.fulltext.arxiv import ArxivClient

FIXTURES = Path(__file__).parent / "fixtures"

@pytest.mark.asyncio
@respx.mock
async def test_find_pdf_by_title():
    body = (FIXTURES / "arxiv" / "find_atom.xml").read_text()
    respx.get("http://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text=body)
    )
    c = ArxivClient()
    url = await c.find_pdf_by_title("caffeine and working memory")
    assert url == "http://arxiv.org/pdf/2301.00001v1"

@pytest.mark.asyncio
@respx.mock
async def test_find_returns_none_when_no_entries():
    respx.get("http://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text='<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>')
    )
    c = ArxivClient()
    assert await c.find_pdf_by_title("nothing matches") is None
