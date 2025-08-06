from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from bot.api.dependencies import get_product_registry_service
from bot.services.product.registry import ProductRegistryService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

# Модель для входящего продукта (упрощённая, для примера)
class ProductUploadIn(BaseModel):
    id: str | int = Field(..., description="Уникальный идентификатор продукта")
    title: str = Field(..., description="Название продукта")
    description: Dict[str, Any] = Field(..., description="Структурированное описание продукта")
    description_cid: str = Field(..., description="CID расширенного описания")
    cover_image: str = Field(..., description="CID обложки")
    gallery: List[str] = Field(default_factory=list, description="Массив дополнительных изображений (CID)")
    categories: List[str] = Field(default_factory=list, description="Список категорий")
    form: str = Field(..., description="Форма продукта (например, powder, tincture и т.д.)")
    species: str = Field(..., description="Вид продукта")
    prices: List[Dict[str, Any]] = Field(..., description="Массив цен")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные поля (sku, stock, tags и др.)")

class ProductsUploadRequest(BaseModel):
    products: List[ProductUploadIn] = Field(..., description="Список продуктов для загрузки")

class ProductUploadResult(BaseModel):
    id: str | int
    blockchain_id: str | None = None
    tx_hash: str | None = None
    metadata_cid: str | None = None
    status: str
    error: str | None = None

class ProductsUploadResponse(BaseModel):
    results: List[ProductUploadResult]

# Модели для обновления продуктов
class ProductUpdateRequest(BaseModel):
    """Модель для полного обновления продукта (PUT запрос)"""
    id: str | int = Field(..., description="Уникальный идентификатор продукта")
    title: str = Field(..., description="Название продукта")
    description: Dict[str, Any] = Field(..., description="Структурированное описание продукта")
    description_cid: str = Field(..., description="CID расширенного описания")
    cover_image: str = Field(..., description="CID обложки")
    gallery: List[str] = Field(default_factory=list, description="Массив дополнительных изображений (CID)")
    categories: List[str] = Field(default_factory=list, description="Список категорий")
    form: str = Field(..., description="Форма продукта (например, powder, tincture и т.д.)")
    species: str = Field(..., description="Вид продукта")
    prices: List[Dict[str, Any]] = Field(..., description="Массив цен")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные поля (sku, stock, tags и др.)")

class ProductStatusUpdateRequest(BaseModel):
    """Модель для обновления статуса активности продукта"""
    status: str = Field(..., description="Новый статус продукта (active/inactive)")

class ProductUpdateResponse(BaseModel):
    """Модель ответа для операций обновления продукта"""
    id: str | int = Field(..., description="Идентификатор обновленного продукта")
    blockchain_id: str | None = Field(None, description="ID продукта в блокчейне")
    tx_hash: str | None = Field(None, description="Хэш транзакции в блокчейне")
    metadata_cid: str | None = Field(None, description="CID обновленных метаданных")
    status: str = Field(..., description="Статус операции (success/error)")
    error: str | None = Field(None, description="Описание ошибки, если есть")

@router.post("/upload", response_model=ProductsUploadResponse)
async def upload_products(
    request: ProductsUploadRequest,
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
            product_dict = product.model_dump()
            logger.info(f"[API] product_dict перед валидацией: {product_dict}")
            # Вызываем обновлённый поток создания продукта
            result = await registry_service.create_product(product_dict)
            logger.info(f"[API] Результат create_product: {result}")
            results.append(ProductUploadResult(
                id=str(result.get("id")) if result.get("id") is not None else None,
                blockchain_id=result.get("blockchain_id"),
                tx_hash=result.get("tx_hash"),
                metadata_cid=result.get("metadata_cid"),
                status=result.get("status", "error"),
                error=result.get("error")
            ))
        except Exception as e:
            logger.error(f"Ошибка при обработке продукта {product.id}: {e}")
            results.append(ProductUploadResult(
                id=product.id,
                status="error",
                error=str(e)
            ))
    logger.info(f"[API] Финальный results: {results}")
    return ProductsUploadResponse(results=results)

@router.put("/{product_id}", response_model=ProductUpdateResponse)
async def update_product(
    product_id: str,
    request: ProductUpdateRequest,
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
            return ProductUpdateResponse(
                id=product_id,
                status="error",
                error="Некорректный ID продукта"
            )
        
        # TODO: TASK-002.2 - Реализовать логику обновления продукта
        # Заглушка для MVP
        response = ProductUpdateResponse(
            id=product_id,
            status="success",
            error=None
        )
        logger.info(f"[API] Результат PUT /products/{product_id}: {response}")
        return response
        
    except Exception as e:
        logger.error(f"[API] Ошибка при обновлении продукта {product_id}: {e}")
        return ProductUpdateResponse(
            id=product_id,
            status="error",
            error=f"Внутренняя ошибка сервера: {str(e)}"
        )

@router.post("/{product_id}/status", response_model=ProductUpdateResponse)
async def update_product_status(
    product_id: str,
    request: ProductStatusUpdateRequest,
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
            return ProductUpdateResponse(
                id=product_id,
                status="error",
                error="Некорректный ID продукта"
            )
        
        # Базовая валидация статуса
        if request.status not in ["active", "inactive"]:
            logger.error(f"[API] Некорректный статус: {request.status}")
            return ProductUpdateResponse(
                id=product_id,
                status="error",
                error="Некорректный статус. Допустимые значения: active, inactive"
            )
        
        # Реализация логики обновления статуса
        logger.info(f"[API] Вызываем registry_service.update_product_status для продукта {product_id}")
        
        # Преобразуем статус в числовой формат для сервиса
        status_mapping = {"active": 1, "inactive": 0}
        numeric_status = status_mapping.get(request.status)
        
        if numeric_status is None:
            logger.error(f"[API] Неизвестный статус: {request.status}")
            return ProductUpdateResponse(
                id=product_id,
                status="error",
                error=f"Неизвестный статус: {request.status}"
            )
        
        # Вызываем сервис для обновления статуса
        try:
            result = await registry_service.update_product_status(int(product_id), numeric_status)
            
            if result:
                logger.info(f"[API] Статус продукта {product_id} успешно обновлен на {request.status}")
                response = ProductUpdateResponse(
                    id=product_id,
                    status="success",
                    error=None
                )
            else:
                logger.error(f"[API] Не удалось обновить статус продукта {product_id}")
                response = ProductUpdateResponse(
                    id=product_id,
                    status="error",
                    error=f"Не удалось обновить статус продукта {product_id}"
                )
                
        except Exception as e:
            logger.error(f"[API] Ошибка при вызове update_product_status: {e}")
            response = ProductUpdateResponse(
                id=product_id,
                status="error",
                error=f"Ошибка сервиса: {str(e)}"
            )
        
        logger.info(f"[API] Результат POST /products/{product_id}/status: {response}")
        return response
        
    except Exception as e:
        logger.error(f"[API] Ошибка при обновлении статуса продукта {product_id}: {e}")
        return ProductUpdateResponse(
            id=product_id,
            status="error",
            error=f"Внутренняя ошибка сервера: {str(e)}"
        )