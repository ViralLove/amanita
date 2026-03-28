"""GptActionsBearerMiddleware: optional Bearer for /activities and /reference."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.gpt_actions_bearer import GptActionsBearerMiddleware


@pytest.fixture
def app_with_guard():
    app = FastAPI()

    @app.get("/activities/me")
    def act():
        return {"ok": True}

    @app.get("/reference/formats")
    def ref():
        return {"formats": []}

    @app.get("/health")
    def health():
        return {"status": "up"}

    app.add_middleware(GptActionsBearerMiddleware, bearer_secret="gpt-secret-token-32chars!!")
    return app


@pytest.fixture
def client(app_with_guard):
    return TestClient(app_with_guard)


@pytest.mark.unit
class TestGptActionsBearerMiddleware:
    def test_allows_health_without_bearer(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_401_activities_without_bearer(self, client):
        r = client.get("/activities/me")
        assert r.status_code == 401
        data = r.json()
        assert data.get("success") is False
        assert data.get("error") == "gpt_actions_auth_error"
        assert data.get("error_code") == "missing_bearer"

    def test_401_wrong_bearer(self, client):
        r = client.get(
            "/activities/me",
            headers={"Authorization": "Bearer wrong"},
        )
        assert r.status_code == 401
        assert r.json().get("error_code") == "invalid_bearer"

    def test_200_valid_bearer_activities(self, client):
        r = client.get(
            "/activities/me",
            headers={"Authorization": "Bearer gpt-secret-token-32chars!!"},
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_200_valid_bearer_reference(self, client):
        r = client.get(
            "/reference/formats",
            headers={"Authorization": "Bearer gpt-secret-token-32chars!!"},
        )
        assert r.status_code == 200


@pytest.mark.unit
def test_middleware_disabled_when_secret_empty():
    app = FastAPI()

    @app.get("/activities/me")
    def act():
        return {"ok": True}

    app.add_middleware(GptActionsBearerMiddleware, bearer_secret="")
    c = TestClient(app)
    r = c.get("/activities/me")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
