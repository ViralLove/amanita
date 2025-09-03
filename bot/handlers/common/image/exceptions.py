"""
Кастомные исключения для ImageService.
Классификация ошибок по типам и уровням серьезности.
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorSeverity(Enum):
    """Уровни серьезности ошибок."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Категории ошибок."""
    NETWORK = "network"
    FILE = "file"
    VALIDATION = "validation"
    SESSION = "session"
    UNKNOWN = "unknown"


class ImageDownloadError(Exception):
    """
    Базовое исключение для всех ошибок загрузки изображений.
    
    Attributes:
        message: Сообщение об ошибке
        category: Категория ошибки
        severity: Уровень серьезности
        error_code: Уникальный код ошибки
        context: Дополнительный контекст
        original_error: Исходное исключение
    """
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.error_code = error_code or f"{category.value}_{severity.value}"
        self.context = context or {}
        self.original_error = original_error
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message='{self.message}', category={self.category}, severity={self.severity})"


class NetworkError(ImageDownloadError):
    """Ошибки сетевого уровня."""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=severity,
            error_code=error_code,
            context=context,
            original_error=original_error
        )


class ConnectionTimeoutError(NetworkError):
    """Ошибка таймаута соединения."""
    
    def __init__(
        self,
        timeout: float,
        url: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Timeout ({timeout}s) при подключении к {url}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="NETWORK_TIMEOUT",
            context=context or {"timeout": timeout, "url": url},
            original_error=original_error
        )


class ConnectionRefusedError(NetworkError):
    """Ошибка отказа в соединении."""
    
    def __init__(
        self,
        url: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Отказ в соединении к {url}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="NETWORK_CONNECTION_REFUSED",
            context=context or {"url": url},
            original_error=original_error
        )


class DNSResolutionError(NetworkError):
    """Ошибка резолвинга DNS."""
    
    def __init__(
        self,
        url: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Ошибка резолвинга DNS для {url}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="NETWORK_DNS_RESOLUTION",
            context=context or {"url": url},
            original_error=original_error
        )


class HTTPStatusError(NetworkError):
    """Ошибка HTTP статуса."""
    
    def __init__(
        self,
        status_code: int,
        url: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"HTTP {status_code} для {url}"
        severity = ErrorSeverity.WARNING if status_code < 500 else ErrorSeverity.ERROR
        super().__init__(
            message=message,
            severity=severity,
            error_code=f"NETWORK_HTTP_{status_code}",
            context=context or {"status_code": status_code, "url": url},
            original_error=original_error
        )


class FileError(ImageDownloadError):
    """Ошибки файловой системы."""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.FILE,
            severity=severity,
            error_code=error_code,
            context=context,
            original_error=original_error
        )


class DiskFullError(FileError):
    """Ошибка нехватки места на диске."""
    
    def __init__(
        self,
        path: str,
        available_space: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Нехватка места на диске для {path}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            error_code="FILE_DISK_FULL",
            context=context or {"path": path, "available_space": available_space},
            original_error=original_error
        )


class PermissionDeniedError(FileError):
    """Ошибка отказа в доступе к файлу."""
    
    def __init__(
        self,
        path: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Отказ в доступе к файлу {path}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="FILE_PERMISSION_DENIED",
            context=context or {"path": path},
            original_error=original_error
        )


class FileCorruptedError(FileError):
    """Ошибка поврежденного файла."""
    
    def __init__(
        self,
        path: str,
        corruption_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Файл поврежден: {path}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="FILE_CORRUPTED",
            context=context or {"path": path, "corruption_type": corruption_type},
            original_error=original_error
        )


class ValidationError(ImageDownloadError):
    """Ошибки валидации."""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=severity,
            error_code=error_code,
            context=context,
            original_error=original_error
        )


