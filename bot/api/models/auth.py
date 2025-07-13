"""
Модели для аутентификации и авторизации API
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

from .common import EthereumAddress, ApiKey, Nonce, Timestamp, RequestId, Signature
from .base import BaseRequest, DataResponse, MessageResponse


class AuthRequest(BaseModel):
    """Базовая модель для аутентифицированных запросов"""
    api_key: ApiKey = Field(..., description="API ключ клиента")
    nonce: Nonce = Field(..., description="Уникальный nonce для предотвращения replay атак")
    timestamp: Timestamp = Field(..., description="Временная метка запроса")
    signature: Signature = Field(..., description="HMAC подпись запроса")
    request_id: Optional[RequestId] = Field(None, description="Уникальный ID запроса")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class AuthResponse(BaseModel):
    """Базовая модель для ответов с аутентификацией"""
    success: bool = Field(..., description="Статус операции")
    request_id: RequestId = Field(..., description="ID запроса")
    timestamp: Timestamp = Field(..., description="Временная метка ответа")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ApiKeyCreateRequest(BaseModel):
    """Запрос на создание нового API ключа"""
    client_address: EthereumAddress = Field(..., description="Ethereum адрес клиента")
    description: Optional[str] = Field(None, max_length=255, description="Описание ключа")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ApiKeyCreateResponse(AuthResponse):
    """Ответ на создание API ключа"""
    api_key: ApiKey = Field(..., description="Созданный API ключ")
    secret_key: str = Field(..., description="Секретный ключ для подписи (показывается только один раз)")


class ApiKeyValidateRequest(AuthRequest):
    """Запрос на валидацию API ключа"""
    pass


class ApiKeyValidateResponse(AuthResponse):
    """Ответ на валидацию API ключа"""
    is_valid: bool = Field(..., description="Валидность API ключа")
    client_address: Optional[EthereumAddress] = Field(None, description="Адрес клиента, если ключ валиден")


class ApiKeyRevokeRequest(AuthRequest):
    """Запрос на отзыв API ключа"""
    pass


class ApiKeyRevokeResponse(AuthResponse):
    """Ответ на отзыв API ключа"""
    revoked: bool = Field(..., description="Статус отзыва ключа")


class AuthTestRequest(BaseRequest):
    """Запрос для тестирования аутентификации"""
    
    # Пустая модель для тестирования HMAC middleware
    pass


class AuthTestData(BaseModel):
    """Данные тестирования аутентификации"""
    
    seller_address: EthereumAddress = Field(..., description="Ethereum адрес продавца")
    authenticated_at: datetime = Field(default_factory=datetime.now, description="Время аутентификации")
    permissions: List[str] = Field(default_factory=list, description="Доступные разрешения")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class AuthTestResponse(DataResponse[AuthTestData]):
    """Ответ тестирования аутентификации"""
    pass


class PermissionCheckRequest(BaseRequest):
    """Запрос на проверку разрешений"""
    
    required_permissions: List[str] = Field(..., description="Требуемые разрешения")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class PermissionCheckData(BaseModel):
    """Данные проверки разрешений"""
    
    has_permissions: bool = Field(..., description="Есть ли все требуемые разрешения")
    missing_permissions: List[str] = Field(default_factory=list, description="Отсутствующие разрешения")
    available_permissions: List[str] = Field(default_factory=list, description="Доступные разрешения")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class PermissionCheckResponse(DataResponse[PermissionCheckData]):
    """Ответ проверки разрешений"""
    pass 