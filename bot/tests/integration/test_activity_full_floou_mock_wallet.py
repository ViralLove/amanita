"""
Full floou test (W7): draft → sign_arweave → (GET sign-payload, эмуляция uploader: PUT status + callback)
→ sign_contract → GET sign-request → POST submit.

Вариант B: тест сам играет роль runner (in-process), без запуска wallet-mock subprocess.
Моки: PrepareResolveService, UploadService (stateful), BlockchainService. Реальные: PayloadCache,
StubPushSender, SignRequestStore.

Вариант E2E (full_floou_real_services): bot в потоке, arweave-uploader и wallet-mock — subprocess.
Тест выполняет sign_arweave до crystalize (скрипт build-full-cycle-data-item.js); uploader вызывает
Backend; wallet-mock обрабатывает только sign_contract.
"""

from __future__ import annotations

import base64
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

# bot root (tests/integration -> tests -> bot)
_bot_dir = Path(__file__).resolve().parent.parent
if str(_bot_dir) not in sys.path:
    sys.path.insert(0, str(_bot_dir))

from model.upload import UploadRecord
from services.upload.jwt_upload_token import JWTUploadTokenError, sign_upload_token
from services.upload.storage import PrepareForDraftResult
from services.wallet_push import PayloadCache, SignRequestStore, StubPushSender

USER_ID = "user-full-floou"
UPLOAD_ID = "upload-full-floou-1"
EDGE_SECRET = "mock-edge-to-backend-secret"
BUNDLE_TX_ID = "bundle-tx-full-floou"


@pytest.fixture(autouse=True)
def env_edge_secret():
    old = os.environ.get("EDGE_TO_BACKEND_SECRET")
    os.environ["EDGE_TO_BACKEND_SECRET"] = EDGE_SECRET
    yield
    if old is None:
        os.environ.pop("EDGE_TO_BACKEND_SECRET", None)
    else:
        os.environ["EDGE_TO_BACKEND_SECRET"] = old


@pytest.fixture
def upload_record():
    """Мутабельная запись upload для мока; статус меняется через update_status и handle_callback."""
    return UploadRecord(
        upload_id=UPLOAD_ID,
        user_id=USER_ID,
        status="prepared",
        payload_hash=None,
        payload_size=100,
        tags_snapshot=None,
        anchor="anchor-1",
        expires_at=datetime.now(timezone.utc),
        item_id=None,
        bundle_tx_id=None,
        activity_id="draft-1",
        created_at=None,
        updated_at=None,
    )


@pytest.fixture
def mock_upload_svc(upload_record):
    svc = MagicMock()

    def get_upload(uid):
        return upload_record if uid == UPLOAD_ID else None

    def update_status(uid, status, failure_code=None):
        if uid == UPLOAD_ID:
            upload_record.status = status

    def handle_callback(uid, item_id=None, bundle_tx_id=None, owner_address=None):
        if uid == UPLOAD_ID:
            upload_record.status = "published"
            upload_record.item_id = item_id or "item-1"
            upload_record.bundle_tx_id = bundle_tx_id or BUNDLE_TX_ID

    svc.get_upload.side_effect = get_upload
    svc.update_status.side_effect = update_status
    svc.handle_callback.side_effect = handle_callback
    return svc


@pytest.fixture
def mock_prepare_svc():
    svc = MagicMock()
    svc.prepare_upload_for_draft.return_value = PrepareForDraftResult(
        upload_id=UPLOAD_ID,
        upload_token="jwt.full-floou",
        payload_bytes=b'{"title": "Full Floou Test", "activity_type": "event"}',
        tags_for_item=[{"name": "Upload-Id", "value": UPLOAD_ID}],
        anchor="anchor-1",
        expires_at=datetime.now(timezone.utc),
    )
    return svc


@pytest.fixture
def push_sender():
    return StubPushSender()


@pytest.fixture
def sign_request_store():
    return SignRequestStore()


@pytest.fixture
def payload_cache():
    return PayloadCache(default_ttl_sec=3600)


@pytest.fixture
def mock_blockchain():
    m = MagicMock()
    m.submit_sign_request_raw_transaction.return_value = "0xtx_hash_full_floou"
    m.get_sign_request_evm_params.return_value = ("137", "0xActivityRegistry")
    return m


