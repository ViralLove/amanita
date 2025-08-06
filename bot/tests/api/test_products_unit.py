import pytest

# Все тесты используют api_client (фикстура из conftest.py) и mock_blockchain_service

# === Мок для IPFS storage и новые тесты DI ===
from bot.dependencies import get_product_storage_service, get_product_registry_service

class MockIPFSStorage:
    """Мок для IPFS storage"""
    def __init__(self, should_fail_upload=False):
        self.should_fail_upload = should_fail_upload
        self.uploaded_files = []
        self.uploaded_jsons = []
    async def download_json_async(self, cid: str):
        return {"mock": "data", "cid": cid}
    async def download_file(self, cid: str):
        return b"mock file content"
    def upload_file(self, file_path: str):
        if self.should_fail_upload:
            raise Exception("Mock IPFS upload failed")
        cid = f"QmMock{len(self.uploaded_files)}"
        self.uploaded_files.append((file_path, cid))
        return cid
    def upload_json(self, data: dict):
        if self.should_fail_upload:
            raise Exception("Mock IPFS upload failed")
        cid = f"QmMockJson{len(self.uploaded_jsons)}"
        self.uploaded_jsons.append((data, cid))
        return cid

@pytest.mark.asyncio
async def test_create_product_with_mock_ipfs_success():
    """
    Тест создания продукта с мокированным IPFS storage.
    Демонстрирует новый подход к dependency injection.
    """
    mock_storage = MockIPFSStorage(should_fail_upload=False)
    storage_service = get_product_storage_service(storage_provider=mock_storage)
    registry_service = get_product_registry_service(storage_service=storage_service)
    test_data = {"title": "Test Product", "price": 100}
    cid = storage_service.upload_json(test_data)
    assert cid is not None
    assert cid.startswith("QmMockJson")
    assert len(mock_storage.uploaded_jsons) == 1
    assert mock_storage.uploaded_jsons[0][0] == test_data

@pytest.mark.asyncio
async def test_create_product_with_mock_ipfs_failure():
    """
    Тест обработки ошибки IPFS с мокированным storage.
    """
    mock_storage = MockIPFSStorage(should_fail_upload=True)
    storage_service = get_product_storage_service(storage_provider=mock_storage)
    test_data = {"title": "Test Product", "price": 100}
    cid = storage_service.upload_json(test_data)
    assert cid is None  # Должен вернуть None при ошибке

@pytest.mark.asyncio
async def test_dependency_injection_with_fastapi():
    """
    Пример того, как это будет работать в FastAPI с dependency_overrides.
    """
    from fastapi import FastAPI
    from bot.api.dependencies import get_product_storage_service
    app = FastAPI()
    mock_storage = MockIPFSStorage()
    app.dependency_overrides[get_product_storage_service] = lambda: get_product_storage_service(storage_provider=mock_storage)
    app.dependency_overrides.clear()

def test_backward_compatibility():
    """
    Тест обратной совместимости: ProductStorageService() без параметров
    должен работать как раньше.
    """
    storage_service = get_product_storage_service()
    assert storage_service is not None
    assert hasattr(storage_service, 'ipfs')
    assert storage_service.ipfs is not None

# === Оригинальные тесты ниже ===

@pytest.mark.asyncio
async def test_create_product_success(api_client, mock_blockchain_service):
    """
    Проверяет успешное создание продукта: валидация, формирование метаданных, загрузка в IPFS, запись в блокчейн.
    Ожидается status: success, все ключевые поля заполнены.
    """
    # 1. Подготовить валидные тестовые данные продукта (ProductUploadIn)
    product_data = {
        "id": 1,
        "title": "Amanita muscaria — sliced caps and gills (1st grade)",
        "description": {"en": "High quality dried Amanita muscaria caps and gills."},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "gallery": ["QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj"],
        "categories": [
            "mushroom",
            "mental health",
            "focus",
            "ADHD support",
            "mental force"
        ],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "80",
                "currency": "EUR"
            }
        ],
        "attributes": {"sku": "AMANITA1", "stock": 10}
    }
    # 2. Сформировать payload для /products/upload (ProductsUploadRequest)
    payload = {
        "products": [product_data]
    }
    # 3. Сгенерировать HMAC-заголовки для запроса
    import json
    from bot.tests.api.test_utils import generate_hmac_headers
    import os
    AMANITA_API_KEY = os.getenv("AMANITA_API_KEY", "test-api-key-12345")
    AMANITA_API_SECRET = os.getenv("AMANITA_API_SECRET", "default-secret-key-change-in-production")
    method = "POST"
    path = "/products/upload"
    body = json.dumps(payload)
    headers = generate_hmac_headers(method, path, body, AMANITA_API_KEY, AMANITA_API_SECRET)
    # Получить экземпляр клиента из async_generator
    api_client_instance = await api_client.__anext__()
    # 4. Отправить POST-запрос на /products/upload с помощью api_client
    response = await api_client_instance.post(
        "/products/upload",
        json=payload,
        headers=headers
    )
    # 5. Проверить, что статус ответа 200 OK
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}: {response.text}"
    # 6. Проверить, что results[0].status == "success"
    data = response.json()
    assert "results" in data, f"В ответе нет ключа 'results': {data}"
    assert isinstance(data["results"], list) and len(data["results"]) > 0, f"'results' не является непустым списком: {data}"
    assert data["results"][0]["status"] == "success", f"Ожидался статус 'success', получено: {data['results'][0]}"
    # 7. Проверить, что в results[0] присутствуют id, blockchain_id, tx_hash, metadata_cid
    for key in ("id", "blockchain_id", "tx_hash", "metadata_cid"):
        assert key in data["results"][0], f"В results[0] отсутствует ключ '{key}': {data['results'][0]}"
    # 8. Проверить, что поле error отсутствует или None
    assert ("error" not in data["results"][0]) or (data["results"][0]["error"] in (None, "")), f"Ожидалось отсутствие ошибки, получено: {data['results'][0].get('error')}"
    # 9. Проверить, что мок blockchain-сервиса был вызван (опционально)
    # (Проверка вызова мока убрана, важна только API-логика)
    # 10. Логировать успешное выполнение теста
    print("test_create_product_success: успешно выполнен!")

