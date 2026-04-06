"""
Unit tests for uploads API: PUT status, POST callback (task 3.2).
TestClient; имитация Edge (Bearer + тела). Без реальной Edge.
Импорт api.dependencies/api.routes тянет registry_singleton → Web3; делаем его внутри фикстуры с моком.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.upload.upload_service import UploadService

# Используем тот же MockSupabase из test_upload_service
from tests.unit.test_upload_service import MockSupabase

EDGE_SECRET = "mock-edge-to-backend-secret"


@pytest.fixture(autouse=True)
def set_edge_secret():
    """Чтобы роутер принимал наш Bearer, задаём тот же секрет в env."""
    old = os.environ.get("EDGE_TO_BACKEND_SECRET")
    os.environ["EDGE_TO_BACKEND_SECRET"] = EDGE_SECRET
    yield
    if old is None:
        os.environ.pop("EDGE_TO_BACKEND_SECRET", None)
    else:
        os.environ["EDGE_TO_BACKEND_SECRET"] = old


@pytest.fixture
def mock_db():
    return MockSupabase()


@pytest.fixture
def upload_svc(mock_db):
    return UploadService(mock_db, rate_limit_per_min=10, rate_limit_bytes_per_day=10**6)


@pytest.fixture
def app(upload_svc):
    """Сборка app без загрузки Web3: мок registry_singleton + blockchain для callback."""
    mock_registry_module = MagicMock()
    mock_registry_module.product_registry_service = MagicMock()
    mock_blockchain = MagicMock()
    mock_blockchain.get_sign_request_evm_params.return_value = (
        "31337",
        "0x0000000000000000000000000000000000000001",
    )
    with patch.dict(sys.modules, {"services.product.registry_singleton": mock_registry_module}):
        from api.dependencies import get_blockchain_service, get_upload_service
        from api.routes import uploads
    app = FastAPI()
    app.include_router(uploads.router)
    app.dependency_overrides[get_upload_service] = lambda: upload_svc
    app.dependency_overrides[get_blockchain_service] = lambda: mock_blockchain
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def _headers():
    return {"Authorization": f"Bearer {EDGE_SECRET}", "Content-Type": "application/json"}


@pytest.mark.unit
class TestUploadFlowAPI:
    def test_put_status_200(self, client, upload_svc, mock_db):
        """PUT status после prepare → 200."""
        from unittest.mock import patch
        with patch("services.upload.upload_service.sign_upload_token", return_value="mock-jwt"):
            result = upload_svc.prepare(b"x", "user-1")
        upload_id = result.upload_id
        r = client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "queued_for_publish"},
            headers=_headers(),
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_put_status_404(self, client):
        """PUT status с неизвестным upload_id → 404."""
        r = client.put(
            "/v1/uploads/00000000-0000-0000-0000-000000000000/status",
            json={"status": "queued_for_publish"},
            headers=_headers(),
        )
        assert r.status_code == 404

    def test_put_status_401_no_bearer(self, client):
        """Без Bearer → 401."""
        r = client.put(
            "/v1/uploads/00000000-0000-0000-0000-000000000000/status",
            json={"status": "queued_for_publish"},
        )
        assert r.status_code == 401

    def test_post_callback_200(self, client, upload_svc, mock_db):
        """Prepare → PUT queued → POST callback → 200."""
        from unittest.mock import patch
        with patch("services.upload.upload_service.sign_upload_token", return_value="mock-jwt"):
            result = upload_svc.prepare(b"x", "user-1")
        upload_id = result.upload_id
        client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "queued_for_publish"},
            headers=_headers(),
        )
        r = client.post(
            "/v1/uploads/callback",
            json={
                "upload_id": upload_id,
                "item_id": "item-1",
                "bundle_tx_id": "bundle-1",
                "published_at": "2026-01-01T12:00:00Z",
            },
            headers=_headers(),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["sign_contract_enqueued"] is True
        assert data["sign_request_id"]
        assert data["error_code"] is None
        assert data["error"] is None

    def test_post_callback_404(self, client):
        """POST callback с неизвестным upload_id → 404."""
        r = client.post(
            "/v1/uploads/callback",
            json={
                "upload_id": "00000000-0000-0000-0000-000000000000",
                "item_id": "i",
                "bundle_tx_id": "b",
                "published_at": "2026-01-01T12:00:00Z",
            },
            headers=_headers(),
        )
        assert r.status_code == 404

    def test_post_callback_409_from_prepared(self, client, upload_svc):
        """POST callback для prepared (без queued) → 409."""
        from unittest.mock import patch
        with patch("services.upload.upload_service.sign_upload_token", return_value="mock-jwt"):
            result = upload_svc.prepare(b"x", "user-1")
        r = client.post(
            "/v1/uploads/callback",
            json={
                "upload_id": result.upload_id,
                "item_id": "i",
                "bundle_tx_id": "b",
                "published_at": "2026-01-01T12:00:00Z",
            },
            headers=_headers(),
        )
        assert r.status_code == 409
