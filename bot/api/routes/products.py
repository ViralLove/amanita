"""
Исправленные роуты для продуктов с правильной валидацией и обработкой ошибок
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from api.dependencies import get_product_registry_service
from services.product.registry import ProductRegistryService
from api.models.product import (
    ProductUploadIn, ProductUploadRequest, ProductResponse, ProductsUploadResponse,
    ProductUpdateIn, ProductStatusUpdate
)
from api.exceptions.validation import ProductValidationError, UnifiedValidationError
from api.converters import ConverterFactory
from api.models.common import EthereumAddress
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/{seller_address}")
async def get_seller_catalog(
    seller_address: str,
    registry_service: ProductRegistryService = Depends(get_product_registry_service),
    http_request: Request = None
):
    """
    Получает каталог продуктов текущего продавца.
    
    Args:
        seller_address: Ethereum адрес продавца
        registry_service: Сервис реестра продуктов
        http_request: HTTP запрос для логирования
        
    Returns:
        Каталог продуктов продавца
        
    Raises:
        HTTPException: При ошибках валидации или доступа
    """
    logger.info(f"[API] Получен запрос GET /products/{seller_address}")
    logger.info(f"[API] Начинаем обработку запроса для продавца: {seller_address}")
    
    try:
        # 1. Валидация Ethereum адреса через общий стандарт
        logger.info(f"[API] Шаг 1: Валидация Ethereum адреса: {seller_address}")
        try:
            validated_address = EthereumAddress(seller_address)
            seller_address = str(validated_address)  # Нормализованный адрес
            logger.info(f"[API] ✅ Ethereum адрес валидирован: {seller_address}")
        except ValueError as e:
            logger.warning(f"[API] ❌ Некорректный формат Ethereum адреса: {seller_address}, ошибка: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Некорректный формат Ethereum адреса: {seller_address}. Ожидается формат: 0x + 40 hex символов"
            )
        
        # 2. Проверка прав доступа (только текущий продавец может получить свой каталог)
        logger.info(f"[API] Шаг 2: Проверка прав доступа")
        current_seller_address = registry_service.seller_account.address
        logger.info(f"[API] Текущий продавец: {current_seller_address}")
        logger.info(f"[API] Запрошенный адрес: {seller_address}")
        
        if seller_address.lower() != current_seller_address.lower():
            logger.warning(f"[API] ❌ Попытка доступа к каталогу другого продавца. Запрошен: {seller_address}, текущий: {current_seller_address}")
            raise HTTPException(
                status_code=403,
                detail="Access denied: can only view own catalog"
            )
        
        logger.info(f"[API] ✅ Доступ к каталогу подтвержден для продавца: {seller_address}")
        
        # 3. Получение каталога через существующий функционал
        logger.info(f"[API] Шаг 3: Запрашиваем каталог для продавца: {seller_address}")
        logger.info(f"[API] Вызываем registry_service.get_all_products()...")
        products = await registry_service.get_all_products()
        
        logger.info(f"[API] ✅ Получено {len(products)} продуктов для продавца {seller_address}")
        if products:
            logger.info(f"[API] Первый продукт: business_id={products[0].business_id if hasattr(products[0], 'business_id') else 'N/A'}")
        else:
            logger.info(f"[API] ⚠️ Каталог пуст - 0 продуктов")
        
        # 4. Формирование ответа
        logger.info(f"[API] Шаг 4: Формирование ответа для {len(products)} продуктов")
        response_data = {
            "seller_address": seller_address,
            "total_count": len(products),
            "products": [
                {
                    "business_id": str(product.business_id),  # 🔧 ИСПРАВЛЕНО: заменено id на business_id
                    "blockchain_id": product.blockchain_id if hasattr(product, 'blockchain_id') and product.blockchain_id else None,  # 🔧 ДОБАВЛЕНО: blockchain_id (сохраняем оригинальный тип)
                    "title": product.title,
                    "status": product.status,
                    "cid": product.cid,
                    "categories": product.categories,
                    "forms": product.forms,
                    "species": product.species,
                    "cover_image_url": product.cover_image_url,
                    "organic_components": [
                        {
                            "component_id": component.component_id,
                            "description_cid": component.description_cid,
                            "proportion": component.proportion
                        } for component in product.organic_components
                    ] if hasattr(product, 'organic_components') and product.organic_components else [],  # 🔧 ДОБАВЛЕНО: organic_components
                    "prices": [
                        {
                            "price": price.price,
                            "currency": price.currency,
                            "weight": price.weight,
                            "weight_unit": price.weight_unit,
                            "volume": price.volume,
                            "volume_unit": price.volume_unit,
                            "form": price.form
                        } for price in product.prices
                    ] if product.prices else []
                } for product in products
            ]
        }
        
        logger.info(f"[API] ✅ Каталог успешно сформирован для продавца {seller_address}")
        logger.info(f"[API] 📊 Структура ответа: seller_address={response_data['seller_address']}, total_count={response_data['total_count']}, products_count={len(response_data['products'])}")
        return response_data
        
    except HTTPException as http_ex:
        # Перебрасываем HTTPException без изменений
        logger.warning(f"[API] ⚠️ HTTPException переброшен: status_code={http_ex.status_code}, detail={http_ex.detail}")
        raise
    except Exception as e:
        logger.error(f"[API] ❌ Неожиданная ошибка при получении каталога продавца {seller_address}: {e}")
        import traceback
        logger.error(f"[API] 🔍 Полный traceback ошибки:")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

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
    
    # Получаем конвертер для продуктов
    product_converter = ConverterFactory.get_product_converter()
    results = []
    
    for product in request.products:
        try:
            # Получаем business_id из модели
            business_id = product.get_business_id()
            
            # Используем конвертер вместо model_dump()
            try:
                product_dict = product_converter.api_to_dict(product)
            except (ValueError, UnifiedValidationError) as e:
                logger.error(f"Ошибка конвертации продукта {product.id}: {e}")
                error_message = str(e)
                if isinstance(e, UnifiedValidationError):
                    error_message = f"Ошибка валидации: {e.message}"
                    if e.error_code:
                        error_message += f" (код: {e.error_code})"
                results.append(ProductResponse(
                    id=str(product.id),
                    status="error",
                    error=error_message
                ))
                continue
            
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
        except (ProductValidationError, UnifiedValidationError) as e:
            logger.error(f"Ошибка валидации продукта {product.id}: {e}")
            error_message = str(e)
            if isinstance(e, UnifiedValidationError):
                error_message = f"Ошибка валидации: {e.message}"
                if e.error_code:
                    error_message += f" (код: {e.error_code})"
            results.append(ProductResponse(
                id=str(product.id),
                status="error",
                error=error_message
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
        
        # Получаем конвертер для продуктов
        product_converter = ConverterFactory.get_product_converter()
        
        # Используем конвертер вместо model_dump()
        try:
            product_dict = product_converter.api_to_dict(request)
        except (ValueError, UnifiedValidationError) as e:
            logger.error(f"Ошибка конвертации продукта {product_id}: {e}")
            error_message = str(e)
            if isinstance(e, UnifiedValidationError):
                error_message = f"Ошибка валидации: {e.message}"
                if e.error_code:
                    error_message += f" (код: {e.error_code})"
            raise HTTPException(
                status_code=422,
                detail=error_message
            )
        
        # Вызываем сервис для обновления продукта
        logger.info(f"[API] Вызываем registry_service.update_product для продукта {product_id}")
        result = await registry_service.update_product(product_id, product_dict)
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