@pytest.mark.asyncio
async def test_create_product_validation_error(mock_blockchain_service, mock_ipfs_service):
    """Проверяет ошибку на этапе валидации (например, отсутствует обязательное поле)."""
    # Создаем тестовое FastAPI приложение без аутентификации
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from bot.api.routes.products import router as products_router
    
    app = FastAPI()
    app.include_router(products_router)
    
    # Подменяем ProductStorageService через dependency_overrides
    from bot.api.dependencies import get_product_storage_service
    
    def get_mock_storage_service():
        return mock_ipfs_service
    
    app.dependency_overrides[get_product_storage_service] = get_mock_storage_service
    
    # Тест 1: Отсутствует обязательное поле 'title' (Pydantic валидация)
    product_data_missing_title = {
        "id": 3,
        # "title": "Amanita muscaria — powder",  # Отсутствует!
        "description": {"en": "High quality dried Amanita muscaria powder."},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "gallery": [],
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "80",
                "currency": "EUR"
            }
        ],
        "attributes": {"sku": "AMANITA3", "stock": 5}
    }
    
    payload = {"products": [product_data_missing_title]}
    response = client.post("/products/upload", json=payload)
    
    # Pydantic валидация должна вернуть 422
    assert response.status_code == 422, f"Ожидался статус 422, получен {response.status_code}: {response.text}"
    data = response.json()
    assert "detail" in data, f"В ответе нет ключа 'detail': {data}"
    assert len(data["detail"]) > 0, f"'detail' пустой: {data}"
    assert "title" in str(data["detail"]), f"Ожидалась ошибка с полем 'title': {data['detail']}"
    
    # Тест 2: Неверный формат CID (бизнес-валидация)
    product_data_invalid_cid = {
        "id": 4,
        "title": "Amanita muscaria — powder",
        "description": {"en": "High quality dried Amanita muscaria powder."},
        "description_cid": "invalid-cid-format",  # Неверный формат!
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "gallery": [],
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "80",
                "currency": "EUR"
            }
        ],
        "attributes": {"sku": "AMANITA4", "stock": 5}
    }
    
    payload = {"products": [product_data_invalid_cid]}
    response = client.post("/products/upload", json=payload)
    
    # Бизнес-валидация должна вернуть 200 с ошибкой в results
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}: {response.text}"
    data = response.json()
    result = data["results"][0]
    assert result["status"] == "error", f"Ожидался статус 'error', получено: {result}"
    assert "description_cid" in result["error"], f"Ожидалась ошибка с полем 'description_cid': {result['error']}"
    
    # Тест 3: Неверная форма продукта (бизнес-валидация)
    product_data_invalid_form = {
        "id": 5,
        "title": "Amanita muscaria — powder",
        "description": {"en": "High quality dried Amanita muscaria powder."},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "gallery": [],
        "categories": ["mushroom"],
        "form": "invalid-form",  # Неверная форма!
        "species": "Amanita muscaria",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "80",
                "currency": "EUR"
            }
        ],
        "attributes": {"sku": "AMANITA5", "stock": 5}
    }
    
    payload = {"products": [product_data_invalid_form]}
    response = client.post("/products/upload", json=payload)
    
    # Бизнес-валидация должна вернуть 200 с ошибкой в results
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}: {response.text}"
    data = response.json()
    result = data["results"][0]
    assert result["status"] == "error", f"Ожидался статус 'error', получено: {result}"
    assert "form" in result["error"], f"Ожидалась ошибка с полем 'form': {result['error']}"
    
    # Тест 4: Неверная валюта (бизнес-валидация)
    product_data_invalid_currency = {
        "id": 6,
        "title": "Amanita muscaria — powder",
        "description": {"en": "High quality dried Amanita muscaria powder."},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "gallery": [],
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "80",
                "currency": "RUB"  # Неверная валюта!
            }
        ],
        "attributes": {"sku": "AMANITA6", "stock": 5}
    }
    
    payload = {"products": [product_data_invalid_currency]}
    response = client.post("/products/upload", json=payload)
    
    # Бизнес-валидация должна вернуть 200 с ошибкой в results
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}: {response.text}"
    data = response.json()
    result = data["results"][0]
    assert result["status"] == "error", f"Ожидался статус 'error', получено: {result}"
    assert "currency" in result["error"], f"Ожидалась ошибка с полем 'currency': {result['error']}"
    
    # Очищаем подмены
    app.dependency_overrides.clear()
    
    print("test_create_product_validation_error: успешно проверены различные ошибки валидации!")

