import httpx
import pytest
import respx

from app.services.verification import verify_job_posting


@pytest.mark.asyncio
@respx.mock
async def test_verify_unreachable_url_not_verified():
    respx.head("https://dead.example.com/job/1").mock(return_value=httpx.Response(404))
    result = await verify_job_posting("https://dead.example.com/job/1", "Engineer", "Acme")
    assert result.verified is False
    assert "not reachable" in result.reason


@pytest.mark.asyncio
@respx.mock
async def test_verify_reachable_no_firecrawl_key_stays_unverified(monkeypatch):
    from app.services import verification as v

    monkeypatch.setattr(v.settings, "firecrawl_api_key", "")
    respx.head("https://acme.com/job/1").mock(return_value=httpx.Response(200))
    result = await verify_job_posting("https://acme.com/job/1", "Engineer", "Acme")
    assert result.verified is False
    assert "no FIRECRAWL_API_KEY" in result.reason


@pytest.mark.asyncio
@respx.mock
async def test_verify_firecrawl_confirms_content(monkeypatch):
    from app.services import verification as v

    monkeypatch.setattr(v.settings, "firecrawl_api_key", "fc-test-key")
    respx.head("https://acme.com/job/1").mock(return_value=httpx.Response(200))
    respx.post("https://api.firecrawl.dev/v2/scrape").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "markdown": "Backend Engineer at Acme Corp. Apply now.",
                    "metadata": {"title": "Backend Engineer - Acme Corp"},
                },
            },
        )
    )
    result = await verify_job_posting("https://acme.com/job/1", "Backend Engineer", "Acme")
    assert result.verified is True


@pytest.mark.asyncio
@respx.mock
async def test_verify_detects_closed_posting(monkeypatch):
    from app.services import verification as v

    monkeypatch.setattr(v.settings, "firecrawl_api_key", "fc-test-key")
    respx.head("https://acme.com/job/2").mock(return_value=httpx.Response(200))
    respx.post("https://api.firecrawl.dev/v2/scrape").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "markdown": "This position has been filled. Thank you for your interest.",
                    "metadata": {"title": "Backend Engineer - Acme Corp"},
                },
            },
        )
    )
    result = await verify_job_posting("https://acme.com/job/2", "Backend Engineer", "Acme")
    assert result.verified is False
    assert "closed" in result.reason.lower() or "filled" in result.reason.lower()
