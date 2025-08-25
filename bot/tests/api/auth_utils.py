"""
Утилиты для HMAC аутентификации в API тестах
"""
import hmac
import hashlib
import time
import secrets
from typing import Dict


def generate_auth_headers(
    method: str,
    path: str,
    body: str = "",
    api_key: str = None,
    secret_key: str = None
) -> Dict[str, str]:
    """
    Генерирует заголовки аутентификации для API запросов
    
    Args:
        method: HTTP метод (GET, POST, PUT, DELETE)
        path: Путь запроса (например, /products/0x123...)
        body: Тело запроса (пустая строка для GET)
        api_key: API ключ (если None, берется из переменных окружения)
        secret_key: Секретный ключ (если None, берется из переменных окружения)
    
    Returns:
        Словарь с заголовками аутентификации
    """
    import os
    
    # Получаем ключи из переменных окружения если не переданы
    if api_key is None:
        api_key = os.getenv("AMANITA_API_KEY")
    if secret_key is None:
        secret_key = os.getenv("AMANITA_API_SECRET")
    
    if not api_key or not secret_key:
        raise ValueError("API ключ и секретный ключ должны быть установлены")
    
    # Генерируем timestamp и nonce
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    
    # Создаем сообщение для подписи
    message = f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}"
    
    # Создаем HMAC подпись
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Возвращаем заголовки
    return {
        "X-API-Key": api_key,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
        "Content-Type": "application/json"
    }


def add_auth_headers_to_client(client, method: str, path: str, body: str = ""):
    """
    Добавляет заголовки аутентификации к HTTP клиенту
    
    Args:
        client: httpx.AsyncClient
        method: HTTP метод
        path: Путь запроса
        body: Тело запроса
    """
    auth_headers = generate_auth_headers(method, path, body)
    client.headers.update(auth_headers)
