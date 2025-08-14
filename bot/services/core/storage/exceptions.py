"""
Типизированные исключения для storage сервиса
Создано согласно TDD плану для правильной обработки ошибок
"""


class StorageError(Exception):
    """Базовый класс для всех ошибок storage сервиса"""
    
    def __init__(self, message: str, status_code: int = None, provider: str = None):
        self.message = message
        self.status_code = status_code
        self.provider = provider
        super().__init__(self.message)
    
    def __str__(self):
        provider_info = f" [{self.provider}]" if self.provider else ""
        status_info = f" (HTTP {self.status_code})" if self.status_code else ""
        return f"{self.message}{status_info}{provider_info}"


class StorageAuthError(StorageError):
    """Ошибка аутентификации (401 Unauthorized)"""
    
    def __init__(self, message: str = "Authentication failed", provider: str = None):
        super().__init__(message, status_code=401, provider=provider)


class StoragePermissionError(StorageError):
    """Ошибка разрешений (403 Forbidden)"""
    
    def __init__(self, message: str = "Insufficient permissions", provider: str = None):
        super().__init__(message, status_code=403, provider=provider)


class StorageRateLimitError(StorageError):
    """Ошибка rate limiting (429 Too Many Requests)"""
    
    def __init__(self, message: str = "Rate limit exceeded", provider: str = None, retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(message, status_code=429, provider=provider)
    
    def __str__(self):
        base = super().__str__()
        if self.retry_after:
            return f"{base} (retry after {self.retry_after}s)"
        return base


class StorageNotFoundError(StorageError):
    """Ошибка - ресурс не найден (404 Not Found)"""
    
    def __init__(self, message: str = "Resource not found", provider: str = None, cid: str = None):
        self.cid = cid
        super().__init__(message, status_code=404, provider=provider)
    
    def __str__(self):
        base = super().__str__()
        if self.cid:
            return f"{base} (CID: {self.cid})"
        return base


class StorageValidationError(StorageError):
    """Ошибка валидации данных (400 Bad Request)"""
    
    def __init__(self, message: str = "Validation failed", provider: str = None, field: str = None):
        self.field = field
        super().__init__(message, status_code=400, provider=provider)
    
    def __str__(self):
        base = super().__str__()
        if self.field:
            return f"{base} (field: {self.field})"
        return base


class StorageTimeoutError(StorageError):
    """Ошибка таймаута"""
    
    def __init__(self, message: str = "Operation timeout", provider: str = None, timeout: float = None):
        self.timeout = timeout
        super().__init__(message, status_code=None, provider=provider)
    
    def __str__(self):
        base = super().__str__()
        if self.timeout:
            return f"{base} (timeout: {self.timeout}s)"
        return base


class StorageNetworkError(StorageError):
    """Ошибка сети"""
    
    def __init__(self, message: str = "Network error", provider: str = None, original_error: Exception = None):
        self.original_error = original_error
        super().__init__(message, status_code=None, provider=provider)
    
    def __str__(self):
        base = super().__str__()
        if self.original_error:
            return f"{base} (original: {self.original_error})"
        return base


class StorageConfigError(StorageError):
    """Ошибка конфигурации"""
    
    def __init__(self, message: str = "Configuration error", missing_key: str = None):
        self.missing_key = missing_key
        super().__init__(message, status_code=None, provider=None)
    
    def __str__(self):
        base = super().__str__()
        if self.missing_key:
            return f"{base} (missing: {self.missing_key})"
        return base


class StorageProviderError(StorageError):
    """Ошибка провайдера (5xx Server Error)"""
    
    def __init__(self, message: str = "Provider error", provider: str = None, status_code: int = None):
        super().__init__(message, status_code=status_code or 500, provider=provider)


# Утилитарные функции для создания исключений
def create_storage_error_from_http_response(status_code: int, message: str = None, provider: str = None) -> StorageError:
    """Создает соответствующее исключение на основе HTTP статус кода"""
    
    if status_code == 401:
        return StorageAuthError(message or "Authentication failed", provider=provider)
    elif status_code == 403:
        return StoragePermissionError(message or "Insufficient permissions", provider=provider)
    elif status_code == 404:
        return StorageNotFoundError(message or "Resource not found", provider=provider)
    elif status_code == 429:
        return StorageRateLimitError(message or "Rate limit exceeded", provider=provider)
    elif status_code == 400:
        return StorageValidationError(message or "Bad request", provider=provider)
    elif status_code >= 500:
        return StorageProviderError(message or f"Provider error ({status_code})", provider=provider, status_code=status_code)
    else:
        return StorageError(message or f"HTTP error {status_code}", status_code=status_code, provider=provider)


def create_storage_error_from_exception(exception: Exception, provider: str = None) -> StorageError:
    """Создает StorageError из обычного исключения"""
    
    if isinstance(exception, StorageError):
        return exception
    
    error_message = str(exception)
    
    # Определяем тип ошибки по сообщению
    if "timeout" in error_message.lower():
        return StorageTimeoutError(f"Operation timeout: {error_message}", provider=provider)
    elif "connection" in error_message.lower() or "network" in error_message.lower():
        return StorageNetworkError(f"Network error: {error_message}", provider=provider, original_error=exception)
    else:
        return StorageError(f"Storage error: {error_message}", provider=provider) 