"""
Unit tests for POST submit broadcast (W8): send_raw_transaction, tx_hash в ответе и в store.
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


def _mock_blockchain(tx_hash_hex="0xabc123"):
    m = MagicMock()
    m.get_sign_request_evm_params.return_value = ("137", "0xActivityRegistry")
    m.submit_sign_request_raw_transaction.return_value = tx_hash_hex
    return m


@pytest.fixture
def client(store, sign_request_id):
    mock_bc = _mock_blockchain("0xtx_hash_456")
    app = FastAPI()
    app.include_router(sign_requests.router)
    app.dependency_overrides[get_sign_request_store] = lambda: store
    app.dependency_overrides[get_blockchain_service] = lambda: mock_bc
    return TestClient(app), mock_bc


def headers(user_id: str):
    return {"X-User-Id": user_id, "Content-Type": "application/json"}


@pytest.mark.unit
class TestSubmitBroadcast:
    def test_submit_with_signed_tx_calls_send_raw_and_returns_tx_hash(self, client, store, sign_request_id):
        c, mock_bc = client
        r = c.post(
            f"/v1/sign-requests/{sign_request_id}/submit",
            json={"signedTransaction": "0xdeadbeef"},
            headers=headers("user-1"),
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True, "tx_hash": "0xtx_hash_456"}
        mock_bc.submit_sign_request_raw_transaction.assert_called_once_with(
            "0xdeadbeef",
            expected_chain_id="137",
            expected_to_address="0xActivityRegistry",
        )
        rec = store.get(sign_request_id)
        assert rec.tx_hash == "0xtx_hash_456"

    def test_submit_broadcast_value_error_returns_422(self, store, sign_request_id):
        mock_bc = MagicMock()
        mock_bc.get_sign_request_evm_params.return_value = ("137", "0xActivityRegistry")
        mock_bc.submit_sign_request_raw_transaction.side_effect = ValueError("Invalid hex")
        app = FastAPI()
        app.include_router(sign_requests.router)
        app.dependency_overrides[get_sign_request_store] = lambda: store
        app.dependency_overrides[get_blockchain_service] = lambda: mock_bc
        c = TestClient(app)
        r = c.post(
            f"/v1/sign-requests/{sign_request_id}/submit",
            json={"signedTransaction": "not-hex"},
            headers=headers("user-1"),
        )
        assert r.status_code == 422
        assert "Invalid" in (r.json().get("detail") or "")

    def test_submit_broadcast_exception_returns_500(self, store, sign_request_id):
        mock_bc = MagicMock()
        mock_bc.get_sign_request_evm_params.return_value = ("137", "0xActivityRegistry")
        mock_bc.submit_sign_request_raw_transaction.side_effect = RuntimeError("RPC error")
        app = FastAPI()
        app.include_router(sign_requests.router)
        app.dependency_overrides[get_sign_request_store] = lambda: store
        app.dependency_overrides[get_blockchain_service] = lambda: mock_bc
        c = TestClient(app)
        r = c.post(
            f"/v1/sign-requests/{sign_request_id}/submit",
            json={"signedTransaction": "0x00"},
            headers=headers("user-1"),
        )
        assert r.status_code == 500
        assert "Broadcast" in (r.json().get("detail") or "")
