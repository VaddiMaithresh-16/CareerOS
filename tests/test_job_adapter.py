import pytest
import respx
import httpx

from app.services.job_api_adapter import MockJobAdapter, AdzunaAdapter, MultiSourceAdapter


@pytest.mark.asyncio
async def test_mock_adapter_returns_raw_postings():
    adapter = MockJobAdapter()
    results = await adapter.search("backend engineer", "Remote")
    assert len(results) >= 1
    assert results[0].apply_url.startswith("https://")
    assert results[0].title


@pytest.mark.asyncio
@respx.mock
async def test_adzuna_adapter_parses_results():
    respx.get("https://api.adzuna.com/v1/api/jobs/us/search/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "123",
                        "title": "Backend Engineer",
                        "company": {"display_name": "Acme"},
                        "location": {"display_name": "Remote"},
                        "contract_time": "full_time",
                        "description": "Python role",
                        "redirect_url": "https://adzuna.com/jobs/123",
                        "created": "2026-08-01T00:00:00Z",
                        "salary_min": 80000,
                        "salary_max": 100000,
                    }
                ]
            },
        )
    )
    adapter = AdzunaAdapter("id", "key", "us")
    results = await adapter.search("backend")
    assert len(results) == 1
    assert results[0].source == "adzuna"
    assert results[0].title == "Backend Engineer"


@pytest.mark.asyncio
async def test_multi_source_merges_and_survives_one_failure():
    class GoodAdapter:
        async def search(self, query, location=None):
            return await MockJobAdapter().search(query, location)

    class BadAdapter:
        async def search(self, query, location=None):
            raise httpx.HTTPError("boom")

    multi = MultiSourceAdapter([GoodAdapter(), BadAdapter()])
    results = await multi.search("backend")
    assert len(results) >= 1  # good adapter's results still come through


@pytest.mark.asyncio
@respx.mock
async def test_remotive_adapter_parses_results():
    from app.services.job_api_adapter import RemotiveAdapter

    respx.get("https://remotive.com/api/remote-jobs").mock(
        return_value=httpx.Response(
            200,
            json={"jobs": [{
                "id": 1, "title": "Backend Engineer", "company_name": "Acme",
                "candidate_required_location": "Worldwide", "job_type": "full_time",
                "description": "Python role", "url": "https://remotive.com/jobs/1",
                "publication_date": "2026-08-01T00:00:00", "salary": "",
            }]},
        )
    )
    results = await RemotiveAdapter().search("backend")
    assert len(results) == 1
    assert results[0].source == "remotive"


@pytest.mark.asyncio
@respx.mock
async def test_remoteok_adapter_skips_legal_notice_and_filters_by_query():
    from app.services.job_api_adapter import RemoteOKAdapter

    respx.get("https://remoteok.com/api").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"legal": "notice text, not a job"},
                {"id": "1", "position": "Backend Engineer", "company": "Acme",
                 "location": "Remote", "tags": ["python"], "description": "desc",
                 "url": "https://remoteok.com/jobs/1", "date": "2026-08-01"},
                {"id": "2", "position": "Graphic Designer", "company": "Acme",
                 "location": "Remote", "tags": ["design"], "description": "desc",
                 "url": "https://remoteok.com/jobs/2", "date": "2026-08-01"},
            ],
        )
    )
    results = await RemoteOKAdapter().search("backend")
    assert len(results) == 1
    assert results[0].title == "Backend Engineer"


@pytest.mark.asyncio
@respx.mock
async def test_arbeitnow_adapter_filters_by_query():
    from app.services.job_api_adapter import ArbeitnowAdapter

    respx.get("https://www.arbeitnow.com/api/job-board-api").mock(
        return_value=httpx.Response(
            200,
            json={"data": [
                {"slug": "a", "title": "Backend Engineer", "company_name": "Acme",
                 "location": "Berlin", "tags": ["python"], "job_types": ["full_time"],
                 "description": "desc", "url": "https://arbeitnow.com/jobs/a"},
                {"slug": "b", "title": "UX Designer", "company_name": "Acme",
                 "location": "Berlin", "tags": ["design"], "job_types": ["full_time"],
                 "description": "desc", "url": "https://arbeitnow.com/jobs/b"},
            ]},
        )
    )
    results = await ArbeitnowAdapter().search("backend")
    assert len(results) == 1
    assert results[0].source == "arbeitnow"
