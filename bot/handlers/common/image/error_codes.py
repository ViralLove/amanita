"""
Система error codes для ImageService.
Обеспечивает уникальные коды ошибок для мониторинга и отслеживания.
"""

import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

from .exceptions import ErrorCategory, ErrorSeverity


@dataclass
class ErrorCodeInfo:
    """Информация об error code."""
    code: str
    category: ErrorCategory
    severity: ErrorSeverity
    description: str
    retryable: bool = False
    fallback_available: bool = True


class ErrorCodeRegistry:
    """
    Реестр error codes с валидацией уникальности.
    
    Обеспечивает:
    - Уникальность всех error codes
    - Структурированную регистрацию
    - Валидацию паттернов
    - Документацию кодов
    """
    
    def __init__(self):
        self._codes: Dict[str, ErrorCodeInfo] = {}
        self._logger = logging.getLogger(__name__)
        self._initialize_default_codes()
    
    def _initialize_default_codes(self):
        """Инициализирует стандартные error codes."""
        # Network error codes
        self.register_code(
            "NETWORK_TIMEOUT",
            ErrorCategory.NETWORK,
            ErrorSeverity.ERROR,
            "Timeout при подключении к серверу",
            retryable=True
        )
        
        self.register_code(
            "NETWORK_CONNECTION_REFUSED",
            ErrorCategory.NETWORK,
            ErrorSeverity.ERROR,
            "Отказ в соединении",
            retryable=True
        )
        
        self.register_code(
            "NETWORK_DNS_RESOLUTION",
            ErrorCategory.NETWORK,
            ErrorSeverity.ERROR,
            "Ошибка резолвинга DNS",
            retryable=True
        )
        
        self.register_code(
            "NETWORK_SSL_HANDSHAKE",
            ErrorCategory.NETWORK,
            ErrorSeverity.ERROR,
            "Ошибка SSL handshake",
            retryable=True
        )
        
        self.register_code(
            "NETWORK_PROXY_ERROR",
            ErrorCategory.NETWORK,
            ErrorSeverity.ERROR,
            "Ошибка прокси",
            retryable=True
        )
        
        self.register_code(
            "NETWORK_RATE_LIMIT",
            ErrorCategory.NETWORK,
            ErrorSeverity.WARNING,
            "Превышен лимит запросов",
            retryable=True
        )
        
        # HTTP status codes
        for status_code in [400, 401, 403, 404, 429, 500, 502, 503, 504]:
            severity = ErrorSeverity.WARNING if status_code < 500 else ErrorSeverity.ERROR
            retryable = status_code in [429, 500, 502, 503, 504]
            
            self.register_code(
                f"NETWORK_HTTP_{status_code}",
                ErrorCategory.NETWORK,
                severity,
                f"HTTP {status_code} ответ",
                retryable=retryable
            )
        
        # File error codes
        self.register_code(
            "FILE_DISK_FULL",
            ErrorCategory.FILE,
            ErrorSeverity.CRITICAL,
            "Нехватка места на диске",
            retryable=False,
            fallback_available=True
        )
        
        self.register_code(
            "FILE_PERMISSION_DENIED",
            ErrorCategory.FILE,
            ErrorSeverity.ERROR,
            "Отказ в доступе к файлу",
            retryable=True
        )
        
        self.register_code(
            "FILE_CORRUPTED",
            ErrorCategory.FILE,
            ErrorSeverity.ERROR,
            "Поврежденный файл",
            retryable=False
        )
        
        self.register_code(
            "FILE_LOCKED",
            ErrorCategory.FILE,
            ErrorSeverity.ERROR,
            "Файл заблокирован",
            retryable=True
        )
        
        self.register_code(
            "FILE_SYSTEM_ERROR",
            ErrorCategory.FILE,
            ErrorSeverity.ERROR,
            "Ошибка файловой системы",
            retryable=True
        )
        
        self.register_code(
            "FILE_INSUFFICIENT_SPACE",
            ErrorCategory.FILE,
            ErrorSeverity.CRITICAL,
            "Недостаточно места на диске",
            retryable=False,
            fallback_available=True
        )
        
        # Validation error codes
        self.register_code(
            "VALIDATION_INVALID_URL",
            ErrorCategory.VALIDATION,
            ErrorSeverity.WARNING,
            "Некорректный URL",
            retryable=False
        )
        
        self.register_code(
            "VALIDATION_UNSUPPORTED_FORMAT",
            ErrorCategory.VALIDATION,
            ErrorSeverity.WARNING,
            "Неподдерживаемый формат",
            retryable=False
        )
        
        self.register_code(
            "VALIDATION_FILE_TOO_LARGE",
            ErrorCategory.VALIDATION,
            ErrorSeverity.WARNING,
            "Файл слишком большой",
            retryable=False
        )
        
        self.register_code(
            "VALIDATION_INVALID_IMAGE_FORMAT",
            ErrorCategory.VALIDATION,
            ErrorSeverity.WARNING,
            "Недопустимый формат изображения",
            retryable=False
        )
        
        self.register_code(
            "VALIDATION_IMAGE_CORRUPTED",
            ErrorCategory.VALIDATION,
            ErrorSeverity.ERROR,
            "Поврежденное изображение",
            retryable=False
        )
        
        self.register_code(
            "VALIDATION_IMAGE_DIMENSIONS",
            ErrorCategory.VALIDATION,
            ErrorSeverity.WARNING,
            "Недопустимые размеры изображения",
            retryable=False
        )
        
        # Session error codes
        self.register_code(
            "SESSION_CLOSED",
            ErrorCategory.SESSION,
            ErrorSeverity.ERROR,
            "Попытка использовать закрытую сессию",
            retryable=True
        )
        
        self.register_code(
            "SESSION_CONTENT_TYPE_MISMATCH",
            ErrorCategory.SESSION,
            ErrorSeverity.WARNING,
            "Несоответствие типа контента",
            retryable=False
        )
        
        self.register_code(
            "SESSION_TIMEOUT",
            ErrorCategory.SESSION,
            ErrorSeverity.ERROR,
            "Таймаут сессии",
            retryable=True
        )
        
        self.register_code(
            "SESSION_POOL_EXHAUSTED",
            ErrorCategory.SESSION,
            ErrorSeverity.ERROR,
            "Исчерпан пул сессий",
            retryable=True
        )
        
        self.register_code(
            "SESSION_CONFIGURATION_ERROR",
            ErrorCategory.SESSION,
            ErrorSeverity.ERROR,
            "Ошибка конфигурации сессии",
            retryable=False
        )
        
        self._logger.info(f"[ErrorCodeRegistry] Инициализирован с {len(self._codes)} error codes")
    
    def register_code(
        self,
        code: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        description: str,
        retryable: bool = False,
        fallback_available: bool = True
    ) -> None:
        """
        Регистрирует новый error code.
        
        Args:
            code: Уникальный код ошибки
            category: Категория ошибки
            severity: Уровень серьезности
            description: Описание ошибки
            retryable: Можно ли повторить операцию
            fallback_available: Доступен ли fallback
            
        Raises:
            ValueError: Если код уже существует или не соответствует паттерну
        """
        # Валидация паттерна кода
        if not self._validate_code_pattern(code):
            raise ValueError(f"Invalid error code pattern: {code}")
        
        # Проверка уникальности
        if code in self._codes:
            raise ValueError(f"Error code already exists: {code}")
        
        # Регистрация кода
        self._codes[code] = ErrorCodeInfo(
            code=code,
            category=category,
            severity=severity,
            description=description,
            retryable=retryable,
            fallback_available=fallback_available
        )
        
        self._logger.debug(f"Registered error code: {code}")
    
    def _validate_code_pattern(self, code: str) -> bool:
        """
        Валидирует паттерн error code.
        
        Args:
            code: Код для валидации
            
        Returns:
            bool: True если паттерн корректный
        """
        # Паттерн: CATEGORY_TYPE или CATEGORY_TYPE_SUBTYPE или CATEGORY_TYPE_NUMBER
        import re
        pattern = r'^[A-Z]+_[A-Z_0-9]+$'
        return bool(re.match(pattern, code))
    
    def get_code_info(self, code: str) -> Optional[ErrorCodeInfo]:
        """
        Получает информацию об error code.
        
        Args:
            code: Код ошибки
            
        Returns:
            ErrorCodeInfo: Информация о коде или None
        """
        return self._codes.get(code)
    
    def get_codes_by_category(self, category: ErrorCategory) -> List[ErrorCodeInfo]:
        """
        Получает все коды по категории.
        
        Args:
            category: Категория ошибки
            
        Returns:
            List[ErrorCodeInfo]: Список кодов
        """
        return [info for info in self._codes.values() if info.category == category]
    
    def get_codes_by_severity(self, severity: ErrorSeverity) -> List[ErrorCodeInfo]:
        """
        Получает все коды по уровню серьезности.
        
        Args:
            severity: Уровень серьезности
            
        Returns:
            List[ErrorCodeInfo]: Список кодов
        """
        return [info for info in self._codes.values() if info.severity == severity]
    
    def get_retryable_codes(self) -> List[ErrorCodeInfo]:
        """
        Получает все retryable коды.
        
        Returns:
            List[ErrorCodeInfo]: Список retryable кодов
        """
        return [info for info in self._codes.values() if info.retryable]
    
    def get_fallback_available_codes(self) -> List[ErrorCodeInfo]:
        """
        Получает все коды с доступным fallback.
        
        Returns:
            List[ErrorCodeInfo]: Список кодов с fallback
        """
        return [info for info in self._codes.values() if info.fallback_available]
    
    def validate_uniqueness(self) -> bool:
        """
        Валидирует уникальность всех кодов.
        
        Returns:
            bool: True если все коды уникальны
        """
        codes = list(self._codes.keys())
        unique_codes = set(codes)
        return len(codes) == len(unique_codes)
    
    def get_all_codes(self) -> Dict[str, ErrorCodeInfo]:
        """
        Получает все зарегистрированные коды.
        
        Returns:
            Dict[str, ErrorCodeInfo]: Словарь всех кодов
        """
        return self._codes.copy()
    
    def get_code_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по кодам.
        
        Returns:
            Dict[str, Any]: Статистика
        """
        total_codes = len(self._codes)
        codes_by_category = {}
        codes_by_severity = {}
        
        for info in self._codes.values():
            # По категориям
            category_name = info.category.value
            codes_by_category[category_name] = codes_by_category.get(category_name, 0) + 1
            
            # По уровням серьезности
            severity_name = info.severity.value
            codes_by_severity[severity_name] = codes_by_severity.get(severity_name, 0) + 1
        
        retryable_count = len(self.get_retryable_codes())
        fallback_count = len(self.get_fallback_available_codes())
        
        return {
            "total_codes": total_codes,
            "codes_by_category": codes_by_category,
            "codes_by_severity": codes_by_severity,
            "retryable_codes": retryable_count,
            "fallback_available_codes": fallback_count,
            "unique_codes": self.validate_uniqueness()
        }
    
    def export_documentation(self) -> str:
        """
        Экспортирует документацию по всем кодам.
        
        Returns:
            str: Markdown документация
        """
        lines = ["# Error Codes Documentation", ""]
        
        # Статистика
        stats = self.get_code_statistics()
        lines.extend([
            "## Statistics",
            f"- Total codes: {stats['total_codes']}",
            f"- Unique codes: {stats['unique_codes']}",
            f"- Retryable codes: {stats['retryable_codes']}",
            f"- Fallback available codes: {stats['fallback_available_codes']}",
            ""
        ])
        
        # По категориям
        for category in ErrorCategory:
            category_codes = self.get_codes_by_category(category)
            if category_codes:
                lines.extend([
                    f"## {category.value.upper()} Errors",
                    ""
                ])
                
                for info in sorted(category_codes, key=lambda x: x.code):
                    lines.extend([
                        f"### {info.code}",
                        f"- **Severity**: {info.severity.value}",
                        f"- **Description**: {info.description}",
                        f"- **Retryable**: {info.retryable}",
                        f"- **Fallback Available**: {info.fallback_available}",
                        ""
                    ])
        
        return "\n".join(lines)
    
    def cleanup(self):
        """Очищает реестр."""
        self._codes.clear()
        self._logger.info("[ErrorCodeRegistry] Cleanup completed")


# Глобальный экземпляр реестра
_error_code_registry = ErrorCodeRegistry()


def get_error_code_registry() -> ErrorCodeRegistry:
    """
    Получает глобальный экземпляр реестра error codes.
    
    Returns:
        ErrorCodeRegistry: Глобальный реестр
    """
    return _error_code_registry


def register_error_code(
    code: str,
    category: ErrorCategory,
    severity: ErrorSeverity,
    description: str,
    retryable: bool = False,
    fallback_available: bool = True
) -> None:
    """
    Регистрирует error code в глобальном реестре.
    
    Args:
        code: Уникальный код ошибки
        category: Категория ошибки
        severity: Уровень серьезности
        description: Описание ошибки
        retryable: Можно ли повторить операцию
        fallback_available: Доступен ли fallback
    """
    _error_code_registry.register_code(
        code, category, severity, description, retryable, fallback_available
    )


def get_error_code_info(code: str) -> Optional[ErrorCodeInfo]:
    """
    Получает информацию об error code.
    
    Args:
        code: Код ошибки
        
    Returns:
        ErrorCodeInfo: Информация о коде или None
    """
    return _error_code_registry.get_code_info(code)


def validate_error_codes() -> bool:
    """
    Валидирует все error codes.
    
    Returns:
        bool: True если все коды валидны
    """
    return _error_code_registry.validate_uniqueness()
