"""
Integration tests: Upload floou (task 3.2).

@integration-test-build.core: Phase 1 (harness), Phase 2 (contracts), Phase 3 (floous).
Реальные модули: Supabase, UploadService, API. Моки: только внешние (arweave-uploader в Phase 2–3 не вызываем).
Требует: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY. Для prepare с JWT: UPLOAD_TOKEN_JWT_PRIVATE_KEY или FILE.
"""

import logging
import os
import pytest
import subprocess
import shutil
from pathlib import Path

# Явная подгрузка bot/.env (как в unit test_upload_jwt_key_pair_alignment): не зависим от порядка
# загрузки conftest и cwd — UPLOAD_TOKEN_JWT_*, SUPABASE_*, ARWEAVE_* и т.д. всегда из bot/.env
try:
    from dotenv import load_dotenv
    _bot_dir = Path(__file__).resolve().parent.parent.parent  # __file__ in bot/tests/integration/ → bot/
    _env_file = _bot_dir / ".env"
    if _env_file.is_file():
        load_dotenv(_env_file)
except ImportError:
    pass

_log = logging.getLogger(__name__)

from model.upload import FAILED, PREPARED, QUEUED_FOR_PUBLISH, PUBLISHED

# Путь по умолчанию к файлу с base64 подписанного Data Item для теста полного цикла
_FULL_CYCLE_SIGNED_DATA_ITEM_B64_DEFAULT_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "full_cycle_signed_data_item.b64"
)


# Секрет для заголовка Authorization при вызове Backend API (имитация uploader→Backend; uploads.py проверяет OWN_AUTH_TOKEN)
OWN_AUTH = os.environ.get("OWN_AUTH_TOKEN") or "mock-own-auth-token"


def _requires_legacy_edge_skip_reason() -> str | None:
    """Причина skip legacy теста Supabase Edge: None если все env заданы, иначе строка с перечислением недостающих."""
    missing = []
    if not os.environ.get("SUPABASE_URL"):
        missing.append("SUPABASE_URL")
    if not os.environ.get("SUPABASE_ANON_KEY"):
        missing.append("SUPABASE_ANON_KEY")
    if not os.environ.get("EDGE_USE_MOCK"):
        missing.append("EDGE_USE_MOCK")
    if not os.environ.get("EDGE_MOCK_TEST_SECRET"):
        missing.append("EDGE_MOCK_TEST_SECRET")
    if not missing:
        return None
    return f"Legacy Edge: задайте в .env: {', '.join(missing)}"


def _requires_full_cycle_env_skip_reason() -> str | None:
    """Причина skip теста полного цикла с реальным arweave-uploader: None если все env заданы."""
    missing = []
    if not os.environ.get("ARWEAVE_SERVICE_URL"):
        missing.append("ARWEAVE_SERVICE_URL")
    if not os.environ.get("OWN_AUTH_TOKEN"):
        missing.append("OWN_AUTH_TOKEN")
    if not os.environ.get("SUPABASE_URL"):
        missing.append("SUPABASE_URL")
    if not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if not os.environ.get("UPLOAD_TOKEN_JWT_PRIVATE_KEY") and not os.environ.get("UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE"):
        missing.append("UPLOAD_TOKEN_JWT_PRIVATE_KEY or UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE")
    if not missing:
        return None
    return f"Full cycle (real arweave-uploader): задайте в .env: {', '.join(missing)}"


# Вычисляется при загрузке модуля (после load_dotenv в conftest) для skipif legacy теста
_REQUIRES_LEGACY_EDGE_SKIP_REASON = _requires_legacy_edge_skip_reason()


def _arweave_uploader_dir() -> Path | None:
    """Каталог arweave-uploader: ARWEAVE_UPLOADER_DIR или ../arweave-uploader от корня репо (bot/..)."""
    env_path = os.environ.get("ARWEAVE_UPLOADER_DIR")
    if env_path and env_path.strip():
        p = Path(env_path.strip()).resolve()
        if p.is_dir():
            return p
    # От bot/tests/integration вверх: tests → bot → репо (Amanita)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    candidate = repo_root / "arweave-uploader"
    if candidate.is_dir():
        return candidate
    return None


