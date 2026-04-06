"""
Integration harness для upload flow (task 3.2).

Phase 1 @integration-test-build.core: real Supabase (test DB), real UploadService, real API.
Требует: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (локальный Supabase или test project).
Таблица uploads должна существовать (миграция 20260129100000_create_uploads_table.sql).
Моки: только внешние (Edge не вызываем; finalizer в тестах не запускаем — тестируем только API + Service + DB).
"""

import os
import sys
from pathlib import Path
from typing import Any, Mapping

import pytest


# bot root
bot_dir = Path(__file__).resolve().parent.parent
if str(bot_dir) not in sys.path:
    sys.path.insert(0, str(bot_dir))


def assert_upload_callback_response_enqueued(body: Mapping[str, Any]) -> None:
    """Ожидаемое тело POST /v1/uploads/callback при успешной цепочке sign_request + push (ASG-2, Variant B)."""
    assert body.get("ok") is True
    assert body.get("sign_contract_enqueued") is True
    assert body.get("sign_request_id")
    assert body.get("error_code") is None
    assert body.get("error") is None


def _upload_integration_available():
    """Проверка доступности Supabase для интеграционных тестов upload."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    return bool(url and key)


@pytest.fixture(scope="module")
def upload_supabase():
    """Реальный SupabaseService для uploads. Пропуск теста если env не задан или ключ невалиден."""
    if not _upload_integration_available():
        pytest.skip(
            "Upload integration: задайте SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY "
            "(например, локальный Supabase: postgresql://postgres:postgres@127.0.0.1:54322/postgres)"
        )
    try:
        from services.core.supabase import SupabaseService
        return SupabaseService()
    except Exception as e:
        if "Invalid API key" in str(e):
            pytest.skip(
                "Upload integration: Supabase client не принял ключ (локальный CLI даёт sb_secret_*, "
                "supabase-py ожидает JWT). Задайте SUPABASE_SERVICE_ROLE_KEY в формате JWT из Dashboard "
                "или используйте облачный проект."
            )
        raise


@pytest.fixture(scope="module")
def upload_service(upload_supabase):
    """Реальный UploadService с реальным Supabase."""
    from services.upload.upload_service import UploadService
    return UploadService(upload_supabase)


@pytest.fixture(scope="module")
def upload_integration_app(upload_service):
    """
    Минимальное FastAPI приложение: только роутер uploads и реальный get_upload_service.
    Без lifespan (finalizer не запускаем в интеграционных тестах).
    Импорт api.dependencies тянет registry_singleton → Web3; мокаем registry_singleton.
    Для POST callback мокаем BlockchainService (get_sign_request_evm_params), чтобы Phase 2–3 не требовали RPC.
    """
    from unittest.mock import MagicMock, patch
    from fastapi import FastAPI

    mock_registry = MagicMock()
    mock_registry_module = MagicMock()
    mock_registry_module.product_registry_service = mock_registry
    mock_blockchain = MagicMock()
    mock_blockchain.get_sign_request_evm_params.return_value = (
        "31337",
        "0x0000000000000000000000000000000000000001",
    )
    with patch.dict(sys.modules, {"services.product.registry_singleton": mock_registry_module}):
        from api.dependencies import get_blockchain_service, get_upload_service
        from api.routes import uploads

    app = FastAPI(title="Upload Integration Test")
    app.include_router(uploads.router)
    app.dependency_overrides[get_upload_service] = lambda: upload_service
    app.dependency_overrides[get_blockchain_service] = lambda: mock_blockchain
    return app


@pytest.fixture(scope="module")
def upload_integration_client(upload_integration_app):
    """TestClient для upload API (реальный сервис + Supabase)."""
    from fastapi.testclient import TestClient
    return TestClient(upload_integration_app)


@pytest.fixture(autouse=True)
def upload_integration_edge_secret():
    """Единый Bearer для тестов (соответствует EDGE_TO_BACKEND_SECRET в env)."""
    secret = os.environ.get("EDGE_TO_BACKEND_SECRET") or "mock-edge-to-backend-secret"
    old = os.environ.get("EDGE_TO_BACKEND_SECRET")
    os.environ["EDGE_TO_BACKEND_SECRET"] = secret
    yield secret
    if old is None:
        os.environ.pop("EDGE_TO_BACKEND_SECRET", None)
    else:
        os.environ["EDGE_TO_BACKEND_SECRET"] = old
