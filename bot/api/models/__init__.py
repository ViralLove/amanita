"""
Модели Pydantic для AMANITA API
"""

from .base import BaseRequest, BaseResponse, DataResponse, MessageResponse, PaginationInfo, PaginatedResponse
from .common import (
    EthereumAddress, ApiKey, Nonce, Timestamp, RequestId, Signature, HexString,
    generate_request_id, get_current_timestamp
)
from .auth import (
    AuthRequest, AuthResponse,
    ApiKeyCreateRequest, ApiKeyCreateResponse,
    ApiKeyValidateRequest, ApiKeyValidateResponse,
    ApiKeyRevokeRequest, ApiKeyRevokeResponse
)
from .errors import (
    ErrorDetail, ErrorResponse,
    ValidationErrorResponse, AuthenticationErrorResponse, AuthorizationErrorResponse,
    NotFoundErrorResponse, InternalServerErrorResponse, RateLimitErrorResponse
)
from .health import HealthStatus, ServiceInfo, HealthCheckResponse

__all__ = [
    # Base models
    "BaseRequest", "BaseResponse", "DataResponse", "MessageResponse", 
    "PaginationInfo", "PaginatedResponse",
    
    # Common types
    "EthereumAddress", "ApiKey", "Nonce", "Timestamp", "RequestId", 
    "Signature", "HexString", "generate_request_id", "get_current_timestamp",
    
    # Auth models
    "AuthRequest", "AuthResponse", "ApiKeyCreateRequest", "ApiKeyCreateResponse",
    "ApiKeyValidateRequest", "ApiKeyValidateResponse", "ApiKeyRevokeRequest", "ApiKeyRevokeResponse",
    
    # Error models
    "ErrorDetail", "ErrorResponse", "ValidationErrorResponse", "AuthenticationErrorResponse",
    "AuthorizationErrorResponse", "NotFoundErrorResponse", "InternalServerErrorResponse", "RateLimitErrorResponse",
    
    # Health models
    "HealthStatus", "ServiceInfo", "HealthCheckResponse"
]