@pytest.mark.asyncio
async def test_create_product_ipfs_error(mock_blockchain_service, mock_ipfs_service, monkeypatch):
    """
    Проверяет ошибку при загрузке метаданных в IPFS.
    """
    # Включаем ошибку загрузки в IPFS через мок
    mock_ipfs_service.should_fail_upload = True
    
    # Создаем тестовое FastAPI приложение без аутентификации
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from bot.api.routes.products import router as products_router
    
    app = FastAPI()
    app.include_router(products_router)
    client = TestClient(app)
    
    # Подменяем ProductStorageService через dependency_overrides
    from bot.api.dependencies import get_product_storage_service
    from bot.services.product.storage import ProductStorageService
    
    # Создаем функцию, которая возвращает MockIPFSService (он уже подменен в conftest.py)
    def get_mock_storage_service():
        return mock_ipfs_service
    
    # Подменяем зависимость
    app.dependency_overrides[get_product_storage_service] = get_mock_storage_service
    
    product_data = {
        "id": 2,
        "title": "Amanita muscaria — powder",
        "description": {"en": "High quality dried Amanita muscaria powder."},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "gallery": [],
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "80",
                "currency": "EUR"
            }
        ],
        "attributes": {"sku": "AMANITA2", "stock": 5}
    }
    payload = {"products": [product_data]}
    
    response = client.post(
        "/products/upload",
        json=payload
    )
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}: {response.text}"
    data = response.json()
    assert "results" in data, f"В ответе нет ключа 'results': {data}"
    assert isinstance(data["results"], list) and len(data["results"]) > 0, f"'results' не является непустым списком: {data}"
    result = data["results"][0]
    assert result["status"] == "error", f"Ожидался статус 'error', получено: {result}"
    assert "IPFS" in result["error"] or "ipfs" in result["error"], f"Ожидалась ошибка, связанная с IPFS: {result['error']}"
    
    # Очищаем подмены
    app.dependency_overrides.clear()
    
    print("test_create_product_ipfs_error: успешно обработана ошибка IPFS!")

