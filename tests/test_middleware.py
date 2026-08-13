import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.middleware import RateLimitMiddleware, RequestContextMiddleware, require_api_key


def _build_app(rate_limit=2, api_key=None):
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit)
    app.add_middleware(RequestContextMiddleware)

    from app import middleware as mw
    mw.settings.api_key = api_key or ""

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/protected", dependencies=[Depends(require_api_key)])
    def protected():
        return {"ok": True}

    return app


def test_request_id_header_present():
    client = TestClient(_build_app())
    resp = client.get("/health")
    assert "X-Request-ID" in resp.headers


def test_rate_limit_blocks_after_threshold():
    client = TestClient(_build_app(rate_limit=2))
    client.get("/protected")
    client.get("/protected")
    third = client.get("/protected")
    assert third.status_code == 429


def test_health_exempt_from_rate_limit():
    client = TestClient(_build_app(rate_limit=1))
    for _ in range(5):
        resp = client.get("/health")
        assert resp.status_code == 200


def test_api_key_required_when_configured():
    client = TestClient(_build_app(rate_limit=100, api_key="secret123"))
    resp = client.get("/protected")
    assert resp.status_code == 401

    resp_ok = client.get("/protected", headers={"X-API-Key": "secret123"})
    assert resp_ok.status_code == 200


def test_api_key_open_when_not_configured():
    client = TestClient(_build_app(rate_limit=100, api_key=None))
    resp = client.get("/protected")
    assert resp.status_code == 200
