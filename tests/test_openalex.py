import respx
import httpx
import pytest
from scriptorium.sources.openalex import OpenAlexAdapter

@pytest.mark.asyncio
@respx.mock
async def test_search_returns_papers(fixture_loader):
    payload = fixture_loader("openalex", "caffeine_query")
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json=payload)
    )
    a = OpenAlexAdapter(mailto="test@example.com")
    papers = await a.search("caffeine working memory", limit=10)
    assert len(papers) == 2
    assert papers[0].paper_id == "W2741809807"
    assert papers[0].source == "openalex"
    assert papers[0].title.startswith("Caffeine")
    assert papers[0].year == 2019
    assert papers[0].doi == "10.1037/xlm0000123"
    assert papers[0].open_access_url == "https://example.org/openalex_oa.pdf"
    assert papers[0].abstract and "improves" in papers[0].abstract

@pytest.mark.asyncio
@respx.mock
async def test_fetch_by_doi(fixture_loader):
    payload = fixture_loader("openalex", "work_W2741809807")
    respx.get("https://api.openalex.org/works/doi:10.1037/xlm0000123").mock(
        return_value=httpx.Response(200, json=payload)
    )
    a = OpenAlexAdapter(mailto="test@example.com")
    p = await a.fetch_by_doi("10.1037/xlm0000123")
    assert p is not None
    assert p.paper_id == "W2741809807"

@pytest.mark.asyncio
@respx.mock
async def test_search_sends_polite_pool_email():
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    a = OpenAlexAdapter(mailto="test@example.com")
    await a.search("anything")
    sent = respx.calls.last.request
    assert "mailto=test%40example.com" in str(sent.url) or "mailto=test@example.com" in str(sent.url)
