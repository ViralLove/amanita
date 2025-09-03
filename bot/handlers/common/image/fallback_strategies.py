"""
Улучшенные fallback стратегии для ImageService.
Обеспечивают множественные варианты восстановления с graceful degradation.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from .exceptions import ErrorCategory, ErrorSeverity, ImageDownloadError
from .error_metrics import record_error, get_error_metrics
from .error_codes import get_error_code_info


class DegradationLevel(Enum):
    """Уровни graceful degradation."""
    FULL_FUNCTIONALITY = "full"           # Полная функциональность
    HIGH_QUALITY = "high"                 # Высокое качество (без некоторых функций)
    MEDIUM_QUALITY = "medium"             # Среднее качество (основные функции)
    BASIC_FUNCTIONALITY = "basic"         # Базовая функциональность
    TEXT_ONLY = "text_only"               # Только текст
    ERROR_MESSAGE = "error_message"       # Только сообщение об ошибке


@dataclass
class FallbackResult:
    """Результат выполнения fallback стратегии."""
    success: bool
    data: Any
    degradation_level: DegradationLevel
    message: str
    fallback_strategy: str
    execution_time: float
    retry_count: int = 0


class ProgressTracker:
    """Отслеживание прогресса fallback операций."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.start_time = None
        self.current_step = 0
        self.total_steps = 0
        self.step_messages = []
    
    def start_operation(self, total_steps: int, operation_name: str):
        """Начинает отслеживание операции."""
        self.start_time = time.time()
        self.current_step = 0
        self.total_steps = total_steps
        self.step_messages = []
        self.logger.info(f"Starting fallback operation: {operation_name} ({total_steps} steps)")
    
    def update_progress(self, step_message: str, step_number: Optional[int] = None):
        """Обновляет прогресс операции."""
        if step_number is not None:
            self.current_step = step_number
        else:
            self.current_step += 1
        
        self.step_messages.append(step_message)
        progress_percent = (self.current_step / self.total_steps) * 100
        
        self.logger.info(f"Progress: {progress_percent:.1f}% - {step_message}")
    
    def get_progress_info(self) -> Dict[str, Any]:
        """Получает информацию о прогрессе."""
        if not self.start_time:
            return {"status": "not_started"}
        
        elapsed_time = time.time() - self.start_time
        progress_percent = (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0
        
        return {
            "status": "in_progress",
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress_percent": progress_percent,
            "elapsed_time": elapsed_time,
            "step_messages": self.step_messages
        }


class UserNotifier:
    """Уведомления пользователя о статусе операций."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def notify_progress(self, message: str, progress_info: Dict[str, Any]) -> None:
        """Уведомляет о прогрессе операции."""
        # В реальной реализации здесь будет отправка сообщения пользователю
        self.logger.info(f"User notification: {message} - Progress: {progress_info['progress_percent']:.1f}%")
    
    async def notify_fallback_start(self, strategy_name: str, reason: str) -> None:
        """Уведомляет о начале fallback стратегии."""
        message = f"🔄 Запуск fallback стратегии: {strategy_name} (причина: {reason})"
        self.logger.info(f"Fallback started: {strategy_name} - {reason}")
        # Здесь можно добавить отправку уведомления пользователю
    
    async def notify_fallback_success(self, strategy_name: str, result: str) -> None:
        """Уведомляет об успешном выполнении fallback."""
        message = f"✅ Fallback успешен: {strategy_name} - {result}"
        self.logger.info(f"Fallback succeeded: {strategy_name} - {result}")
        # Здесь можно добавить отправку уведомления пользователю
    
    async def notify_fallback_failure(self, strategy_name: str, error: str) -> None:
        """Уведомляет о неудачном выполнении fallback."""
        message = f"❌ Fallback не удался: {strategy_name} - {error}"
        self.logger.warning(f"Fallback failed: {strategy_name} - {error}")
        # Здесь можно добавить отправку уведомления пользователю


class EnhancedPlaceholderImageFallbackStrategy:
    """Улучшенная стратегия fallback на placeholder изображения."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.placeholder_urls = self._get_placeholder_urls()
        self.progress_tracker = ProgressTracker()
        self.user_notifier = UserNotifier()
    
    def _get_placeholder_urls(self) -> List[Dict[str, Any]]:
        """Получает список placeholder URL с метаданными."""
        return [
            {
                "url": "https://via.placeholder.com/400x300/cccccc/666666?text=Image+Not+Available",
                "width": 400,
                "height": 300,
                "quality": "high",
                "fallback_type": "external_service"
            },
            {
                "url": "https://via.placeholder.com/300x200/eeeeee/999999?text=No+Image",
                "width": 300,
                "height": 200,
                "quality": "medium",
                "fallback_type": "external_service"
            },
            {
                "url": "https://via.placeholder.com/200x150/f5f5f5/cccccc?text=Image+Error",
                "width": 200,
                "height": 150,
                "quality": "low",
                "fallback_type": "external_service"
            }
        ]
    
    async def execute(self, context: Dict[str, Any]) -> FallbackResult:
        """Выполняет fallback на placeholder изображения."""
        start_time = time.time()
        
        try:
            await self.user_notifier.notify_fallback_start(
                "Enhanced Placeholder Images",
                "Ошибка загрузки оригинальных изображений"
            )
            
            self.progress_tracker.start_operation(3, "Placeholder Image Fallback")
            
            # Шаг 1: Валидация placeholder URL
            self.progress_tracker.update_progress("Валидация placeholder URL", 1)
            valid_urls = await self._validate_placeholder_urls()
            
            if not valid_urls:
                raise ValueError("No valid placeholder URLs available")
            
            # Шаг 2: Выбор лучшего placeholder
            self.progress_tracker.update_progress("Выбор оптимального placeholder", 2)
            best_placeholder = self._select_best_placeholder(valid_urls, context)
            
            # Шаг 3: Подготовка результата
            self.progress_tracker.update_progress("Подготовка результата", 3)
            result_data = {
                "urls": [best_placeholder["url"]],
                "width": best_placeholder["width"],
                "height": best_placeholder["height"],
                "quality": best_placeholder["quality"],
                "fallback_type": "placeholder",
                "original_error": context.get("error", "Unknown error")
            }
            
            execution_time = time.time() - start_time
            
            await self.user_notifier.notify_fallback_success(
                "Enhanced Placeholder Images",
                f"Placeholder {best_placeholder['width']}x{best_placeholder['height']} загружен"
            )
            
            # Записываем метрику успешного fallback
            record_error(
                "FALLBACK_PLACEHOLDER_SUCCESS",
                ErrorCategory.VALIDATION,
                ErrorSeverity.WARNING,
                context,
                fallback_used=True
            )
            
            return FallbackResult(
                success=True,
                data=result_data,
                degradation_level=DegradationLevel.MEDIUM_QUALITY,
                message="Placeholder изображение успешно загружено",
                fallback_strategy="enhanced_placeholder",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            await self.user_notifier.notify_fallback_failure(
                "Enhanced Placeholder Images",
                str(e)
            )
            
            # Записываем метрику неудачного fallback
            record_error(
                "FALLBACK_PLACEHOLDER_FAILURE",
                ErrorCategory.VALIDATION,
                ErrorSeverity.ERROR,
                context,
                fallback_used=True
            )
            
            return FallbackResult(
                success=False,
                data=None,
                degradation_level=DegradationLevel.TEXT_ONLY,
                message=f"Placeholder fallback не удался: {e}",
                fallback_strategy="enhanced_placeholder",
                execution_time=execution_time
            )
    
    async def _validate_placeholder_urls(self) -> List[Dict[str, Any]]:
        """Валидирует доступность placeholder URL."""
        valid_urls = []
        
        for placeholder in self.placeholder_urls:
            try:
                # В реальной реализации здесь будет проверка доступности URL
                # Пока просто добавляем все
                valid_urls.append(placeholder)
            except Exception as e:
                self.logger.warning(f"Invalid placeholder URL {placeholder['url']}: {e}")
        
        return valid_urls
    
    def _select_best_placeholder(self, valid_urls: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """Выбирает лучший placeholder на основе контекста."""
        # Простая логика выбора - берем первый доступный
        # В реальной реализации здесь может быть более сложная логика
        return valid_urls[0]


class AlternativeURLRetryStrategy:
    """Стратегия retry с альтернативными URL."""
    
    def __init__(self, max_retry_attempts: int = 3):
        self.max_retry_attempts = max_retry_attempts
        self.logger = logging.getLogger(__name__)
        self.progress_tracker = ProgressTracker()
        self.user_notifier = UserNotifier()
    
    async def execute(self, context: Dict[str, Any]) -> FallbackResult:
        """Выполняет retry с альтернативными URL."""
        start_time = time.time()
        
        try:
            await self.user_notifier.notify_fallback_start(
                "Alternative URL Retry",
                "Попытка загрузки с альтернативных источников"
            )
            
            original_urls = context.get("urls", [])
            if not original_urls:
                raise ValueError("No URLs provided for retry")
            
            self.progress_tracker.start_operation(
                len(original_urls) * self.max_retry_attempts,
                "Alternative URL Retry"
            )
            
            # Генерируем альтернативные URL
            alternative_urls = self._generate_alternative_urls(original_urls)
            
            # Пытаемся загрузить с альтернативных URL
            for attempt in range(self.max_retry_attempts):
                for alt_url in alternative_urls:
                    try:
                        self.progress_tracker.update_progress(
                            f"Попытка {attempt + 1}/{self.max_retry_attempts}: {alt_url}"
                        )
                        
                        # В реальной реализации здесь будет попытка загрузки
                        # Пока просто симулируем успех
                        if attempt == 1:  # Вторая попытка успешна
                            execution_time = time.time() - start_time
                            
                            await self.user_notifier.notify_fallback_success(
                                "Alternative URL Retry",
                                f"Успешная загрузка с {alt_url}"
                            )
                            
                            # Записываем метрику успешного retry
                            record_error(
                                "FALLBACK_ALTERNATIVE_URL_SUCCESS",
                                ErrorCategory.NETWORK,
                                ErrorSeverity.WARNING,
                                context,
                                retry_count=attempt + 1,
                                fallback_used=True
                            )
                            
                            return FallbackResult(
                                success=True,
                                data={"urls": [alt_url], "source": "alternative_url"},
                                degradation_level=DegradationLevel.HIGH_QUALITY,
                                message=f"Изображение загружено с альтернативного URL: {alt_url}",
                                fallback_strategy="alternative_url_retry",
                                execution_time=execution_time,
                                retry_count=attempt + 1
                            )
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to load from {alt_url}: {e}")
                        continue
            
            # Все попытки исчерпаны
            raise Exception("All alternative URL attempts failed")
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            await self.user_notifier.notify_fallback_failure(
                "Alternative URL Retry",
                str(e)
            )
            
            # Записываем метрику неудачного retry
            record_error(
                "FALLBACK_ALTERNATIVE_URL_FAILURE",
                ErrorCategory.NETWORK,
                ErrorSeverity.ERROR,
                context,
                fallback_used=True
            )
            
            return FallbackResult(
                success=False,
                data=None,
                degradation_level=DegradationLevel.MEDIUM_QUALITY,
                message=f"Alternative URL retry не удался: {e}",
                fallback_strategy="alternative_url_retry",
                execution_time=execution_time
            )
    
    def _generate_alternative_urls(self, original_urls: List[str]) -> List[str]:
        """Генерирует альтернативные URL на основе оригинальных."""
        alternative_urls = []
        
        for url in original_urls:
            # Простая логика генерации альтернативных URL
            # В реальной реализации здесь может быть более сложная логика
            
            # Пример: замена домена
            if "example.com" in url:
                alt_url = url.replace("example.com", "cdn.example.com")
                alternative_urls.append(alt_url)
            
            # Пример: замена протокола
            if url.startswith("http://"):
                alt_url = url.replace("http://", "https://")
                alternative_urls.append(alt_url)
            
            # Добавляем оригинальный URL как fallback
            alternative_urls.append(url)
        
        return alternative_urls


class GracefulDegradationStrategy:
    """Стратегия graceful degradation по уровням."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.progress_tracker = ProgressTracker()
        self.user_notifier = UserNotifier()
        self.degradation_levels = self._define_degradation_levels()
    
    def _define_degradation_levels(self) -> List[Dict[str, Any]]:
        """Определяет уровни graceful degradation."""
        return [
            {
                "level": DegradationLevel.FULL_FUNCTIONALITY,
                "description": "Полная функциональность",
                "features": ["high_quality_images", "full_metadata", "interactive_elements"],
                "fallback_strategies": []
            },
            {
                "level": DegradationLevel.HIGH_QUALITY,
                "description": "Высокое качество",
                "features": ["medium_quality_images", "full_metadata", "basic_interaction"],
                "fallback_strategies": ["alternative_url_retry"]
            },
            {
                "level": DegradationLevel.MEDIUM_QUALITY,
                "description": "Среднее качество",
                "features": ["placeholder_images", "basic_metadata", "text_only"],
                "fallback_strategies": ["enhanced_placeholder", "alternative_url_retry"]
            },
            {
                "level": DegradationLevel.BASIC_FUNCTIONALITY,
                "description": "Базовая функциональность",
                "features": ["text_description", "basic_info"],
                "fallback_strategies": ["text_fallback", "enhanced_placeholder"]
            },
            {
                "level": DegradationLevel.TEXT_ONLY,
                "description": "Только текст",
                "features": ["text_description"],
                "fallback_strategies": ["text_fallback"]
            },
            {
                "level": DegradationLevel.ERROR_MESSAGE,
                "description": "Только сообщение об ошибке",
                "features": ["error_message"],
                "fallback_strategies": []
            }
        ]
    
    async def execute(self, context: Dict[str, Any]) -> FallbackResult:
        """Выполняет graceful degradation по уровням."""
        start_time = time.time()
        
        try:
            await self.user_notifier.notify_fallback_start(
                "Graceful Degradation",
                "Пошаговое снижение функциональности"
            )
            
            error_severity = context.get("error_severity", ErrorSeverity.ERROR)
            current_level = self._determine_initial_level(error_severity)
            
            self.progress_tracker.start_operation(
                len(self.degradation_levels),
                "Graceful Degradation"
            )
            
            # Пытаемся выполнить fallback на каждом уровне
            for i, level_info in enumerate(self.degradation_levels):
                if level_info["level"].value < current_level.value:
                    continue
                
                self.progress_tracker.update_progress(
                    f"Попытка уровня: {level_info['description']}", i + 1
                )
                
                # Пытаемся выполнить fallback стратегии для этого уровня
                result = await self._try_level_fallback(level_info, context)
                
                if result.success:
                    execution_time = time.time() - start_time
                    
                    await self.user_notifier.notify_fallback_success(
                        "Graceful Degradation",
                        f"Успешное восстановление на уровне: {level_info['description']}"
                    )
                    
                    # Записываем метрику успешного graceful degradation
                    record_error(
                        "FALLBACK_GRACEFUL_DEGRADATION_SUCCESS",
                        ErrorCategory.VALIDATION,
                        ErrorSeverity.WARNING,
                        context,
                        fallback_used=True
                    )
                    
                    return FallbackResult(
                        success=True,
                        data=result.data,
                        degradation_level=level_info["level"],
                        message=f"Функциональность восстановлена на уровне: {level_info['description']}",
                        fallback_strategy="graceful_degradation",
                        execution_time=execution_time
                    )
            
            # Ни один уровень не сработал
            raise Exception("All degradation levels failed")
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            await self.user_notifier.notify_fallback_failure(
                "Graceful Degradation",
                str(e)
            )
            
            # Записываем метрику неудачного graceful degradation
            record_error(
                "FALLBACK_GRACEFUL_DEGRADATION_FAILURE",
                ErrorCategory.VALIDATION,
                ErrorSeverity.ERROR,
                context,
                fallback_used=True
            )
            
            return FallbackResult(
                success=False,
                data=None,
                degradation_level=DegradationLevel.ERROR_MESSAGE,
                message=f"Graceful degradation не удался: {e}",
                fallback_strategy="graceful_degradation",
                execution_time=execution_time
            )
    
    def _determine_initial_level(self, error_severity: ErrorSeverity) -> DegradationLevel:
        """Определяет начальный уровень degradation на основе серьезности ошибки."""
        if error_severity == ErrorSeverity.CRITICAL:
            return DegradationLevel.TEXT_ONLY
        elif error_severity == ErrorSeverity.ERROR:
            return DegradationLevel.BASIC_FUNCTIONALITY
        elif error_severity == ErrorSeverity.WARNING:
            return DegradationLevel.MEDIUM_QUALITY
        else:
            return DegradationLevel.FULL_FUNCTIONALITY
    
    async def _try_level_fallback(self, level_info: Dict[str, Any], context: Dict[str, Any]) -> FallbackResult:
        """Пытается выполнить fallback для конкретного уровня."""
        # В реальной реализации здесь будет попытка выполнения fallback стратегий
        # Пока просто симулируем успех для средних уровней
        if level_info["level"] in [DegradationLevel.MEDIUM_QUALITY, DegradationLevel.BASIC_FUNCTIONALITY]:
            return FallbackResult(
                success=True,
                data={"level": level_info["level"].value, "features": level_info["features"]},
                degradation_level=level_info["level"],
                message=f"Уровень {level_info['description']} доступен",
                fallback_strategy="graceful_degradation",
                execution_time=0.1
            )
        
        return FallbackResult(
            success=False,
            data=None,
            degradation_level=level_info["level"],
            message=f"Уровень {level_info['description']} недоступен",
            fallback_strategy="graceful_degradation",
            execution_time=0.1
        )
