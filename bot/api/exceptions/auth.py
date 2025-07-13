"""
Исключения для аутентификации AMANITA API
"""
from fastapi import HTTPException
from typing import Optional, Dict, Any


class AuthenticationError(HTTPException):
    """Базовое исключение для ошибок аутентификации"""
    
    def __init__(
        self,
        detail: str = "Authentication failed",
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status_code=401, detail=detail, headers=headers)


class InvalidSignatureError(AuthenticationError):
    """Ошибка неверной HMAC подписи"""
    
    def __init__(self, detail: str = "Invalid HMAC signature"):
        super().__init__(detail=detail)


class ExpiredTimestampError(AuthenticationError):
    """Ошибка истекшего timestamp"""
    
    def __init__(self, detail: str = "Request timestamp expired"):
        super().__init__(detail=detail)


class InvalidTimestampError(AuthenticationError):
    """Ошибка неверного timestamp"""
    
    def __init__(self, detail: str = "Invalid timestamp"):
        super().__init__(detail=detail)


class DuplicateNonceError(AuthenticationError):
    """Ошибка повторного использования nonce"""
    
    def __init__(self, detail: str = "Nonce already used"):
        super().__init__(detail=detail)


class MissingHeaderError(AuthenticationError):
    """Ошибка отсутствующего заголовка"""
    
    def __init__(self, header_name: str):
        super().__init__(detail=f"Missing required header: {header_name}")


class InvalidAPIKeyError(AuthenticationError):
    """Ошибка неверного API ключа"""
    
    def __init__(self, detail: str = "Invalid API key"):
        super().__init__(detail=detail) 