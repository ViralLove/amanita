"""
Обработчики для навигации по каталогу.
Содержит логику скролла и навигации между разделами каталога.
Использует BaseCatalogHandler и миксины для устранения дублирования кода.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from .base_handler import BaseCatalogHandler
from .mixins import ErrorHandlerMixin, LocalizationMixin, ProgressMixin, ValidationMixin

router = Router()
logger = logging.getLogger(__name__)


class NavigationHandler(BaseCatalogHandler, ErrorHandlerMixin, LocalizationMixin, ProgressMixin, ValidationMixin):
    """Обработчик для навигации по каталогу"""
    
    def __init__(self):
        """Инициализация обработчика навигации"""
        super().__init__()
        # Инициализируем кэш локализации для LocalizationMixin
        self._localization_cache = {}
        self.logger.info(f"[{self.__class__.__name__}] Инициализирован")
    
    async def handle_callback(self, callback: CallbackQuery) -> None:
        """Реализация абстрактного метода для обработки callback"""
        await handle_scroll_to_catalog(callback)


# Создаем экземпляр обработчика
navigation_handler = NavigationHandler()

@router.callback_query(F.data == "scroll:catalog")
async def scroll_to_catalog(callback: CallbackQuery):
    """
    Обработчик для скролла к каталогу вместо перезагрузки.
    Отправляет сообщение с хэштегами для быстрой навигации и поиска.
    """
    logger.info(f"[NAVIGATION_HANDLER] scroll_to_catalog вызван! callback.data={callback.data}, from_user={callback.from_user.id}")
    
    try:
        # Получаем локализацию через миксин
        loc = navigation_handler.get_localization(callback)
        
        # Создаем улучшенное сообщение с хэштегами для навигации
        scroll_message = (
            f"📚 <b>Каталог продуктов</b>\n\n"
            f"• #catalog - основной каталог\n"
            f"💡 <i>Нажмите на хэштег для быстрого перехода к нужному разделу</i>"
        )
        
        await callback.message.answer(
            scroll_message,
            parse_mode="HTML"
        )
        
        logger.info(f"[NAVIGATION_HANDLER] Улучшенное сообщение со скроллом к каталогу отправлено для пользователя {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"[NAVIGATION_HANDLER] Ошибка при скролле к каталогу: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Отправляем сообщение об ошибке пользователю
        try:
            await callback.message.answer("❌ Произошла ошибка при переходе к каталогу")
        except:
            pass
    
    finally:
        await callback.answer()


# Добавляем метод обработки в класс NavigationHandler
async def handle_scroll_to_catalog(self, callback: CallbackQuery) -> None:
    """
    Обработка скролла к каталогу
    
    Args:
        callback: Callback запрос от пользователя
    """
    try:
        # Валидация
        validations = {
            "callback_data": {"patterns": [r"^scroll:catalog$"]},
            "user_permissions": {"permissions": ["catalog_navigation"]}
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
        
        # Создаем сообщение с хэштегами для навигации
        try:
            catalog_title = loc.t('catalog.title')
        except:
            catalog_title = 'Каталог продуктов'
        try:
            catalog_main = loc.t('catalog.main')
        except:
            catalog_main = 'основной каталог'
        try:
            catalog_search = loc.t('catalog.search')
        except:
            catalog_search = 'поиск по каталогу'
        try:
            catalog_categories = loc.t('catalog.categories')
        except:
            catalog_categories = 'категории продуктов'
        try:
            catalog_favorites = loc.t('catalog.favorites')
        except:
            catalog_favorites = 'избранные продукты'
        try:
            catalog_tip = loc.t('catalog.tip')
        except:
            catalog_tip = 'Используйте хэштеги для быстрой навигации!'
            
        scroll_message = (
            f"📚 <b>{catalog_title}</b>\n\n"
            f"• #catalog - {catalog_main}\n"
            f"• #search - {catalog_search}\n"
            f"• #categories - {catalog_categories}\n"
            f"• #favorites - {catalog_favorites}\n\n"
            f"💡 {catalog_tip}"
        )
        
        # Отправляем сообщение
        await callback.message.answer(scroll_message, parse_mode="HTML")
        
    except Exception as e:
        loc = self.get_localization(callback)
        await self.handle_error(e, callback, loc, "scroll_to_catalog")


# Привязываем метод к классу
# NavigationHandler.handle_callback = handle_scroll_to_catalog  # Теперь реализовано в классе
