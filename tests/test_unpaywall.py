# tests/test_unpaywall.py
import respx, httpx, pytest
from scriptorium.fulltext.unpaywall import UnpaywallClient

@pytest.mark.asyncio
@respx.mock
async def test_oa_hit_returns_pdf_url(fixture_loader):
    payload = fixture_loader("unpaywall", "oa_hit")
    respx.get("https://api.unpaywall.org/v2/10.1037/xlm0000123").mock(
        return_value=httpx.Response(200, json=payload)
    )
    c = UnpaywallClient(email="test@example.com")
    url = await c.find_pdf("10.1037/xlm0000123")
    assert url == "https://example.org/best.pdf"

@pytest.mark.asyncio
@respx.mock
async def test_closed_returns_none(fixture_loader):
    payload = fixture_loader("unpaywall", "closed")
    respx.get("https://api.unpaywall.org/v2/10.1037/closed").mock(
        return_value=httpx.Response(200, json=payload)
    )
    c = UnpaywallClient(email="test@example.com")
    assert await c.find_pdf("10.1037/closed") is None

@pytest.mark.asyncio
@respx.mock
async def test_email_is_required_param():
    respx.get("https://api.unpaywall.org/v2/10.1/x").mock(
        return_value=httpx.Response(200, json={"is_oa": False})
    )
    c = UnpaywallClient(email="test@example.com")
    await c.find_pdf("10.1/x")
    assert "email=test%40example.com" in str(respx.calls.last.request.url) or \
           "email=test@example.com" in str(respx.calls.last.request.url)
