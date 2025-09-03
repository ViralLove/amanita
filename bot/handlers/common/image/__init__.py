"""
Модуль для работы с изображениями.
Содержит сервисы, интерфейсы и конфигурации для обработки изображений.
"""

# Импортируем интерфейс
from .image_service_interface import IImageService

# Импортируем конфигурацию
from .image_service_config import ImageServiceConfig

# Импортируем основной сервис
from .image_service import ImageService

# Импортируем session manager
from .session_manager import SessionManager

# Импортируем обработчик ошибок
from .error_handler import ImageErrorHandler, RetryStrategy, FallbackStrategy

# Импортируем исключения
from .exceptions import (
    ImageDownloadError, NetworkError, FileError, ValidationError, SessionError,
    ErrorCategory, ErrorSeverity, create_image_error
)

# Импортируем систему error codes
from .error_codes import (
    ErrorCodeRegistry, ErrorCodeInfo, get_error_code_registry,
    register_error_code, get_error_code_info, validate_error_codes
)

# Импортируем систему метрик
from .error_metrics import (
    ErrorMetrics, ErrorMetric, ErrorStats, get_error_metrics,
    record_error, get_error_stats
)

# Импортируем систему мониторинга
from .error_monitoring import (
    ErrorMonitoring, MonitoringBackend, PrometheusBackend, LoggingBackend,
    AlertRule, HealthCheck, get_error_monitoring, setup_prometheus_monitoring,
    start_monitoring
)

# Импортируем улучшенные fallback стратегии
from .fallback_strategies import (
    DegradationLevel, FallbackResult, ProgressTracker, UserNotifier,
    EnhancedPlaceholderImageFallbackStrategy, AlternativeURLRetryStrategy,
    GracefulDegradationStrategy
)

# Импортируем систему прогресс-индикаторов
from .progress_indicators import (
    ProgressStatus, ProgressType, ProgressStep, ProgressInfo,
    ProgressCallback, LoggingProgressCallback, TelegramProgressCallback,
    ProgressManager, get_progress_manager, add_progress_callback,
    remove_progress_callback
)

# Импортируем dependency providers
from .dependencies import (
    get_image_service,
    get_image_service_with_config,
    get_default_image_service_config,
    get_optimized_image_service_config,
    get_fast_image_service_config
)

# Экспортируем основные компоненты
__all__ = [
    # Интерфейсы
    'IImageService',
    
    # Конфигурации
    'ImageServiceConfig',
    
    # Сервисы
    'ImageService',
    
    # Session management
    'SessionManager',
    
    # Error handling
    'ImageErrorHandler',
    'RetryStrategy',
    'FallbackStrategy',
    
    # Exceptions
    'ImageDownloadError',
    'NetworkError',
    'FileError',
    'ValidationError',
    'SessionError',
    'ErrorCategory',
    'ErrorSeverity',
    'create_image_error',
    
    # Error codes
    'ErrorCodeRegistry',
    'ErrorCodeInfo',
    'get_error_code_registry',
    'register_error_code',
    'get_error_code_info',
    'validate_error_codes',
    
    # Error metrics
    'ErrorMetrics',
    'ErrorMetric',
    'ErrorStats',
    'get_error_metrics',
    'record_error',
    'get_error_stats',
    
    # Error monitoring
    'ErrorMonitoring',
    'MonitoringBackend',
    'PrometheusBackend',
    'LoggingBackend',
    'AlertRule',
    'HealthCheck',
    'get_error_monitoring',
    'setup_prometheus_monitoring',
    'start_monitoring',
    
    # Fallback strategies
    'DegradationLevel',
    'FallbackResult',
    'ProgressTracker',
    'UserNotifier',
    'EnhancedPlaceholderImageFallbackStrategy',
    'AlternativeURLRetryStrategy',
    'GracefulDegradationStrategy',
    
    # Progress indicators
    'ProgressStatus',
    'ProgressType',
    'ProgressStep',
    'ProgressInfo',
    'ProgressCallback',
    'LoggingProgressCallback',
    'TelegramProgressCallback',
    'ProgressManager',
    'get_progress_manager',
    'add_progress_callback',
    'remove_progress_callback',
    
    # Dependency providers
    'get_image_service',
    'get_image_service_with_config',
    'get_default_image_service_config',
    'get_optimized_image_service_config',
    'get_fast_image_service_config',
]