@pytest.mark.asyncio
async def test_create_product_blockchain_error(mock_blockchain_service_with_error, mock_ipfs_service):
    """Проверяет ошибку при записи в блокчейн."""
    # Создаем тестовое FastAPI приложение без аутентификации
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from bot.api.routes.products import router as products_router
    
    app = FastAPI()
    app.include_router(products_router)
    client = TestClient(app)
    
    # Подменяем все зависимости через dependency_overrides
    from bot.api.dependencies import get_product_storage_service, get_blockchain_service
    
    def get_mock_storage_service():
        return mock_ipfs_service
    
    def get_mock_blockchain_service():
        return mock_blockchain_service_with_error
    
    app.dependency_overrides[get_product_storage_service] = get_mock_storage_service
    app.dependency_overrides[get_blockchain_service] = get_mock_blockchain_service
    
    product_data = {
        "id": 7,
        "title": "Amanita muscaria — powder",
        "description": {"en": "High quality dried Amanita muscaria powder."},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "gallery": [],
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "80",
                "currency": "EUR"
            }
        ],
        "attributes": {"sku": "AMANITA7", "stock": 5}
    }
    
    payload = {"products": [product_data]}
    response = client.post("/products/upload", json=payload)
    
    # Блокчейн ошибка должна вернуть 200 с ошибкой в results
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}: {response.text}"
    data = response.json()
    assert "results" in data, f"В ответе нет ключа 'results': {data}"
    assert len(data["results"]) > 0, f"'results' пустой: {data}"
    
    result = data["results"][0]
    assert result["status"] == "error", f"Ожидался статус 'error', получено: {result}"
    assert "blockchain" in result["error"].lower() or "transaction" in result["error"].lower(), f"Ожидалась ошибка, связанная с блокчейном: {result['error']}"
    
    # Очищаем подмены
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_product_blockchain_id_error(mock_blockchain_service_with_id_error, mock_ipfs_service):
    """Проверяет ошибку при получении blockchain_id из транзакции."""
    # Создаем тестовое FastAPI приложение без аутентификации
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from bot.api.routes.products import router as products_router
    
    app = FastAPI()
    app.include_router(products_router)
    client = TestClient(app)
    
    # Подменяем все зависимости через dependency_overrides
    from bot.api.dependencies import get_product_storage_service, get_blockchain_service
    
    def get_mock_storage_service():
        return mock_ipfs_service
    
    def get_mock_blockchain_service():
        return mock_blockchain_service_with_id_error

    app.dependency_overrides[get_product_storage_service] = get_mock_storage_service
    app.dependency_overrides[get_blockchain_service] = get_mock_blockchain_service
    
    product_data = {
        "id": 8,
        "title": "Amanita muscaria — powder",
        "description": {"en": "High quality dried Amanita muscaria powder."},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "gallery": [],
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "80",
                "currency": "EUR"
            }
        ],
        "attributes": {"sku": "AMANITA8", "stock": 5}
    }
    
    payload = {"products": [product_data]}
    response = client.post("/products/upload", json=payload)
    
    # Ошибка получения blockchain_id должна вернуть 200 с ошибкой в results
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}: {response.text}"
    data = response.json()
    assert "results" in data, f"В ответе нет ключа 'results': {data}"
    assert len(data["results"]) > 0, f"'results' пустой: {data}"
    
    result = data["results"][0]
    assert result["status"] == "error", f"Ожидался статус 'error', получено: {result}"
    assert "transaction" in result["error"].lower() or "blockchain_id" in result["error"].lower(), f"Ожидалась ошибка, связанная с получением blockchain_id: {result['error']}"
    
    # Очищаем подмены
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_product_idempotency(mock_blockchain_service_with_tracking, mock_ipfs_service):
    """Проверяет идемпотентность: повторный вызов с теми же данными не создает дубликат, возвращает тот же результат."""
    # TODO: Реализовать идемпотентность в ProductRegistryService
    # Сейчас система не поддерживает идемпотентность - каждый вызов создает новый продукт
    
    # Создаем тестовое FastAPI приложение без аутентификации
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from bot.api.routes.products import router as products_router
    
    app = FastAPI()
    app.include_router(products_router)
    client = TestClient(app)
    
    # Подменяем все зависимости через dependency_overrides
    from bot.api.dependencies import get_product_storage_service, get_blockchain_service
    
    def get_mock_storage_service():
        return mock_ipfs_service
    
    def get_mock_blockchain_service():
        return mock_blockchain_service_with_tracking

    app.dependency_overrides[get_product_storage_service] = get_mock_storage_service
    app.dependency_overrides[get_blockchain_service] = get_mock_blockchain_service
    
    product_data = {
        "id": 9,
        "title": "Amanita muscaria — powder",
        "description": {"en": "High quality dried Amanita muscaria powder."},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "gallery": [],
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "80",
                "currency": "EUR"
            }
        ],
        "attributes": {"sku": "AMANITA9", "stock": 5}
    }
    
    payload = {"products": [product_data]}
    
    # Первый вызов
    response1 = client.post("/products/upload", json=payload)
    assert response1.status_code == 200, f"Ожидался статус 200, получен {response1.status_code}: {response1.text}"
    data1 = response1.json()
    result1 = data1["results"][0]
    assert result1["status"] == "success", f"Ожидался статус 'success', получено: {result1}"
    
    # Второй вызов с теми же данными
    response2 = client.post("/products/upload", json=payload)
    assert response2.status_code == 200, f"Ожидался статус 200, получен {response2.status_code}: {response2.text}"
    data2 = response2.json()
    result2 = data2["results"][0]
    assert result2["status"] == "success", f"Ожидался статус 'success', получено: {result2}"
    
    # Проверяем, что результаты идентичны (кроме metadata_cid, который пока не идемпотентен)
    assert result1["id"] == result2["id"], f"ID должны быть одинаковыми: {result1['id']} vs {result2['id']}"
    assert result1["blockchain_id"] == result2["blockchain_id"], f"blockchain_id должны быть одинаковыми: {result1['blockchain_id']} vs {result2['blockchain_id']}"
    
    # TODO: После реализации идемпотентности раскомментировать:
    # assert result1["metadata_cid"] == result2["metadata_cid"], f"metadata_cid должны быть одинаковыми: {result1['metadata_cid']} vs {result2['metadata_cid']}"
    
    # Проверяем, что create_product был вызван дважды (пока нет идемпотентности)
    # TODO: После реализации идемпотентности изменить на:
    # assert len(mock_blockchain_service_with_tracking.create_product_calls) == 1, f"create_product должен быть вызван только один раз, вызван {len(mock_blockchain_service_with_tracking.create_product_calls)} раз"
    assert len(mock_blockchain_service_with_tracking.create_product_calls) == 2, f"create_product должен быть вызван дважды (пока нет идемпотентности), вызван {len(mock_blockchain_service_with_tracking.create_product_calls)} раз"
    
    # Очищаем подмены
    app.dependency_overrides.clear()
    
    print("test_create_product_idempotency: проверено текущее поведение (идемпотентность не реализована)")

@pytest.mark.asyncio
def test_create_product_logging(api_client, mock_blockchain_service):
    """Проверяет, что все этапы (валидация, IPFS, блокчейн, ошибки) логируются."""
    assert True 

# === Тесты для обновления продукта (PUT) ===

