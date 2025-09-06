"""
Миксин для отображения прогресса в обработчиках каталога.
Содержит логику создания и управления сообщениями о прогрессе.
"""

import logging
from typing import Optional, Dict, Any
from aiogram.types import CallbackQuery, Message
from services.common.localization import Localization
from services.application.catalog.progress_service import ProgressService

logger = logging.getLogger(__name__)


class ProgressMixin:
    """Миксин для отображения прогресса в обработчиках каталога"""
    
    def __init__(self):
        """Инициализация миксина прогресса"""
        self.progress_service = ProgressService()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"[{self.__class__.__name__}] ProgressMixin инициализирован")
    
    async def create_progress_message(self, callback: CallbackQuery, operation: str, 
                                    loc: Localization) -> Optional[Message]:
        """
        Создает сообщение о прогрессе операции
        
        Args:
            callback: Callback запрос от пользователя
            operation: Название операции
            loc: Объект локализации
            
        Returns:
            Optional[Message]: Сообщение о прогрессе или None
        """
        try:
            self.logger.info(f"[{self.__class__.__name__}] Создание сообщения о прогрессе для операции: {operation}")
            
            progress_message = await self.progress_service.create_progress_message(
                callback.message, operation, loc
            )
            
            if progress_message:
                self.logger.info(f"[{self.__class__.__name__}] Сообщение о прогрессе создано для операции: {operation}")
            else:
                self.logger.warning(f"[{self.__class__.__name__}] Не удалось создать сообщение о прогрессе для операции: {operation}")
            
            return progress_message
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка создания сообщения о прогрессе: {e}")
            return None
    
    async def update_progress(self, operation: str, progress: int, total: int, 
                            loc: Localization, additional_info: str = "") -> bool:
        """
        Обновляет сообщение о прогрессе
        
        Args:
            operation: Название операции
            progress: Текущий прогресс
            total: Общее количество
            loc: Объект локализации
            additional_info: Дополнительная информация
            
        Returns:
            bool: True если обновление прошло успешно
        """
        try:
            self.logger.debug(f"[{self.__class__.__name__}] Обновление прогресса: {progress}/{total} для операции {operation}")
            
            success = await self.progress_service.update_progress(
                operation, progress, total, loc, additional_info
            )
            
            if success:
                self.logger.debug(f"[{self.__class__.__name__}] Прогресс обновлен успешно для операции: {operation}")
            else:
                self.logger.warning(f"[{self.__class__.__name__}] Не удалось обновить прогресс для операции: {operation}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка обновления прогресса: {e}")
            return False
    
    async def complete_progress(self, operation: str, loc: Localization, 
                              success: bool = True, final_message: str = "") -> bool:
        """
        Завершает отображение прогресса
        
        Args:
            operation: Название операции
            loc: Объект локализации
            success: Успешность операции
            final_message: Финальное сообщение
            
        Returns:
            bool: True если завершение прошло успешно
        """
        try:
            self.logger.info(f"[{self.__class__.__name__}] Завершение прогресса для операции: {operation} (успех: {success})")
            
            completion_success = await self.progress_service.complete_progress(
                operation, loc, success, final_message
            )
            
            if completion_success:
                self.logger.info(f"[{self.__class__.__name__}] Прогресс завершен успешно для операции: {operation}")
            else:
                self.logger.warning(f"[{self.__class__.__name__}] Не удалось завершить прогресс для операции: {operation}")
            
            return completion_success
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка завершения прогресса: {e}")
            return False
    
    async def cleanup_progress(self, operation: Optional[str] = None) -> None:
        """
        Очищает сообщения о прогрессе
        
        Args:
            operation: Название операции для очистки (если None - очищает все)
        """
        try:
            if operation:
                self.logger.info(f"[{self.__class__.__name__}] Очистка прогресса для операции: {operation}")
                # TODO: Добавить метод для очистки конкретной операции в ProgressService
            else:
                self.logger.info(f"[{self.__class__.__name__}] Очистка всех сообщений о прогрессе")
                await self.progress_service.cleanup_progress_messages()
                
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка очистки прогресса: {e}")
    
    def get_active_operations(self) -> list:
        """
        Возвращает список активных операций
        
        Returns:
            list: Список названий активных операций
        """
        try:
            return self.progress_service.get_active_operations()
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка получения активных операций: {e}")
            return []
    
    def is_operation_active(self, operation: str) -> bool:
        """
        Проверяет, активна ли операция
        
        Args:
            operation: Название операции
            
        Returns:
            bool: True если операция активна
        """
        try:
            active_operations = self.get_active_operations()
            return operation in active_operations
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка проверки активности операции: {e}")
            return False
    
    async def create_simple_progress(self, callback: CallbackQuery, operation: str, 
                                   loc: Localization) -> Optional[Message]:
        """
        Создает простое сообщение о прогрессе без детального отслеживания
        
        Args:
            callback: Callback запрос от пользователя
            operation: Название операции
            loc: Объект локализации
            
        Returns:
            Optional[Message]: Сообщение о прогрессе или None
        """
        try:
            progress_text = loc.t(f'progress.{operation}', f'⏳ {operation}...')
            progress_message = await callback.message.answer(progress_text)
            
            self.logger.info(f"[{self.__class__.__name__}] Создано простое сообщение о прогрессе для операции: {operation}")
            return progress_message
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка создания простого сообщения о прогрессе: {e}")
            return None
    
    async def update_simple_progress(self, message: Message, operation: str, 
                                   loc: Localization, progress: int, total: int) -> bool:
        """
        Обновляет простое сообщение о прогрессе
        
        Args:
            message: Сообщение для обновления
            operation: Название операции
            loc: Объект локализации
            progress: Текущий прогресс
            total: Общее количество
            
        Returns:
            bool: True если обновление прошло успешно
        """
        try:
            percentage = int((progress / total) * 100) if total > 0 else 0
            progress_bar = "█" * int((progress / total) * 10) + "░" * (10 - int((progress / total) * 10)) if total > 0 else "░" * 10
            
            progress_text = f"{loc.t(f'progress.{operation}', f'⏳ {operation}...')}\n{progress_bar} {percentage}%"
            
            await message.edit_text(progress_text)
            
            self.logger.debug(f"[{self.__class__.__name__}] Обновлено простое сообщение о прогрессе: {progress}/{total}")
            return True
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка обновления простого сообщения о прогрессе: {e}")
            return False
    
    async def complete_simple_progress(self, message: Message, operation: str, 
                                     loc: Localization, success: bool = True) -> bool:
        """
        Завершает простое сообщение о прогрессе
        
        Args:
            message: Сообщение для завершения
            operation: Название операции
            loc: Объект локализации
            success: Успешность операции
            
        Returns:
            bool: True если завершение прошло успешно
        """
        try:
            if success:
                completion_text = loc.t(f'progress.{operation}.completed', f'✅ {operation} завершено успешно!')
            else:
                completion_text = loc.t(f'progress.{operation}.failed', f'❌ {operation} завершилось с ошибкой')
            
            await message.edit_text(completion_text)
            
            self.logger.info(f"[{self.__class__.__name__}] Завершено простое сообщение о прогрессе для операции: {operation}")
            return True
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка завершения простого сообщения о прогрессе: {e}")
            return False
