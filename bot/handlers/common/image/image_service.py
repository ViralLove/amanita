"""
Сервис для работы с изображениями.
Реализация IImageService для загрузки, обработки и отправки изображений.
"""

import asyncio
import aiohttp
import logging
import os
import tempfile
import time
import glob
import uuid
from typing import List, Any, Optional, Dict
from dataclasses import replace
from urllib.parse import urlparse

from aiogram.types import InputMediaPhoto, FSInputFile
from bot.services.common.localization import Localization
from .image_service_interface import IImageService
from .image_service_config import ImageServiceConfig
from .session_manager import SessionManager
from .error_handler import ImageErrorHandler
from .fallback_strategies import (
    DegradationLevel, FallbackResult, EnhancedPlaceholderImageFallbackStrategy,
    AlternativeURLRetryStrategy, GracefulDegradationStrategy
)
from .progress_indicators import get_progress_manager, ProgressType
from .error_metrics import record_error, get_error_metrics
from .exceptions import (
    ImageDownloadError, NetworkError, FileError, ValidationError,
    ErrorCategory, ErrorSeverity, create_image_error
)


class ImageService(IImageService):
    """
    Сервис для работы с изображениями.
    
    Обеспечивает:
    - Асинхронную загрузку изображений
    - Создание медиа-групп для Telegram
    - Управление временными файлами
    - Кэширование изображений
    - Обработку ошибок
    """
    
    def __init__(self, config: Optional[ImageServiceConfig] = None):
        """
        Инициализация сервиса изображений.
        
        Args:
            config: Конфигурация сервиса
        """
        self.config = config or ImageServiceConfig()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config.logging_level)
        
        # Валидируем конфигурацию
        errors = self.config.validate_config()
        if errors:
            raise ValueError(f"Ошибки в конфигурации ImageService: {', '.join(errors)}")
        
        # Инициализируем менеджер сессий
        self.session_manager = SessionManager()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Инициализируем ErrorHandler и fallback стратегии
        self.error_handler = ImageErrorHandler()
        self.placeholder_fallback = EnhancedPlaceholderImageFallbackStrategy()
        self.alternative_url_fallback = AlternativeURLRetryStrategy()
        self.graceful_degradation = GracefulDegradationStrategy()
        
        # Менеджер прогресса для отслеживания операций
        self.progress_manager = get_progress_manager()
        
        self.logger.info(f"[ImageService] Инициализирован с конфигурацией: "
                        f"timeout={self.config.download_timeout}s, "
                        f"max_size={self.config.max_file_size}bytes, "
                        f"cache={'enabled' if self.config.enable_cache else 'disabled'}, "
                        f"error_handling={'enabled' if self.error_handler else 'disabled'}")
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Полная проверка здоровья ImageService и всех его компонентов.
        
        Returns:
            Dict[str, Any]: Детальный статус здоровья
        """
        # Детальное логирование начала health check
        self.logger.info(
            "[ImageService] Начинаем полную проверку здоровья сервиса",
            extra={
                "operation": "health_check",
                "result": "starting_health_check"
            }
        )
        
        health_status = {
            "overall_status": "healthy",
            "timestamp": time.time(),
            "components": {},
            "summary": {
                "healthy": 0,
                "degraded": 0,
                "unhealthy": 0
            }
        }
        
        # Проверяем каждый компонент
        components_to_check = [
            ("error_handler", self._check_error_handler_health),
            ("session_manager", self._check_session_manager_health),
            ("cache", self._check_cache_health),
            ("metrics", self._check_metrics_health),
            ("fallback_strategies", self._check_fallback_health)
        ]
        
        for component_name, check_method in components_to_check:
            try:
                if asyncio.iscoroutinefunction(check_method):
                    component_status = await check_method()
                else:
                    component_status = check_method()
                
                health_status["components"][component_name] = component_status
                
                # Обновляем статистику
                status = component_status.get("status", "unknown")
                if status == "healthy":
                    health_status["summary"]["healthy"] += 1
                elif status == "degraded":
                    health_status["summary"]["degraded"] += 1
                else:
                    health_status["summary"]["unhealthy"] += 1
                    health_status["overall_status"] = "unhealthy"
                
            except Exception as e:
                # Обрабатываем ошибку через ErrorHandler
                operation_context = {
                    "component_name": component_name,
                    "operation_type": "health_check"
                }
                
                custom_error = self.error_handler.handle_error(e, operation_context)
                
                health_status["components"][component_name] = {
                    "status": "unhealthy",
                    "error": custom_error.message,
                    "error_context": custom_error.context
                }
                health_status["summary"]["unhealthy"] += 1
                health_status["overall_status"] = "unhealthy"
                
                # Детальное логирование ошибки health check
                self.logger.error(
                    f"[ImageService] Ошибка health check компонента {component_name}: {custom_error.message}",
                    extra={
                        "component_name": component_name,
                        "operation": "health_check",
                        "error_context": custom_error.context,
                        "result": "component_check_failed"
                    }
                )
        
        # Определяем общий статус
        if health_status["summary"]["unhealthy"] > 0:
            health_status["overall_status"] = "unhealthy"
        elif health_status["summary"]["degraded"] > 0:
            health_status["overall_status"] = "degraded"
        
        # Детальное логирование завершения health check
        self.logger.info(
            f"[ImageService] Health check завершен: {health_status['overall_status']}",
            extra={
                "operation": "health_check",
                "overall_status": health_status["overall_status"],
                "summary": health_status["summary"],
                "result": "health_check_completed"
            }
        )
        
        return health_status
    
    def _check_error_handler_health(self) -> Dict[str, Any]:
        """Проверяет здоровье ErrorHandler."""
        try:
            if not self.error_handler:
                return {"status": "unhealthy", "error": "ErrorHandler not initialized"}
            
            # Тестируем обработку ошибки
            test_error = Exception("Health check test error")
            test_context = {"test": True, "operation": "health_check"}
            
            result = self.error_handler.handle_error(test_error, test_context)
            
            if isinstance(result, ImageDownloadError):
                return {
                    "status": "healthy",
                    "test_error_code": result.error_code,
                    "test_category": result.category.value,
                    "test_severity": result.severity.value
                }
            else:
                return {"status": "degraded", "warning": "ErrorHandler returned unexpected type"}
                
        except Exception as e:
            return {"status": "unhealthy", "error": f"ErrorHandler health check failed: {e}"}
    
    async def _check_session_manager_health(self) -> Dict[str, Any]:
        """Проверяет здоровье SessionManager."""
        try:
            if not self.session_manager:
                return {"status": "unhealthy", "error": "SessionManager not initialized"}
            
            # Проверяем возможность получения сессии
            test_session = await self.session_manager.get_session(self.config)
            
            if test_session and not test_session.closed:
                return {
                    "status": "healthy",
                    "session_closed": test_session.closed,
                    "connector_limit": getattr(test_session.connector, '_limit', 'unknown')
                }
            else:
                return {"status": "degraded", "warning": "Session is closed or unavailable"}
                
        except Exception as e:
            return {"status": "unhealthy", "error": f"SessionManager health check failed: {e}"}
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход."""
        self.session = await self.session_manager.get_session(self.config)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход."""
        # Не закрываем сессию, так как она переиспользуется через SessionManager
        self.session = None
    
    async def download_image(self, url: str, product_id: str) -> str:
        """
        Загружает изображение по URL и сохраняет во временный файл.
        
        Args:
            url: URL изображения для загрузки
            product_id: ID продукта для именования файла
            
        Returns:
            str: Путь к сохраненному временному файлу
            
        Raises:
            Exception: При ошибках загрузки или сохранения
        """
        operation_id = f"download_{product_id}_{uuid.uuid4().hex[:8]}"
        
        # Детальное логирование начала операции
        self.logger.info(
            f"[ImageService] Начинаем загрузку изображения",
            extra={
                "operation_id": operation_id,
                "product_id": product_id,
                "url": url,
                "config": {
                    "validate_urls": self.config.validate_urls,
                    "enable_cache": self.config.enable_cache,
                    "retry_attempts": self.config.retry_attempts,
                    "max_file_size": self.config.max_file_size
                }
            }
        )
        
        # Начинаем отслеживание операции
        self.progress_manager.start_operation(
            operation_id, 
            f"Download Image for Product {product_id}", 
            4,  # URL validation, cache check, download, fallback
            ProgressType.DETERMINATE
        )
        
        try:
            if not self.session:
                raise RuntimeError("ImageService не инициализирован. Используйте async with.")
            
            # Создаем контекст для операции
            operation_context = {
                "product_id": product_id,
                "url": url,
                "operation_type": "download_image",
                "operation_id": operation_id
            }
            
            # Детальное логирование перехода к валидации
            self.logger.debug(
                f"[ImageService] Переходим к валидации URL",
                extra={
                    "operation_id": operation_id,
                    "product_id": product_id,
                    "url": url,
                    "validate_urls": self.config.validate_urls,
                    "result": "starting_validation"
                }
            )
            
            # Шаг 1: Валидация URL
            self.progress_manager.add_step(operation_id, "validate_url", "URL Validation", "Проверка доступности URL")
            self.progress_manager.start_step(operation_id, "validate_url")
            
            if self.config.validate_urls:
                if not await self.validate_image_url(url):
                    error_msg = f"Недоступный URL изображения: {url}"
                    # Детальное логирование неудачной валидации URL
                    self.logger.warning(
                        f"[ImageService] URL недоступен: {url}",
                        extra={
                            "operation_id": operation_id,
                            "product_id": product_id,
                            "url": url,
                            "validation_type": "url_unavailable",
                            "result": "validation_failed"
                        }
                    )
                    self.progress_manager.fail_step(operation_id, "validate_url", error_msg)
                    
                    # Обрабатываем ошибку через ErrorHandler
                    validation_error = ValueError(error_msg)
                    custom_error = self.error_handler.handle_error(
                        validation_error, 
                        {**operation_context, "error_type": "url_unavailable"}
                    )
                    
                    # Записываем метрику ошибки
                    record_error(
                        custom_error.error_code,
                        custom_error.category,
                        custom_error.severity,
                        custom_error.context
                    )
                    
                    raise custom_error
                
                if not self.config.is_valid_domain(url):
                    error_msg = f"Недопустимый домен: {url}"
                    # Детальное логирование неудачной валидации домена
                    self.logger.warning(
                        f"[ImageService] Недопустимый домен: {url}",
                        extra={
                            "operation_id": operation_id,
                            "product_id": product_id,
                            "url": url,
                            "validation_type": "invalid_domain",
                            "result": "validation_failed"
                        }
                    )
                    self.progress_manager.fail_step(operation_id, "validate_url", error_msg)
                    
                    # Обрабатываем ошибку через ErrorHandler
                    validation_error = ValueError(error_msg)
                    custom_error = self.error_handler.handle_error(
                        validation_error, 
                        {**operation_context, "error_type": "invalid_domain"}
                    )
                    
                    # Записываем метрику ошибки
                    record_error(
                        custom_error.error_code,
                        custom_error.category,
                        custom_error.severity,
                        custom_error.context
                    )
                    
                    raise custom_error
            
            self.progress_manager.complete_step(operation_id, "validate_url")
            
            # Детальное логирование перехода к проверке кэша
            self.logger.debug(
                f"[ImageService] Переходим к проверке кэша",
                extra={
                    "operation_id": operation_id,
                    "product_id": product_id,
                    "url": url,
                    "cache_enabled": self.config.enable_cache,
                    "result": "starting_cache_check"
                }
            )
            
            # Шаг 2: Проверка кэша
            self.progress_manager.add_step(operation_id, "check_cache", "Cache Check", "Проверка кэша изображения")
            self.progress_manager.start_step(operation_id, "check_cache")
            
            if self.config.enable_cache:
                cached_path = self.get_cached(url)
                if cached_path is not None:
                    self.logger.debug(f"[ImageService] Используем свежий кэш: {cached_path}")
                    self.progress_manager.complete_step(operation_id, "check_cache")
                    self.progress_manager.complete_operation(operation_id, {"result": "cached", "path": cached_path})
                
                # Детальное логирование успешного использования кэша
                self.logger.info(
                    f"[ImageService] Использован кэш изображения",
                    extra={
                        "operation_id": operation_id,
                        "product_id": product_id,
                        "url": url,
                        "cached_path": cached_path,
                        "result": "cached"
                    }
                )
                return cached_path
            
            self.progress_manager.complete_step(operation_id, "check_cache")
            
            # Детальное логирование перехода к загрузке
            self.logger.debug(
                f"[ImageService] Кэш не найден, переходим к загрузке",
                extra={
                    "operation_id": operation_id,
                    "product_id": product_id,
                    "url": url,
                    "cache_enabled": self.config.enable_cache,
                    "result": "cache_miss"
                }
            )
            
            # Детальное логирование перехода к загрузке
            self.logger.debug(
                f"[ImageService] Переходим к загрузке изображения",
                extra={
                    "operation_id": operation_id,
                    "product_id": product_id,
                    "url": url,
                    "retry_attempts": self.config.retry_attempts,
                    "result": "starting_download"
                }
            )
            
            # Шаг 3: Загрузка изображения
            self.progress_manager.add_step(operation_id, "download", "Image Download", "Загрузка изображения с сервера")
            self.progress_manager.start_step(operation_id, "download")
            
            # Загружаем изображение с повторными попытками
            for attempt in range(self.config.retry_attempts + 1):
                try:
                    result = await self._download_image_internal(url, product_id)
                    self.progress_manager.complete_step(operation_id, "download")
                    self.progress_manager.complete_operation(operation_id, {"result": "success", "path": result})
                    
                    # Детальное логирование успешной загрузки
                    self.logger.info(
                        f"[ImageService] Изображение успешно загружено",
                        extra={
                            "operation_id": operation_id,
                            "product_id": product_id,
                            "url": url,
                            "result_path": result,
                            "result": "success"
                        }
                    )
                    return result
                    
                except Exception as e:
                    if attempt == self.config.retry_attempts:
                        # Все попытки исчерпаны, запускаем fallback
                        # Детальное логирование неудачного шага загрузки
                        self.logger.error(
                            f"[ImageService] Все попытки загрузки исчерпаны",
                            extra={
                                "operation_id": operation_id,
                                "product_id": product_id,
                                "url": url,
                                "attempt": attempt + 1,
                                "max_attempts": self.config.retry_attempts + 1,
                                "error": str(e),
                                "result": "download_failed"
                            }
                        )
                        self.progress_manager.fail_step(operation_id, "download", f"Attempt {attempt + 1} failed: {e}")
                        break
                    
                    # Детальное логирование неудачной попытки
                    self.logger.warning(
                        f"[ImageService] Попытка {attempt + 1} не удалась, повторяем через {self.config.retry_delay}s: {e}",
                        extra={
                            "operation_id": operation_id,
                            "product_id": product_id,
                            "url": url,
                            "attempt": attempt + 1,
                            "max_attempts": self.config.retry_attempts + 1,
                            "retry_delay": self.config.retry_delay,
                            "error": str(e)
                        }
                    )
                    await asyncio.sleep(self.config.retry_delay)
            
            # Детальное логирование перехода к fallback
            self.logger.info(
                f"[ImageService] Переходим к fallback стратегиям",
                extra={
                    "operation_id": operation_id,
                    "product_id": product_id,
                    "url": url,
                    "retry_attempts": self.config.retry_attempts,
                    "result": "fallback_required"
                }
            )
            
            # Шаг 4: Fallback стратегии
            self.progress_manager.add_step(operation_id, "fallback", "Fallback Strategies", "Применение fallback стратегий")
            self.progress_manager.start_step(operation_id, "fallback")
            
            # Обрабатываем ошибку через ErrorHandler
            download_error = Exception("Все попытки загрузки изображения не удались")
            custom_error = self.error_handler.handle_error(
                download_error, 
                {**operation_context, "error_type": "all_attempts_failed", "retry_attempts": self.config.retry_attempts}
            )
            
            # Записываем метрику неудачной загрузки
            record_error(
                custom_error.error_code,
                custom_error.category,
                custom_error.severity,
                {"url": url, "product_id": product_id, "attempts": self.config.retry_attempts + 1}
            )
            
            # Пытаемся использовать fallback стратегии
            fallback_result = await self._execute_fallback_strategies(url, product_id, operation_id)
            
            if fallback_result.success:
                self.progress_manager.complete_step(operation_id, "fallback")
                self.progress_manager.complete_operation(operation_id, {"result": "fallback_success", "data": fallback_result.data})
                
                # Детальное логирование успешного fallback
                fallback_data = fallback_result.data.get("path") or fallback_result.data.get("urls", [""])[0]
                self.logger.info(
                    f"[ImageService] Fallback стратегия успешно применена",
                    extra={
                        "operation_id": operation_id,
                        "product_id": product_id,
                        "url": url,
                        "fallback_data": fallback_data,
                        "fallback_strategy": fallback_result.fallback_strategy,
                        "degradation_level": fallback_result.degradation_level.value,
                        "result": "fallback_success"
                    }
                )
                return fallback_data
            else:
                # Детальное логирование неудачного fallback
                self.logger.error(
                    f"[ImageService] Все fallback стратегии исчерпаны",
                    extra={
                        "operation_id": operation_id,
                        "product_id": product_id,
                        "url": url,
                        "result": "fallback_exhausted",
                        "fallback_message": fallback_result.message,
                        "fallback_data": fallback_result.data
                    }
                )
                self.progress_manager.fail_step(operation_id, "fallback", fallback_result.message)
                self.progress_manager.fail_operation(operation_id, Exception(f"All fallback strategies failed: {fallback_result.message}"))
                raise Exception(f"Не удалось загрузить изображение и все fallback стратегии исчерпаны: {url}")
                
        except Exception as e:
            # Записываем метрику критической ошибки
            record_error(
                "DOWNLOAD_CRITICAL_ERROR",
                ErrorCategory.NETWORK,
                ErrorSeverity.CRITICAL,
                {"url": url, "product_id": product_id, "error": str(e)}
            )
            
            # Логируем ошибку с контекстом
            self.logger.error(
                f"[ImageService] Критическая ошибка при загрузке изображения: {url} "
                f"для продукта {product_id}: {e}",
                extra={
                    "operation_id": operation_id,
                    "product_id": product_id,
                    "url": url,
                    "result": "critical_error",
                    "error": str(e)
                },
                exc_info=True
            )
            
            # Помечаем операцию как неудачную
            self.progress_manager.fail_operation(operation_id, e)
            raise
    
    async def _execute_fallback_strategies(self, url: str, product_id: str, operation_id: str) -> FallbackResult:
        """
        Выполняет fallback стратегии при неудачной загрузке изображения.
        
        Args:
            url: URL изображения
            product_id: ID продукта
            operation_id: ID операции для отслеживания прогресса
            
        Returns:
            FallbackResult: Результат выполнения fallback стратегий
        """
        self.logger.info(f"[ImageService] Запуск fallback стратегий для {url}")
        
        # Контекст для fallback стратегий
        context = {
            "url": url,
            "product_id": product_id,
            "operation_id": operation_id,
            "error_severity": ErrorSeverity.ERROR,
            "original_error": "Download failed after all retry attempts"
        }
        
        try:
            # Стратегия 1: Попытка с альтернативными URL
            self.logger.debug(f"[ImageService] Попытка fallback с альтернативными URL")
            alt_url_result = await self.alternative_url_fallback.execute(context)
            
            if alt_url_result.success:
                self.logger.info(f"[ImageService] Fallback с альтернативными URL успешен")
                return alt_url_result
            
            # Стратегия 2: Placeholder изображения
            self.logger.debug(f"[ImageService] Попытка fallback с placeholder изображениями")
            placeholder_result = await self.placeholder_fallback.execute(context)
            
            if placeholder_result.success:
                self.logger.info(f"[ImageService] Fallback с placeholder изображениями успешен")
                return placeholder_result
            
            # Стратегия 3: Graceful degradation
            self.logger.debug(f"[ImageService] Попытка graceful degradation")
            degradation_result = await self.graceful_degradation.execute(context)
            
            if degradation_result.success:
                self.logger.info(f"[ImageService] Graceful degradation успешен")
                return degradation_result
            
            # Все стратегии исчерпаны
            self.logger.error(f"[ImageService] Все fallback стратегии исчерпаны для {url}")
            
            # Записываем метрику неудачного fallback
            record_error(
                "FALLBACK_ALL_STRATEGIES_FAILED",
                ErrorCategory.VALIDATION,
                ErrorSeverity.CRITICAL,
                context
            )
            
            return FallbackResult(
                success=False,
                data=None,
                degradation_level=DegradationLevel.ERROR_MESSAGE,
                message="Все fallback стратегии исчерпаны",
                fallback_strategy="all_failed",
                execution_time=0.0
            )
            
        except Exception as e:
            self.logger.error(f"[ImageService] Ошибка при выполнении fallback стратегий: {e}", exc_info=True)
            
            # Записываем метрику ошибки fallback
            record_error(
                "FALLBACK_EXECUTION_ERROR",
                ErrorCategory.VALIDATION,
                ErrorSeverity.CRITICAL,
                {**context, "fallback_error": str(e)}
            )
            
            return FallbackResult(
                success=False,
                data=None,
                degradation_level=DegradationLevel.ERROR_MESSAGE,
                message=f"Ошибка выполнения fallback: {e}",
                fallback_strategy="execution_error",
                execution_time=0.0
            )
    
    async def _download_image_internal(self, url: str, product_id: str) -> str:
        """Внутренний метод загрузки изображения."""
        temp_path = self.config.get_temp_file_path(product_id)
        
        self.logger.debug(f"[ImageService] Загружаем изображение: {url} -> {temp_path}")
        
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                
                # Проверяем размер файла
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.config.max_file_size:
                    raise ValueError(f"Файл слишком большой: {content_length} bytes")
                
                # Проверяем тип контента
                content_type = response.headers.get('content-type', '')
                if not any(ext in content_type for ext in ['image/jpeg', 'image/png', 'image/webp']):
                    raise ValueError(f"Недопустимый тип контента: {content_type}")
                
                # Сохраняем файл
                with open(temp_path, 'wb') as f:
                    total_size = 0
                    async for chunk in response.content.iter_chunked(8192):
                        total_size += len(chunk)
                        if total_size > self.config.max_file_size:
                            raise ValueError(f"Файл превышает максимальный размер: {total_size} bytes")
                        f.write(chunk)
                
                # Кэшируем если включено
                if self.config.enable_cache:
                    cache_path = self.config.get_cache_file_path(url)
                    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                    import shutil
                    shutil.copy2(temp_path, cache_path)
                    self.logger.debug(f"[ImageService] Изображение закэшировано: {cache_path}")
                
                self.logger.info(f"[ImageService] Изображение успешно загружено: {temp_path} ({total_size} bytes)")
                return temp_path
                
        except Exception as e:
            # Обрабатываем ошибку через ErrorHandler
            operation_context = {
                "url": url,
                "product_id": product_id,
                "operation_type": "download_image_internal",
                "temp_path": temp_path
            }
            
            custom_error = self.error_handler.handle_error(e, operation_context)
            
            # Записываем метрику ошибки загрузки
            record_error(
                custom_error.error_code,
                custom_error.category,
                custom_error.severity,
                custom_error.context
            )
            
            # Логируем ошибку с контекстом
            self.logger.error(
                f"[ImageService] Ошибка внутренней загрузки изображения: {url} -> {temp_path}: {custom_error.message}",
                extra={"error_context": custom_error.context},
                exc_info=True
            )
            raise custom_error
    
    async def create_media_group(
        self, 
        product: Any, 
        images: List[str], 
        loc: Localization
    ) -> List[InputMediaPhoto]:
        """
        Создает медиа-группу для отправки в Telegram.
        
        Args:
            product: Объект продукта
            images: Список путей к изображениям
            loc: Объект локализации
            
        Returns:
            List[InputMediaPhoto]: Список медиа-объектов для Telegram
        """
        # Детальное логирование начала операции
        self.logger.info(
            f"[ImageService] Создаем медиа-группу для продукта",
            extra={
                "product_id": getattr(product, 'id', 'unknown'),
                "images_count": len(images),
                "max_media_group_size": self.config.max_media_group_size,
                "enable_html_caption": self.config.enable_html_caption
            }
        )
        
        if not images:
            self.logger.warning("[ImageService] Нет изображений для создания медиа-группы")
            return []
        
        # Ограничиваем количество изображений
        images = images[:self.config.max_media_group_size]
        
        # Создаем описание продукта
        caption = self._create_product_caption(product, loc)
        
        media_group = []
        for i, image_path in enumerate(images):
            try:
                # Проверяем существование файла
                if not os.path.exists(image_path):
                    self.logger.warning(f"[ImageService] Файл не найден: {image_path}")
                    continue
                
                # Создаем FSInputFile
                photo = FSInputFile(image_path)
                
                # Добавляем подпись только к первому изображению
                media_item = InputMediaPhoto(
                    media=photo,
                    caption=caption if i == 0 else None,
                    parse_mode="HTML" if self.config.enable_html_caption else None
                )
                
                media_group.append(media_item)
                self.logger.debug(f"[ImageService] Добавлено изображение в медиа-группу: {image_path}")
                
            except Exception as e:
                # Обрабатываем ошибку через ErrorHandler
                operation_context = {
                    "image_path": image_path,
                    "product_id": getattr(product, 'id', 'unknown'),
                    "operation_type": "create_media_group",
                    "image_index": i
                }
                
                custom_error = self.error_handler.handle_error(e, operation_context)
                
                # Записываем метрику ошибки
                record_error(
                    custom_error.error_code,
                    custom_error.category,
                    custom_error.severity,
                    custom_error.context
                )
                
                self.logger.error(
                    f"[ImageService] Ошибка при создании медиа-элемента для {image_path}: {custom_error.message}",
                    extra={"error_context": custom_error.context}
                )
                continue
        
        # Детальное логирование успешного создания медиа-группы
        self.logger.info(
            f"[ImageService] Создана медиа-группа с {len(media_group)} изображениями",
            extra={
                "product_id": getattr(product, 'id', 'unknown'),
                "images_count": len(images),
                "media_group_size": len(media_group),
                "result": "success"
            }
        )
        return media_group
    
    async def send_product_with_images(
        self, 
        message, 
        product: Any, 
        images: List[str], 
        loc: Localization
    ) -> None:
        """
        Отправляет продукт с изображениями в Telegram.
        
        Args:
            message: Объект сообщения Telegram
            product: Объект продукта
            images: Список путей к изображениям
            loc: Объект локализации
        """
        operation_id = f"send_product_{getattr(product, 'id', 'unknown')}_{uuid.uuid4().hex[:8]}"
        
        # Детальное логирование начала операции
        self.logger.info(
            f"[ImageService] Начинаем отправку продукта с изображениями",
            extra={
                "operation_id": operation_id,
                "product_id": getattr(product, 'id', 'unknown'),
                "images_count": len(images),
                "config": {
                    "show_error_placeholders": self.config.show_error_placeholders,
                    "enable_html_caption": self.config.enable_html_caption
                }
            }
        )
        
        # Начинаем отслеживание операции
        self.progress_manager.start_operation(
            operation_id,
            f"Send Product with Images",
            3,  # Create media group, send media, fallback
            ProgressType.DETERMINATE
        )
        
        try:
            # Детальное логирование перехода к созданию медиа-группы
            self.logger.debug(
                f"[ImageService] Переходим к созданию медиа-группы",
                extra={
                    "operation_id": operation_id,
                    "product_id": getattr(product, 'id', 'unknown'),
                    "images_count": len(images),
                    "result": "starting_media_creation"
                }
            )
            
            # Шаг 1: Создание медиа-группы
            self.progress_manager.add_step(operation_id, "create_media", "Create Media Group", "Создание медиа-группы")
            self.progress_manager.start_step(operation_id, "create_media")
            
            media_group = await self.create_media_group(product, images, loc)
            
            if not media_group:
                # Если нет изображений, отправляем текстовое сообщение
                caption = self._create_product_caption(product, loc)
                await message.answer(
                    caption,
                    parse_mode="HTML" if self.config.enable_html_caption else None
                )
                
                self.progress_manager.complete_step(operation_id, "create_media")
                self.progress_manager.complete_operation(operation_id, {"result": "text_only", "reason": "no_images"})
                
                # Детальное логирование отправки текстового сообщения
                self.logger.info(
                    f"[ImageService] Отправлено текстовое сообщение (нет изображений)",
                    extra={
                        "operation_id": operation_id,
                        "product_id": getattr(product, 'id', 'unknown'),
                        "images_count": len(images),
                        "result": "text_only",
                        "reason": "no_images"
                    }
                )
                return
            
            self.progress_manager.complete_step(operation_id, "create_media")
            
            # Детальное логирование перехода к отправке
            self.logger.debug(
                f"[ImageService] Переходим к отправке медиа-группы",
                extra={
                    "operation_id": operation_id,
                    "product_id": getattr(product, 'id', 'unknown'),
                    "media_group_size": len(media_group),
                    "result": "media_group_created"
                }
            )
            
            # Детальное логирование перехода к отправке медиа
            self.logger.debug(
                f"[ImageService] Переходим к отправке медиа-группы",
                extra={
                    "operation_id": operation_id,
                    "product_id": getattr(product, 'id', 'unknown'),
                    "media_group_size": len(media_group),
                    "result": "starting_media_send"
                }
            )
            
            # Шаг 2: Отправка медиа-группы
            self.progress_manager.add_step(operation_id, "send_media", "Send Media Group", "Отправка медиа-группы в Telegram")
            self.progress_manager.start_step(operation_id, "send_media")
            
            await message.answer_media_group(media_group)
            
            self.progress_manager.complete_step(operation_id, "send_media")
            self.progress_manager.complete_operation(operation_id, {"result": "success", "images_count": len(media_group)})
            
            # Детальное логирование успешной отправки
            self.logger.info(
                f"[ImageService] Отправлена медиа-группа с {len(media_group)} изображениями",
                extra={
                    "operation_id": operation_id,
                    "product_id": getattr(product, 'id', 'unknown'),
                    "images_count": len(images),
                    "media_group_size": len(media_group),
                    "result": "success"
                }
            )
            
        except Exception as e:
            # Обрабатываем ошибку через ErrorHandler
            operation_context = {
                "product_id": getattr(product, 'id', 'unknown'),
                "images_count": len(images),
                "operation_type": "send_product_with_images",
                "operation_id": operation_id
            }
            
            custom_error = self.error_handler.handle_error(e, operation_context)
            
            # Записываем метрику ошибки отправки
            record_error(
                custom_error.error_code,
                custom_error.category,
                custom_error.severity,
                custom_error.context
            )
            
            # Логируем ошибку с контекстом
            self.logger.error(
                f"[ImageService] Ошибка при отправке продукта с изображениями: "
                f"product_id={getattr(product, 'id', 'unknown')}, "
                f"images_count={len(images)}: {custom_error.message}",
                extra={"error_context": custom_error.context},
                exc_info=True
            )
            
            # Детальное логирование перехода к fallback
            self.logger.info(
                f"[ImageService] Переходим к fallback сообщению",
                extra={
                    "operation_id": operation_id,
                    "product_id": getattr(product, 'id', 'unknown'),
                    "images_count": len(images),
                    "result": "fallback_required"
                }
            )
            
            # Детальное логирование перехода к fallback
            self.logger.info(
                f"[ImageService] Переходим к fallback сообщению",
                extra={
                    "operation_id": operation_id,
                    "product_id": getattr(product, 'id', 'unknown'),
                    "images_count": len(images),
                    "result": "fallback_required"
                }
            )
            
            # Шаг 3: Fallback - отправляем текстовое сообщение
            self.progress_manager.add_step(operation_id, "fallback", "Fallback Message", "Отправка fallback сообщения")
            self.progress_manager.start_step(operation_id, "fallback")
            
            try:
                if self.config.show_error_placeholders:
                    caption = self._create_product_caption(product, loc)
                    await message.answer(
                        f"{caption}\n\n⚠️ Ошибка при загрузке изображений",
                        parse_mode="HTML" if self.config.enable_html_caption else None
                    )
                    
                    self.progress_manager.complete_step(operation_id, "fallback")
                    self.progress_manager.complete_operation(operation_id, {"result": "fallback_success", "type": "text_message"})
                    
                    # Детальное логирование отправки fallback сообщения
                    self.logger.info(
                        f"[ImageService] Отправлено fallback сообщение",
                        extra={
                            "operation_id": operation_id,
                            "product_id": getattr(product, 'id', 'unknown'),
                            "images_count": len(images),
                            "result": "fallback_success",
                            "type": "text_message"
                        }
                    )
                else:
                    # Детальное логирование отключенного fallback
                    self.logger.warning(
                        f"[ImageService] Fallback отключен в конфигурации",
                        extra={
                            "operation_id": operation_id,
                            "product_id": getattr(product, 'id', 'unknown'),
                            "images_count": len(images),
                            "result": "fallback_disabled",
                            "config_show_error_placeholders": self.config.show_error_placeholders
                        }
                    )
                    self.progress_manager.fail_step(operation_id, "fallback", "Fallback disabled in config")
                    self.progress_manager.fail_operation(operation_id, e)
                    raise
                    
            except Exception as fallback_error:
                # Обрабатываем ошибку fallback через ErrorHandler
                fallback_context = {
                    **operation_context,
                    "error_type": "fallback_failed",
                    "original_error": str(e),
                    "fallback_error": str(fallback_error)
                }
                
                fallback_custom_error = self.error_handler.handle_error(fallback_error, fallback_context)
                
                # Записываем метрику ошибки fallback
                record_error(
                    fallback_custom_error.error_code,
                    fallback_custom_error.category,
                    fallback_custom_error.severity,
                    fallback_custom_error.context
                )
                
                # Детальное логирование неудачного fallback
                self.logger.error(
                    f"[ImageService] Fallback стратегия не удалась",
                    extra={
                        "operation_id": operation_id,
                        "product_id": getattr(product, 'id', 'unknown'),
                        "images_count": len(images),
                        "result": "fallback_failed",
                        "fallback_error": fallback_custom_error.message,
                        "error_context": fallback_custom_error.context
                    }
                )
                self.progress_manager.fail_step(operation_id, "fallback", f"Fallback failed: {fallback_custom_error.message}")
                self.progress_manager.fail_operation(operation_id, fallback_custom_error)
                
                # Детальное логирование критической ошибки fallback
                self.logger.critical(
                    f"[ImageService] Критическая ошибка fallback: {fallback_custom_error.message}",
                    extra={
                        "operation_id": operation_id,
                        "product_id": getattr(product, 'id', 'unknown'),
                        "images_count": len(images),
                        "original_error": str(e),
                        "fallback_error": str(fallback_error),
                        "error_context": fallback_custom_error.context,
                        "result": "fallback_critical_error"
                    }
                )
                
                raise fallback_error
    
    async def cleanup_temp_files(self, file_paths: List[str]) -> None:
        """
        Очищает временные файлы изображений.
        
        Args:
            file_paths: Список путей к файлам для удаления
        """
        operation_id = f"cleanup_{uuid.uuid4().hex[:8]}"
        
        # Детальное логирование начала операции
        self.logger.info(
            f"[ImageService] Начинаем очистку временных файлов",
            extra={
                "operation_id": operation_id,
                "files_count": len(file_paths),
                "result": "starting_cleanup"
            }
        )
        
        # Начинаем отслеживание операции
        self.progress_manager.start_operation(
            operation_id,
            f"Cleanup Temporary Files",
            len(file_paths),
            ProgressType.DETERMINATE
        )
        
        cleaned_count = 0
        errors = []
        
        for i, file_path in enumerate(file_paths):
            step_id = f"cleanup_file_{i}"
            
            # Детальное логирование начала очистки файла
            self.logger.debug(
                f"[ImageService] Начинаем очистку файла {i+1}/{len(file_paths)}",
                extra={
                    "operation_id": operation_id,
                    "step_id": step_id,
                    "file_path": file_path,
                    "file_index": i,
                    "total_files": len(file_paths),
                    "result": "starting_file_cleanup"
                }
            )
            
            self.progress_manager.add_step(operation_id, step_id, f"Cleanup File {i+1}", f"Удаление файла: {os.path.basename(file_path)}")
            self.progress_manager.start_step(operation_id, step_id)
            
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned_count += 1
                    
                    # Детальное логирование успешного удаления
                    self.logger.debug(
                        f"[ImageService] Удален временный файл: {file_path}",
                        extra={
                            "operation_id": operation_id,
                            "step_id": step_id,
                            "file_path": file_path,
                            "file_index": i,
                            "cleaned_count": cleaned_count,
                            "result": "file_removed"
                        }
                    )
                    self.progress_manager.complete_step(operation_id, step_id)
                else:
                    # Детальное логирование несуществующего файла
                    self.logger.debug(
                        f"[ImageService] Файл не существует: {file_path}",
                        extra={
                            "operation_id": operation_id,
                            "step_id": step_id,
                            "file_path": file_path,
                            "file_index": i,
                            "result": "file_not_exists"
                        }
                    )
                    self.progress_manager.complete_step(operation_id, step_id)
                    
            except Exception as e:
                # Обрабатываем ошибку через ErrorHandler
                operation_context = {
                    "operation_id": operation_id,
                    "step_id": step_id,
                    "file_path": file_path,
                    "file_index": i,
                    "operation_type": "cleanup_temp_files"
                }
                
                custom_error = self.error_handler.handle_error(e, operation_context)
                
                # Записываем метрику ошибки
                record_error(
                    custom_error.error_code,
                    custom_error.category,
                    custom_error.severity,
                    custom_error.context
                )
                
                error_msg = f"Ошибка при удалении файла {file_path}: {custom_error.message}"
                errors.append(error_msg)
                
                # Детальное логирование ошибки
                self.logger.error(
                    f"[ImageService] Ошибка при удалении файла {file_path}: {custom_error.message}",
                    extra={
                        "operation_id": operation_id,
                        "step_id": step_id,
                        "file_path": file_path,
                        "file_index": i,
                        "error_context": custom_error.context,
                        "result": "cleanup_error"
                    }
                )
                
                # Записываем метрику ошибки очистки
                record_error(
                    "CLEANUP_FILE_ERROR",
                    ErrorCategory.FILE,
                    ErrorSeverity.WARNING,
                    {"file_path": file_path, "error": str(e)}
                )
                
                self.logger.error(error_msg)
                self.progress_manager.fail_step(operation_id, step_id, error_msg)
        
        # Завершаем операцию
        if errors:
            self.progress_manager.complete_operation(
                operation_id, 
                {
                    "result": "partial_success",
                    "cleaned_count": cleaned_count,
                    "total_count": len(file_paths),
                    "errors": errors
                }
            )
            self.logger.warning(f"[ImageService] Очистка завершена с ошибками: {cleaned_count}/{len(file_paths)} файлов удалено")
        else:
            self.progress_manager.complete_operation(
                operation_id, 
                {
                    "result": "success",
                    "cleaned_count": cleaned_count,
                    "total_count": len(file_paths)
                }
            )
            self.logger.info(f"[ImageService] Очищено {cleaned_count} временных файлов")
    
    async def validate_image_url(self, url: str) -> bool:
        """
        Проверяет доступность изображения по URL.
        
        Args:
            url: URL изображения для проверки
            
        Returns:
            bool: True если изображение доступно, False иначе
        """
        # Детальное логирование начала валидации
        self.logger.debug(
            f"[ImageService] Начинаем валидацию URL: {url}",
            extra={
                "url": url,
                "operation": "validate_image_url",
                "result": "starting_validation"
            }
        )
        if not self.session:
            # Обрабатываем ошибку через ErrorHandler
            operation_context = {
                "url": url,
                "operation_type": "validate_image_url"
            }
            
            session_error = RuntimeError("ImageService не инициализирован. Используйте async with.")
            custom_error = self.error_handler.handle_error(session_error, operation_context)
            
            # Записываем метрику ошибки валидации
            record_error(
                custom_error.error_code,
                custom_error.category,
                custom_error.severity,
                custom_error.context
            )
            
            # Детальное логирование ошибки
            self.logger.error(
                f"[ImageService] Ошибка валидации: нет активной сессии для {url}",
                extra={
                    "url": url,
                    "operation": "validate_image_url",
                    "error_context": custom_error.context,
                    "result": "validation_failed_no_session"
                }
            )
            return False
        
        try:
            async with self.session.head(url) as response:
                if response.status == 200:
                    # Детальное логирование успешной валидации
                    self.logger.debug(
                        f"[ImageService] URL валиден: {url}",
                        extra={
                            "url": url,
                            "status_code": response.status,
                            "operation": "validate_image_url",
                            "result": "validation_success"
                        }
                    )
                    return True
                else:
                    # Обрабатываем ошибку через ErrorHandler
                    operation_context = {
                        "url": url,
                        "status_code": response.status,
                        "operation_type": "validate_image_url"
                    }
                    
                    http_error = Exception(f"HTTP {response.status} для {url}")
                    custom_error = self.error_handler.handle_error(http_error, operation_context)
                    
                    # Записываем метрику HTTP ошибки
                    record_error(
                        custom_error.error_code,
                        custom_error.category,
                        custom_error.severity,
                        custom_error.context
                    )
                    # Детальное логирование HTTP ошибки
                    self.logger.debug(
                        f"[ImageService] URL недоступен {url}: HTTP {response.status}",
                        extra={
                            "url": url,
                            "status_code": response.status,
                            "operation": "validate_image_url",
                            "result": "validation_failed_http"
                        }
                    )
                    return False
                    
        except Exception as e:
            # Обрабатываем ошибку через ErrorHandler
            operation_context = {
                "url": url,
                "error": str(e),
                "operation_type": "validate_image_url"
            }
            
            custom_error = self.error_handler.handle_error(e, operation_context)
            
            # Записываем метрику ошибки валидации
            record_error(
                custom_error.error_code,
                custom_error.category,
                custom_error.severity,
                custom_error.context
            )
            # Детальное логирование сетевой ошибки
            self.logger.debug(
                f"[ImageService] URL недоступен {url}: {e}",
                extra={
                    "url": url,
                    "error": str(e),
                    "operation": "validate_image_url",
                    "result": "validation_failed_network"
                }
            )
            return False
    
    async def get_image_info(self, file_path: str) -> dict:
        """
        Получает информацию об изображении.
        
        Args:
            file_path: Путь к файлу изображения
            
        Returns:
            dict: Информация об изображении
        """
        # Детальное логирование начала получения информации
        self.logger.debug(
            f"[ImageService] Начинаем получение информации об изображении: {file_path}",
            extra={
                "file_path": file_path,
                "operation": "get_image_info",
                "result": "starting_info_extraction"
            }
        )
        try:
            import PIL.Image
            
            with PIL.Image.open(file_path) as img:
                info = {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'file_size': os.path.getsize(file_path)
                }
                
                # Дополнительная информация если доступна
                if hasattr(img, 'info'):
                    info.update(img.info)
                
                # Детальное логирование успешного получения информации
                self.logger.debug(
                    f"[ImageService] Получена информация об изображении: {file_path} - {info['width']}x{info['height']}",
                    extra={
                        "file_path": file_path,
                        "image_info": info,
                        "operation": "get_image_info",
                        "result": "info_extraction_success"
                    }
                )
                return info
                
        except Exception as e:
            # Обрабатываем ошибку через ErrorHandler
            operation_context = {
                "file_path": file_path,
                "operation_type": "get_image_info"
            }
            
            custom_error = self.error_handler.handle_error(e, operation_context)
            
            # Записываем метрику ошибки получения информации
            record_error(
                custom_error.error_code,
                custom_error.category,
                custom_error.severity,
                custom_error.context
            )
            
            # Детальное логирование ошибки
            self.logger.error(
                f"[ImageService] Ошибка при получении информации об изображении {file_path}: {custom_error.message}",
                extra={
                    "file_path": file_path,
                    "operation": "get_image_info",
                    "error_context": custom_error.context,
                    "result": "info_extraction_failed"
                }
            )
            
            self.logger.error(
                f"[ImageService] Ошибка при получении информации об изображении {file_path}: {e}",
                exc_info=True
            )
            return {'error': str(e)}
    
    def _create_product_caption(self, product: Any, loc: Localization) -> str:
        """
        Создает подпись для продукта.
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            str: Подпись для изображения
        """
        try:
            # Базовая информация о продукте
            title = getattr(product, 'title', 'Продукт')
            description = getattr(product, 'description', '')
            
            caption = f"🏷️ <b>{title}</b>"
            
            if description:
                # Обрезаем описание если оно слишком длинное
                max_desc_length = self.config.caption_max_length - len(caption) - 50
                if len(description) > max_desc_length:
                    description = description[:max_desc_length] + "..."
                caption += f"\n\n{description}"
            
            # Добавляем цену если доступна
            if hasattr(product, 'price') and product.price:
                caption += f"\n\n💰 Цена: {product.price}"
            
            return caption
            
        except Exception as e:
            self.logger.error(f"[ImageService] Ошибка при создании подписи: {e}")
            return "🏷️ <b>Продукт</b>"
    
    def get_config(self) -> ImageServiceConfig:
        """Возвращает текущую конфигурацию."""
        return self.config
    
    def update_config(self, new_config: ImageServiceConfig) -> None:
        """Обновляет конфигурацию сервиса."""
        self.config = new_config
        self.logger.info("[ImageService] Конфигурация обновлена")
    
    def create_custom_config(self, **kwargs) -> ImageServiceConfig:
        """Создает кастомную конфигурацию на основе текущей."""
        return replace(self.config, **kwargs)
    
    def get_session_info(self) -> dict:
        """
        Возвращает информацию о текущей HTTP сессии.
        
        Returns:
            dict: Информация о сессии
        """
        return self.session_manager.get_session_info()
    
    def get_cached(self, url: str) -> Optional[str]:
        """
        Возвращает путь к кэшированному файлу, если он существует и не просрочен.
        
        Args:
            url: URL изображения
            
        Returns:
            Optional[str]: Путь к кэшированному файлу или None
        """
        if not self.config.enable_cache:
            return None
        
        cache_path = self.config.get_cache_file_path(url)
        if not os.path.exists(cache_path):
            return None
        
        if self._is_cache_fresh(cache_path):
            return cache_path
        
        return None
    
    def invalidate_cache(self, url: str) -> bool:
        """
        Удаляет кэш для указанного URL.
        
        Args:
            url: URL изображения
            
        Returns:
            bool: True если файл был удален, False если файл не существовал
        """
        cache_path = self.config.get_cache_file_path(url)
        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)
                self.logger.debug(f"[ImageService] Кэш удален: {cache_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"[ImageService] Ошибка удаления кэша {cache_path}: {e}")
            return False
    
    def clear_cache(self) -> int:
        """
        Полностью очищает директорию кэша.
        
        Returns:
            int: Количество удаленных файлов
        """
        removed = 0
        try:
            pattern = os.path.join(self.config.cache_dir, "*")
            for path in glob.glob(pattern):
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                        removed += 1
                        self.logger.debug(f"[ImageService] Удален файл кэша: {path}")
                    except Exception as e:
                        self.logger.error(f"[ImageService] Ошибка удаления файла кэша {path}: {e}")
        except Exception as e:
            self.logger.error(f"[ImageService] Ошибка очистки кэша: {e}")
        
        self.logger.info(f"[ImageService] Очищено {removed} файлов кэша")
        return removed
    
    def cleanup_expired(self) -> int:
        """
        Удаляет просроченные файлы из кэша.
        
        Returns:
            int: Количество удаленных просроченных файлов
        """
        removed = 0
        try:
            pattern = os.path.join(self.config.cache_dir, "*")
            for path in glob.glob(pattern):
                if os.path.isfile(path) and not self._is_cache_fresh(path):
                    try:
                        os.remove(path)
                        removed += 1
                        self.logger.debug(f"[ImageService] Удален просроченный кэш: {path}")
                    except Exception as e:
                        self.logger.error(f"[ImageService] Ошибка удаления просроченного кэша {path}: {e}")
        except Exception as e:
            self.logger.error(f"[ImageService] Ошибка при очистке просроченного кэша: {e}")
        
        self.logger.info(f"[ImageService] Очищено {removed} просроченных файлов кэша")
        return removed
    
    def _is_cache_fresh(self, path: str) -> bool:
        """
        Проверяет, не истек ли TTL кэша для файла.
        
        Args:
            path: Путь к файлу кэша
            
        Returns:
            bool: True если кэш свежий, False если просрочен
        """
        try:
            mtime = os.path.getmtime(path)
            age = time.time() - mtime
            is_fresh = age <= self.config.cache_duration
            self.logger.debug(f"[ImageService] Проверка свежести кэша {path}: возраст {age:.1f}s, TTL {self.config.cache_duration}s, свежий: {is_fresh}")
            return is_fresh
        except Exception as e:
            self.logger.error(f"[ImageService] Ошибка проверки свежести кэша {path}: {e}")
            return False
    
    # ==================== HEALTH CHECK METHODS ====================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Выполняет полную проверку здоровья сервиса.
        
        Returns:
            Dict[str, Any]: Результат health check
        """
        health_status = {
            "service": "ImageService",
            "timestamp": time.time(),
            "status": "healthy",
            "checks": {}
        }
        
        try:
            # Проверка 1: HTTP сессия
            session_check = await self._check_session_health()
            health_status["checks"]["session"] = session_check
            
            # Проверка 2: Кэш
            cache_check = self._check_cache_health()
            health_status["checks"]["cache"] = cache_check
            
            # Проверка 3: Метрики ошибок
            metrics_check = self._check_metrics_health()
            health_status["checks"]["metrics"] = metrics_check
            
            # Проверка 4: Fallback стратегии
            fallback_check = await self._check_fallback_health()
            health_status["checks"]["fallback"] = fallback_check
            
            # Определяем общий статус
            all_healthy = all(check.get("status") == "healthy" for check in health_status["checks"].values())
            health_status["status"] = "healthy" if all_healthy else "degraded"
            
            if health_status["status"] != "healthy":
                health_status["status"] = "unhealthy"
            
            self.logger.info(f"[ImageService] Health check completed: {health_status['status']}")
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            self.logger.error(f"[ImageService] Health check failed: {e}", exc_info=True)
            
            # Записываем метрику ошибки health check
            record_error(
                "HEALTH_CHECK_FAILED",
                ErrorCategory.VALIDATION,
                ErrorSeverity.ERROR,
                {"service": "ImageService", "error": str(e)}
            )
        
        return health_status
    
    async def _check_session_health(self) -> Dict[str, Any]:
        """Проверяет здоровье HTTP сессии."""
        try:
            session_info = self.session_manager.get_session_info()
            
            if not session_info:
                return {"status": "unhealthy", "error": "No session info available"}
            
            # Проверяем, что сессия активна
            if session_info.get("closed", False):
                return {"status": "unhealthy", "error": "Session is closed"}
            
            # Проверяем timeout настройки
            if session_info.get("timeout", 0) <= 0:
                return {"status": "degraded", "warning": "Invalid timeout configuration"}
            
            return {
                "status": "healthy",
                "session_info": session_info
            }
            
        except Exception as e:
            return {"status": "unhealthy", "error": f"Session health check failed: {e}"}
    
    def _check_cache_health(self) -> Dict[str, Any]:
        """Проверяет здоровье кэша."""
        try:
            if not self.config.enable_cache:
                return {"status": "healthy", "message": "Cache disabled"}
            
            # Проверяем директорию кэша
            if not os.path.exists(self.config.cache_dir):
                return {"status": "unhealthy", "error": "Cache directory does not exist"}
            
            # Проверяем права доступа
            if not os.access(self.config.cache_dir, os.W_OK):
                return {"status": "unhealthy", "error": "No write access to cache directory"}
            
            # Проверяем свободное место
            try:
                import shutil
                total, used, free = shutil.disk_usage(self.config.cache_dir)
                free_gb = free / (1024**3)
                
                if free_gb < 1.0:  # Меньше 1GB
                    return {"status": "degraded", "warning": f"Low disk space: {free_gb:.2f}GB free"}
                
                return {
                    "status": "healthy",
                    "disk_space": {
                        "total_gb": total / (1024**3),
                        "used_gb": used / (1024**3),
                        "free_gb": free_gb
                    }
                }
                
            except Exception as e:
                return {"status": "degraded", "warning": f"Could not check disk space: {e}"}
                
        except Exception as e:
            return {"status": "unhealthy", "error": f"Cache health check failed: {e}"}
    
    def _check_metrics_health(self) -> Dict[str, Any]:
        """Проверяет здоровье метрик."""
        try:
            metrics = get_error_metrics()
            stats = metrics.get_error_stats()
            
            # Проверяем health score
            health_score = metrics.get_health_score()
            
            if health_score >= 0.8:
                status = "healthy"
            elif health_score >= 0.6:
                status = "degraded"
            else:
                status = "unhealthy"
            
            return {
                "status": status,
                "health_score": health_score,
                "total_errors": stats.total_errors,
                "recent_errors": len(metrics.get_recent_errors()),
                "error_rate": stats.error_rate_per_minute
            }
            
        except Exception as e:
            return {"status": "unhealthy", "error": f"Metrics health check failed: {e}"}
    
    async def _check_fallback_health(self) -> Dict[str, Any]:
        """Проверяет здоровье fallback стратегий."""
        try:
            # Проверяем placeholder fallback
            placeholder_check = await self.placeholder_fallback.execute({
                "test": True,
                "operation": "health_check"
            })
            
            # Проверяем alternative URL fallback
            alt_url_check = await self.alternative_url_fallback.execute({
                "test": True,
                "urls": ["https://example.com/test.jpg"],
                "operation": "health_check"
            })
            
            # Проверяем graceful degradation
            degradation_check = await self.graceful_degradation.execute({
                "test": True,
                "error_severity": ErrorSeverity.WARNING,
                "operation": "health_check"
            })
            
            all_healthy = all([
                placeholder_check.success,
                alt_url_check.success,
                degradation_check.success
            ])
            
            return {
                "status": "healthy" if all_healthy else "degraded",
                "strategies": {
                    "placeholder": placeholder_check.success,
                    "alternative_url": alt_url_check.success,
                    "graceful_degradation": degradation_check.success
                }
            }
            
        except Exception as e:
            return {"status": "unhealthy", "error": f"Fallback health check failed: {e}"}
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Возвращает текущий статус сервиса.
        
        Returns:
            Dict[str, Any]: Статус сервиса
        """
        # Детальное логирование начала получения статуса
        self.logger.debug(
            "[ImageService] Получаем статус сервиса",
            extra={
                "operation": "get_service_status",
                "result": "starting_status_collection"
            }
        )
        
        try:
            status = {
                "service": "ImageService",
                "config": {
                    "cache_enabled": self.config.enable_cache,
                    "max_file_size": self.config.max_file_size,
                    "retry_attempts": self.config.retry_attempts,
                    "download_timeout": self.config.download_timeout
                },
                "session": self.session_manager.get_session_info(),
                "cache_stats": self._get_cache_stats(),
                "error_metrics": self._get_error_metrics_summary()
            }
            
            # Детальное логирование успешного получения статуса
            self.logger.debug(
                "[ImageService] Статус сервиса получен успешно",
                extra={
                    "operation": "get_service_status",
                    "service_status": status,
                    "result": "status_collection_success"
                }
            )
            
            return status
            
        except Exception as e:
            # Обрабатываем ошибку через ErrorHandler
            operation_context = {
                "operation_type": "get_service_status"
            }
            
            custom_error = self.error_handler.handle_error(e, operation_context)
            
            # Детальное логирование ошибки
            self.logger.error(
                f"[ImageService] Ошибка при получении статуса сервиса: {custom_error.message}",
                extra={
                    "operation": "get_service_status",
                    "error_context": custom_error.context,
                    "result": "status_collection_failed"
                }
            )
            
            return {
                "service": "ImageService",
                "status": "error",
                "error": custom_error.message,
                "error_context": custom_error.context
            }
    
    def _get_cache_stats(self) -> Dict[str, Any]:
        """Получает статистику кэша."""
        # Детальное логирование начала получения статистики кэша
        self.logger.debug(
            "[ImageService] Получаем статистику кэша",
            extra={
                "operation": "get_cache_stats",
                "cache_enabled": self.config.enable_cache,
                "result": "starting_cache_stats"
            }
        )
        
        if not self.config.enable_cache:
            self.logger.debug(
                "[ImageService] Кэш отключен",
                extra={
                    "operation": "get_cache_stats",
                    "result": "cache_disabled"
                }
            )
            return {"enabled": False}
        
        try:
            pattern = os.path.join(self.config.cache_dir, "*")
            cache_files = glob.glob(pattern)
            
            total_size = 0
            for file_path in cache_files:
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
            
            stats = {
                "enabled": True,
                "file_count": len(cache_files),
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024**2)
            }
            
            # Детальное логирование успешного получения статистики кэша
            self.logger.debug(
                "[ImageService] Статистика кэша получена успешно",
                extra={
                    "operation": "get_cache_stats",
                    "cache_stats": stats,
                    "result": "cache_stats_success"
                }
            )
            
            return stats
            
        except Exception as e:
            # Обрабатываем ошибку через ErrorHandler
            operation_context = {
                "operation_type": "get_cache_stats"
            }
            
            custom_error = self.error_handler.handle_error(e, operation_context)
            
            # Детальное логирование ошибки
            self.logger.error(
                f"[ImageService] Ошибка при получении статистики кэша: {custom_error.message}",
                extra={
                    "operation": "get_cache_stats",
                    "error_context": custom_error.context,
                    "result": "cache_stats_failed"
                }
            )
            
            return {"enabled": True, "error": custom_error.message}
    
    def _get_error_metrics_summary(self) -> Dict[str, Any]:
        """Получает краткую сводку метрик ошибок."""
        try:
            # Детальное логирование начала получения метрик
            self.logger.debug(
                "[ImageService] Получаем сводку метрик ошибок",
                extra={
                    "operation": "get_error_metrics_summary",
                    "result": "starting_metrics_collection"
                }
            )
            
            metrics = get_error_metrics()
            stats = metrics.get_error_stats()
            
            summary = {
                "health_score": metrics.get_health_score(),
                "total_errors": stats.total_errors,
                "recent_errors": len(metrics.get_recent_errors()),
                "error_rate": stats.error_rate_per_minute
            }
            
            # Детальное логирование успешного получения метрик
            self.logger.debug(
                "[ImageService] Метрики ошибок получены успешно",
                extra={
                    "operation": "get_error_metrics_summary",
                    "metrics_summary": summary,
                    "result": "metrics_collection_success"
                }
            )
            
            return summary
            
        except Exception as e:
            # Обрабатываем ошибку через ErrorHandler
            operation_context = {
                "operation_type": "get_error_metrics_summary"
            }
            
            custom_error = self.error_handler.handle_error(e, operation_context)
            
            # Детальное логирование ошибки
            self.logger.error(
                f"[ImageService] Ошибка при получении метрик ошибок: {custom_error.message}",
                extra={
                    "operation": "get_error_metrics_summary",
                    "error_context": custom_error.context,
                    "result": "metrics_collection_failed"
                }
            )
            return {"error": f"Failed to get error metrics: {custom_error.message}"}
