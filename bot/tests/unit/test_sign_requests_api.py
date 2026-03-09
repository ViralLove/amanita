"""
Unit tests for sign-requests API (W5): GET /v1/sign-requests/{id}, POST /v1/sign-requests/{id}/submit.
"""

import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_sign_request_store
from api.routes import sign_requests
from services.wallet_push import SignRequestStore


@pytest.fixture
def store():
    return SignRequestStore()


@pytest.fixture
def sign_request_id(store):
    return store.create("user-1", "create_activity", "upload-1", "cid-abc")


@pytest.fixture(autouse=True)
def env_chain():
    with patch.dict(
        os.environ,
        {"CHAIN_ID": "137", "ACTIVITY_REGISTRY_ADDRESS": "0xActivityRegistry"},
        clear=False,
    ):
        yield


@pytest.fixture
def app(store):
    app = FastAPI()
    app.include_router(sign_requests.router)
    app.dependency_overrides[get_sign_request_store] = lambda: store
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def headers(user_id: str):
    return {"X-User-Id": user_id, "Content-Type": "application/json"}


@pytest.mark.unit
class TestGetSignRequest:
    def test_get_200_returns_params(self, client, sign_request_id):
        r = client.get(f"/v1/sign-requests/{sign_request_id}", headers=headers("user-1"))
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "create_activity"
        assert data["cid"] == "cid-abc"
        assert data["upload_id"] == "upload-1"
        assert data["chain_id"] == "137"
        assert data["contract_address"] == "0xActivityRegistry"
        assert "deadline" in data

    def test_get_401_without_x_user_id(self, client, sign_request_id):
        r = client.get(f"/v1/sign-requests/{sign_request_id}")
        assert r.status_code == 401
        assert "X-User-Id" in (r.json().get("detail") or "")

    def test_get_403_wrong_user(self, client, sign_request_id):
        r = client.get(f"/v1/sign-requests/{sign_request_id}", headers=headers("other-user"))
        assert r.status_code == 403

    def test_get_404_unknown_id(self, client):
        r = client.get("/v1/sign-requests/unknown-id", headers=headers("user-1"))
        assert r.status_code == 404


@pytest.mark.unit
class TestSubmitSignRequest:
    def test_submit_200_and_store_updated(self, client, store, sign_request_id):
        r = client.post(
            f"/v1/sign-requests/{sign_request_id}/submit",
            json={"signedTransaction": "0xabc"},
            headers=headers("user-1"),
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        rec = store.get(sign_request_id)
        assert rec is not None
        assert rec.submitted_at is not None
        assert rec.status == "submitted"
        assert rec.signed_tx == "0xabc"

    def test_submit_200_signature_message(self, client, store, sign_request_id):
        r = client.post(
            f"/v1/sign-requests/{sign_request_id}/submit",
            json={"signature": "0xsig", "message": "0xmsg"},
            headers=headers("user-1"),
        )
        assert r.status_code == 200
        rec = store.get(sign_request_id)
        assert rec.signature == "0xsig"
        assert rec.message == "0xmsg"
        assert rec.status == "submitted"

    def test_submit_401_without_x_user_id(self, client, sign_request_id):
        r = client.post(
            f"/v1/sign-requests/{sign_request_id}/submit",
            json={"signedTransaction": "0x"},
        )
        assert r.status_code == 401

    def test_submit_403_wrong_user(self, client, sign_request_id):
        r = client.post(
            f"/v1/sign-requests/{sign_request_id}/submit",
            json={"signedTransaction": "0x"},
            headers=headers("other-user"),
        )
        assert r.status_code == 403

    def test_submit_404_unknown_id(self, client):
        r = client.post(
            "/v1/sign-requests/unknown-id/submit",
            json={"signedTransaction": "0x"},
            headers=headers("user-1"),
        )
        assert r.status_code == 404
