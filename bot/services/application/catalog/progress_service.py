"""
Сервис для отображения прогресса операций.
Содержит логику создания и обновления сообщений о прогрессе.
"""

import logging
from typing import Dict, Any, Optional, List
from aiogram.types import Message
from services.common.localization import Localization

logger = logging.getLogger(__name__)


class ProgressService:
    """Сервис для отображения прогресса операций"""
    
    def __init__(self):
        """Инициализация сервиса прогресса"""
        self.logger = logging.getLogger(__name__)
        self.active_progress_messages: Dict[str, Message] = {}
        self.logger.info("[ProgressService] Инициализирован")
    
    async def create_progress_message(self, message: Message, operation: str, loc: Localization) -> Optional[Message]:
        """
        Создает сообщение о прогрессе операции
        
        Args:
            message: Исходное сообщение
            operation: Название операции
            loc: Объект локализации
            
        Returns:
            Optional[Message]: Сообщение о прогрессе или None
        """
        try:
            self.logger.info(f"[ProgressService] Создание сообщения о прогрессе для операции: {operation}")
            
            progress_text = self._get_progress_text(operation, 0, loc)
            progress_message = await message.answer(progress_text)
            
            # Сохраняем сообщение для последующего обновления
            self.active_progress_messages[operation] = progress_message
            
            self.logger.info(f"[ProgressService] Сообщение о прогрессе создано для операции: {operation}")
            return progress_message
            
        except Exception as e:
            self.logger.error(f"[ProgressService] Ошибка создания сообщения о прогрессе: {e}")
            return None
    
    async def update_progress(self, operation: str, progress: int, total: int, loc: Localization, 
                            additional_info: str = "") -> bool:
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
            if operation not in self.active_progress_messages:
                self.logger.warning(f"[ProgressService] Сообщение о прогрессе для операции {operation} не найдено")
                return False
            
            progress_message = self.active_progress_messages[operation]
            progress_text = self._get_progress_text(operation, progress, total, loc, additional_info)
            
            await progress_message.edit_text(progress_text)
            
            self.logger.debug(f"[ProgressService] Прогресс обновлен: {progress}/{total} для операции {operation}")
            return True
            
        except Exception as e:
            self.logger.error(f"[ProgressService] Ошибка обновления прогресса: {e}")
            return False
    
    async def complete_progress(self, operation: str, loc: Localization, success: bool = True, 
                              final_message: str = "") -> bool:
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
            if operation not in self.active_progress_messages:
                self.logger.warning(f"[ProgressService] Сообщение о прогрессе для операции {operation} не найдено")
                return False
            
            progress_message = self.active_progress_messages[operation]
            
            if success:
                completion_text = final_message or loc.t('progress.completed', '✅ Операция завершена успешно!')
            else:
                completion_text = final_message or loc.t('progress.failed', '❌ Операция завершилась с ошибкой')
            
            await progress_message.edit_text(completion_text)
            
            # Удаляем из активных сообщений
            del self.active_progress_messages[operation]
            
            self.logger.info(f"[ProgressService] Прогресс завершен для операции: {operation}")
            return True
            
        except Exception as e:
            self.logger.error(f"[ProgressService] Ошибка завершения прогресса: {e}")
            return False
    
    def _get_progress_text(self, operation: str, progress: int, total: int = 0, 
                          loc: Localization = None, additional_info: str = "") -> str:
        """
        Создает текст сообщения о прогрессе
        
        Args:
            operation: Название операции
            progress: Текущий прогресс
            total: Общее количество
            loc: Объект локализации
            additional_info: Дополнительная информация
            
        Returns:
            str: Текст сообщения о прогрессе
        """
        try:
            if not loc:
                return f"⏳ {operation}... {progress}"
            
            # Создаем прогресс-бар
            if total > 0:
                percentage = int((progress / total) * 100)
                progress_bar = self._create_progress_bar(progress, total)
                progress_text = f"{progress_bar} {percentage}%"
            else:
                progress_text = f"⏳ {progress}..."
            
            # Базовое сообщение
            base_message = loc.t(f'progress.{operation}', f'⏳ {operation}...')
            
            # Добавляем дополнительную информацию
            if additional_info:
                return f"{base_message}\n{progress_text}\n{additional_info}"
            else:
                return f"{base_message}\n{progress_text}"
                
        except Exception as e:
            self.logger.error(f"[ProgressService] Ошибка создания текста прогресса: {e}")
            return f"⏳ {operation}... {progress}"
    
    def _create_progress_bar(self, progress: int, total: int, length: int = 10) -> str:
        """
        Создает визуальный прогресс-бар
        
        Args:
            progress: Текущий прогресс
            total: Общее количество
            length: Длина прогресс-бара
            
        Returns:
            str: Визуальный прогресс-бар
        """
        try:
            if total == 0:
                return "█" * length
            
            filled = int((progress / total) * length)
            empty = length - filled
            
            return "█" * filled + "░" * empty
            
        except Exception as e:
            self.logger.error(f"[ProgressService] Ошибка создания прогресс-бара: {e}")
            return "█" * length
    
    async def cleanup_progress_messages(self) -> None:
        """
        Очищает все активные сообщения о прогрессе
        """
        try:
            self.logger.info(f"[ProgressService] Очистка {len(self.active_progress_messages)} активных сообщений о прогрессе")
            
            for operation, message in self.active_progress_messages.items():
                try:
                    await message.delete()
                    self.logger.debug(f"[ProgressService] Удалено сообщение о прогрессе для операции: {operation}")
                except Exception as e:
                    self.logger.warning(f"[ProgressService] Ошибка удаления сообщения о прогрессе для операции {operation}: {e}")
            
            self.active_progress_messages.clear()
            self.logger.info("[ProgressService] Все сообщения о прогрессе очищены")
            
        except Exception as e:
            self.logger.error(f"[ProgressService] Ошибка очистки сообщений о прогрессе: {e}")
    
    def get_active_operations(self) -> List[str]:
        """
        Возвращает список активных операций
        
        Returns:
            List[str]: Список названий активных операций
        """
        return list(self.active_progress_messages.keys())
