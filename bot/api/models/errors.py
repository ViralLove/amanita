"""
Модели для обработки ошибок API
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from .common import RequestId, Timestamp


class ErrorDetail(BaseModel):
    """Детали ошибки"""
    
    field: Optional[str] = Field(None, description="Поле, в котором произошла ошибка")
    message: str = Field(..., description="Сообщение об ошибке")
    value: Optional[Any] = Field(None, description="Значение, которое вызвало ошибку")
    error_code: Optional[str] = Field(None, description="Код ошибки для программной обработки")
    suggestions: Optional[List[str]] = Field(None, description="Предложения по исправлению ошибки")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ErrorResponse(BaseModel):
    """Стандартная модель ответа с ошибкой"""
    success: bool = Field(False, description="Статус операции (всегда false для ошибок)")
    error: str = Field(..., description="Тип ошибки")
    message: str = Field(..., description="Человекочитаемое сообщение об ошибке")
    details: Optional[list[ErrorDetail]] = Field(None, description="Детали ошибки")
    request_id: Optional[RequestId] = Field(None, description="ID запроса")
    timestamp: Timestamp = Field(..., description="Временная метка ошибки")
    path: Optional[str] = Field(None, description="Путь запроса")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ValidationErrorResponse(ErrorResponse):
    """Ответ с ошибкой валидации"""
    error: str = Field("validation_error", description="Тип ошибки")
    message: str = Field("Ошибка валидации данных", description="Сообщение об ошибке")


class UnifiedValidationErrorResponse(ErrorResponse):
    """Ответ с унифицированной ошибкой валидации"""
    error: str = Field("unified_validation_error", description="Тип ошибки")
    message: str = Field("Ошибка валидации данных", description="Сообщение об ошибке")
    validation_source: Optional[str] = Field(None, description="Источник валидации (api, service, core)")


class AuthenticationErrorResponse(ErrorResponse):
    """Ответ с ошибкой аутентификации"""
    error: str = Field("authentication_error", description="Тип ошибки")
    message: str = Field("Ошибка аутентификации", description="Сообщение об ошибке")


class AuthorizationErrorResponse(ErrorResponse):
    """Ответ с ошибкой авторизации"""
    error: str = Field("authorization_error", description="Тип ошибки")
    message: str = Field("Недостаточно прав для выполнения операции", description="Сообщение об ошибке")


class NotFoundErrorResponse(ErrorResponse):
    """Ответ с ошибкой 'не найдено'"""
    error: str = Field("not_found", description="Тип ошибки")
    message: str = Field("Запрашиваемый ресурс не найден", description="Сообщение об ошибке")


class InternalServerErrorResponse(ErrorResponse):
    """Ответ с внутренней ошибкой сервера"""
    error: str = Field("internal_server_error", description="Тип ошибки")
    message: str = Field("Внутренняя ошибка сервера", description="Сообщение об ошибке")


class RateLimitErrorResponse(ErrorResponse):
    """Ответ с ошибкой превышения лимита запросов"""
    error: str = Field("rate_limit_exceeded", description="Тип ошибки")
    message: str = Field("Превышен лимит запросов", description="Сообщение об ошибке")
    retry_after: Optional[int] = Field(None, description="Время ожидания до следующего запроса в секундах")


class ConflictErrorResponse(ErrorResponse):
    """Модель для ошибок конфликта (409)"""
    
    error: str = Field(default="conflict", description="Тип ошибки")
    status_code: int = Field(default=409, description="HTTP статус код")
    
    @classmethod
    def resource_exists(cls, resource_type: str, resource_id: str, request_id: Optional[str] = None):
        """Ошибка ресурс уже существует"""
        return cls(
            message=f"{resource_type} already exists: {resource_id}",
            request_id=request_id
        )
    
    @classmethod
    def duplicate_request(cls, nonce: str, request_id: Optional[str] = None):
        """Ошибка дублирования запроса"""
        return cls(
            message=f"Duplicate request detected. Nonce already used: {nonce}",
            request_id=request_id
        )


class RateLimitErrorResponse(ErrorResponse):
    """Модель для ошибок rate limiting (429)"""
    
    error: str = Field(default="rate_limit_exceeded", description="Тип ошибки")
    status_code: int = Field(default=429, description="HTTP статус код")
    
    retry_after: Optional[int] = Field(None, description="Время в секундах до следующего запроса")
    
    @classmethod
    def rate_limit_exceeded(cls, retry_after: Optional[int] = None, request_id: Optional[str] = None):
        """Ошибка превышения лимита запросов"""
        return cls(
            message="Rate limit exceeded",
            retry_after=retry_after,
            request_id=request_id
        )


class InternalServerErrorResponse(ErrorResponse):
    """Модель для внутренних ошибок сервера (500)"""
    
    error: str = Field(default="internal_server_error", description="Тип ошибки")
    status_code: int = Field(default=500, description="HTTP статус код")
    
    # Для production не показываем детали ошибки
    show_details: bool = Field(default=False, description="Показывать ли детали ошибки")
    
    @classmethod
    def internal_error(cls, message: str = "Internal server error", 
                      details: Optional[List[ErrorDetail]] = None,
                      show_details: bool = False,
                      request_id: Optional[str] = None):
        """Внутренняя ошибка сервера"""
        return cls(
            message=message,
            details=details if show_details else None,
            show_details=show_details,
            request_id=request_id
        )


class ServiceUnavailableErrorResponse(ErrorResponse):
    """Модель для ошибок недоступности сервиса (503)"""
    
    error: str = Field(default="service_unavailable", description="Тип ошибки")
    status_code: int = Field(default=503, description="HTTP статус код")
    
    @classmethod
    def service_unavailable(cls, service_name: str, request_id: Optional[str] = None):
        """Ошибка недоступности сервиса"""
        return cls(
            message=f"Service unavailable: {service_name}",
            request_id=request_id
        )


class BlockchainErrorResponse(ErrorResponse):
    """Модель для ошибок блокчейна"""
    
    error: str = Field(default="blockchain_error", description="Тип ошибки")
    status_code: int = Field(default=502, description="HTTP статус код")
    
    tx_hash: Optional[str] = Field(None, description="Hash транзакции (если есть)")
    
    @classmethod
    def transaction_failed(cls, tx_hash: Optional[str] = None, 
                          message: str = "Blockchain transaction failed",
                          request_id: Optional[str] = None):
        """Ошибка неудачной транзакции"""
        return cls(
            message=message,
            tx_hash=tx_hash,
            request_id=request_id
        )
    
    @classmethod
    def network_error(cls, message: str = "Blockchain network error", request_id: Optional[str] = None):
        """Ошибка сети блокчейна"""
        return cls(
            message=message,
            request_id=request_id
        )


# Словарь для быстрого доступа к классам ошибок по HTTP кодам
ERROR_RESPONSES = {
    400: ValidationErrorResponse,
    401: AuthenticationErrorResponse,
    403: AuthorizationErrorResponse,
    404: NotFoundErrorResponse,
    409: ConflictErrorResponse,
    429: RateLimitErrorResponse,
    500: InternalServerErrorResponse,
    502: BlockchainErrorResponse,
    503: ServiceUnavailableErrorResponse,
    422: ValidationErrorResponse,
} 