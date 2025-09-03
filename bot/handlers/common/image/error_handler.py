"""
Централизованный обработчик ошибок для ImageService.
Обеспечивает единообразную обработку всех типов ошибок с retry стратегиями и fallback цепочками.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from functools import wraps

from .exceptions import (
    ImageDownloadError, NetworkError, FileError, ValidationError, SessionError,
    ErrorCategory, ErrorSeverity, create_image_error
)
from .image_service_config import ImageServiceConfig


class RetryStrategy:
    """Стратегия повторных попыток с exponential backoff."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """
        Вычисляет задержку для попытки.
        
        Args:
            attempt: Номер попытки (начиная с 0)
            
        Returns:
            float: Задержка в секундах
        """
        if attempt == 0:
            return 0
        
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Добавляем случайность для предотвращения thundering herd
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay


class FallbackStrategy:
    """Стратегия fallback для восстановления после ошибок."""
    
    def __init__(self, name: str, priority: int = 0):
        self.name = name
        self.priority = priority  # Меньше = выше приоритет
    
    async def execute(self, context: Dict[str, Any]) -> Any:
        """
        Выполняет fallback стратегию.
        
        Args:
            context: Контекст выполнения
            
        Returns:
            Any: Результат выполнения fallback
        """
        raise NotImplementedError("Subclasses must implement execute method")


class TextFallbackStrategy(FallbackStrategy):
    """Fallback на текстовое сообщение."""
    
    def __init__(self):
        super().__init__("text_fallback", priority=0)
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """Возвращает текстовое сообщение как fallback."""
        product = context.get('product')
        loc = context.get('loc')
        
        if not product or not loc:
            return "⚠️ Ошибка при загрузке изображений"
        
        # Создаем базовое описание продукта
        title = getattr(product, 'title', 'Продукт')
        description = getattr(product, 'description', '')
        
        caption = f"🏷️ <b>{title}</b>"
        if description:
            caption += f"\n\n{description}"
        
        if hasattr(product, 'price') and product.price:
            caption += f"\n\n💰 Цена: {product.price}"
        
        caption += "\n\n⚠️ Ошибка при загрузке изображений"
        return caption


class PlaceholderImageFallbackStrategy(FallbackStrategy):
    """Fallback на placeholder изображения."""
    
    def __init__(self, placeholder_urls: Optional[List[str]] = None):
        super().__init__("placeholder_image", priority=1)
        self.placeholder_urls = placeholder_urls or [
            "https://via.placeholder.com/400x300/cccccc/666666?text=Image+Not+Available"
        ]
    
    async def execute(self, context: Dict[str, Any]) -> List[str]:
        """Возвращает список placeholder изображений."""
        return self.placeholder_urls


class RetryFallbackStrategy(FallbackStrategy):
    """Fallback с повторными попытками."""
    
    def __init__(self, retry_strategy: RetryStrategy):
        super().__init__("retry_fallback", priority=2)
        self.retry_strategy = retry_strategy
    
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Выполняет операцию с повторными попытками."""
        operation = context.get('operation')
        if not operation:
            raise ValueError("Operation not provided in context")
        
        return await self._retry_operation(operation, context)
    
    async def _retry_operation(
        self,
        operation: Callable,
        context: Dict[str, Any]
    ) -> Any:
        """Выполняет операцию с retry логикой."""
        last_error = None
        
        for attempt in range(self.retry_strategy.max_attempts):
            try:
                return await operation()
            except Exception as e:
                last_error = e
                
                if attempt < self.retry_strategy.max_attempts - 1:
                    delay = self.retry_strategy.get_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    break
        
        # Если все попытки исчерпаны, создаем кастомную ошибку
        raise create_image_error(
            last_error,
            ErrorCategory.NETWORK,
            context
        )


