"""
Утилиты для API тестов
"""
import time
import uuid
import hmac
import hashlib
from typing import Dict, Any


def generate_hmac_headers(method: str, path: str, body: str, 
                         api_key: str, api_secret: str) -> Dict[str, str]:
    """
    Генерация HMAC заголовков для тестов
    
    Args:
        method: HTTP метод (GET, POST, etc.)
        path: Путь запроса
        body: Тело запроса
        api_key: API ключ
        api_secret: Секретный ключ
    
    Returns:
        Dict с заголовками аутентификации
    """
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


def assert_error_response(response, expected_status: int, expected_error: str):
    """
    Утилита для проверки ответов с ошибками
    
    Args:
        response: HTTP ответ
        expected_status: Ожидаемый статус код
        expected_error: Ожидаемый тип ошибки
    """
    assert response.status_code == expected_status, \
        f"Ожидался статус {expected_status}, получен {response.status_code}"
    
    data = response.json()
    assert data["success"] is False, "Поле success должно быть False"
    assert data["error"] == expected_error, \
        f"Ожидалась ошибка {expected_error}, получена {data.get('error')}"
    assert "message" in data, "Отсутствует поле message"
    assert "timestamp" in data, "Отсутствует поле timestamp"


def assert_success_response(response, expected_status: int = 200):
    """
    Утилита для проверки успешных ответов
    
    Args:
        response: HTTP ответ
        expected_status: Ожидаемый статус код
    """
    assert response.status_code == expected_status, \
        f"Ожидался статус {expected_status}, получен {response.status_code}"
    
    data = response.json()
    assert data["success"] is True, "Поле success должно быть True"
    assert "timestamp" in data, "Отсутствует поле timestamp"


def assert_health_response(response):
    """
    Утилита для проверки health check ответов
    
    Args:
        response: HTTP ответ
    """
    assert_success_response(response)
    data = response.json()
    
    # Проверяем обязательные поля health response
    assert "status" in data, "Отсутствует поле status"
    assert "service" in data, "Отсутствует поле service"
    assert "uptime" in data, "Отсутствует поле uptime"
    
    # Проверяем структуру status
    status = data["status"]
    assert "status" in status, "Отсутствует поле status.status"
    assert status["status"] in ["healthy", "degraded", "unhealthy"], \
        f"Невалидный статус: {status['status']}"


def assert_detailed_health_response(response):
    """
    Утилита для проверки детальных health check ответов
    
    Args:
        response: HTTP ответ
    """
    assert_health_response(response)
    data = response.json()
    
    # Проверяем дополнительные поля для detailed health
    assert "components" in data, "Отсутствует поле components"
    assert "system_metrics" in data, "Отсутствует поле system_metrics"
    
    # Проверяем структуру компонентов
    components = data["components"]
    assert isinstance(components, list), "components должен быть списком"
    
    for component in components:
        assert "name" in component, "Отсутствует поле name в компоненте"
        assert "status" in component, "Отсутствует поле status в компоненте"
        assert "latency" in component, "Отсутствует поле latency в компоненте"


def create_test_request_data(**kwargs) -> Dict[str, Any]:
    """
    Создание тестовых данных запроса
    
    Args:
        **kwargs: Дополнительные поля
    
    Returns:
        Dict с тестовыми данными
    """
    default_data = {
        "client_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
        "description": "Test API key"
    }
    default_data.update(kwargs)
    return default_data


def create_invalid_request_data() -> Dict[str, Any]:
    """
    Создание невалидных тестовых данных
    
    Returns:
        Dict с невалидными данными
    """
    return {
        "client_address": "invalid-address",
        "description": "x" * 300  # Слишком длинное описание
    }


def assert_ethereum_address_format(address: str):
    """
    Проверка формата Ethereum адреса
    
    Args:
        address: Адрес для проверки
    """
    import re
    pattern = r'^0x[a-fA-F0-9]{40}$'
    assert re.match(pattern, address), \
        f"Невалидный формат Ethereum адреса: {address}"


def assert_api_key_format(api_key: str):
    """
    Проверка формата API ключа
    
    Args:
        api_key: API ключ для проверки
    """
    import re
    pattern = r'^[a-fA-F0-9]{64}$'
    assert re.match(pattern, api_key), \
        f"Невалидный формат API ключа: {api_key}"


def assert_timestamp_format(timestamp: int):
    """
    Проверка формата timestamp
    
    Args:
        timestamp: Timestamp для проверки
    """
    current_time = int(time.time())
    # Timestamp должен быть положительным и не слишком старым/новым
    assert timestamp > 0, "Timestamp должен быть положительным"
    assert timestamp <= current_time + 3600, "Timestamp слишком новый"
    assert timestamp >= current_time - 3600, "Timestamp слишком старый"


def assert_request_id_format(request_id: str):
    """
    Проверка формата request ID
    
    Args:
        request_id: Request ID для проверки
    """
    import re
    pattern = r'^[a-zA-Z0-9\-_]{8,64}$'
    assert re.match(pattern, request_id), \
        f"Невалидный формат request ID: {request_id}" 