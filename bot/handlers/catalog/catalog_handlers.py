"""
Обработчики для работы с каталогом продуктов.
Содержит только UI логику, бизнес-логика вынесена в CatalogService.
Использует BaseCatalogHandler и миксины для устранения дублирования кода.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from services.application.catalog.catalog_service import CatalogService
from dependencies import get_catalog_service
from .base_handler import BaseCatalogHandler
from .mixins import ErrorHandlerMixin, LocalizationMixin, ProgressMixin, ValidationMixin

router = Router()
logger = logging.getLogger(__name__)


class CatalogHandler(BaseCatalogHandler, ErrorHandlerMixin, LocalizationMixin, ProgressMixin, ValidationMixin):
    """Обработчик для работы с каталогом продуктов"""
    
    def __init__(self):
        """Инициализация обработчика каталога"""
        super().__init__()
        self.logger.info(f"[{self.__class__.__name__}] Инициализирован")
    
    async def handle_callback(self, callback: CallbackQuery) -> None:
        """Реализация абстрактного метода для обработки callback"""
        await handle_show_catalog(callback)


# Создаем экземпляр обработчика
catalog_handler = CatalogHandler()

@router.callback_query(F.data == "menu:catalog")
async def show_catalog(callback: CallbackQuery):
    """
    Обработчик для показа каталога товаров.
    Использует CatalogHandler с миксинами для устранения дублирования кода.
    """
    await catalog_handler.process_callback(callback)


# Добавляем метод обработки в класс CatalogHandler
async def handle_show_catalog(self, callback: CallbackQuery) -> None:
    """
    Обработка показа каталога товаров
    
    Args:
        callback: Callback запрос от пользователя
    """
    try:
        # Валидация
        validations = {
            "callback_data": {"patterns": [r"^menu:catalog$"]},
            "user_permissions": {"permissions": ["catalog_view"]}
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
        progress_message = await self.create_simple_progress(callback, "catalog_loading", loc)
        
        try:
            # Получаем сервис каталога
            catalog_service = get_catalog_service()
            
            # Получаем каталог через сервис
            products = await catalog_service.get_catalog_with_progress()
            
            if not products:
                # Каталог пуст
                empty_message = loc.t('catalog.empty', '📭 Каталог товаров пуст')
                if progress_message:
                    await self.complete_simple_progress(progress_message, "catalog_loading", loc, False)
                    await callback.message.answer(empty_message)
                else:
                    await callback.message.answer(empty_message)
            else:
                # Отправляем каталог через сервис
                await catalog_service.send_catalog_to_user(callback, products, loc)
                
                if progress_message:
                    await self.complete_simple_progress(progress_message, "catalog_loading", loc, True)
        
        except Exception as e:
            if progress_message:
                await self.complete_simple_progress(progress_message, "catalog_loading", loc, False)
            await self.handle_error(e, callback, loc, "catalog_loading")
            
    except Exception as e:
        loc = self.get_localization(callback)
        await self.handle_error(e, callback, loc, "show_catalog")


# Привязываем метод к классу
# CatalogHandler.handle_callback = handle_show_catalog  # Теперь реализовано в классе
