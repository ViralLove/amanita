"""
Unit tests for GET /v1/pending-sign-requests (W6): события для wallet-mock runner.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_push_sender
from api.routes import pending_sign_requests
from services.wallet_push import StubPushSender


@pytest.fixture
def push_sender():
    return StubPushSender()


@pytest.fixture
def app(push_sender):
    app = FastAPI()
    app.include_router(pending_sign_requests.router)
    app.dependency_overrides[get_push_sender] = lambda: push_sender
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def headers(user_id: str):
    return {"X-User-Id": user_id}


@pytest.mark.unit
class TestPendingSignRequests:
    def test_get_200_returns_events_and_claims(self, client, push_sender):
        push_sender.send_sign_request("user-1", "sign_arweave", "upload-1")
        r = client.get("/v1/pending-sign-requests?user_id=user-1", headers=headers("user-1"))
        assert r.status_code == 200
        data = r.json()
        assert "events" in data
        assert len(data["events"]) == 1
        assert data["events"][0]["user_id"] == "user-1"
        assert data["events"][0]["request_type"] == "sign_arweave"
        assert data["events"][0]["request_id"] == "upload-1"
        # second call returns empty (claimed)
        r2 = client.get("/v1/pending-sign-requests?user_id=user-1", headers=headers("user-1"))
        assert r2.status_code == 200
        assert len(r2.json()["events"]) == 0

    def test_get_401_without_x_user_id(self, client):
        r = client.get("/v1/pending-sign-requests?user_id=user-1")
        assert r.status_code == 401

    def test_get_403_wrong_user(self, client, push_sender):
        push_sender.send_sign_request("user-1", "sign_arweave", "up-1")
        r = client.get("/v1/pending-sign-requests?user_id=user-1", headers=headers("other-user"))
        assert r.status_code == 403
