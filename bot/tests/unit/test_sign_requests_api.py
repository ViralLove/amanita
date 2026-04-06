"""
Unit tests for sign-requests API (W5, W8): GET /v1/sign-requests/{id}, POST /v1/sign-requests/{id}/submit.
W8: при signedTransaction — broadcast, возврат tx_hash, store.set_tx_hash.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_blockchain_service, get_sign_request_store
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
def mock_blockchain():
    """W8: мок BlockchainService для GET (EVM params) и submit broadcast."""
    m = MagicMock()
    m.submit_sign_request_raw_transaction.return_value = "0xbroadcast_tx_hash_abc"
    m.get_sign_request_evm_params.return_value = ("137", "0xActivityRegistry")
    return m


@pytest.fixture
def app(store, mock_blockchain):
    app = FastAPI()
    app.include_router(sign_requests.router)
    app.dependency_overrides[get_sign_request_store] = lambda: store
    app.dependency_overrides[get_blockchain_service] = lambda: mock_blockchain
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

    def test_get_uses_evm_snapshot_from_record_when_set(self, mock_blockchain):
        """Контекст сети/контракта зафиксирован при create — GET не дергает fallback из BlockchainService."""
        store = SignRequestStore()
        sid = store.create(
            "user-1",
            "create_activity",
            "upload-1",
            "cid-abc",
            evm_chain_id="42161",
            evm_contract_address="0x1111111111111111111111111111111111111111",
        )
        app = FastAPI()
        app.include_router(sign_requests.router)
        app.dependency_overrides[get_sign_request_store] = lambda: store
        app.dependency_overrides[get_blockchain_service] = lambda: mock_blockchain
        c = TestClient(app)
        r = c.get(f"/v1/sign-requests/{sid}", headers=headers("user-1"))
        assert r.status_code == 200
        data = r.json()
        assert data["chain_id"] == "42161"
        assert data["contract_address"] == "0x1111111111111111111111111111111111111111"
        mock_blockchain.get_sign_request_evm_params.assert_not_called()


@pytest.mark.unit
class TestSubmitSignRequest:
    def test_submit_200_and_store_updated(self, client, store, sign_request_id, mock_blockchain):
        r = client.post(
            f"/v1/sign-requests/{sign_request_id}/submit",
            json={"signedTransaction": "0xabc"},
            headers=headers("user-1"),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data.get("tx_hash") == "0xbroadcast_tx_hash_abc"
        rec = store.get(sign_request_id)
        assert rec is not None
        assert rec.submitted_at is not None
        assert rec.status == "submitted"
        assert rec.signed_tx == "0xabc"
        assert rec.tx_hash == "0xbroadcast_tx_hash_abc"
        mock_blockchain.submit_sign_request_raw_transaction.assert_called_once_with(
            "0xabc",
            expected_chain_id="137",
            expected_to_address="0xActivityRegistry",
        )

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

    def test_submit_passes_snapshot_context_to_blockchain(self, mock_blockchain):
        """POST submit передаёт в submit_sign_request_raw_transaction ожидаемые chain/contract из снимка записи."""
        store = SignRequestStore()
        sid = store.create(
            "user-1",
            "create_activity",
            "upload-1",
            "cid-abc",
            evm_chain_id="42161",
            evm_contract_address="0x2222222222222222222222222222222222222222",
        )
        app = FastAPI()
        app.include_router(sign_requests.router)
        app.dependency_overrides[get_sign_request_store] = lambda: store
        app.dependency_overrides[get_blockchain_service] = lambda: mock_blockchain
        c = TestClient(app)
        r = c.post(
            f"/v1/sign-requests/{sid}/submit",
            json={"signedTransaction": "0xab"},
            headers=headers("user-1"),
        )
        assert r.status_code == 200
        mock_blockchain.submit_sign_request_raw_transaction.assert_called_once_with(
            "0xab",
            expected_chain_id="42161",
            expected_to_address="0x2222222222222222222222222222222222222222",
        )
