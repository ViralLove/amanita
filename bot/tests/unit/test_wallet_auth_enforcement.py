import os
import sys
from unittest.mock import patch

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from api.services.wallet_auth import WalletAuthService
from services.wallet_push import StubPushSender


@pytest.fixture
def auth_service():
    return WalletAuthService()


@pytest.fixture
def push_sender():
    return StubPushSender()


@pytest.fixture
def app(auth_service, push_sender):
    mock_registry = MagicMock()
    with patch.dict(sys.modules, {"services.product.registry_singleton": mock_registry}):
        from api.dependencies import get_push_sender, get_wallet_auth_service
        from api.routes import pending_sign_requests, wallet_auth
        from api.utils import wallet_auth_guard

    app = FastAPI()
    app.include_router(wallet_auth.router)
    app.include_router(pending_sign_requests.router)
    app.dependency_overrides[get_wallet_auth_service] = lambda: auth_service
    app.dependency_overrides[get_push_sender] = lambda: push_sender
    wallet_auth_guard.get_wallet_auth_service = lambda: auth_service
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def _issue_and_verify(client: TestClient, user_id: str = "user-1"):
    acct = Account.create()
    wallet = acct.address
    issue = client.post(
        "/v1/wallet-auth/challenge",
        json={"wallet_address": wallet, "user_id": user_id, "auth_scope": "signing_flow"},
    )
    assert issue.status_code == 200
    payload = issue.json()
    sig = Account.sign_message(
        encode_defunct(text=payload["canonical_message"]),
        private_key=acct.key,
    ).signature.hex()
    verify = client.post(
        "/v1/wallet-auth/verify",
        json={
            "challenge_id": payload["challenge_id"],
            "wallet_address": wallet,
            "user_id": user_id,
            "signature": sig,
        },
    )
    assert verify.status_code == 200
    token = verify.json()["wallet_auth_token"]
    return wallet, token, payload


@pytest.mark.unit
def test_wallet_auth_verify_and_pending_with_bearer(client, push_sender):
    with patch.dict(os.environ, {"ALLOW_X_USER_ID_FALLBACK": "false"}, clear=False):
        wallet, token, _ = _issue_and_verify(client, user_id="user-1")
        push_sender.send_sign_request("user-1", "sign_arweave", "upload-1")
        resp = client.get(
            "/v1/pending-sign-requests?user_id=user-1",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Wallet-Address": wallet.lower(),
            },
        )
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 1
        assert events[0]["request_id"] == "upload-1"


@pytest.mark.unit
def test_wallet_auth_challenge_reuse_returns_409(client):
    acct = Account.create()
    wallet = acct.address
    issue = client.post(
        "/v1/wallet-auth/challenge",
        json={"wallet_address": wallet, "user_id": "user-1", "auth_scope": "signing_flow"},
    )
    payload = issue.json()
    sig = Account.sign_message(
        encode_defunct(text=payload["canonical_message"]),
        private_key=acct.key,
    ).signature.hex()
    first = client.post(
        "/v1/wallet-auth/verify",
        json={
            "challenge_id": payload["challenge_id"],
            "wallet_address": wallet,
            "user_id": "user-1",
            "signature": sig,
        },
    )
    assert first.status_code == 200
    second = client.post(
        "/v1/wallet-auth/verify",
        json={
            "challenge_id": payload["challenge_id"],
            "wallet_address": wallet,
            "user_id": "user-1",
            "signature": sig,
        },
    )
    assert second.status_code == 409


@pytest.mark.unit
def test_wallet_auth_expired_session_returns_401(client, auth_service, push_sender):
    with patch.dict(os.environ, {"ALLOW_X_USER_ID_FALLBACK": "false"}, clear=False):
        wallet, token, _ = _issue_and_verify(client, user_id="user-1")
        auth_service._sessions[token].expires_at = 0  # force expiration for test
        push_sender.send_sign_request("user-1", "sign_arweave", "upload-1")
        resp = client.get(
            "/v1/pending-sign-requests?user_id=user-1",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Wallet-Address": wallet.lower(),
            },
        )
        assert resp.status_code == 401
        detail = resp.json().get("detail", {})
        assert detail.get("error_code") == "auth_session_expired"

