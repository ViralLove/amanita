"""
Глобальные обработчики ошибок для AMANITA API
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging

from bot.api.models.errors import (
    ValidationErrorResponse,
    AuthenticationErrorResponse,
    AuthorizationErrorResponse,
    NotFoundErrorResponse,
    InternalServerErrorResponse,
    RateLimitErrorResponse,
    ErrorDetail
)
from bot.api.models.common import get_current_timestamp, generate_request_id, Timestamp

logger = logging.getLogger("amanita.api.errors")

# 422: Pydantic validation error
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"422 Validation error: {exc.errors()} | path={request.url.path}")
    
    # Преобразуем ошибки Pydantic в наши ErrorDetail
    details = []
    for error in exc.errors():
        field = error.get('loc', [None])[-1] if error.get('loc') else None
        details.append(ErrorDetail(
            field=str(field) if field else None,
            message=error.get('msg', 'Validation error'),
            value=error.get('input')
        ))
    
    response = ValidationErrorResponse(
        message="Ошибка валидации данных",
        details=details,
        timestamp=Timestamp(get_current_timestamp()),
        path=str(request.url.path)
    )
    
    return JSONResponse(status_code=422, content=response.model_dump())

# 400: Pydantic ValidationError (direct)
async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
    logger.warning(f"400 Pydantic ValidationError: {exc.errors()} | path={request.url.path}")
    
    # Преобразуем ошибки Pydantic в наши ErrorDetail
    details = []
    for error in exc.errors():
        field = error.get('loc', [None])[-1] if error.get('loc') else None
        details.append(ErrorDetail(
            field=str(field) if field else None,
            message=error.get('msg', 'Validation error'),
            value=error.get('input')
        ))
    
    response = ValidationErrorResponse(
        message="Ошибка валидации данных",
        details=details,
        timestamp=Timestamp(get_current_timestamp()),
        path=str(request.url.path)
    )
    
    return JSONResponse(status_code=400, content=response.model_dump())

# HTTPException (универсальный)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException {exc.status_code}: {exc.detail} | path={request.url.path}")
    
    # Выбираем подходящий тип ошибки на основе статус кода
    if exc.status_code == 401:
        response = AuthenticationErrorResponse(
            message=str(exc.detail),
            timestamp=Timestamp(get_current_timestamp()),
            path=str(request.url.path)
        )
    elif exc.status_code == 403:
        response = AuthorizationErrorResponse(
            message=str(exc.detail),
            timestamp=Timestamp(get_current_timestamp()),
            path=str(request.url.path)
        )
    elif exc.status_code == 404:
        response = NotFoundErrorResponse(
            message=str(exc.detail),
            timestamp=Timestamp(get_current_timestamp()),
            path=str(request.url.path)
        )
    elif exc.status_code == 429:
        response = RateLimitErrorResponse(
            message=str(exc.detail),
            timestamp=Timestamp(get_current_timestamp()),
            path=str(request.url.path)
        )
    else:
        response = InternalServerErrorResponse(
            message=str(exc.detail),
            timestamp=Timestamp(get_current_timestamp()),
            path=str(request.url.path)
        )
    
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())

# 500: Unhandled Exception
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"500 Internal error: {exc} | path={request.url.path}", exc_info=True)
    
    response = InternalServerErrorResponse(
        message="Внутренняя ошибка сервера",
        timestamp=Timestamp(get_current_timestamp()),
        path=str(request.url.path)
    )
    
    return JSONResponse(status_code=500, content=response.model_dump())

# 404: Not Found (кастомный обработчик)
async def not_found_exception_handler(request: Request, exc: Exception):
    logger.warning(f"404 Not Found: {request.url.path}")
    
    response = NotFoundErrorResponse(
        message="Ресурс не найден",
        timestamp=Timestamp(get_current_timestamp()),
        path=str(request.url.path)
    )
    
    return JSONResponse(status_code=404, content=response.model_dump())

# Можно добавить кастомные бизнес-исключения по мере необходимости 