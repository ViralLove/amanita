"""
Базовые модели для API запросов и ответов
"""
from datetime import datetime
from typing import Optional, Generic, TypeVar, Any, Dict, List
from pydantic import BaseModel, Field, ConfigDict
from pydantic import BaseModel

from .common import Timestamp, Nonce, RequestId, PaginationParams


class BaseRequest(BaseModel):
    """Базовая модель для всех запросов"""
    request_id: Optional[RequestId] = Field(None, description="Уникальный ID запроса")
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )


class BaseResponse(BaseModel):
    """Базовая модель для всех ответов"""
    success: bool = Field(..., description="Статус операции")
    request_id: Optional[RequestId] = Field(None, description="ID запроса")
    timestamp: Timestamp = Field(..., description="Временная метка ответа")
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )


# Generic типы для типизированных ответов
T = TypeVar('T')


class DataResponse(BaseResponse, Generic[T]):
    """Базовая модель для ответов с данными"""
    data: T = Field(..., description="Данные ответа")


class PaginationInfo(BaseModel):
    """Информация о пагинации"""
    page: int = Field(..., ge=1, description="Номер страницы")
    per_page: int = Field(..., ge=1, le=100, description="Количество элементов на странице")
    total: int = Field(..., ge=0, description="Общее количество элементов")
    total_pages: int = Field(..., ge=0, description="Общее количество страниц")
    has_next: bool = Field(..., description="Есть ли следующая страница")
    has_prev: bool = Field(..., description="Есть ли предыдущая страница")


class PaginatedResponse(BaseResponse, Generic[T]):
    """Базовая модель для пагинированных ответов"""
    data: list[T] = Field(..., description="Список данных")
    pagination: PaginationInfo = Field(..., description="Информация о пагинации")


class MessageResponse(BaseResponse):
    """Модель для ответов с сообщением"""
    
    message: str = Field(..., description="Сообщение ответа")
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали")


class StatusResponse(BaseResponse):
    """Модель для ответов со статусом"""
    
    status: str = Field(..., description="Статус операции")
    message: Optional[str] = Field(None, description="Сообщение о статусе")
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали")


class EmptyResponse(BaseResponse):
    """Модель для пустых ответов (например, для DELETE операций)"""
    
    message: Optional[str] = Field(default="Operation completed successfully", description="Сообщение о завершении операции") 