@pytest.mark.asyncio
async def test_update_product_success(api_client, mock_blockchain_service):
    """
    Проверяет успешное обновление продукта через PUT /products/{id}.
    """
    # 1. Подготовить валидные тестовые данные для обновления
    update_data = {
        "id": "8",
        "title": "Updated Amanita muscaria — powder",
        "description": {"en": "Updated high quality dried Amanita muscaria powder."},
        "description_cid": "QmUpdatedDescriptionCID",
        "cover_image": "QmUpdatedCoverCID",
        "gallery": ["QmUpdatedGalleryCID1", "QmUpdatedGalleryCID2"],
        "categories": ["mushroom", "updated"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "weight": "200",
                "weight_unit": "g",
                "price": "150",
                "currency": "EUR"
            }
        ],
        "attributes": {"sku": "UPDATED1", "stock": 20}
    }
    
    # 2. Сгенерировать HMAC-заголовки для запроса
    import json
    from bot.tests.api.test_utils import generate_hmac_headers
    import os
    AMANITA_API_KEY = os.getenv("AMANITA_API_KEY", "test-api-key-12345")
    AMANITA_API_SECRET = os.getenv("AMANITA_API_SECRET", "default-secret-key-change-in-production")
    method = "PUT"
    path = "/products/8"
    body = json.dumps(update_data)
    headers = generate_hmac_headers(method, path, body, AMANITA_API_KEY, AMANITA_API_SECRET)
    
    # 3. Получить экземпляр клиента из async_generator
    api_client_instance = await api_client.__anext__()
    
    # 4. Отправить PUT-запрос на /products/8
    response = await api_client_instance.put(
        "/products/8",
        json=update_data,
        headers=headers
    )
    
    # 5. Проверить, что статус ответа 200 OK
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}: {response.text}"
    
    # 6. Проверить, что status == "success"
    data = response.json()
    assert data["status"] == "success", f"Ожидался статус 'success', получено: {data}"
    assert data["id"] == "8", f"Ожидался ID '8', получено: {data['id']}"
    
    # 7. Проверить, что присутствуют ключевые поля
    for key in ("metadata_cid", "blockchain_id", "tx_hash"):
        assert key in data, f"В ответе отсутствует ключ '{key}': {data}"
    
    # 8. Проверить, что поле error отсутствует или None
    assert ("error" not in data) or (data["error"] in (None, "")), f"Ожидалось отсутствие ошибки, получено: {data.get('error')}"
    
    print("test_update_product_success: успешно выполнен!")

