import os
import pytest
import asyncio
import httpx
import time
import uuid
import hmac
import hashlib
# Используем реальные API ключи из .env файла
AMANITA_API_KEY = os.getenv("AMANITA_API_KEY", "ak_22bc74537e53698e")
AMANITA_API_SECRET = os.getenv("AMANITA_API_SECRET", "sk_9160864a1ba617780cce32258248c21d085d8ddb18d3250ff4532925102d1b68")

API_URL = os.getenv("AMANITA_API_URL", "http://localhost:8000")

# Важно: FastAPI сервер должен быть запущен!


def generate_hmac_headers(method, path, body, api_key, api_secret):
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    message = f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}"
    signature = hmac.new(
        api_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return {
        "X-API-Key": api_key,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
        "Content-Type": "application/json"
    }

@pytest.mark.asyncio
async def test_auth_success():
    """Проверяет успешную авторизацию по HMAC"""
    method = "POST"
    path = "/auth-test"
    url = API_URL + path
    body = "{}"
    headers = generate_hmac_headers(method, path, body, AMANITA_API_KEY, AMANITA_API_SECRET)
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, content=body)
        assert resp.status_code == 200, f"Ожидался 200, получено {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("success") is True
        assert data.get("message") == "Authentication successful"
        print("✅ Успешная авторизация прошла")

@pytest.mark.asyncio
async def test_auth_fail_wrong_signature():
    """Проверяет отказ при неправильной подписи"""
    method = "POST"
    path = "/auth-test"
    url = API_URL + path
    body = "{}"
    headers = generate_hmac_headers(method, path, body, AMANITA_API_KEY, AMANITA_API_SECRET)
    headers["X-Signature"] = "invalidsignature"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, content=body)
        assert resp.status_code == 401, f"Ожидался 401, получено {resp.status_code}: {resp.text}"
        print("✅ Неверная подпись правильно отклонена")

@pytest.mark.asyncio
async def test_auth_fail_wrong_key():
    """Проверяет отказ при неправильном API ключе"""
    method = "POST"
    path = "/auth-test"
    url = API_URL + path
    body = "{}"
    headers = generate_hmac_headers(method, path, body, "ak_invalidkey123", AMANITA_API_SECRET)
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, content=body)
        assert resp.status_code == 401, f"Ожидался 401, получено {resp.status_code}: {resp.text}"
        print("✅ Неверный API ключ правильно отклонён")

@pytest.mark.asyncio
async def test_auth_fail_no_headers():
    """Проверяет отказ при отсутствии HMAC-заголовков"""
    method = "POST"
    path = "/auth-test"
    url = API_URL + path
    body = "{}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, content=body)
        assert resp.status_code == 401, f"Ожидался 401, получено {resp.status_code}: {resp.text}"
        print("✅ Отсутствие HMAC-заголовков правильно отклонено")

@pytest.mark.asyncio
async def test_docs_public_access():
    """Проверяет публичный доступ к /docs, /redoc без HMAC"""
    async with httpx.AsyncClient() as client:
        resp_docs = await client.get(API_URL + "/docs")
        assert resp_docs.status_code == 200, f"/docs: {resp_docs.status_code} {resp_docs.text}"
        assert "Swagger UI" in resp_docs.text or "swagger-ui" in resp_docs.text.lower()

        resp_redoc = await client.get(API_URL + "/redoc")
        assert resp_redoc.status_code == 200, f"/redoc: {resp_redoc.status_code} {resp_redoc.text}"
        assert "Redoc" in resp_redoc.text or "redoc" in resp_redoc.text.lower()

        # TODO: Исправить проблему с /openapi.json
        # resp_openapi = await client.get(API_URL + "/openapi.json")
        # assert resp_openapi.status_code == 200, f"/openapi.json: {resp_openapi.status_code} {resp_openapi.text}"
        # assert resp_openapi.headers["content-type"].startswith("application/json")
        # assert "openapi" in resp_openapi.text
        print("✅ Публичный доступ к документации работает") 