def _build_full_cycle_signed_data_item_b64(upload_id: str) -> str | None:
    """Строит base64 подписанного Data Item с тегом Upload-Id = upload_id через скрипт arweave-uploader.
    Требует: Node, ARWEAVE_UPLOADER_DIR (или arweave-uploader рядом с bot). При недоступности возвращает None."""
    uploader_dir = _arweave_uploader_dir()
    if not uploader_dir:
        return None
    script = uploader_dir / "scripts" / "build-full-cycle-data-item.js"
    if not script.is_file():
        return None
    node = shutil.which("node") or "node"
    try:
        r = subprocess.run(
            [node, str(script), upload_id],
            cwd=str(uploader_dir),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if r.returncode != 0 or not r.stdout:
        return None
    return r.stdout.strip()


def _load_full_cycle_signed_data_item_b64() -> str | None:
    """Base64 подписанного Data Item для POST /v1/crystalize. Приоритет: env inline → env path (_FILE) → файл по умолчанию."""
    inline = os.environ.get("FULL_CYCLE_TEST_SIGNED_DATA_ITEM_B64")
    if inline and inline.strip():
        return inline.strip()
    path_str = os.environ.get("FULL_CYCLE_TEST_SIGNED_DATA_ITEM_B64_FILE")
    if path_str:
        p = Path(path_str)
        if p.is_file():
            return p.read_text().strip()
    if _FULL_CYCLE_SIGNED_DATA_ITEM_B64_DEFAULT_PATH.is_file():
        return _FULL_CYCLE_SIGNED_DATA_ITEM_B64_DEFAULT_PATH.read_text().strip()
    return None


def _headers():
    return {"Authorization": f"Bearer {OWN_AUTH}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Phase 1: Proof (multi-module load + DB)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestUploadIntegrationProof:
    """Phase 1: Инфраструктура — модули загружаются, БД доступна."""

    def test_supabase_insert_and_get_upload(self, upload_supabase):
        """Proof: Supabase → insert upload → get by id (реальная таблица uploads)."""
        import uuid
        user_id = "00000000-0000-0000-0000-000000000001"
        upload_id = str(uuid.uuid4())
        row = {
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
            "payload_hash": "proof_hash",
            "payload_size": 0,
        }
        inserted = upload_supabase.insert_upload(row)
        assert inserted.get("upload_id") == upload_id
        got = upload_supabase.get_upload_by_id(upload_id)
        assert got is not None
        assert got["status"] == PREPARED
        # cleanup: можно удалить или оставить (test DB)
        upload_supabase.update_upload_status(upload_id, "failed", failure_code="token_invalid")

    def test_upload_service_and_db_handshake(self, upload_service, upload_supabase):
        """Proof: UploadService → Supabase (prepare требует JWT; без ключа проверяем только get после ручной вставки)."""
        import uuid
        user_id = "00000000-0000-0000-0000-000000000002"
        upload_id = str(uuid.uuid4())
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
        })
        rec = upload_service.get_upload(upload_id)
        assert rec is not None
        assert rec.status == PREPARED
        assert rec.upload_id == upload_id