def _create_app(prepare_svc, mock_upload_svc, push_sender, sign_request_store, payload_cache, mock_blockchain):
    mock_registry = MagicMock()
    with patch.dict(sys.modules, {"services.product.registry_singleton": mock_registry}):
        from api.dependencies import (
            get_activity_storage,
            get_blockchain_service,
            get_payload_cache,
            get_prepare_resolve_service,
            get_push_sender,
            get_sign_request_store,
            get_upload_service,
        )
        from api.routes import activities, pending_sign_requests, sign_requests, uploads
        from api.services import ActivityStorage

        def _get_blockchain():
            return mock_blockchain

    app = FastAPI()
    app.include_router(activities.router)
    app.include_router(uploads.router)
    app.include_router(pending_sign_requests.router)
    app.include_router(sign_requests.router)
    app.dependency_overrides[get_activity_storage] = lambda: ActivityStorage()
    app.dependency_overrides[get_prepare_resolve_service] = lambda: prepare_svc
    app.dependency_overrides[get_upload_service] = lambda: mock_upload_svc
    app.dependency_overrides[get_push_sender] = lambda: push_sender
    app.dependency_overrides[get_sign_request_store] = lambda: sign_request_store
    app.dependency_overrides[get_payload_cache] = lambda: payload_cache
    app.dependency_overrides[get_blockchain_service] = _get_blockchain
    return app


@pytest.fixture
def app(mock_prepare_svc, mock_upload_svc, push_sender, sign_request_store, payload_cache, mock_blockchain):
    return _create_app(
        mock_prepare_svc, mock_upload_svc, push_sender, sign_request_store, payload_cache, mock_blockchain
    )


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def e2e_prepare_svc():
    """Prepare-сервис для E2E: возвращает реальный JWT (uploader проверяет при crystalize)."""
    try:
        upload_token = sign_upload_token(
            upload_id=UPLOAD_ID,
            user_id=USER_ID,
            max_bytes=2**20,
            exp_seconds=3600,
        )
    except JWTUploadTokenError:
        pytest.skip("E2E: не удалось подписать JWT (ключ из env)")
    svc = MagicMock()
    svc.prepare_upload_for_draft.return_value = PrepareForDraftResult(
        upload_id=UPLOAD_ID,
        upload_token=upload_token,
        payload_bytes=b'{"title": "Full Floou E2E", "activity_type": "event"}',
        tags_for_item=[{"name": "Upload-Id", "value": UPLOAD_ID}],
        anchor="anchor-1",
        expires_at=datetime.now(timezone.utc),
    )
    return svc


@pytest.fixture
def app_e2e(
    e2e_prepare_svc, mock_upload_svc, push_sender, sign_request_store, payload_cache, mock_blockchain
):
    """App для E2E: prepare с реальным JWT (тот же store/sender для проверки)."""
    return _create_app(
        e2e_prepare_svc, mock_upload_svc, push_sender, sign_request_store, payload_cache, mock_blockchain
    )


def _x_user_id():
    return {"X-User-Id": USER_ID, "Content-Type": "application/json"}


def _edge_headers():
    return {"Authorization": f"Bearer {EDGE_SECRET}", "Content-Type": "application/json"}


@pytest.mark.integration
@pytest.mark.full_floou_mock_wallet
class TestFullFloouDraftToSubmitInProcessRunner:
    """
    Сквозной тест: draft → pending (sign_arweave) → sign-payload → PUT status + callback
    → pending (sign_contract) → sign-request → submit → проверка store (submitted, tx_hash).
    """

    def test_full_floou_draft_to_submit_in_process_runner(
        self, client, push_sender, sign_request_store, upload_record
    ):
        # 1) POST draft
        r = client.post(
            "/activities/draft",
            json={
                "activity_type": "event",
                "title": "Full Floou",
                "short_summary": "Summary",
            },
            headers=_x_user_id(),
        )
        assert r.status_code == 201
        data = r.json()
        assert data.get("success") is True
        assert data.get("upload_id") == UPLOAD_ID

        # 2) GET pending-sign-requests (runner забирает событие sign_arweave)
        r2 = client.get(
            f"/v1/pending-sign-requests?user_id={USER_ID}",
            headers=_x_user_id(),
        )
        assert r2.status_code == 200
        events = r2.json().get("events") or []
        assert len(events) == 1
        assert events[0]["request_type"] == "sign_arweave"
        assert events[0]["request_id"] == UPLOAD_ID

        # 3) GET sign-payload
        r3 = client.get(
            f"/v1/uploads/{UPLOAD_ID}/sign-payload",
            headers=_x_user_id(),
        )
        assert r3.status_code == 200
        payload_data = r3.json()
        assert payload_data.get("upload_id") == UPLOAD_ID
        assert "payload_base64" in payload_data

        # 4) Эмуляция uploader: PUT status, затем POST callback (без реального crystalize)
        r4 = client.put(
            f"/v1/uploads/{UPLOAD_ID}/status",
            json={"status": "queued_for_publish"},
            headers=_edge_headers(),
        )
        assert r4.status_code == 200

        r5 = client.post(
            "/v1/uploads/callback",
            json={
                "upload_id": UPLOAD_ID,
                "item_id": "item-1",
                "bundle_tx_id": BUNDLE_TX_ID,
                "published_at": "2026-01-29T12:00:00Z",
            },
            headers=_edge_headers(),
        )
        assert r5.status_code == 200
        cb = r5.json()
        assert cb.get("ok") is True
        assert cb.get("sign_contract_enqueued") is True
        assert cb.get("sign_request_id")
        assert upload_record.status == "published"

        # 6) GET pending-sign-requests (событие sign_contract)
        r6 = client.get(
            f"/v1/pending-sign-requests?user_id={USER_ID}",
            headers=_x_user_id(),
        )
        assert r6.status_code == 200
        events2 = r6.json().get("events") or []
        assert len(events2) == 1
        assert events2[0]["request_type"] == "sign_contract"
        sign_request_id = events2[0]["request_id"]
        assert sign_request_id

        # 7) GET sign-request
        r7 = client.get(
            f"/v1/sign-requests/{sign_request_id}",
            headers=_x_user_id(),
        )
        assert r7.status_code == 200
        assert r7.json().get("upload_id") == UPLOAD_ID
        assert r7.json().get("cid") == BUNDLE_TX_ID

        # 8) POST submit (мок broadcast возвращает tx_hash)
        r8 = client.post(
            f"/v1/sign-requests/{sign_request_id}/submit",
            json={"signedTransaction": "0x00"},
            headers=_x_user_id(),
        )
        assert r8.status_code == 200
        submit_data = r8.json()
        assert submit_data.get("ok") is True
        assert submit_data.get("tx_hash") == "0xtx_hash_full_floou"

        # 9) Проверка store
        rec = sign_request_store.get(sign_request_id)
        assert rec is not None
        assert rec.status == "submitted"
        assert rec.submitted_at is not None
        assert rec.tx_hash == "0xtx_hash_full_floou"


