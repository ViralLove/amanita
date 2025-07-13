"""
API эндпоинты для управления API ключами
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
import logging

from services.core.api_key import ApiKeyService
from services.service_factory import ServiceFactory
from api.models.auth import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyValidateRequest,
    ApiKeyValidateResponse,
    ApiKeyRevokeRequest,
    ApiKeyRevokeResponse
)
from api.models.common import get_current_timestamp, generate_request_id, ApiKey, RequestId, Timestamp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def get_service_factory() -> ServiceFactory:
    """Dependency injection для ServiceFactory"""
    return ServiceFactory()


def get_api_key_service(service_factory: ServiceFactory = Depends(get_service_factory)) -> ApiKeyService:
    """Dependency injection для ApiKeyService"""
    return service_factory.create_api_key_service()


@router.post("/", response_model=ApiKeyCreateResponse)
async def create_api_key(
    request: ApiKeyCreateRequest,
    api_key_service: ApiKeyService = Depends(get_api_key_service)
):
    """
    Создает новый API ключ для клиента
    
    Args:
        request: Данные для создания ключа
        api_key_service: Сервис управления API ключами
    
    Returns:
        Информация о созданном API ключе
    """
    try:
        logger.info(f"Создание API ключа для клиента {request.client_address}")
        
        result = await api_key_service.create_api_key(
            seller_address=request.client_address,
            description=request.description or ""
        )
        
        logger.info(f"API ключ создан успешно: {result['api_key']}")
        
        return ApiKeyCreateResponse(
            success=True,
            api_key=ApiKey(result["api_key"]),
            secret_key=result["secret_key"],
            request_id=RequestId(generate_request_id()),
            timestamp=Timestamp(get_current_timestamp())
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания API ключа: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create API key: {str(e)}")


@router.get("/{client_address}", response_model=List[dict])
async def get_client_api_keys(
    client_address: str,
    api_key_service: ApiKeyService = Depends(get_api_key_service)
):
    """
    Получает список API ключей клиента
    
    Args:
        client_address: Адрес клиента
        api_key_service: Сервис управления API ключами
    
    Returns:
        Список API ключей клиента
    """
    try:
        logger.info(f"Получение API ключей для клиента {client_address}")
        
        keys = await api_key_service.get_seller_api_keys(client_address)
        
        logger.info(f"Найдено {len(keys)} API ключей для клиента {client_address}")
        
        return [
            {
                "api_key": key["api_key"],
                "client_address": client_address,
                "description": key.get("description", ""),
                "created_at": key.get("created_at", ""),
                "active": key.get("active", True)
            }
            for key in keys
        ]
        
    except Exception as e:
        logger.error(f"Ошибка получения API ключей: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get API keys: {str(e)}")


@router.delete("/{api_key}")
async def revoke_api_key(
    api_key: str,
    request: Request,
    api_key_service: ApiKeyService = Depends(get_api_key_service)
):
    """
    Отзывает API ключ
    
    Args:
        api_key: API ключ для отзыва
        request: FastAPI request объект
        api_key_service: Сервис управления API ключами
    
    Returns:
        Статус операции
    """
    try:
        # Получаем адрес клиента из request state (установлен middleware)
        client_address = getattr(request.state, 'client_address', None)
        
        if not client_address:
            raise HTTPException(status_code=400, detail="Client address not found in request context")
        
        logger.info(f"Отзыв API ключа {api_key} для клиента {client_address}")
        
        success = await api_key_service.revoke_api_key(api_key, client_address)
        
        if success:
            logger.info(f"API ключ {api_key} успешно отозван")
            return {"message": "API key revoked successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to revoke API key")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка отзыва API ключа: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to revoke API key: {str(e)}")


@router.get("/validate/{api_key}")
async def validate_api_key(
    api_key: str,
    api_key_service: ApiKeyService = Depends(get_api_key_service)
):
    """
    Валидирует API ключ (для тестирования)
    
    Args:
        api_key: API ключ для валидации
        api_key_service: Сервис управления API ключами
    
    Returns:
        Информация о валидности ключа
    """
    try:
        logger.info(f"Валидация API ключа {api_key}")
        
        key_info = await api_key_service.validate_api_key(api_key)
        
        logger.info(f"API ключ {api_key} валиден")
        
        return {
            "valid": True,
            "client_address": key_info["seller_address"],
            "description": key_info.get("description", ""),
            "active": key_info.get("active", True)
        }
        
    except Exception as e:
        logger.warning(f"API ключ {api_key} невалиден: {e}")
        return {
            "valid": False,
            "error": str(e)
        } 