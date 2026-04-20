# tests/test_pmc.py
import respx, httpx, pytest
from pathlib import Path
from scriptorium.fulltext.pmc import PMCClient

FIXTURES = Path(__file__).parent / "fixtures"

@pytest.mark.asyncio
@respx.mock
async def test_find_pdf_by_pmcid():
    body = (FIXTURES / "pmc" / "oa_lookup.xml").read_text()
    respx.get("https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi").mock(
        return_value=httpx.Response(200, text=body)
    )
    c = PMCClient()
    url = await c.find_pdf("PMC1234567")
    assert url and url.endswith("main.pdf")

@pytest.mark.asyncio
@respx.mock
async def test_find_returns_none_when_no_record():
    respx.get("https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi").mock(
        return_value=httpx.Response(200, text='<?xml version="1.0"?><OA><records returned-count="0"></records></OA>')
    )
    c = PMCClient()
    assert await c.find_pdf("PMC0000000") is None