# ---------------------------------------------------------------------------
# E2E с реальными сервисами (bot в потоке, arweave-uploader, wallet-mock — subprocess)
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Корень репо: bot/tests/integration -> bot -> repo."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _arweave_uploader_dir() -> Path | None:
    """Каталог arweave-uploader (для скрипта и запуска сервера)."""
    env_path = os.environ.get("ARWEAVE_UPLOADER_DIR")
    if env_path and env_path.strip():
        p = Path(env_path.strip()).resolve()
        if p.is_dir():
            return p
    candidate = _repo_root() / "arweave-uploader"
    return candidate if candidate.is_dir() else None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _build_signed_data_item_b64(upload_id: str, payload_base64: str, uploader_dir: Path) -> str | None:
    """Подписанный Data Item base64 через scripts/build-full-cycle-data-item.js (payload из temp file)."""
    script = uploader_dir / "scripts" / "build-full-cycle-data-item.js"
    if not script.is_file():
        return None
    node = shutil.which("node") or "node"
    payload_bytes = base64.b64decode(payload_base64) if payload_base64 else b'{"title":"full-cycle-test"}'
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(payload_bytes)
        tmp = f.name
    try:
        r = subprocess.run(
            [node, str(script), upload_id, tmp],
            cwd=str(uploader_dir),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode != 0 or not r.stdout:
            return None
        return r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _skip_reason_real_services() -> str | None:
    """Причина skip E2E real services: None если можно запускать."""
    if not shutil.which("node"):
        return "Node.js не найден (нужен для arweave-uploader и wallet-mock)"
    uploader_dir = _arweave_uploader_dir()
    if not uploader_dir:
        return "ARWEAVE_UPLOADER_DIR или каталог arweave-uploader не найден"
    if not (uploader_dir / "dist" / "server.js").is_file():
        return "arweave-uploader: dist/server.js не найден (соберите проект)"
    # Uploader проверяет JWT при crystalize; нужна пара ключей (bot — private, uploader — public)
    if not (os.environ.get("UPLOAD_TOKEN_JWT_PRIVATE_KEY") or os.environ.get("UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE")):
        return "Для E2E задайте UPLOAD_TOKEN_JWT_PRIVATE_KEY или UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE (bot)"
    if not (os.environ.get("UPLOAD_TOKEN_JWT_PUBLIC_KEY") or os.environ.get("UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE")):
        return "Для E2E задайте UPLOAD_TOKEN_JWT_PUBLIC_KEY или UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE (uploader)"
    return None


@pytest.mark.integration
@pytest.mark.full_floou_real_services
@pytest.mark.skipif(_skip_reason_real_services() is not None, reason=_skip_reason_real_services() or "")
class TestFullFloouRealServices:
    """
    E2E: bot (uvicorn в потоке) + arweave-uploader + wallet-mock.
    Тест выполняет sign_arweave до crystalize (валидный Data Item через скрипт); uploader вызывает
    Backend; wallet-mock обрабатывает sign_contract (GET sign-request → POST submit).
    """

    def test_full_floou_real_services(
        self,
        app_e2e,
        sign_request_store,
        upload_record,
    ):
        uploader_dir = _arweave_uploader_dir()
        assert uploader_dir is not None
        repo = _repo_root()
        wallet_runner = repo / "wallet" / "mock-runner" / "index.js"
        if not wallet_runner.is_file():
            pytest.skip("wallet/mock-runner/index.js не найден")

        bot_port = _free_port()
        uploader_port = _free_port()
        base_url = f"http://127.0.0.1:{bot_port}"
        uploader_url = f"http://127.0.0.1:{uploader_port}"
        env_uploader = {
            **os.environ,
            "BACKEND_URL": base_url,
            "EDGE_TO_BACKEND_SECRET": EDGE_SECRET,
            "PORT": str(uploader_port),
        }
        env_wallet = {
            **os.environ,
            "BOT_URL": base_url,
            "USER_ID": USER_ID,
            "POLL_INTERVAL_MS": "500",
        }

        # Запуск bot в потоке
        import uvicorn
        thread = threading.Thread(
            target=uvicorn.run,
            kwargs={"app": app_e2e, "host": "127.0.0.1", "port": bot_port, "log_level": "warning"},
            daemon=True,
        )
        thread.start()
        time.sleep(1.5)

        proc_uploader = None
        proc_wallet = None
        try:
            # Запуск arweave-uploader
            proc_uploader = subprocess.Popen(
                [shutil.which("node") or "node", "dist/server.js"],
                cwd=str(uploader_dir),
                env=env_uploader,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            time.sleep(1.0)

            # 1) POST draft
            r = requests.post(
                f"{base_url}/activities/draft",
                json={"activity_type": "event", "title": "Full Floou E2E", "short_summary": "Summary"},
                headers={"X-User-Id": USER_ID, "Content-Type": "application/json"},
                timeout=5,
            )
            assert r.status_code == 201, r.text
            assert r.json().get("upload_id") == UPLOAD_ID

            # 2) Тест забирает sign_arweave и выполняет crystalize
            r2 = requests.get(
                f"{base_url}/v1/pending-sign-requests",
                params={"user_id": USER_ID},
                headers={"X-User-Id": USER_ID},
                timeout=5,
            )
            assert r2.status_code == 200
            events = r2.json().get("events") or []
            assert len(events) == 1 and events[0]["request_type"] == "sign_arweave"

            r3 = requests.get(
                f"{base_url}/v1/uploads/{UPLOAD_ID}/sign-payload",
                headers={"X-User-Id": USER_ID},
                timeout=5,
            )
            assert r3.status_code == 200
            payload_data = r3.json()
            payload_b64 = payload_data.get("payload_base64") or ""
            upload_token = payload_data.get("upload_token") or ""
            payload_size = len(base64.b64decode(payload_b64)) if payload_b64 else 0

            signed_b64 = _build_signed_data_item_b64(UPLOAD_ID, payload_b64, uploader_dir)
            assert signed_b64, "Не удалось собрать подписанный Data Item"

            r4 = requests.post(
                f"{uploader_url}/v1/crystalize",
                json={
                    "upload_id": UPLOAD_ID,
                    "upload_token": upload_token,
                    "signed_data_item": signed_b64,
                    "payload_size": payload_size,
                },
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            assert r4.status_code == 200, (r4.status_code, r4.text)

            # 3) Ждём callback от uploader к боту
            time.sleep(3.0)
            assert upload_record.status == "published"

            # 4) Запуск wallet-mock (обработает sign_contract)
            proc_wallet = subprocess.Popen(
                [shutil.which("node") or "node", str(wallet_runner)],
                cwd=str(repo),
                env=env_wallet,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

            # 5) Ожидание submit по store
            deadline = time.monotonic() + 15.0
            submitted_rec = None
            while time.monotonic() < deadline:
                for rec in sign_request_store.list_by_user(USER_ID):
                    if rec.status == "submitted" and rec.tx_hash:
                        submitted_rec = rec
                        break
                if submitted_rec:
                    break
                time.sleep(0.5)

            assert submitted_rec is not None, "В store не появилась запись submitted с tx_hash"
            assert submitted_rec.tx_hash == "0xtx_hash_full_floou"
        finally:
            if proc_wallet:
                proc_wallet.terminate()
                proc_wallet.wait(timeout=5)
            if proc_uploader:
                proc_uploader.terminate()
                proc_uploader.wait(timeout=5)