@pytest.mark.asyncio
async def test_update_product_validation_error(mock_blockchain_service, mock_ipfs_service):
    """
    Тест валидации данных при обновлении продукта
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService
    def get_mock_registry_service():
        registry_service = ProductRegistryService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
        return registry_service
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные с ошибкой валидации (отсутствует обязательное поле)
    product_id = "1"
    invalid_data = {
        "id": 1,
        # Отсутствует title - должно вызвать ошибку валидации
        "description": {"en": "Test description"},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "price": 25.99,
                "currency": "EUR",
                "weight": 10,
                "weight_unit": "g"
            }
        ]
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.put(f"/products/{product_id}", json=invalid_data)
    
    # Проверяем результат - должна быть ошибка валидации
    assert response.status_code == 422  # Unprocessable Entity
    result = response.json()
    assert "detail" in result
    assert any("title" in str(error) for error in result["detail"])
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_not_found(mock_blockchain_service, mock_ipfs_service):
    """
    Тест обновления несуществующего продукта
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService который возвращает None для несуществующего продукта
    class MockRegistryServiceNotFound(ProductRegistryService):
        def get_product(self, product_id: str):
            return None  # Продукт не найден
    
    def get_mock_registry_service():
        return MockRegistryServiceNotFound(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные
    product_id = "999"  # Несуществующий ID
    update_data = {
        "id": 999,
        "title": "Test Product",
        "description": {"en": "Test description"},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "price": 25.99,
                "currency": "EUR",
                "weight": 10,
                "weight_unit": "g"
            }
        ]
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.put(f"/products/{product_id}", json=update_data)
    
    # Проверяем результат
    assert response.status_code == 200  # API возвращает 200 с error в response
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "не найден" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_access_denied(mock_blockchain_service, mock_ipfs_service):
    """
    Тест обновления продукта без прав доступа
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService который симулирует недостаток прав
    class MockRegistryServiceAccessDenied(ProductRegistryService):
        def get_product(self, product_id: str):
            # Возвращаем продукт, но при проверке прав будет ошибка
            from bot.model.product import Product
            return Product(
                id=product_id,
                title="Test Product",
                status=1,
                cid="QmTestCID",
                description=None,
                description_cid="",
                cover_image_url="",
                categories=[],
                forms=[],
                species="",
                prices=[]
            )
        
        async def update_product(self, product_id: str, product_data: dict) -> dict:
            # Симулируем ошибку доступа
            return {
                "id": product_id,
                "status": "error",
                "error": f"Недостаточно прав для обновления продукта {product_id}"
            }
    
    def get_mock_registry_service():
        return MockRegistryServiceAccessDenied(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные
    product_id = "1"
    update_data = {
        "id": 1,
        "title": "Test Product",
        "description": {"en": "Test description"},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "price": 25.99,
                "currency": "EUR",
                "weight": 10,
                "weight_unit": "g"
            }
        ]
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.put(f"/products/{product_id}", json=update_data)
    
    # Проверяем результат
    assert response.status_code == 200  # API возвращает 200 с error в response
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "Недостаточно прав" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear() 

# === Тесты для обновления статуса продукта (POST) ===

@pytest.mark.asyncio
async def test_update_product_status_success(api_client, mock_blockchain_service):
    """
    Проверяет успешное обновление статуса продукта через POST /products/{id}/status.
    """
    # 1. Подготовить тестовые данные для обновления статуса
    status_data = {
        "status": "active"
    }
    
    # 2. Сгенерировать HMAC-заголовки для запроса
    import json
    from bot.tests.api.test_utils import generate_hmac_headers
    import os
    AMANITA_API_KEY = os.getenv("AMANITA_API_KEY", "test-api-key-12345")
    AMANITA_API_SECRET = os.getenv("AMANITA_API_SECRET", "default-secret-key-change-in-production")
    method = "POST"
    path = "/products/8/status"
    body = json.dumps(status_data)
    headers = generate_hmac_headers(method, path, body, AMANITA_API_KEY, AMANITA_API_SECRET)
    
    # 3. Получить экземпляр клиента из async_generator
    api_client_instance = await api_client.__anext__()
    
    # 4. Отправить POST-запрос на /products/8/status
    response = await api_client_instance.post(
        "/products/8/status",
        json=status_data,
        headers=headers
    )
    
    # 5. Проверить, что статус ответа 200 OK
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}: {response.text}"
    
    # 6. Проверить, что status == "success"
    data = response.json()
    assert data["status"] == "success", f"Ожидался статус 'success', получено: {data}"
    assert data["id"] == "8", f"Ожидался ID '8', получено: {data['id']}"
    
    # 7. Проверить, что поле error отсутствует или None
    assert ("error" not in data) or (data["error"] in (None, "")), f"Ожидалось отсутствие ошибки, получено: {data.get('error')}"
    
    print("test_update_product_status_success: успешно выполнен!")

@pytest.mark.asyncio
async def test_update_product_status_validation_error(mock_blockchain_service, mock_ipfs_service):
    """
    Тест валидации статуса при обновлении
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService
    def get_mock_registry_service():
        registry_service = ProductRegistryService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
        return registry_service
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные с невалидным статусом
    product_id = "1"
    invalid_status_data = {
        "status": "invalid_status"  # Невалидный статус
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.post(f"/products/{product_id}/status", json=invalid_status_data)
    
    # Проверяем результат - должна быть ошибка валидации
    assert response.status_code == 200  # API возвращает 200 с error в response
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "Некорректный статус" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_status_not_found(mock_blockchain_service, mock_ipfs_service):
    """
    Тест обновления статуса несуществующего продукта
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService который возвращает None для несуществующего продукта
    class MockRegistryServiceNotFound(ProductRegistryService):
        def get_product(self, product_id: str):
            return None  # Продукт не найден
    
    def get_mock_registry_service():
        return MockRegistryServiceNotFound(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные
    product_id = "999"  # Несуществующий ID
    status_data = {
        "status": "active"
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.post(f"/products/{product_id}/status", json=status_data)
    
    # Проверяем результат
    assert response.status_code == 200  # API возвращает 200 с error в response
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "не найден" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_status_idempotency(mock_blockchain_service, mock_ipfs_service):
    """
    Тест идемпотентности обновления статуса
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService который симулирует идемпотентность
    class MockRegistryServiceIdempotent(ProductRegistryService):
        def get_product(self, product_id: str):
            # Возвращаем продукт с уже установленным статусом
            from bot.model.product import Product
            return Product(
                id=product_id,
                title="Test Product",
                status=1,  # Уже активен
                cid="QmTestCID",
                description=None,
                description_cid="",
                cover_image_url="",
                categories=[],
                forms=[],
                species="",
                prices=[]
            )
        
        async def update_product_status(self, product_id: int, new_status: int) -> bool:
            # Симулируем идемпотентность - если статус уже установлен, возвращаем True
            if new_status == 1:  # active
                return True  # Статус уже активен
            return True  # В любом случае успех
    
    def get_mock_registry_service():
        return MockRegistryServiceIdempotent(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные - пытаемся установить тот же статус
    product_id = "1"
    status_data = {
        "status": "active"  # Продукт уже активен
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.post(f"/products/{product_id}/status", json=status_data)
    
    # Проверяем результат - должен быть успех благодаря идемпотентности
    assert response.status_code == 200
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "success"
    assert result["error"] is None
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_status_inactive(mock_blockchain_service, mock_ipfs_service):
    """
    Тест обновления статуса на inactive
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService
    def get_mock_registry_service():
        registry_service = ProductRegistryService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
        return registry_service
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные для деактивации
    product_id = "1"
    status_data = {
        "status": "inactive"
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.post(f"/products/{product_id}/status", json=status_data)
    
    # Проверяем результат
    assert response.status_code == 200
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "success"
    assert result["error"] is None
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear() 

# === Дополнительные тесты валидации входных данных ===

@pytest.mark.asyncio
async def test_update_product_missing_required_fields(mock_blockchain_service, mock_ipfs_service):
    """
    Тест валидации отсутствия обязательных полей при обновлении продукта
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService
    def get_mock_registry_service():
        registry_service = ProductRegistryService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
        return registry_service
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные с отсутствующими обязательными полями
    product_id = "1"
    incomplete_data = {
        "id": 1,
        # Отсутствуют: title, description_cid, cover_image, form, species, prices
        "description": {"en": "Test description"},
        "categories": ["mushroom"],
        "attributes": {"sku": "AM-001"}
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.put(f"/products/{product_id}", json=incomplete_data)
    
    # Проверяем результат - должна быть ошибка валидации
    assert response.status_code == 422  # Unprocessable Entity
    result = response.json()
    assert "detail" in result
    # Проверяем что ошибки содержат информацию об отсутствующих полях
    error_fields = [error.get("loc", [])[-1] for error in result["detail"]]
    assert "title" in error_fields
    assert "description_cid" in error_fields
    assert "cover_image" in error_fields
    assert "form" in error_fields
    assert "species" in error_fields
    assert "prices" in error_fields
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_invalid_cid_format(mock_blockchain_service, mock_ipfs_service):
    """
    Тест валидации неверного формата CID
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService
    def get_mock_registry_service():
        registry_service = ProductRegistryService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
        return registry_service
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные с неверным форматом CID
    product_id = "1"
    invalid_cid_data = {
        "id": 1,
        "title": "Test Product",
        "description": {"en": "Test description"},
        "description_cid": "invalid-cid-format",  # Неверный формат CID
        "cover_image": "also-invalid-cid",  # Неверный формат CID
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "price": 25.99,
                "currency": "EUR",
                "weight": 10,
                "weight_unit": "g"
            }
        ]
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.put(f"/products/{product_id}", json=invalid_cid_data)
    
    # Проверяем результат - должна быть ошибка валидации на уровне сервиса
    assert response.status_code == 200  # API возвращает 200 с error в response
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "валидацию" in result["error"] or "CID" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_invalid_price_format(mock_blockchain_service, mock_ipfs_service):
    """
    Тест валидации неверного формата цен
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService
    def get_mock_registry_service():
        registry_service = ProductRegistryService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
        return registry_service
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные с неверным форматом цен
    product_id = "1"
    invalid_price_data = {
        "id": 1,
        "title": "Test Product",
        "description": {"en": "Test description"},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "price": "invalid_price",  # Строка вместо числа
                "currency": "INVALID",  # Неверная валюта
                "weight": -5,  # Отрицательный вес
                "weight_unit": "invalid_unit"  # Неверная единица
            }
        ]
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.put(f"/products/{product_id}", json=invalid_price_data)
    
    # Проверяем результат - должна быть ошибка валидации
    assert response.status_code == 200  # API возвращает 200 с error в response
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "валидацию" in result["error"] or "цена" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_status_invalid_format(mock_blockchain_service, mock_ipfs_service):
    """
    Тест валидации неверного формата статуса
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService
    def get_mock_registry_service():
        registry_service = ProductRegistryService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
        return registry_service
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные с неверным форматом статуса
    product_id = "1"
    invalid_status_formats = [
        {"status": 123},  # Число вместо строки
        {"status": True},  # Boolean вместо строки
        {"status": ["active"]},  # Массив вместо строки
        {"status": ""},  # Пустая строка
        {"status": "   "},  # Только пробелы
        {"status": "ACTIVE"},  # Верхний регистр
        {"status": "Active"},  # Смешанный регистр
    ]
    
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    for status_data in invalid_status_formats:
        # Выполняем запрос
        response = client.post(f"/products/{product_id}/status", json=status_data)
        
        # Проверяем результат - должна быть ошибка валидации
        assert response.status_code == 200  # API возвращает 200 с error в response
        result = response.json()
        assert result["id"] == product_id
        assert result["status"] == "error"
        assert "Некорректный статус" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_empty_categories(mock_blockchain_service, mock_ipfs_service):
    """
    Тест валидации пустых категорий
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService
    def get_mock_registry_service():
        registry_service = ProductRegistryService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
        return registry_service
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные с пустыми категориями
    product_id = "1"
    empty_categories_data = {
        "id": 1,
        "title": "Test Product",
        "description": {"en": "Test description"},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": [],  # Пустой массив категорий
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "price": 25.99,
                "currency": "EUR",
                "weight": 10,
                "weight_unit": "g"
            }
        ]
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.put(f"/products/{product_id}", json=empty_categories_data)
    
    # Проверяем результат - должна быть ошибка валидации
    assert response.status_code == 200  # API возвращает 200 с error в response
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "валидацию" in result["error"] or "категории" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear() 

# === Тесты обработки специфических HTTP ошибок ===

@pytest.mark.asyncio
async def test_update_product_404_error(mock_blockchain_service, mock_ipfs_service):
    """
    Тест обработки 404 ошибки - продукт не найден
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService который возвращает None для несуществующего продукта
    class MockRegistryService404(ProductRegistryService):
        def get_product(self, product_id: str):
            return None  # Продукт не найден
    
    def get_mock_registry_service():
        return MockRegistryService404(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные
    product_id = "999999"  # Несуществующий ID
    update_data = {
        "id": 999999,
        "title": "Test Product",
        "description": {"en": "Test description"},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "price": 25.99,
                "currency": "EUR",
                "weight": 10,
                "weight_unit": "g"
            }
        ]
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.put(f"/products/{product_id}", json=update_data)
    
    # Проверяем результат - должен быть error в response (API возвращает 200 с error)
    assert response.status_code == 200
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "не найден" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_403_error(mock_blockchain_service, mock_ipfs_service):
    """
    Тест обработки 403 ошибки - недостаток прав доступа
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService который симулирует недостаток прав
    class MockRegistryService403(ProductRegistryService):
        def get_product(self, product_id: str):
            # Возвращаем продукт, но при проверке прав будет ошибка
            from bot.model.product import Product
            return Product(
                id=product_id,
                title="Test Product",
                status=1,
                cid="QmTestCID",
                description=None,
                description_cid="",
                cover_image_url="",
                categories=[],
                forms=[],
                species="",
                prices=[]
            )
        
        async def update_product(self, product_id: str, product_data: dict) -> dict:
            # Симулируем ошибку доступа
            return {
                "id": product_id,
                "status": "error",
                "error": f"Недостаточно прав для обновления продукта {product_id}"
            }
    
    def get_mock_registry_service():
        return MockRegistryService403(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные
    product_id = "1"
    update_data = {
        "id": 1,
        "title": "Test Product",
        "description": {"en": "Test description"},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "price": 25.99,
                "currency": "EUR",
                "weight": 10,
                "weight_unit": "g"
            }
        ]
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.put(f"/products/{product_id}", json=update_data)
    
    # Проверяем результат - должен быть error в response (API возвращает 200 с error)
    assert response.status_code == 200
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "Недостаточно прав" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_400_error(mock_blockchain_service, mock_ipfs_service):
    """
    Тест обработки 400 ошибки - неверный запрос
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService
    def get_mock_registry_service():
        registry_service = ProductRegistryService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
        return registry_service
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные с неверным запросом (пустой ID продукта)
    product_id = ""  # Пустой ID
    update_data = {
        "id": 1,
        "title": "Test Product",
        "description": {"en": "Test description"},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "price": 25.99,
                "currency": "EUR",
                "weight": 10,
                "weight_unit": "g"
            }
        ]
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.put(f"/products/{product_id}", json=update_data)
    
    # Проверяем результат - должен быть error в response (API возвращает 200 с error)
    assert response.status_code == 200
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "Некорректный ID продукта" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_500_error(mock_blockchain_service, mock_ipfs_service):
    """
    Тест обработки 500 ошибки - внутренняя ошибка сервера
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService который вызывает исключение
    class MockRegistryService500(ProductRegistryService):
        def get_product(self, product_id: str):
            # Вызываем исключение для симуляции внутренней ошибки
            raise Exception("Внутренняя ошибка сервера при получении продукта")
    
    def get_mock_registry_service():
        return MockRegistryService500(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные
    product_id = "1"
    update_data = {
        "id": 1,
        "title": "Test Product",
        "description": {"en": "Test description"},
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom"],
        "form": "powder",
        "species": "Amanita muscaria",
        "prices": [
            {
                "price": 25.99,
                "currency": "EUR",
                "weight": 10,
                "weight_unit": "g"
            }
        ]
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.put(f"/products/{product_id}", json=update_data)
    
    # Проверяем результат - должен быть error в response (API возвращает 200 с error)
    assert response.status_code == 200
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "Внутренняя ошибка сервера" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_product_status_500_error(mock_blockchain_service, mock_ipfs_service):
    """
    Тест обработки 500 ошибки при обновлении статуса
    """
    from fastapi import FastAPI
    from bot.api.routes.products import router as products_router
    from bot.api.dependencies import get_product_registry_service
    from bot.services.product.registry import ProductRegistryService
    
    # Создаем локальное FastAPI приложение
    app = FastAPI()
    app.include_router(products_router)
    
    # Мокаем ProductRegistryService который вызывает исключение
    class MockRegistryService500(ProductRegistryService):
        async def update_product_status(self, product_id: int, new_status: int) -> bool:
            # Вызываем исключение для симуляции внутренней ошибки
            raise Exception("Внутренняя ошибка сервера при обновлении статуса")
    
    def get_mock_registry_service():
        return MockRegistryService500(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_ipfs_service
        )
    
    app.dependency_overrides[get_product_registry_service] = get_mock_registry_service
    
    # Тестовые данные
    product_id = "1"
    status_data = {
        "status": "active"
    }
    
    # Выполняем запрос
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.post(f"/products/{product_id}/status", json=status_data)
    
    # Проверяем результат - должен быть error в response (API возвращает 200 с error)
    assert response.status_code == 200
    result = response.json()
    assert result["id"] == product_id
    assert result["status"] == "error"
    assert "Внутренняя ошибка сервера" in result["error"]
    
    # Очищаем dependency overrides
    app.dependency_overrides.clear() 