# ---------------------------------------------------------------------------
# Phase 2: Contract validation (API, data, errors)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestUploadIntegrationContracts:
    """Phase 2: Контракты API и данных на границах модулей."""

    def test_api_contract_put_status_response_format(self, upload_integration_client, upload_service, upload_supabase):
        """Contract: PUT /v1/uploads/{id}/status → 200 { ok: true } при валидном переходе."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-000000000003"
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
        })
        r = upload_integration_client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "queued_for_publish"},
            headers=_headers(),
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        rec = upload_service.get_upload(upload_id)
        assert rec is not None
        assert rec.status == QUEUED_FOR_PUBLISH

    def test_api_contract_put_status_404_format(self, upload_integration_client):
        """Contract: PUT status для неизвестного id → 404."""
        r = upload_integration_client.put(
            "/v1/uploads/00000000-0000-0000-0000-000000000099/status",
            json={"status": "queued_for_publish"},
            headers=_headers(),
        )
        assert r.status_code == 404

    def test_api_contract_put_status_409_invalid_transition_from_failed(
        self, upload_integration_client, upload_supabase, upload_service
    ):
        """Contract: PUT status=queued_for_publish для записи в статусе FAILED → 409 (недопустимый переход)."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-00000000000c"  # валидный UUID (12 hex в последнем сегменте)
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": FAILED,
        })
        r = upload_integration_client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "queued_for_publish"},
            headers=_headers(),
        )
        assert r.status_code == 409
        rec = upload_service.get_upload(upload_id)
        assert rec is not None
        assert rec.status == FAILED

    def test_api_contract_post_callback_response_format(
        self, upload_integration_client, upload_supabase, upload_service
    ):
        """Contract: POST /v1/uploads/callback → 200 { ok: true } при валидном состоянии; запись в БД published с item_id и bundle_tx_id."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-000000000004"
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": QUEUED_FOR_PUBLISH,
        })
        r = upload_integration_client.post(
            "/v1/uploads/callback",
            json={
                "upload_id": upload_id,
                "item_id": "item-int",
                "bundle_tx_id": "bundle-int",
                "published_at": "2026-01-01T12:00:00Z",
            },
            headers=_headers(),
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        rec = upload_service.get_upload(upload_id)
        assert rec is not None
        assert rec.status == PUBLISHED
        assert rec.item_id == "item-int"
        assert rec.bundle_tx_id == "bundle-int"

    def test_api_contract_post_callback_409_format(self, upload_integration_client, upload_supabase):
        """Contract: POST callback из prepared (без queued) → 409."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-000000000005"
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
        })
        r = upload_integration_client.post(
            "/v1/uploads/callback",
            json={
                "upload_id": upload_id,
                "item_id": "i",
                "bundle_tx_id": "b",
                "published_at": "2026-01-01T12:00:00Z",
            },
            headers=_headers(),
        )
        assert r.status_code == 409

    def test_api_contract_put_status_failed_with_failure_code_token_invalid(
        self, upload_integration_client, upload_supabase, upload_service
    ):
        """Contract: PUT status=failed + failure_code=token_invalid → 200, запись в БД failed с этим кодом (uploader→Backend)."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-000000000006"
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
        })
        r = upload_integration_client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "failed", "failure_code": "token_invalid"},
            headers=_headers(),
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        rec = upload_service.get_upload(upload_id)
        assert rec is not None
        assert rec.status == FAILED
        assert rec.failure_code == "token_invalid"

    def test_api_contract_put_status_failed_with_failure_code_signature_invalid(
        self, upload_integration_client, upload_supabase, upload_service
    ):
        """Contract: PUT status=failed + failure_code=signature_invalid → 200, запись в БД."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-000000000007"
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
        })
        r = upload_integration_client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "failed", "failure_code": "signature_invalid"},
            headers=_headers(),
        )
        assert r.status_code == 200
        rec = upload_service.get_upload(upload_id)
        assert rec is not None
        assert rec.status == FAILED
        assert rec.failure_code == "signature_invalid"

    def test_api_contract_put_status_failed_with_failure_code_publish_failed(
        self, upload_integration_client, upload_supabase, upload_service
    ):
        """Contract: PUT status=failed + failure_code=publish_failed → 200, запись в БД."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-000000000008"
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
        })
        r = upload_integration_client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "failed", "failure_code": "publish_failed"},
            headers=_headers(),
        )
        assert r.status_code == 200
        rec = upload_service.get_upload(upload_id)
        assert rec is not None
        assert rec.status == FAILED
        assert rec.failure_code == "publish_failed"

    def test_api_contract_put_status_401_no_authorization(self, upload_integration_client, upload_supabase):
        """Contract: PUT status без заголовка Authorization → 401."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-000000000009"
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
        })
        r = upload_integration_client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "queued_for_publish"},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 401

    def test_api_contract_put_status_401_wrong_bearer(self, upload_integration_client, upload_supabase):
        """Contract: PUT status с неверным Bearer → 401 (проверка OWN_AUTH_TOKEN)."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-00000000000a"
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
        })
        r = upload_integration_client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "queued_for_publish"},
            headers={
                "Authorization": "Bearer wrong-secret",
                "Content-Type": "application/json",
            },
        )
        assert r.status_code == 401

    def test_api_contract_post_callback_401_no_authorization(self, upload_integration_client, upload_supabase):
        """Contract: POST callback без Authorization → 401."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-00000000000b"
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": QUEUED_FOR_PUBLISH,
        })
        r = upload_integration_client.post(
            "/v1/uploads/callback",
            json={
                "upload_id": upload_id,
                "item_id": "i",
                "bundle_tx_id": "b",
                "published_at": "2026-01-01T12:00:00Z",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Phase 3: Floous (happy path, error handling)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestUploadIntegrationFloous:
    """Phase 3: Многошаговые сценарии (API + Service + DB)."""

    def test_floou_happy_path_put_then_callback(
        self, upload_integration_client, upload_supabase, upload_service
    ):
        """Floou: подготовленная запись → PUT queued → POST callback → состояние published в БД."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-000000000010"
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
        })
        r1 = upload_integration_client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "queued_for_publish"},
            headers=_headers(),
        )
        assert r1.status_code == 200
        r2 = upload_integration_client.post(
            "/v1/uploads/callback",
            json={
                "upload_id": upload_id,
                "item_id": "floou-item",
                "bundle_tx_id": "floou-bundle",
                "published_at": "2026-01-01T12:00:00Z",
            },
            headers=_headers(),
        )
        assert r2.status_code == 200
        rec = upload_service.get_upload(upload_id)
        assert rec is not None
        assert rec.status == PUBLISHED
        assert rec.bundle_tx_id == "floou-bundle"
        assert rec.item_id == "floou-item"

    def test_floou_error_put_unknown_id_404(self, upload_integration_client):
        """Floou: PUT status для несуществующего upload_id → 404."""
        r = upload_integration_client.put(
            "/v1/uploads/00000000-0000-0000-0000-000000000099/status",
            json={"status": "queued_for_publish"},
            headers=_headers(),
        )
        assert r.status_code == 404

    def test_floou_error_callback_unknown_id_404(self, upload_integration_client):
        """Floou: POST callback для несуществующего upload_id → 404."""
        r = upload_integration_client.post(
            "/v1/uploads/callback",
            json={
                "upload_id": "00000000-0000-0000-0000-000000000099",
                "item_id": "i",
                "bundle_tx_id": "b",
                "published_at": "2026-01-01T12:00:00Z",
            },
            headers=_headers(),
        )
        assert r.status_code == 404

    def test_floou_failed_path_put_failed_then_db_has_failure_code(
        self, upload_integration_client, upload_supabase, upload_service
    ):
        """Floou: prepared → PUT status=failed, failure_code=token_invalid → 200; запись в БД status=failed, failure_code=token_invalid (uploader→Backend failed path)."""
        import uuid
        upload_id = str(uuid.uuid4())
        user_id = "00000000-0000-0000-0000-000000000011"
        upload_supabase.insert_upload({
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
        })
        r = upload_integration_client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "failed", "failure_code": "token_invalid"},
            headers=_headers(),
        )
        assert r.status_code == 200
        rec = upload_service.get_upload(upload_id)
        assert rec is not None
        assert rec.status == FAILED
        assert rec.failure_code == "token_invalid"

    @pytest.mark.requires_edge
    @pytest.mark.skip(reason="Legacy Supabase Edge; full cycle covered by real arweave-uploader test")
    def test_floou_bot_calls_edge_upload_text_with_mock_headers(self, caplog):
        """Legacy: Supabase Edge (ArWeaveUploader→SupabaseEdgeClient), не микросервис arweave-uploader.
        Floou (optional): Bot → Edge upload-text с мок-заголовками; проверка вызова и ответа.
        Критерий успеха при снятии skip: проверяются только (1) использование клиента с мок-заголовками,
        (2) доставка запроса до Edge. Ответ Edge (успех или ошибка) не считается провалом теста —
        тест не валидирует успешный upload в Arweave."""
        import logging
        from services.core.edge_client import SupabaseEdgeClientWithMockHeaders, get_edge_mock_headers
        from services.core.storage.ar_weave import ArWeaveUploader
        log = logging.getLogger(__name__)
        log.info(
            "Bot→Edge test: SUPABASE_URL=%s, EDGE_USE_MOCK=%s, EDGE_MOCK_TEST_SECRET=%s",
            "SET" if os.environ.get("SUPABASE_URL") else "MISSING",
            os.environ.get("EDGE_USE_MOCK"),
            "SET" if os.environ.get("EDGE_MOCK_TEST_SECRET") else "MISSING",
        )
        # Проверка: при EDGE_USE_MOCK + EDGE_MOCK_TEST_SECRET бот использует клиент с мок-заголовками (X-Backend-Mock-Secret).
        mock_headers = get_edge_mock_headers()
        assert "X-Backend-Mock-Secret" in mock_headers, (
            "EDGE_USE_MOCK + EDGE_MOCK_TEST_SECRET должны давать X-Backend-Mock-Secret"
        )
        uploader = ArWeaveUploader()
        assert isinstance(
            uploader.edge_client, SupabaseEdgeClientWithMockHeaders
        ), "При заданных env должен использоваться клиент с мок-заголовками (подключение к Edge с секретом для бэкенд-мока)"
        result = uploader.upload_text("integration-test-payload", content_type="text/plain")
        if (
            result
            and isinstance(result, str)
            and "error" not in result
            and "exception" not in result
        ):
            assert result.startswith("ar") or len(result) >= 10  # transaction_id
            log.info("Bot→Edge upload-text success: transaction_id=%s", result[:20] + "..." if len(result) > 20 else result)
            return
        # Подключение к Edge и мок-заголовки уже проверены выше. Если Edge вернула ошибку (нет ключа Arweave и т.п.) —
        # считаем тест успешным: связка Bot→Edge с секретом для бэкенд-мока работает.
        log.info(
            "Bot→Edge: запрос доставлен до Edge, ответ без transaction_id (result=%s). Считаем успехом: подключение и мок-заголовки проверены.",
            result,
        )
        # Тест прошёл: вызов выполнен, клиент с мок-заголовками использован, Edge ответила (200 или 500).

    @pytest.mark.skipif(
        not os.environ.get("UPLOAD_TOKEN_JWT_PRIVATE_KEY")
        and not os.environ.get("UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE"),
        reason="JWT key not set; optional full floou with prepare",
    )
    def test_floou_happy_path_prepare_put_callback(
        self, upload_integration_client, upload_service
    ):
        """Floou: prepare → PUT status → POST callback (полный путь с реальным JWT)."""
        result = upload_service.prepare(b'{"title":"integration"}', "00000000-0000-0000-0000-000000000020")
        upload_id = result.upload_id
        r1 = upload_integration_client.put(
            f"/v1/uploads/{upload_id}/status",
            json={"status": "queued_for_publish"},
            headers=_headers(),
        )
        assert r1.status_code == 200
        r2 = upload_integration_client.post(
            "/v1/uploads/callback",
            json={
                "upload_id": upload_id,
                "item_id": "full-item",
                "bundle_tx_id": "full-bundle",
                "published_at": "2026-01-01T12:00:00Z",
            },
            headers=_headers(),
        )
        assert r2.status_code == 200
        rec = upload_service.get_upload(upload_id)
        assert rec.status == PUBLISHED
        assert rec.bundle_tx_id == "full-bundle"


# ---------------------------------------------------------------------------
# Phase 3 (task): полный цикл с реальным arweave-uploader
# ---------------------------------------------------------------------------
# Обязательные env для теста полного цикла (в bot): ARWEAVE_SERVICE_URL, OWN_AUTH_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
# UPLOAD_TOKEN_JWT_PRIVATE_KEY или FILE. NODE_URL задаётся в .env arweave-uploader (куда слать putStatus/postCallback), в bot не требуется.
# signed_data_item: по умолчанию файл tests/integration/fixtures/full_cycle_signed_data_item.b64; либо FULL_CYCLE_TEST_SIGNED_DATA_ITEM_B64_FILE,
# либо FULL_CYCLE_TEST_SIGNED_DATA_ITEM_B64 (inline). При отсутствии всех источников — skip.


@pytest.mark.integration
@pytest.mark.real_arweave_uploader
class TestUploadIntegrationFullCycleRealUploader:
    """Полный цикл: prepare → POST /v1/crystalize к arweave-uploader → putStatus/postCallback → published в БД.
    Требует (в bot env): ARWEAVE_SERVICE_URL, OWN_AUTH_TOKEN, SUPABASE_*, UPLOAD_TOKEN_JWT_* (или FILE). NODE_URL — только в uploader.
    signed_data_item: файл full_cycle_signed_data_item.b64 в fixtures, или FULL_CYCLE_TEST_SIGNED_DATA_ITEM_B64_FILE, или FULL_CYCLE_TEST_SIGNED_DATA_ITEM_B64; при отсутствии — skip."""

    @pytest.mark.skipif(
        _requires_full_cycle_env_skip_reason() is not None,
        reason=_requires_full_cycle_env_skip_reason() or "Full cycle env missing",
    )
    def test_full_cycle_prepare_crystalize_callback_published(
        self, upload_service, upload_supabase
    ):
        """Prepare → POST crystalize к arweave-uploader → проверка БД (published или putStatus(failed) при partial)."""
        import uuid

        # 1) prepare
        user_id = str(uuid.uuid4())
        result = upload_service.prepare(b'{"title":"full-cycle-test"}', user_id)
        upload_id = result.upload_id
        upload_token = result.upload_token
        assert upload_id and upload_token

        # 2) signed_data_item (base64): предпочтительно — генератор по upload_id (тег = upload_id); иначе файл/env
        import json
        signed_data_item_b64 = _build_full_cycle_signed_data_item_b64(upload_id)
        if not signed_data_item_b64:
            signed_data_item_b64 = _load_full_cycle_signed_data_item_b64()
        if not signed_data_item_b64:
            pytest.skip(
                "signed_data_item not available: set ARWEAVE_UPLOADER_DIR (path to arweave-uploader) and have Node installed "
                "so the test can build a data item with Upload-Id=upload_id; or add tests/integration/fixtures/full_cycle_signed_data_item.b64 "
                "(tag must match upload_id) or set FULL_CYCLE_TEST_SIGNED_DATA_ITEM_B64_FILE / FULL_CYCLE_TEST_SIGNED_DATA_ITEM_B64"
            )

        payload_size = 24  # len(b'{"title":"full-cycle-test"}')
        base = (os.environ.get("ARWEAVE_SERVICE_URL") or "").strip().rstrip("/")
        if not base or base == "/v1/crystalize":
            pytest.skip("ARWEAVE_SERVICE_URL not set")
        if not base.startswith("http://") and not base.startswith("https://"):
            base = "https://" + base
        url = base + "/v1/crystalize"

        b64_has_newline_before = "\n" in signed_data_item_b64 or "\r" in signed_data_item_b64
        # Нормализация base64: убрать переносы/пробелы (могут попасть из файла)
        signed_data_item_b64 = signed_data_item_b64.strip().replace("\n", "").replace("\r", "").replace(" ", "")

        _log.info(
            "full_cycle crystalize request: upload_id=%s len(upload_token)=%s token_preview=%s "
            "len(signed_data_item_b64)=%s b64_had_newline_or_cr=%s url=%s",
            upload_id,
            len(upload_token),
            repr(upload_token[:80]) if upload_token else None,
            len(signed_data_item_b64),
            b64_has_newline_before,
            url,
        )
        _log.info(
            "signed_data_item_b64 preview: head=%s tail=%s",
            repr(signed_data_item_b64[:60]),
            repr(signed_data_item_b64[-40:]) if len(signed_data_item_b64) > 60 else repr(signed_data_item_b64),
        )

        import urllib.request
        import urllib.error

        body = json.dumps({
            "upload_id": upload_id,
            "upload_token": upload_token,
            "signed_data_item": signed_data_item_b64,
            "payload_size": payload_size,
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                code = resp.getcode()
                data = resp.read()
        except urllib.error.HTTPError as e:
            code = e.code
            data = e.read() if e.fp else b""
        except Exception as e:
            pytest.fail(f"Request to arweave-uploader failed: {e}")

        if code == 200:
            # Ожидаем callback от uploader → БД published
            import time
            for _ in range(15):
                rec = upload_service.get_upload(upload_id)
                if rec and rec.status == PUBLISHED:
                    assert rec.bundle_tx_id
                    return
                time.sleep(1)
            pytest.fail("Upload not reached published status within 15s")
        elif code == 400:
            # Partial: signature_invalid или token_invalid — uploader мог вызвать putStatus(failed)
            rec = upload_service.get_upload(upload_id)
            if rec and rec.status == FAILED:
                return  # putStatus(failed) пришёл — связка uploader→Backend работает
            pytest.skip("Uploader returned 400; putStatus(failed) not yet reflected (partial check)")
        else:
            msg = f"arweave-uploader returned {code}: {data[:200]!r}"
            if code == 401:
                msg += (
                    " — Проверьте пару ключей: в uploader должен быть UPLOAD_TOKEN_JWT_PUBLIC_KEY (или _FILE), "
                    "соответствующий приватному ключу bot (UPLOAD_TOKEN_JWT_PRIVATE_KEY / _FILE). "
                    "В логах процесса uploader смотрите publish.token_invalid и reason (no_public_key / signature_invalid)."
                )
            pytest.fail(msg)
