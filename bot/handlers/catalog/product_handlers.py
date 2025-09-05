"""
Обработчики для работы с детальной информацией о продуктах.
Содержит только UI логику, бизнес-логика вынесена в ProductService.
Использует BaseCatalogHandler и миксины для устранения дублирования кода.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from bot.services.application.catalog.product_service import ProductService
from bot.dependencies import get_product_service
from .base_handler import BaseCatalogHandler
from .mixins import ErrorHandlerMixin, LocalizationMixin, ProgressMixin, ValidationMixin

router = Router()
logger = logging.getLogger(__name__)


class ProductHandler(BaseCatalogHandler, ErrorHandlerMixin, LocalizationMixin, ProgressMixin, ValidationMixin):
    """Обработчик для работы с детальной информацией о продуктах"""
    
    def __init__(self):
        """Инициализация обработчика продуктов"""
        super().__init__()
        self.logger.info(f"[{self.__class__.__name__}] Инициализирован")
    
    async def handle_callback(self, callback: CallbackQuery) -> None:
        """Реализация абстрактного метода для обработки callback"""
        await handle_show_product_details(callback)


# Создаем экземпляр обработчика
product_handler = ProductHandler()

@router.callback_query(F.data.startswith("product:details:"))
async def show_product_details(callback: CallbackQuery):
    """
    Обработчик для показа детальной информации о продукте.
    Вызывается при нажатии кнопки "📖 Подробнее" в каталоге.
    """
    logger.info(f"[PRODUCT_HANDLER] show_product_details вызван! callback.data={callback.data}, from_user={callback.from_user.id}")
    
    try:
        # Получаем сервисы через DI
        product_service = get_product_service()
        
        # Извлекаем product_id из callback.data
        # Формат: "product:details:{product_id}"
        product_id = callback.data.split(":")[-1]
        logger.info(f"[PRODUCT_HANDLER] Извлечен product_id: {product_id}")
        
        if not product_id or product_id == "details":
            logger.error("[PRODUCT_HANDLER] Некорректный product_id")
            await callback.message.answer("❌ Ошибка: не удалось определить продукт")
            await callback.answer()
            return
        
        # Получаем локализацию через миксин
        loc = product_handler.get_localization(callback)
        
        # Отправляем сообщение о загрузке
        loading_message = await callback.message.answer(
            loc.t("catalog.loading") if hasattr(loc, 't') else "🔄 Загружаем информацию о продукте..."
        )
        
        # Делегируем поиск продукта в сервис
        product = await product_service.get_product_by_id(product_id)
        
        # Удаляем сообщение о загрузке
        await loading_message.delete()
        
        if not product:
            logger.error(f"[PRODUCT_HANDLER] Продукт с ID {product_id} не найден")
            await callback.message.answer("❌ Продукт не найден")
            await callback.answer()
            return
        
        # Делегируем отправку деталей продукта в сервис
        await product_service.send_product_details(callback, product, loc)
        
    except Exception as e:
        logger.error(f"[PRODUCT_HANDLER] Ошибка при показе детальной информации: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Отправляем сообщение об ошибке пользователю
        try:
            await callback.message.answer("❌ Произошла ошибка при загрузке информации о продукте")
        except:
            pass
    
    finally:
        await callback.answer()


# Добавляем метод обработки в класс ProductHandler
async def handle_show_product_details(self, callback: CallbackQuery) -> None:
    """
    Обработка показа детальной информации о продукте
    
    Args:
        callback: Callback запрос от пользователя
    """
    try:
        # Извлекаем product_id из callback данных
        product_id = self.extract_product_id_from_callback(callback, "product:details:")
        
        # Валидация
        validations = {
            "callback_data": {"patterns": [r"^product:details:.+$"]},
            "user_permissions": {"permissions": ["product_view"]},
            "product_id": product_id
        }
        validation_results = self.validate_all(callback, validations)
        validation_errors = self.get_validation_errors(validation_results)
        
        if validation_errors:
            loc = self.get_localization(callback)
            await self.send_error_message(callback, loc, "validation", 
                                        f"❌ Ошибка валидации: {', '.join(validation_errors)}")
            return
        
        # Получаем локализацию
        loc = self.get_localization(callback)
        
        # Создаем сообщение о прогрессе
        progress_message = await self.create_simple_progress(callback, "product_loading", loc)
        
        try:
            # Получаем сервис продуктов
            product_service = get_product_service()
            
            # Получаем продукт через сервис
            product = await product_service.get_product_by_id(product_id)
            
            if not product:
                # Продукт не найден
                not_found_message = loc.t('product.not_found', f'📭 Продукт с ID {product_id} не найден')
                if progress_message:
                    await self.complete_simple_progress(progress_message, "product_loading", loc, False)
                    await callback.message.answer(not_found_message)
                else:
                    await callback.message.answer(not_found_message)
            else:
                # Отправляем детали продукта через сервис
                await product_service.send_product_details(callback, product, loc)
                
                if progress_message:
                    await self.complete_simple_progress(progress_message, "product_loading", loc, True)
        
        except Exception as e:
            if progress_message:
                await self.complete_simple_progress(progress_message, "product_loading", loc, False)
            await self.handle_error(e, callback, loc, "product_loading")
            
    except Exception as e:
        loc = self.get_localization(callback)
        await self.handle_error(e, callback, loc, "show_product_details")


# Привязываем метод к классу
# ProductHandler.handle_callback = handle_show_product_details  # Теперь реализовано в классе
