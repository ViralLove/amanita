"""
Исправленные роуты для продуктов с правильной валидацией и обработкой ошибок
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from bot.api.dependencies import get_product_registry_service
from bot.services.product.registry import ProductRegistryService
from bot.api.models.product import (
    ProductUploadIn, ProductUploadRequest, ProductResponse, ProductsUploadResponse,
    ProductUpdateIn, ProductStatusUpdate
)
from bot.api.exceptions.validation import ProductValidationError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

@router.post("/upload", response_model=ProductsUploadResponse)
async def upload_products(
    request: ProductUploadRequest,
    registry_service: ProductRegistryService = Depends(get_product_registry_service),
    http_request: Request = None
):
    """
    Загрузка (создание/обновление) продуктов из e-commerce систем.
    """
    logger.info(f"[API] Получен запрос /products/upload: {request}")
    logger.info(f"[API] request.products: {request.products}")
    results = []
    
    for product in request.products:
        try:
            # Получаем business_id из модели
            business_id = product.get_business_id()
            
            # Подготавливаем данные для сервиса
            product_dict = product.model_dump()
            
            # Добавляем business_id если его нет
            if 'business_id' not in product_dict or not product_dict['business_id']:
                product_dict['business_id'] = business_id
            
            logger.info(f"[API] product_dict перед валидацией: {product_dict}")
            
            # Вызываем обновлённый поток создания продукта
            result = await registry_service.create_product(product_dict)
            logger.info(f"[API] Результат create_product: {result}")
            
            results.append(ProductResponse(
                id=business_id,
                blockchain_id=result.get("blockchain_id"),
                tx_hash=result.get("tx_hash"),
                metadata_cid=result.get("metadata_cid"),
                status=result.get("status", "error"),
                error=result.get("error")
            ))
        except ProductValidationError as e:
            logger.error(f"Ошибка валидации продукта {product.id}: {e}")
            results.append(ProductResponse(
                id=str(product.id),
                status="error",
                error=str(e)
            ))
        except Exception as e:
            logger.error(f"Ошибка при обработке продукта {product.id}: {e}")
            results.append(ProductResponse(
                id=str(product.id),
                status="error",
                error=str(e)
            ))
    logger.info(f"[API] Финальный results: {results}")
    return ProductsUploadResponse(results=results)

@router.put("/{product_id}")
async def update_product(
    product_id: str,
    request: ProductUpdateIn,
    registry_service: ProductRegistryService = Depends(get_product_registry_service),
    http_request: Request = None
):
    """
    Полное обновление продукта по ID.
    """
    logger.info(f"[API] Получен запрос PUT /products/{product_id}: {request}")
    
    try:
        # Базовая валидация ID продукта
        if not product_id or product_id.strip() == "":
            logger.error(f"[API] Некорректный ID продукта: {product_id}")
            raise HTTPException(
                status_code=400,
                detail="Некорректный ID продукта"
            )
        
        # Вызываем сервис для обновления продукта
        logger.info(f"[API] Вызываем registry_service.update_product для продукта {product_id}")
        result = await registry_service.update_product(product_id, request.model_dump())
        logger.info(f"[API] Результат update_product: {result}")
        
        # Проверяем результат операции
        if result.get("status") == "error":
            error_message = result.get("error", "Неизвестная ошибка")
            logger.error(f"[API] Ошибка обновления продукта {product_id}: {error_message}")
            
            # Определяем HTTP статус код на основе типа ошибки
            if "не найден" in error_message.lower():
                raise HTTPException(status_code=404, detail=error_message)
            elif "недостаточно прав" in error_message.lower():
                raise HTTPException(status_code=403, detail=error_message)
            elif "валидация" in error_message.lower():
                raise HTTPException(status_code=422, detail=error_message)
            else:
                raise HTTPException(status_code=500, detail=error_message)
        
        # Возвращаем успешный ответ
        response = ProductResponse(
            id=result.get("id", product_id),
            blockchain_id=result.get("blockchain_id"),
            tx_hash=result.get("tx_hash"),
            metadata_cid=result.get("metadata_cid"),
            status=result.get("status", "success"),
            error=result.get("error")
        )
        logger.info(f"[API] Результат PUT /products/{product_id}: {response}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Ошибка при обновлении продукта {product_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )

@router.post("/{product_id}/status")
async def update_product_status(
    product_id: str,
    request: ProductStatusUpdate,
    registry_service: ProductRegistryService = Depends(get_product_registry_service),
    http_request: Request = None
):
    """
    Обновление статуса активности продукта.
    """
    logger.info(f"[API] Получен запрос POST /products/{product_id}/status: {request}")
    
    try:
        # Базовая валидация ID продукта
        if not product_id or product_id.strip() == "":
            logger.error(f"[API] Некорректный ID продукта: {product_id}")
            raise HTTPException(
                status_code=400,
                detail="Некорректный ID продукта"
            )
        
        # Базовая валидация статуса
        if request.status not in [0, 1]:
            logger.error(f"[API] Некорректный статус: {request.status}")
            raise HTTPException(
                status_code=400,
                detail="Некорректный статус. Допустимые значения: 0 (неактивен), 1 (активен)"
            )
        
        # TODO: TASK-002.3 - Реализовать логику обновления статуса продукта
        # Заглушка для MVP
        response = ProductResponse(
            id=product_id,
            status="success",
            error=None
        )
        logger.info(f"[API] Результат POST /products/{product_id}/status: {response}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Ошибка при обновлении статуса продукта {product_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )
