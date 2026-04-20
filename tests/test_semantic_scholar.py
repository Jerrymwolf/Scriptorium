import respx, httpx, pytest
from scriptorium.sources.semantic_scholar import SemanticScholarAdapter

@pytest.mark.asyncio
@respx.mock
async def test_search_returns_papers(fixture_loader):
    payload = fixture_loader("semantic_scholar", "caffeine_query")
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=httpx.Response(200, json=payload)
    )
    a = SemanticScholarAdapter(api_key=None)
    papers = await a.search("caffeine cognition")
    assert len(papers) == 1
    p = papers[0]
    assert p.paper_id == "abc123def456"
    assert p.source == "semantic_scholar"
    assert p.doi == "10.1146/annurev-psych-010418"
    assert p.year == 2018
    assert p.open_access_url == "https://example.org/ss_oa.pdf"

@pytest.mark.asyncio
@respx.mock
async def test_search_sends_api_key_when_provided():
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    a = SemanticScholarAdapter(api_key="SECRET")
    await a.search("x")
    assert respx.calls.last.request.headers.get("x-api-key") == "SECRET"