class InvalidURLError(ValidationError):
    """Ошибка некорректного URL."""
    
    def __init__(
        self,
        url: str,
        reason: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Некорректный URL: {url}"
        if reason:
            message += f" (причина: {reason})"
        super().__init__(
            message=message,
            severity=ErrorSeverity.WARNING,
            error_code="VALIDATION_INVALID_URL",
            context=context or {"url": url, "reason": reason},
            original_error=original_error
        )


class UnsupportedFormatError(ValidationError):
    """Ошибка неподдерживаемого формата."""
    
    def __init__(
        self,
        format_type: str,
        supported_formats: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Неподдерживаемый формат: {format_type}"
        if supported_formats:
            message += f" (поддерживаемые: {', '.join(supported_formats)})"
        super().__init__(
            message=message,
            severity=ErrorSeverity.WARNING,
            error_code="VALIDATION_UNSUPPORTED_FORMAT",
            context=context or {"format_type": format_type, "supported_formats": supported_formats},
            original_error=original_error
        )


class FileTooLargeError(ValidationError):
    """Ошибка превышения размера файла."""
    
    def __init__(
        self,
        file_size: int,
        max_size: int,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Файл слишком большой: {file_size} bytes (максимум: {max_size} bytes)"
        super().__init__(
            message=message,
            severity=ErrorSeverity.WARNING,
            error_code="VALIDATION_FILE_TOO_LARGE",
            context=context or {"file_size": file_size, "max_size": max_size},
            original_error=original_error
        )


class SessionError(ImageDownloadError):
    """Ошибки HTTP сессии."""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.SESSION,
            severity=severity,
            error_code=error_code,
            context=context,
            original_error=original_error
        )


class SessionClosedError(SessionError):
    """Ошибка закрытой сессии."""
    
    def __init__(
        self,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = "Попытка использовать закрытую HTTP сессию"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="SESSION_CLOSED",
            context=context,
            original_error=original_error
        )


class ContentTypeMismatchError(SessionError):
    """Ошибка несоответствия типа контента."""
    
    def __init__(
        self,
        expected_type: str,
        actual_type: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Несоответствие типа контента: ожидался {expected_type}, получен {actual_type}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.WARNING,
            error_code="SESSION_CONTENT_TYPE_MISMATCH",
            context=context or {"expected_type": expected_type, "actual_type": actual_type},
            original_error=original_error
        )


# Дополнительные сетевые ошибки
class SSLHandshakeError(NetworkError):
    """Ошибка SSL handshake."""
    
    def __init__(
        self,
        url: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Ошибка SSL handshake для {url}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="NETWORK_SSL_HANDSHAKE",
            context=context or {"url": url},
            original_error=original_error
        )


class ProxyError(NetworkError):
    """Ошибка прокси."""
    
    def __init__(
        self,
        proxy_url: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Ошибка прокси: {proxy_url}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="NETWORK_PROXY_ERROR",
            context=context or {"proxy_url": proxy_url},
            original_error=original_error
        )


class RateLimitError(NetworkError):
    """Ошибка превышения лимита запросов."""
    
    def __init__(
        self,
        url: str,
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Превышен лимит запросов для {url}"
        if retry_after:
            message += f" (повторить через {retry_after}s)"
        super().__init__(
            message=message,
            severity=ErrorSeverity.WARNING,
            error_code="NETWORK_RATE_LIMIT",
            context=context or {"url": url, "retry_after": retry_after},
            original_error=original_error
        )


# Дополнительные файловые ошибки
class FileLockedError(FileError):
    """Ошибка заблокированного файла."""
    
    def __init__(
        self,
        path: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Файл заблокирован: {path}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="FILE_LOCKED",
            context=context or {"path": path},
            original_error=original_error
        )


class FileSystemError(FileError):
    """Ошибка файловой системы."""
    
    def __init__(
        self,
        path: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Ошибка файловой системы при {operation}: {path}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="FILE_SYSTEM_ERROR",
            context=context or {"path": path, "operation": operation},
            original_error=original_error
        )


class InsufficientSpaceError(FileError):
    """Ошибка нехватки места на диске."""
    
    def __init__(
        self,
        required_space: int,
        available_space: int,
        path: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Недостаточно места: требуется {required_space}, доступно {available_space} для {path}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            error_code="FILE_INSUFFICIENT_SPACE",
            context=context or {"required_space": required_space, "available_space": available_space, "path": path},
            original_error=original_error
        )


# Дополнительные ошибки валидации
class InvalidImageFormatError(ValidationError):
    """Ошибка недопустимого формата изображения."""
    
    def __init__(
        self,
        format_type: str,
        supported_formats: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Недопустимый формат изображения: {format_type}"
        if supported_formats:
            message += f" (поддерживаемые: {', '.join(supported_formats)})"
        super().__init__(
            message=message,
            severity=ErrorSeverity.WARNING,
            error_code="VALIDATION_INVALID_IMAGE_FORMAT",
            context=context or {"format_type": format_type, "supported_formats": supported_formats},
            original_error=original_error
        )


class ImageCorruptedError(ValidationError):
    """Ошибка поврежденного изображения."""
    
    def __init__(
        self,
        path: str,
        corruption_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Поврежденное изображение: {path}"
        if corruption_type:
            message += f" (тип повреждения: {corruption_type})"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="VALIDATION_IMAGE_CORRUPTED",
            context=context or {"path": path, "corruption_type": corruption_type},
            original_error=original_error
        )


class ImageDimensionsError(ValidationError):
    """Ошибка размеров изображения."""
    
    def __init__(
        self,
        width: int,
        height: int,
        max_width: int,
        max_height: int,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Недопустимые размеры изображения: {width}x{height} (максимум: {max_width}x{max_height})"
        super().__init__(
            message=message,
            severity=ErrorSeverity.WARNING,
            error_code="VALIDATION_IMAGE_DIMENSIONS",
            context=context or {"width": width, "height": height, "max_width": max_width, "max_height": max_height},
            original_error=original_error
        )


# Дополнительные ошибки сессий
class SessionTimeoutError(SessionError):
    """Ошибка таймаута сессии."""
    
    def __init__(
        self,
        timeout: float,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Таймаут сессии: {timeout}s"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="SESSION_TIMEOUT",
            context=context or {"timeout": timeout},
            original_error=original_error
        )


class SessionPoolExhaustedError(SessionError):
    """Ошибка исчерпания пула сессий."""
    
    def __init__(
        self,
        pool_size: int,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Исчерпан пул сессий (размер: {pool_size})"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="SESSION_POOL_EXHAUSTED",
            context=context or {"pool_size": pool_size},
            original_error=original_error
        )


class SessionConfigurationError(SessionError):
    """Ошибка конфигурации сессии."""
    
    def __init__(
        self,
        config_key: str,
        config_value: Any,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Ошибка конфигурации сессии: {config_key}={config_value}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            error_code="SESSION_CONFIGURATION_ERROR",
            context=context or {"config_key": config_key, "config_value": config_value},
            original_error=original_error
        )


# Функция для создания ошибки из стандартного исключения
def create_image_error(
    error: Exception,
    category: ErrorCategory,
    context: Optional[Dict[str, Any]] = None
) -> ImageDownloadError:
    """
    Создает ImageDownloadError из стандартного исключения.
    
    Args:
        error: Стандартное исключение
        category: Категория ошибки
        context: Дополнительный контекст
        
    Returns:
        ImageDownloadError: Кастомное исключение
    """
    if isinstance(error, ImageDownloadError):
        return error
    
    # Определяем тип ошибки по классу
    if isinstance(error, TimeoutError):
        return ConnectionTimeoutError(
            timeout=getattr(error, 'timeout', 30),
            url=context.get('url', 'unknown') if context else 'unknown',
            context=context,
            original_error=error
        )
    elif isinstance(error, ConnectionError):
        return ConnectionRefusedError(
            url=context.get('url', 'unknown') if context else 'unknown',
            context=context,
            original_error=error
        )
    elif isinstance(error, OSError):
        if error.errno == 28:  # No space left on device
            return DiskFullError(
                path=context.get('path', 'unknown') if context else 'unknown',
                context=context,
                original_error=error
            )
        elif error.errno == 13:  # Permission denied
            return PermissionDeniedError(
                path=context.get('path', 'unknown') if context else 'unknown',
                context=context,
                original_error=error
            )
        else:
            return FileError(
                message=str(error),
                context=context,
                original_error=error
            )
    else:
        return ImageDownloadError(
            message=str(error),
            category=category,
            context=context,
            original_error=error
        )
