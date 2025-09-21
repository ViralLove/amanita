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
        # Инициализируем кэш локализации для LocalizationMixin
        self._localization_cache = {}
        self.logger.info(f"[{self.__class__.__name__}] Инициализирован")
    
    async def handle_callback(self, callback: CallbackQuery) -> None:
        """Реализация абстрактного метода для обработки callback"""
        self.logger.info(f"[{self.__class__.__name__}] handle_callback вызван! callback.data={callback.data}, from_user={callback.from_user.id}")
        try:
            await self.handle_show_catalog(callback)
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка в handle_callback для user_id {callback.from_user.id}: {e}")
            loc = self.get_localization(callback)
            await self.handle_error(e, callback, loc, "handle_callback")
    
    async def handle_show_catalog(self, callback: CallbackQuery) -> None:
        """
        Обработка показа каталога товаров
        
        Args:
            callback: Callback запрос от пользователя
        """
        self.logger.info(f"[{self.__class__.__name__}] handle_show_catalog вызван для user_id {callback.from_user.id}")
        
        try:
            # Валидация
            self.logger.info(f"[{self.__class__.__name__}] Начинаем валидацию для user_id {callback.from_user.id}")
            validations = {
                "callback_data": {"patterns": [r"^menu:catalog$"]},
                "user_permissions": {"permissions": ["catalog_view"]}
            }
            validation_results = self.validate_all(callback, validations)
            validation_errors = self.get_validation_errors(validation_results)
            
            if validation_errors:
                self.logger.warning(f"[{self.__class__.__name__}] Ошибки валидации для user_id {callback.from_user.id}: {validation_errors}")
                loc = self.get_localization(callback)
                await self.send_error_message(callback, loc, "validation", 
                                            f"❌ Ошибка валидации: {', '.join(validation_errors)}")
                return
            
            self.logger.info(f"[{self.__class__.__name__}] Валидация пройдена для user_id {callback.from_user.id}")
            
            # Получаем локализацию
            loc = self.get_localization(callback)
            self.logger.info(f"[{self.__class__.__name__}] Локализация получена для user_id {callback.from_user.id}: {loc}")
            
            # Создаем сообщение о прогрессе
            self.logger.info(f"[{self.__class__.__name__}] Создаем сообщение о прогрессе для user_id {callback.from_user.id}")
            progress_message = await self.create_simple_progress(callback, "catalog_loading", loc)
            self.logger.info(f"[{self.__class__.__name__}] Сообщение о прогрессе создано: {progress_message is not None}")
            
            try:
                # Получаем сервис каталога
                self.logger.info(f"[{self.__class__.__name__}] Получаем сервис каталога для user_id {callback.from_user.id}")
                catalog_service = get_catalog_service()
                self.logger.info(f"[{self.__class__.__name__}] Сервис каталога получен: {catalog_service is not None}")
                
                # Получаем каталог через сервис
                self.logger.info(f"[{self.__class__.__name__}] Запрашиваем каталог через сервис для user_id {callback.from_user.id}")
                products = await catalog_service.get_catalog_with_progress()
                self.logger.info(f"[{self.__class__.__name__}] Каталог получен для user_id {callback.from_user.id}: {len(products) if products else 0} продуктов")
                
                if not products:
                    # Каталог пуст
                    self.logger.info(f"[{self.__class__.__name__}] Каталог пуст для user_id {callback.from_user.id}")
                    try:
                        empty_message = loc.t('catalog.empty')
                    except:
                        empty_message = '📭 Каталог товаров пуст'
                    if progress_message:
                        await self.complete_simple_progress(progress_message, "catalog_loading", loc, False)
                        await callback.message.answer(empty_message)
                    else:
                        await callback.message.answer(empty_message)
                else:
                    # Отправляем каталог через сервис
                    self.logger.info(f"[{self.__class__.__name__}] Отправляем каталог пользователю {callback.from_user.id}: {len(products)} продуктов")
                    await catalog_service.send_catalog_to_user(callback, products, loc)
                    self.logger.info(f"[{self.__class__.__name__}] Каталог отправлен пользователю {callback.from_user.id}")
                    
                    if progress_message:
                        await self.complete_simple_progress(progress_message, "catalog_loading", loc, True)
            
            except Exception as e:
                self.logger.error(f"[{self.__class__.__name__}] Ошибка при работе с каталогом для user_id {callback.from_user.id}: {e}")
                if progress_message:
                    await self.complete_simple_progress(progress_message, "catalog_loading", loc, False)
                await self.handle_error(e, callback, loc, "catalog_loading")
                
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Общая ошибка в handle_show_catalog для user_id {callback.from_user.id}: {e}")
            loc = self.get_localization(callback)
            await self.handle_error(e, callback, loc, "show_catalog")


# Создаем экземпляр обработчика
catalog_handler = CatalogHandler()

@router.callback_query(F.data == "menu:catalog")
async def show_catalog(callback: CallbackQuery):
    """
    Обработчик для показа каталога товаров.
    Использует CatalogHandler с миксинами для устранения дублирования кода.
    """
    await catalog_handler.process_callback(callback)


# Метод handle_show_catalog теперь реализован внутри класса CatalogHandler
