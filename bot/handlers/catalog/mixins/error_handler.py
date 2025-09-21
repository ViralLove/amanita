"""
Миксин для обработки ошибок в обработчиках каталога.
Содержит централизованную логику обработки ошибок.
"""

import logging
from typing import Optional, Dict, Any
from aiogram.types import CallbackQuery
from services.common.localization import Localization
from services.application.catalog.error_handling_service import ErrorHandlingService

logger = logging.getLogger(__name__)


class ErrorHandlerMixin:
    """Миксин для обработки ошибок в обработчиках каталога"""
    
    def __init__(self):
        """Инициализация миксина обработки ошибок"""
        self.error_handling_service = ErrorHandlingService()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"[{self.__class__.__name__}] ErrorHandlerMixin инициализирован")
    
    async def handle_error(self, error: Exception, callback: CallbackQuery, 
                          loc: Localization, context: str = "") -> bool:
        """
        Обрабатывает ошибку с использованием ErrorHandlingService
        
        Args:
            error: Исключение для обработки
            callback: Callback запрос
            loc: Объект локализации
            context: Контекст ошибки
            
        Returns:
            bool: True если ошибка обработана успешно
        """
        try:
            self.logger.error(f"[{self.__class__.__name__}] Обработка ошибки в {context}: {error}")
            
            # Определяем тип ошибки и выбираем соответствующий обработчик
            if "catalog" in context.lower():
                return await self.error_handling_service.handle_catalog_error(error, callback, loc, context)
            elif "product" in context.lower():
                product_id = getattr(error, 'product_id', '')
                return await self.error_handling_service.handle_product_error(error, callback, loc, product_id)
            elif "image" in context.lower():
                image_url = getattr(error, 'image_url', '')
                return await self.error_handling_service.handle_image_error(error, callback, loc, image_url)
            else:
                # Общая обработка ошибок
                return await self._handle_general_error(error, callback, loc, context)
                
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка при обработке ошибки: {e}")
            return False
    
    async def _handle_general_error(self, error: Exception, callback: CallbackQuery, 
                                   loc: Localization, context: str) -> bool:
        """
        Обрабатывает общие ошибки
        
        Args:
            error: Исключение
            callback: Callback запрос
            loc: Объект локализации
            context: Контекст ошибки
            
        Returns:
            bool: True если ошибка обработана успешно
        """
        try:
            error_message = self._get_general_error_message(error, loc)
            await callback.message.answer(error_message)
            await callback.answer()
            return True
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка при обработке общей ошибки: {e}")
            return False
    
    def _get_general_error_message(self, error: Exception, loc: Localization) -> str:
        """
        Получает сообщение об общей ошибке
        
        Args:
            error: Исключение
            loc: Объект локализации
            
        Returns:
            str: Сообщение об ошибке
        """
        try:
            error_type = type(error).__name__
            error_message = str(error).lower()
            
            if "timeout" in error_message:
                try:
                    return loc.t('error.timeout')
                except:
                    return '⏰ Время ожидания истекло. Попробуйте позже.'
            elif "connection" in error_message:
                try:
                    return loc.t('error.connection')
                except:
                    return '🔌 Ошибка подключения. Проверьте интернет.'
            elif "not found" in error_message:
                try:
                    return loc.t('error.not_found')
                except:
                    return '📭 Запрашиваемый ресурс не найден.'
            elif "permission" in error_message or "access" in error_message:
                try:
                    return loc.t('error.permission')
                except:
                    return '🔒 Недостаточно прав для выполнения операции.'
            elif "validation" in error_message or "invalid" in error_message:
                try:
                    return loc.t('error.validation')
                except:
                    return '❌ Некорректные данные.'
            else:
                try:
                    return loc.t('error.general')
                except:
                    return '❌ Произошла ошибка. Попробуйте позже.'
                
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка получения сообщения об ошибке: {e}")
            return "❌ Произошла ошибка"
    
    def log_error(self, error: Exception, context: str = "", user_id: Optional[int] = None) -> None:
        """
        Логирует ошибку с контекстом
        
        Args:
            error: Исключение
            context: Контекст ошибки
            user_id: ID пользователя (опционально)
        """
        try:
            user_info = f" для user_id {user_id}" if user_id else ""
            self.logger.error(f"[{self.__class__.__name__}] Ошибка в {context}{user_info}: {error}")
            
            # Дополнительная информация для отладки
            self.logger.debug(f"[{self.__class__.__name__}] Тип ошибки: {type(error).__name__}")
            self.logger.debug(f"[{self.__class__.__name__}] Сообщение ошибки: {str(error)}")
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка при логировании ошибки: {e}")
    
    async def send_error_message(self, callback: CallbackQuery, loc: Localization, 
                                error_type: str = "general", custom_message: str = "") -> None:
        """
        Отправляет сообщение об ошибке пользователю
        
        Args:
            callback: Callback запрос
            loc: Объект локализации
            error_type: Тип ошибки
            custom_message: Кастомное сообщение об ошибке
        """
        try:
            if custom_message:
                error_message = custom_message
            else:
                try:
                    error_message = loc.t(f'error.{error_type}')
                except:
                    error_message = f'❌ Ошибка: {error_type}'
            
            await callback.message.answer(error_message)
            await callback.answer()
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка отправки сообщения об ошибке: {e}")
    
    def register_fallback_strategy(self, error_key: str, strategy) -> None:
        """
        Регистрирует fallback стратегию для ошибки
        
        Args:
            error_key: Ключ ошибки
            strategy: Функция fallback стратегии
        """
        try:
            self.error_handling_service.register_fallback_strategy(error_key, strategy)
            self.logger.info(f"[{self.__class__.__name__}] Зарегистрирована fallback стратегия для: {error_key}")
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка регистрации fallback стратегии: {e}")
    
    def get_error_statistics(self) -> Dict[str, int]:
        """
        Возвращает статистику ошибок
        
        Returns:
            Dict[str, int]: Словарь с количеством ошибок по типам
        """
        try:
            return self.error_handling_service.get_error_statistics()
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка получения статистики ошибок: {e}")
            return {}
    
    def clear_error_statistics(self) -> None:
        """Очищает статистику ошибок"""
        try:
            self.error_handling_service.clear_error_statistics()
            self.logger.info(f"[{self.__class__.__name__}] Статистика ошибок очищена")
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка очистки статистики ошибок: {e}")
