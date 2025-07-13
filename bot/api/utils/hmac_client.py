"""
Утилита для генерации HMAC подписей на стороне клиента
"""
import hashlib
import hmac
import time
import uuid
import requests
from typing import Dict, Optional


class HMACClient:
    """
    Клиент для работы с HMAC аутентификацией
    
    Используется для:
    - Генерации HMAC подписей для запросов
    - Отправки аутентифицированных запросов к API
    - Тестирования HMAC middleware
    """
    
    def __init__(self, api_key: str, secret_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.secret_key = secret_key.encode('utf-8')
        self.base_url = base_url.rstrip('/')
    
    def generate_auth_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """
        Генерирует заголовки аутентификации для запроса
        
        Args:
            method: HTTP метод (GET, POST, etc.)
            path: Путь запроса
            body: Тело запроса (для POST/PUT)
        
        Returns:
            Dict с заголовками аутентификации
        """
        timestamp = str(int(time.time()))
        nonce = str(uuid.uuid4())
        
        # Создаем строку для подписи
        message = f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}"
        
        # Вычисляем HMAC подпись
        signature = hmac.new(
            self.secret_key,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "X-API-Key": self.api_key,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature
        }
    
    def make_request(self, method: str, path: str, data: Optional[Dict] = None, 
                    headers: Optional[Dict] = None) -> requests.Response:
        """
        Отправляет аутентифицированный запрос к API
        
        Args:
            method: HTTP метод
            path: Путь запроса
            data: Данные для отправки (для POST/PUT)
            headers: Дополнительные заголовки
        
        Returns:
            Response объект
        """
        url = f"{self.base_url}{path}"
        body = ""
        
        if data:
            import json
            body = json.dumps(data)
        
        # Генерируем заголовки аутентификации
        auth_headers = self.generate_auth_headers(method, path, body)
        
        # Объединяем с дополнительными заголовками
        request_headers = {**auth_headers}
        if headers:
            request_headers.update(headers)
        
        # Отправляем запрос
        response = requests.request(
            method=method,
            url=url,
            headers=request_headers,
            data=body if method in ["POST", "PUT", "PATCH"] else None,
            json=data if method in ["POST", "PUT", "PATCH"] and not body else None
        )
        
        return response
    
    def get(self, path: str, headers: Optional[Dict] = None) -> requests.Response:
        """GET запрос"""
        return self.make_request("GET", path, headers=headers)
    
    def post(self, path: str, data: Optional[Dict] = None, 
             headers: Optional[Dict] = None) -> requests.Response:
        """POST запрос"""
        return self.make_request("POST", path, data=data, headers=headers)
    
    def put(self, path: str, data: Optional[Dict] = None, 
            headers: Optional[Dict] = None) -> requests.Response:
        """PUT запрос"""
        return self.make_request("PUT", path, data=data, headers=headers)
    
    def delete(self, path: str, headers: Optional[Dict] = None) -> requests.Response:
        """DELETE запрос"""
        return self.make_request("DELETE", path, headers=headers)


def create_test_client(api_key: str = "test-api-key-12345", 
                      secret_key: str = "default-secret-key-change-in-production",
                      base_url: str = "http://localhost:8000") -> HMACClient:
    """
    Создает тестовый HMAC клиент
    
    Args:
        api_key: API ключ для тестирования
        secret_key: Секретный ключ (должен совпадать с настройками сервера)
        base_url: Базовый URL API
    
    Returns:
        HMACClient для тестирования
    """
    return HMACClient(api_key, secret_key, base_url)


# Пример использования
if __name__ == "__main__":
    # Создаем тестовый клиент
    client = create_test_client()
    
    # Тестируем аутентифицированный запрос
    response = client.post("/auth-test", {"test": "data"})
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}") 