class ImageErrorHandler:
    """
    Централизованный обработчик ошибок для ImageService.
    
    Обеспечивает:
    - Классификацию ошибок по типам
    - Retry стратегии с exponential backoff
    - Fallback цепочки для восстановления
    - Единообразное логирование ошибок
    """
    
    def __init__(self, config: Optional[ImageServiceConfig] = None):
        """
        Инициализация обработчика ошибок.
        
        Args:
            config: Конфигурация сервиса
        """
        self.config = config or ImageServiceConfig()
        self.logger = logging.getLogger(__name__)
        
        # Настройка retry стратегии
        self.retry_strategy = RetryStrategy(
            max_attempts=getattr(self.config, 'retry_attempts', 3),
            base_delay=getattr(self.config, 'retry_delay', 1.0)
        )
        
        # Инициализация fallback стратегий
        self.fallback_strategies = self._initialize_fallback_strategies()
        
        self.logger.info(f"[ImageErrorHandler] Инициализирован с {len(self.fallback_strategies)} fallback стратегиями")
    
    def _initialize_fallback_strategies(self) -> List[FallbackStrategy]:
        """Инициализирует fallback стратегии."""
        strategies = [
            TextFallbackStrategy(),
            PlaceholderImageFallbackStrategy(),
            RetryFallbackStrategy(self.retry_strategy)
        ]
        
        # Сортируем по приоритету
        strategies.sort(key=lambda s: s.priority)
        return strategies
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> ImageDownloadError:
        """
        Обрабатывает ошибку и создает кастомное исключение.
        
        Args:
            error: Исходное исключение
            context: Контекст ошибки
            
        Returns:
            ImageDownloadError: Кастомное исключение
        """
        context = context or {}
        
        # Создаем кастомное исключение
        if isinstance(error, ImageDownloadError):
            custom_error = error
        else:
            # Определяем категорию по типу ошибки
            category = self._categorize_error(error)
            custom_error = create_image_error(error, category, context)
        
        # Логируем ошибку
        self._log_error(custom_error, context)
        
        return custom_error
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Определяет категорию ошибки."""
        error_type = type(error).__name__
        
        if error_type in ['TimeoutError', 'ConnectionError', 'DNSResolutionError']:
            return ErrorCategory.NETWORK
        elif error_type in ['OSError', 'FileNotFoundError', 'PermissionError']:
            return ErrorCategory.FILE
        elif error_type in ['ValueError', 'TypeError']:
            return ErrorCategory.VALIDATION
        elif error_type in ['aiohttp.ClientError', 'aiohttp.ServerError']:
            return ErrorCategory.SESSION
        else:
            return ErrorCategory.UNKNOWN
    
    def _log_error(self, error: ImageDownloadError, context: Dict[str, Any]):
        """Логирует ошибку с контекстом."""
        log_level = logging.WARNING if error.severity == ErrorSeverity.WARNING else logging.ERROR
        
        self.logger.log(
            log_level,
            f"[{error.error_code}] {error.message} | "
            f"Category: {error.category.value}, "
            f"Severity: {error.severity.value}, "
            f"Context: {context}"
        )
        
        if error.original_error:
            self.logger.debug(f"Original error: {error.original_error}")
    
    async def handle_network_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Any:
        """
        Обрабатывает сетевые ошибки с retry стратегией.
        
        Args:
            error: Сетевая ошибка
            context: Контекст ошибки
            
        Returns:
            Any: Результат обработки или fallback
        """
        custom_error = self.handle_error(error, context)
        
        # Определяем, можно ли повторить попытку
        if self._is_retryable_network_error(custom_error):
            return await self._retry_network_operation(context)
        else:
            # Используем fallback стратегии
            return await self._execute_fallback_chain(custom_error, context)
    
    def _is_retryable_network_error(self, error: ImageDownloadError) -> bool:
        """Определяет, можно ли повторить сетевую операцию."""
        if error.category != ErrorCategory.NETWORK:
            return False
        
        # Не повторяем для критических ошибок
        if error.severity == ErrorSeverity.CRITICAL:
            return False
        
        # Не повторяем для определенных HTTP статусов
        if hasattr(error, 'context') and 'status_code' in error.context:
            status_code = error.context['status_code']
            if status_code in [400, 401, 403, 404]:  # Client errors
                return False
        
        return True
    
    async def _retry_network_operation(self, context: Dict[str, Any]) -> Any:
        """Повторяет сетевую операцию с exponential backoff."""
        operation = context.get('operation')
        if not operation:
            raise ValueError("Operation not provided in context for retry")
        
        last_error = None
        
        for attempt in range(self.retry_strategy.max_attempts):
            try:
                return await operation()
            except Exception as e:
                last_error = e
                
                if attempt < self.retry_strategy.max_attempts - 1:
                    delay = self.retry_strategy.get_delay(attempt)
                    self.logger.info(f"Retry attempt {attempt + 1}/{self.retry_strategy.max_attempts} in {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    break
        
        # Если все попытки исчерпаны, используем fallback
        self.logger.warning(f"All retry attempts exhausted, using fallback strategies")
        return await self._execute_fallback_chain(last_error, context)
    
    async def handle_file_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Any:
        """
        Обрабатывает файловые ошибки.
        
        Args:
            error: Файловая ошибка
            context: Контекст ошибки
            
        Returns:
            Any: Результат обработки или fallback
        """
        custom_error = self.handle_error(error, context)
        
        # Для критических файловых ошибок используем fallback
        if custom_error.severity == ErrorSeverity.CRITICAL:
            return await self._execute_fallback_chain(custom_error, context)
        
        # Для обычных файловых ошибок пытаемся исправить
        return await self._fix_file_error(custom_error, context)
    
    async def _fix_file_error(
        self,
        error: ImageDownloadError,
        context: Dict[str, Any]
    ) -> Any:
        """Пытается исправить файловую ошибку."""
        if isinstance(error, PermissionDeniedError):
            # Пытаемся изменить права доступа
            path = error.context.get('path')
            if path:
                try:
                    import os
                    os.chmod(path, 0o644)
                    self.logger.info(f"Fixed permissions for {path}")
                    return await self._retry_file_operation(context)
                except Exception as e:
                    self.logger.error(f"Failed to fix permissions for {path}: {e}")
        
        # Если исправить не удалось, используем fallback
        return await self._execute_fallback_chain(error, context)
    
    async def _retry_file_operation(self, context: Dict[str, Any]) -> Any:
        """Повторяет файловую операцию."""
        operation = context.get('operation')
        if operation:
            return await operation()
        return None
    
    async def handle_validation_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Any:
        """
        Обрабатывает ошибки валидации.
        
        Args:
            error: Ошибка валидации
            context: Контекст ошибки
            
        Returns:
            Any: Результат обработки или fallback
        """
        custom_error = self.handle_error(error, context)
        
        # Для ошибок валидации обычно используем fallback
        return await self._execute_fallback_chain(custom_error, context)
    
    async def _execute_fallback_chain(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Any:
        """
        Выполняет цепочку fallback стратегий.
        
        Args:
            error: Ошибка, для которой нужен fallback
            context: Контекст выполнения
            
        Returns:
            Any: Результат первой успешной fallback стратегии
        """
        context['error'] = error
        
        for strategy in self.fallback_strategies:
            try:
                self.logger.info(f"Trying fallback strategy: {strategy.name}")
                result = await strategy.execute(context)
                
                if result is not None:
                    self.logger.info(f"Fallback strategy {strategy.name} succeeded")
                    return result
                    
            except Exception as e:
                self.logger.warning(f"Fallback strategy {strategy.name} failed: {e}")
                continue
        
        # Если все fallback стратегии не удались
        self.logger.error("All fallback strategies failed")
        raise error
    
    def create_retry_decorator(
        self,
        max_attempts: Optional[int] = None,
        base_delay: Optional[float] = None
    ):
        """
        Создает декоратор для автоматических retry.
        
        Args:
            max_attempts: Максимальное количество попыток
            base_delay: Базовая задержка
            
        Returns:
            Callable: Декоратор функции
        """
        retry_strategy = RetryStrategy(
            max_attempts=max_attempts or self.retry_strategy.max_attempts,
            base_delay=base_delay or self.retry_strategy.base_delay
        )
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                last_error = None
                
                for attempt in range(retry_strategy.max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_error = e
                        
                        if attempt < retry_strategy.max_attempts - 1:
                            delay = retry_strategy.get_delay(attempt)
                            self.logger.info(f"Retry attempt {attempt + 1}/{retry_strategy.max_attempts} in {delay:.1f}s")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            break
                
                # Если все попытки исчерпаны, создаем кастомную ошибку
                raise create_image_error(
                    last_error,
                    ErrorCategory.NETWORK,
                    {"function": func.__name__, "args": args, "kwargs": kwargs}
                )
            
            return wrapper
        
        return decorator
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику ошибок.
        
        Returns:
            Dict[str, Any]: Статистика ошибок
        """
        # В реальной реализации здесь можно собирать метрики
        return {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "retry_attempts": 0,
            "fallback_successes": 0
        }
    
    async def cleanup(self):
        """Очищает ресурсы обработчика ошибок."""
        self.logger.info("[ImageErrorHandler] Cleanup completed")
