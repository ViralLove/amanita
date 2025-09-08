"""
HMAC Middleware для аутентификации AMANITA API
"""
import hashlib
import hmac
import time
import logging
from typing import Dict, Set, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..exceptions.auth import (
    AuthenticationError,
    InvalidSignatureError,
    ExpiredTimestampError,
    InvalidTimestampError,
    DuplicateNonceError,
    MissingHeaderError,
    InvalidAPIKeyError
)
from ..config import APIConfig
from services.core.api_key import ApiKeyService

logger = logging.getLogger("amanita_api.auth")


class HMACMiddleware(BaseHTTPMiddleware):
    """
    Middleware для HMAC аутентификации запросов
    
    Проверяет:
    - HMAC-SHA256 подпись запроса
    - Валидность timestamp (защита от replay атак)
    - Уникальность nonce (дополнительная защита от replay атак)
    - Валидность API ключа
    """
    
    def __init__(self, app, config: Optional[Dict] = None, api_key_service: Optional[ApiKeyService] = None):
        super().__init__(app)
        self.config = config or APIConfig.get_hmac_config()
        self.timestamp_window = self.config["timestamp_window"]
        self.nonce_cache_ttl = self.config["nonce_cache_ttl"]
        
        # ApiKeyService для валидации ключей
        self.api_key_service = api_key_service
        
        # Кэш использованных nonce (в production должен быть Redis)
        self.used_nonces: Set[str] = set()
        self.nonce_timestamps: Dict[str, float] = {}
        
        # Очистка старых nonce каждые 5 минут
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 минут
        
        logger.info("HMAC Middleware инициализирован", extra={
            "timestamp_window": self.timestamp_window,
            "nonce_cache_ttl": self.nonce_cache_ttl,
            "api_key_service_available": api_key_service is not None
        })
    
    async def dispatch(self, request: Request, call_next):
        """
        Обработка запроса с HMAC аутентификацией
        """
        start_time = time.time()
        
        # Пропускаем аутентификацию для определенных путей
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        # Проверяем наличие заголовков аутентификации
        if not self._has_auth_headers(request):
            # Для защищённых путей возвращаем 401 при отсутствии заголовков
            # Но сначала проверяем, существует ли путь (позволяет FastAPI вернуть 404)
            try:
                # Пробуем обработать запрос, чтобы проверить, существует ли путь
                response = await call_next(request)
                # Если путь существует, но нет заголовков - возвращаем 401
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "error": "authentication_error",
                        "message": "Ошибка аутентификации",
                        "details": [{"field": "auth", "message": "Missing authentication headers"}],
                        "timestamp": int(time.time()),
                        "path": request.url.path
                    }
                )
            except Exception:
                # Если путь не существует, пропускаем для получения 404
                return await call_next(request)
        
        try:
            # Извлекаем заголовки аутентификации
            auth_headers = self._extract_auth_headers(request)
            
            # Валидируем timestamp
            self._validate_timestamp(auth_headers["timestamp"])
            
            # Валидируем nonce
            self._validate_nonce(auth_headers["nonce"])
            
            # Валидируем API ключ и получаем секретный ключ
            secret_key = await self._validate_api_key(auth_headers["api_key"])
            
            # Валидируем HMAC подпись
            await self._validate_signature(request, auth_headers, secret_key)
            
            # Добавляем контекст продавца в request state
            request.state.seller_address = auth_headers["api_key"]  # Пока используем API ключ как адрес
            
            # Очищаем старые nonce если нужно
            self._cleanup_old_nonces()
            
            # Логируем успешную аутентификацию
            processing_time = time.time() - start_time
            logger.info("HMAC аутентификация успешна", extra={
                "api_key": auth_headers["api_key"],
                "timestamp": auth_headers["timestamp"],
                "nonce": auth_headers["nonce"],
                "processing_time_ms": round(processing_time * 1000, 2),
                "path": request.url.path,
                "method": request.method
            })
            
            # Продолжаем обработку запроса
            response = await call_next(request)
            
            # Добавляем security headers
            self._add_security_headers(response)
            
            return response
            
        except AuthenticationError as e:
            # Логируем неудачную аутентификацию
            processing_time = time.time() - start_time
            logger.warning("HMAC аутентификация неудачна", extra={
                "error": str(e),
                "processing_time_ms": round(processing_time * 1000, 2),
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown"
            })
            
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "authentication_error",
                    "message": "Ошибка аутентификации",
                    "details": [{"field": "auth", "message": str(e)}],
                    "timestamp": int(time.time()),
                    "path": request.url.path
                }
            )
        
        except Exception as e:
            # Логируем неожиданные ошибки
            processing_time = time.time() - start_time
            logger.error("Неожиданная ошибка в HMAC middleware", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time_ms": round(processing_time * 1000, 2),
                "path": request.url.path,
                "method": request.method
            })
            
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "internal_server_error",
                    "message": "Внутренняя ошибка сервера",
                    "timestamp": int(time.time()),
                    "path": request.url.path
                }
            )
    
    def _should_skip_auth(self, path: str) -> bool:
        """Определяет, нужно ли пропустить аутентификацию для данного пути"""
        skip_paths = {
            "/",
            "/health",
            "/health/detailed",
            "/hello",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
        return path in skip_paths
    
    def _extract_auth_headers(self, request: Request) -> Dict[str, str]:
        """Извлекает заголовки аутентификации из запроса"""
        headers = request.headers
        
        # Проверяем наличие обязательных заголовков
        required_headers = {
            "X-API-Key": "api_key",
            "X-Timestamp": "timestamp",
            "X-Nonce": "nonce",
            "X-Signature": "signature"
        }
        
        auth_headers = {}
        for header_name, key in required_headers.items():
            value = headers.get(header_name)
            if not value:
                raise MissingHeaderError(header_name)
            auth_headers[key] = value
        
        return auth_headers
    
    def _validate_timestamp(self, timestamp_str: str):
        """Валидирует timestamp запроса"""
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            raise InvalidTimestampError("Timestamp must be a valid integer")
        
        current_time = int(time.time())
        time_diff = abs(current_time - timestamp)
        
        if time_diff > self.timestamp_window:
            raise ExpiredTimestampError(
                f"Request timestamp expired. Time difference: {time_diff}s, max allowed: {self.timestamp_window}s"
            )
    
    def _validate_nonce(self, nonce: str):
        """Валидирует уникальность nonce"""
        current_time = time.time()
        
        # Проверяем, не использовался ли nonce ранее
        if nonce in self.used_nonces:
            raise DuplicateNonceError(f"Nonce {nonce} already used")
        
        # Добавляем nonce в кэш
        self.used_nonces.add(nonce)
        self.nonce_timestamps[nonce] = current_time
    
    async def _validate_api_key(self, api_key: str) -> str:
        """Валидирует API ключ и возвращает секретный ключ"""
        if not self.api_key_service:
            # Fallback на базовую проверку если ApiKeyService недоступен
            if not api_key or len(api_key) < 10:
                raise InvalidAPIKeyError("API key is invalid or too short")
            # Возвращаем дефолтный секретный ключ для совместимости
            return self.config.get("secret_key", "default-secret-key-change-in-production")
        
        try:
            # Валидируем через ApiKeyService
            key_info = await self.api_key_service.validate_api_key(api_key)
            
            if not key_info.get("active", True):
                raise InvalidAPIKeyError("API key is inactive")
            
            # Добавляем информацию о селлере в request state
            return key_info["secret_key"]
            
        except Exception as e:
            logger.warning(f"Ошибка валидации API ключа {api_key}: {e}")
            raise InvalidAPIKeyError(f"Invalid API key: {api_key}")
    
    async def _validate_signature(self, request: Request, auth_headers: Dict[str, str], secret_key: str):
        """Валидирует HMAC подпись запроса"""
        # Получаем тело запроса
        body = await self._get_request_body(request)
        
        # Создаем строку для подписи
        message = self._create_signature_message(
            method=request.method,
            path=request.url.path,
            body=body,
            timestamp=auth_headers["timestamp"],
            nonce=auth_headers["nonce"]
        )
        
        # Вычисляем ожидаемую подпись
        secret_key_bytes = secret_key.encode('utf-8')
        expected_signature = hmac.new(
            secret_key_bytes,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Сравниваем с полученной подписью
        if not hmac.compare_digest(expected_signature, auth_headers["signature"]):
            raise InvalidSignatureError("HMAC signature validation failed")
    
    async def _get_request_body(self, request: Request) -> str:
        """Получает тело запроса как строку"""
        if request.method in ["GET", "HEAD", "DELETE"]:
            return ""
        
        # Читаем тело запроса
        body = await request.body()
        return body.decode('utf-8') if body else ""
    
    def _create_signature_message(self, method: str, path: str, body: str, timestamp: str, nonce: str) -> str:
        """
        Создает строку для HMAC подписи
        
        Формат: {method}\n{path}\n{body}\n{timestamp}\n{nonce}
        """
        return f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}"
    
    def _cleanup_old_nonces(self):
        """Очищает старые nonce из кэша"""
        current_time = time.time()
        
        # Очищаем каждые 5 минут
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        # Удаляем nonce старше TTL
        expired_nonces = [
            nonce for nonce, timestamp in self.nonce_timestamps.items()
            if current_time - timestamp > self.nonce_cache_ttl
        ]
        
        for nonce in expired_nonces:
            self.used_nonces.discard(nonce)
            del self.nonce_timestamps[nonce]
        
        if expired_nonces:
            logger.debug(f"Очищено {len(expired_nonces)} старых nonce")
        
        self.last_cleanup = current_time
    
    def _add_security_headers(self, response: Response):
        """Добавляет security headers к ответу"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Добавляем HSTS только для HTTPS
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains" 

    def _has_auth_headers(self, request: Request) -> bool:
        """Проверяет наличие заголовков аутентификации"""
        headers = request.headers
        required_headers = ["X-API-Key", "X-Timestamp", "X-Nonce", "X-Signature"]
        
        return all(headers.get(header) for header in required_headers) 