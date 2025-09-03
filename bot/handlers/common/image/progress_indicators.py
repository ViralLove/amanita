"""
Система прогресс-индикаторов для fallback операций.
Обеспечивает уведомления пользователя о статусе операций.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from .fallback_strategies import DegradationLevel, FallbackResult


class ProgressStatus(Enum):
    """Статусы прогресса операций."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressType(Enum):
    """Типы прогресса."""
    DETERMINATE = "determinate"      # С определенным количеством шагов
    INDETERMINATE = "indeterminate"  # Без определенного количества шагов
    SPINNER = "spinner"              # Спиннер с анимацией


@dataclass
class ProgressStep:
    """Шаг прогресса."""
    id: str
    name: str
    description: str
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressInfo:
    """Информация о прогрессе операции."""
    operation_id: str
    operation_name: str
    status: ProgressStatus
    progress_type: ProgressType
    current_step: int
    total_steps: int
    progress_percent: float
    start_time: float
    elapsed_time: float
    estimated_remaining: Optional[float] = None
    steps: List[ProgressStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProgressCallback(ABC):
    """Абстрактный callback для уведомлений о прогрессе."""
    
    @abstractmethod
    async def on_progress_update(self, progress_info: ProgressInfo) -> None:
        """Вызывается при обновлении прогресса."""
        pass
    
    @abstractmethod
    async def on_step_complete(self, step: ProgressStep) -> None:
        """Вызывается при завершении шага."""
        pass
    
    @abstractmethod
    async def on_operation_complete(self, progress_info: ProgressInfo, result: Any) -> None:
        """Вызывается при завершении операции."""
        pass
    
    @abstractmethod
    async def on_operation_failed(self, progress_info: ProgressInfo, error: Exception) -> None:
        """Вызывается при ошибке операции."""
        pass


class LoggingProgressCallback(ProgressCallback):
    """Callback для логирования прогресса."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def on_progress_update(self, progress_info: ProgressInfo) -> None:
        """Логирует обновление прогресса."""
        self.logger.info(
            f"Progress: {progress_info.operation_name} - "
            f"{progress_info.progress_percent:.1f}% "
            f"({progress_info.current_step}/{progress_info.total_steps})"
        )
    
    async def on_step_complete(self, step: ProgressStep) -> None:
        """Логирует завершение шага."""
        if step.error:
            self.logger.error(f"Step failed: {step.name} - {step.error}")
        else:
            self.logger.info(f"Step completed: {step.name}")
    
    async def on_operation_complete(self, progress_info: ProgressInfo, result: Any) -> None:
        """Логирует завершение операции."""
        self.logger.info(
            f"Operation completed: {progress_info.operation_name} "
            f"in {progress_info.elapsed_time:.2f}s"
        )
    
    async def on_operation_failed(self, progress_info: ProgressInfo, error: Exception) -> None:
        """Логирует ошибку операции."""
        self.logger.error(
            f"Operation failed: {progress_info.operation_name} "
            f"after {progress_info.elapsed_time:.2f}s - {error}"
        )


class TelegramProgressCallback(ProgressCallback):
    """Callback для отправки уведомлений в Telegram."""
    
    def __init__(self, message_sender: Optional[Callable] = None):
        self.message_sender = message_sender
        self.logger = logging.getLogger(__name__)
    
    async def on_progress_update(self, progress_info: ProgressInfo) -> None:
        """Отправляет уведомление о прогрессе в Telegram."""
        if self.message_sender:
            try:
                message = self._format_progress_message(progress_info)
                await self.message_sender(message)
            except Exception as e:
                self.logger.error(f"Failed to send Telegram progress message: {e}")
        else:
            self.logger.info(f"Telegram progress: {progress_info.progress_percent:.1f}%")
    
    async def on_step_complete(self, step: ProgressStep) -> None:
        """Отправляет уведомление о завершении шага в Telegram."""
        if self.message_sender:
            try:
                message = self._format_step_message(step)
                await self.message_sender(message)
            except Exception as e:
                self.logger.error(f"Failed to send Telegram step message: {e}")
    
    async def on_operation_complete(self, progress_info: ProgressInfo, result: Any) -> None:
        """Отправляет уведомление о завершении операции в Telegram."""
        if self.message_sender:
            try:
                message = self._format_completion_message(progress_info, result)
                await self.message_sender(message)
            except Exception as e:
                self.logger.error(f"Failed to send Telegram completion message: {e}")
    
    async def on_operation_failed(self, progress_info: ProgressInfo, error: Exception) -> None:
        """Отправляет уведомление об ошибке операции в Telegram."""
        if self.message_sender:
            try:
                message = self._format_error_message(progress_info, error)
                await self.message_sender(message)
            except Exception as e:
                self.logger.error(f"Failed to send Telegram error message: {e}")
    
    def _format_progress_message(self, progress_info: ProgressInfo) -> str:
        """Форматирует сообщение о прогрессе."""
        emoji = "🔄" if progress_info.status == ProgressStatus.IN_PROGRESS else "✅"
        return (
            f"{emoji} **{progress_info.operation_name}**\n"
            f"Прогресс: {progress_info.progress_percent:.1f}% "
            f"({progress_info.current_step}/{progress_info.total_steps})\n"
            f"Время: {progress_info.elapsed_time:.1f}s"
        )
    
    def _format_step_message(self, step: ProgressStep) -> str:
        """Форматирует сообщение о шаге."""
        if step.error:
            return f"❌ **{step.name}** - Ошибка: {step.error}"
        else:
            return f"✅ **{step.name}** - Завершен"
    
    def _format_completion_message(self, progress_info: ProgressInfo, result: Any) -> str:
        """Форматирует сообщение о завершении."""
        return (
            f"🎉 **{progress_info.operation_name}** - Завершено!\n"
            f"Время выполнения: {progress_info.elapsed_time:.1f}s\n"
            f"Результат: {result}"
        )
    
    def _format_error_message(self, progress_info: ProgressInfo, error: Exception) -> str:
        """Форматирует сообщение об ошибке."""
        return (
            f"💥 **{progress_info.operation_name}** - Ошибка!\n"
            f"Время выполнения: {progress_info.elapsed_time:.1f}s\n"
            f"Ошибка: {error}"
        )


class ProgressManager:
    """Менеджер прогресса операций."""
    
    def __init__(self, callbacks: Optional[List[ProgressCallback]] = None):
        self.callbacks = callbacks or [LoggingProgressCallback()]
        self.logger = logging.getLogger(__name__)
        self.active_operations: Dict[str, ProgressInfo] = {}
    
    def start_operation(
        self,
        operation_id: str,
        operation_name: str,
        total_steps: int,
        progress_type: ProgressType = ProgressType.DETERMINATE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProgressInfo:
        """Начинает отслеживание операции."""
        progress_info = ProgressInfo(
            operation_id=operation_id,
            operation_name=operation_name,
            status=ProgressStatus.IN_PROGRESS,
            progress_type=progress_type,
            current_step=0,
            total_steps=total_steps,
            progress_percent=0.0,
            start_time=time.time(),
            elapsed_time=0.0,
            steps=[],
            metadata=metadata or {}
        )
        
        self.active_operations[operation_id] = progress_info
        self.logger.info(f"Started progress tracking: {operation_name} ({total_steps} steps)")
        
        return progress_info
    
    def add_step(
        self,
        operation_id: str,
        step_id: str,
        step_name: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProgressStep:
        """Добавляет шаг к операции."""
        if operation_id not in self.active_operations:
            raise ValueError(f"Operation {operation_id} not found")
        
        progress_info = self.active_operations[operation_id]
        step = ProgressStep(
            id=step_id,
            name=step_name,
            description=description,
            metadata=metadata or {}
        )
        
        progress_info.steps.append(step)
        return step
    
    def start_step(self, operation_id: str, step_id: str) -> None:
        """Начинает выполнение шага."""
        if operation_id not in self.active_operations:
            raise ValueError(f"Operation {operation_id} not found")
        
        progress_info = self.active_operations[operation_id]
        step = self._find_step(progress_info, step_id)
        
        if step:
            step.status = ProgressStatus.IN_PROGRESS
            step.start_time = time.time()
            self.logger.info(f"Started step: {step.name}")
    
    def complete_step(self, operation_id: str, step_id: str, error: Optional[str] = None) -> None:
        """Завершает выполнение шага."""
        if operation_id not in self.active_operations:
            raise ValueError(f"Operation {operation_id} not found")
        
        progress_info = self.active_operations[operation_id]
        step = self._find_step(progress_info, step_id)
        
        if step:
            step.status = ProgressStatus.COMPLETED if not error else ProgressStatus.FAILED
            step.end_time = time.time()
            step.error = error
            
            # Обновляем прогресс
            progress_info.current_step += 1
            progress_info.progress_percent = (progress_info.current_step / progress_info.total_steps) * 100
            progress_info.elapsed_time = time.time() - progress_info.start_time
            
            # Уведомляем callbacks (только если есть event loop)
            try:
                asyncio.create_task(self._notify_step_complete(step))
                asyncio.create_task(self._notify_progress_update(progress_info))
            except RuntimeError:
                # Нет event loop, просто логируем
                self.logger.debug("No event loop, skipping async notifications")
            
            self.logger.info(f"Completed step: {step.name}")
    
    def fail_step(self, operation_id: str, step_id: str, error: str) -> None:
        """Отмечает шаг как неудачный."""
        self.complete_step(operation_id, step_id, error)
    
    def complete_operation(self, operation_id: str, result: Any) -> None:
        """Завершает операцию."""
        if operation_id not in self.active_operations:
            raise ValueError(f"Operation {operation_id} not found")
        
        progress_info = self.active_operations[operation_id]
        progress_info.status = ProgressStatus.COMPLETED
        progress_info.elapsed_time = time.time() - progress_info.start_time
        progress_info.progress_percent = 100.0
        
        # Уведомляем callbacks (только если есть event loop)
        try:
            asyncio.create_task(self._notify_operation_complete(progress_info, result))
        except RuntimeError:
            # Нет event loop, просто логируем
            self.logger.debug("No event loop, skipping async notifications")
        
        # Удаляем из активных операций
        del self.active_operations[operation_id]
        
        self.logger.info(f"Completed operation: {progress_info.operation_name}")
    
    def fail_operation(self, operation_id: str, error: Exception) -> None:
        """Отмечает операцию как неудачную."""
        if operation_id not in self.active_operations:
            raise ValueError(f"Operation {operation_id} not found")
        
        progress_info = self.active_operations[operation_id]
        progress_info.status = ProgressStatus.FAILED
        progress_info.elapsed_time = time.time() - progress_info.start_time
        
        # Уведомляем callbacks (только если есть event loop)
        try:
            asyncio.create_task(self._notify_operation_failed(progress_info, error))
        except RuntimeError:
            # Нет event loop, просто логируем
            self.logger.debug("No event loop, skipping async notifications")
        
        # Удаляем из активных операций
        del self.active_operations[operation_id]
        
        self.logger.error(f"Failed operation: {progress_info.operation_name} - {error}")
    
    def get_progress(self, operation_id: str) -> Optional[ProgressInfo]:
        """Получает информацию о прогрессе операции."""
        return self.active_operations.get(operation_id)
    
    def get_all_progress(self) -> List[ProgressInfo]:
        """Получает информацию о всех активных операциях."""
        return list(self.active_operations.values())
    
    def _find_step(self, progress_info: ProgressInfo, step_id: str) -> Optional[ProgressStep]:
        """Находит шаг по ID."""
        for step in progress_info.steps:
            if step.id == step_id:
                return step
        return None
    
    async def _notify_progress_update(self, progress_info: ProgressInfo) -> None:
        """Уведомляет callbacks об обновлении прогресса."""
        for callback in self.callbacks:
            try:
                await callback.on_progress_update(progress_info)
            except Exception as e:
                self.logger.error(f"Callback error in on_progress_update: {e}")
    
    async def _notify_step_complete(self, step: ProgressStep) -> None:
        """Уведомляет callbacks о завершении шага."""
        for callback in self.callbacks:
            try:
                await callback.on_step_complete(step)
            except Exception as e:
                self.logger.error(f"Callback error in on_step_complete: {e}")
    
    async def _notify_operation_complete(self, progress_info: ProgressInfo, result: Any) -> None:
        """Уведомляет callbacks о завершении операции."""
        for callback in self.callbacks:
            try:
                await callback.on_operation_complete(progress_info, result)
            except Exception as e:
                self.logger.error(f"Callback error in on_operation_complete: {e}")
    
    async def _notify_operation_failed(self, progress_info: ProgressInfo, error: Exception) -> None:
        """Уведомляет callbacks об ошибке операции."""
        for callback in self.callbacks:
            try:
                await callback.on_operation_failed(progress_info, error)
            except Exception as e:
                self.logger.error(f"Callback error in on_operation_failed: {e}")


# Глобальный экземпляр менеджера прогресса
_progress_manager = ProgressManager()


def get_progress_manager() -> ProgressManager:
    """
    Получает глобальный экземпляр менеджера прогресса.
    
    Returns:
        ProgressManager: Глобальный менеджер прогресса
    """
    return _progress_manager


def add_progress_callback(callback: ProgressCallback) -> None:
    """
    Добавляет callback для уведомлений о прогрессе.
    
    Args:
        callback: Callback для добавления
    """
    _progress_manager.callbacks.append(callback)


def remove_progress_callback(callback: ProgressCallback) -> bool:
    """
    Удаляет callback для уведомлений о прогрессе.
    
    Args:
        callback: Callback для удаления
        
    Returns:
        bool: True если callback был удален
    """
    try:
        _progress_manager.callbacks.remove(callback)
        return True
    except ValueError:
        return False
