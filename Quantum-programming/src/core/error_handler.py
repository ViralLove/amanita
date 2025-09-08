"""
Обработчик ошибок валидации протокола SIRIUS-FELINE_BRANCH_PROTOCOL.
Централизованная система для обработки, логирования и исправления ошибок валидации.
"""

import logging
import traceback
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import json


class ValidationError:
    """Представление ошибки валидации."""
    
    def __init__(self, error_type: str, message: str, field_path: str = "", 
                 severity: str = "error", details: Dict[str, Any] = None):
        self.error_type = error_type
        self.message = message
        self.field_path = field_path
        self.severity = severity  # error, warning, info
        self.details = details or {}
        self.timestamp = datetime.now()
        self.error_id = self._generate_error_id()
        self.stack_trace = traceback.format_exc()
    
    def _generate_error_id(self) -> str:
        """Генерация уникального ID для ошибки."""
        return f"{self.error_type}_{self.timestamp.strftime('%Y%m%d_%H%M%S_%f')}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование ошибки в словарь для логирования."""
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "message": self.message,
            "field_path": self.field_path,
            "severity": self.severity,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace
        }
    
    def __str__(self) -> str:
        return f"{self.severity.upper()}: {self.message} (поле: {self.field_path})"
    
    def __repr__(self) -> str:
        return f"ValidationError(type='{self.error_type}', severity='{self.severity}', field='{self.field_path}')"


class ErrorCorrection:
    """Автоматическое исправление простых ошибок валидации."""
    
    @staticmethod
    def correct_field_name(field_name: str) -> str:
        """Исправление названий полей."""
        corrections = {
            "prime_directives": "prime_directives",
            "primeDirectives": "prime_directives",
            "PrimeDirectives": "prime_directives",
            "operations": "operations",
            "Operations": "operations",
            "participants": "participants",
            "Participants": "participants"
        }
        return corrections.get(field_name, field_name)
    
    @staticmethod
    def correct_priority_value(priority: str) -> str:
        """Исправление значений приоритета."""
        corrections = {
            "highest": "highest",
            "high": "highest",
            "max": "highest",
            "children_first": "children_first",
            "childrenFirst": "children_first",
            "children": "children_first"
        }
        return corrections.get(priority, priority)
    
    @staticmethod
    def correct_boolean_value(value: Any) -> bool:
        """Исправление булевых значений."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', '1', 'yes', 'да', 'истина']
        if isinstance(value, int):
            return value == 1
        return False


class ValidationErrorHandler:
    """Централизованный обработчик ошибок валидации."""
    
    def __init__(self, log_level: int = logging.INFO, enable_auto_correction: bool = True):
        """Инициализация обработчика ошибок."""
        self.logger = self._setup_logger(log_level)
        self.enable_auto_correction = enable_auto_correction
        self.errors: List[ValidationError] = []
        self.corrections_applied: List[Dict[str, Any]] = []
        self.error_patterns = self._load_error_patterns()
        
        # Счетчики ошибок по типам
        self.error_counts = {
            "structure": 0,
            "type": 0,
            "value": 0,
            "logical": 0,
            "business": 0,
            "system": 0
        }
    
    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Настройка логгера для обработчика ошибок."""
        logger = logging.getLogger(__name__)
        logger.setLevel(log_level)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Загрузка паттернов ошибок и рекомендаций по исправлению."""
        return {
            "missing_field": {
                "description": "Отсутствует обязательное поле",
                "recommendation": "Добавить недостающее поле в соответствующий раздел",
                "auto_correctable": False
            },
            "invalid_type": {
                "description": "Неверный тип данных",
                "recommendation": "Изменить тип данных на ожидаемый",
                "auto_correctable": True
            },
            "invalid_value": {
                "description": "Недопустимое значение",
                "recommendation": "Использовать значение из допустимого диапазона",
                "auto_correctable": True
            },
            "logical_inconsistency": {
                "description": "Логическая несостоятельность",
                "recommendation": "Проверить и исправить логические связи между разделами",
                "auto_correctable": False
            },
            "business_rule_violation": {
                "description": "Нарушение бизнес-правил",
                "recommendation": "Привести в соответствие с требованиями протокола",
                "auto_correctable": False
            }
        }
    
    def add_error(self, error_type: str, message: str, field_path: str = "", 
                  severity: str = "error", details: Dict[str, Any] = None) -> ValidationError:
        """Добавление новой ошибки валидации."""
        error = ValidationError(error_type, message, field_path, severity, details)
        self.errors.append(error)
        
        # Обновление счетчика ошибок
        if error_type in self.error_counts:
            self.error_counts[error_type] += 1
        
        # Логирование ошибки
        self.logger.error(f"Ошибка валидации: {error}")
        
        return error
    
    def add_structural_error(self, message: str, field_path: str = "", 
                           details: Dict[str, Any] = None) -> ValidationError:
        """Добавление структурной ошибки."""
        return self.add_error("structure", message, field_path, "error", details)
    
    def add_type_error(self, message: str, field_path: str = "", 
                      details: Dict[str, Any] = None) -> ValidationError:
        """Добавление ошибки типа данных."""
        return self.add_error("type", message, field_path, "error", details)
    
    def add_value_error(self, message: str, field_path: str = "", 
                       details: Dict[str, Any] = None) -> ValidationError:
        """Добавление ошибки значения."""
        return self.add_error("value", message, field_path, "error", details)
    
    def add_logical_error(self, message: str, field_path: str = "", 
                         details: Dict[str, Any] = None) -> ValidationError:
        """Добавление логической ошибки."""
        return self.add_error("logical", message, field_path, "error", details)
    
    def add_business_error(self, message: str, field_path: str = "", 
                          details: Dict[str, Any] = None) -> ValidationError:
        """Добавление ошибки бизнес-правил."""
        return self.add_error("business", message, field_path, "error", details)
    
    def add_warning(self, error_type: str, message: str, field_path: str = "", 
                   details: Dict[str, Any] = None) -> ValidationError:
        """Добавление предупреждения."""
        return self.add_error(error_type, message, field_path, "warning", details)
    
    def get_errors_by_type(self, error_type: str) -> List[ValidationError]:
        """Получение ошибок определенного типа."""
        return [error for error in self.errors if error.error_type == error_type]
    
    def get_errors_by_severity(self, severity: str) -> List[ValidationError]:
        """Получение ошибок определенной важности."""
        return [error for error in self.errors if error.severity == severity]
    
    def get_critical_errors(self) -> List[ValidationError]:
        """Получение критических ошибок (error severity)."""
        return self.get_errors_by_severity("error")
    
    def has_critical_errors(self) -> bool:
        """Проверка наличия критических ошибок."""
        return len(self.get_critical_errors()) > 0
    
    def can_proceed_with_warnings(self) -> bool:
        """Проверка возможности продолжения с предупреждениями."""
        return not self.has_critical_errors()
    
    def attempt_auto_correction(self, protocol_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Попытка автоматического исправления ошибок.
        
        Args:
            protocol_data: Данные протокола для исправления
            
        Returns:
            Tuple[Dict[str, Any], List[Dict[str, Any]]]: Исправленные данные и список примененных исправлений
        """
        if not self.enable_auto_correction:
            return protocol_data, []
        
        self.logger.info("Начинаю автоматическое исправление ошибок")
        corrected_data = protocol_data.copy()
        corrections = []
        
        # Исправление ошибок типов
        type_errors = self.get_errors_by_type("type")
        for error in type_errors:
            correction = self._correct_type_error(error, corrected_data)
            if correction:
                corrections.append(correction)
        
        # Исправление ошибок значений
        value_errors = self.get_errors_by_type("value")
        for error in value_errors:
            correction = self._correct_value_error(error, corrected_data)
            if correction:
                corrections.append(correction)
        
        self.corrections_applied.extend(corrections)
        self.logger.info(f"Автоматическое исправление завершено. Применено исправлений: {len(corrections)}")
        
        return corrected_data, corrections
    
    def _correct_type_error(self, error: ValidationError, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Исправление ошибки типа данных."""
        field_path = error.field_path
        if not field_path:
            return None
        
        # Простое исправление для корневых полей
        if "." not in field_path and field_path in data:
            original_value = data[field_path]
            corrected_value = self._convert_value_type(original_value, error.details.get("expected_type"))
            
            if corrected_value is not None and corrected_value != original_value:
                data[field_path] = corrected_value
                return {
                    "error_id": error.error_id,
                    "field_path": field_path,
                    "original_value": original_value,
                    "corrected_value": corrected_value,
                    "correction_type": "type_conversion"
                }
        
        return None
    
    def _correct_value_error(self, error: ValidationError, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Исправление ошибки значения."""
        field_path = error.field_path
        if not field_path:
            return None
        
        # Исправление названий полей
        if "field_name" in error.details:
            original_name = error.details["field_name"]
            corrected_name = ErrorCorrection.correct_field_name(original_name)
            
            if corrected_name != original_name and original_name in data:
                data[corrected_name] = data.pop(original_name)
                return {
                    "error_id": error.error_id,
                    "field_path": field_path,
                    "original_value": original_name,
                    "corrected_value": corrected_name,
                    "correction_type": "field_name_correction"
                }
        
        # Исправление значений приоритета
        if "priority" in field_path.lower():
            original_value = self._get_field_value(data, field_path)
            if original_value:
                corrected_value = ErrorCorrection.correct_priority_value(original_value)
                if corrected_value != original_value:
                    self._set_field_value(data, field_path, corrected_value)
                    return {
                        "error_id": error.error_id,
                        "field_path": field_path,
                        "original_value": original_value,
                        "corrected_value": corrected_value,
                        "correction_type": "priority_correction"
                    }
        
        return None
    
    def _convert_value_type(self, value: Any, expected_type: str) -> Any:
        """Преобразование типа значения."""
        try:
            if expected_type == "str":
                return str(value)
            elif expected_type == "int":
                return int(value)
            elif expected_type == "float":
                return float(value)
            elif expected_type == "bool":
                return ErrorCorrection.correct_boolean_value(value)
            elif expected_type == "list" and not isinstance(value, list):
                return [value]
            elif expected_type == "dict" and not isinstance(value, dict):
                return {"value": value}
        except (ValueError, TypeError):
            pass
        return None
    
    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Получение значения поля по пути."""
        try:
            keys = field_path.split(".")
            current = data
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return None
    
    def _set_field_value(self, data: Dict[str, Any], field_path: str, value: Any) -> bool:
        """Установка значения поля по пути."""
        try:
            keys = field_path.split(".")
            current = data
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value
            return True
        except (KeyError, TypeError):
            return False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Получение сводки по ошибкам."""
        return {
            "total_errors": len(self.errors),
            "critical_errors": len(self.get_critical_errors()),
            "warnings": len(self.get_errors_by_severity("warning")),
            "error_counts_by_type": self.error_counts.copy(),
            "can_proceed": self.can_proceed_with_warnings(),
            "auto_corrections_applied": len(self.corrections_applied)
        }
    
    def get_detailed_report(self) -> str:
        """Получение детального отчета об ошибках."""
        report = []
        report.append("=" * 80)
        report.append("ДЕТАЛЬНЫЙ ОТЧЕТ ОБ ОШИБКАХ ВАЛИДАЦИИ")
        report.append("=" * 80)
        report.append(f"Время генерации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Сводка
        summary = self.get_error_summary()
        report.append("СВОДКА:")
        report.append(f"  Всего ошибок: {summary['total_errors']}")
        report.append(f"  Критических ошибок: {summary['critical_errors']}")
        report.append(f"  Предупреждений: {summary['warnings']}")
        report.append(f"  Можно продолжить: {'Да' if summary['can_proceed'] else 'Нет'}")
        report.append(f"  Автоисправлений: {summary['auto_corrections_applied']}")
        report.append("")
        
        # Ошибки по типам
        report.append("ОШИБКИ ПО ТИПАМ:")
        for error_type, count in summary["error_counts_by_type"].items():
            if count > 0:
                report.append(f"  {error_type}: {count}")
        report.append("")
        
        # Детали по ошибкам
        if self.errors:
            report.append("ДЕТАЛИ ОШИБОК:")
            for i, error in enumerate(self.errors, 1):
                report.append(f"{i}. {error}")
                if error.details:
                    for key, value in error.details.items():
                        report.append(f"   {key}: {value}")
                report.append("")
        
        # Примененные исправления
        if self.corrections_applied:
            report.append("ПРИМЕНЕННЫЕ АВТОИСПРАВЛЕНИЯ:")
            for i, correction in enumerate(self.corrections_applied, 1):
                report.append(f"{i}. {correction['correction_type']}")
                report.append(f"   Поле: {correction['field_path']}")
                report.append(f"   Было: {correction['original_value']}")
                report.append(f"   Стало: {correction['corrected_value']}")
                report.append("")
        
        report.append("=" * 80)
        return "\n".join(report)
    
    def save_error_log(self, file_path: str) -> bool:
        """Сохранение лога ошибок в файл."""
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "error_summary": self.get_error_summary(),
                "errors": [error.to_dict() for error in self.errors],
                "corrections_applied": self.corrections_applied
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Лог ошибок сохранен в файл: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении лога: {str(e)}")
            return False
    
    def clear_errors(self):
        """Очистка всех ошибок."""
        self.errors.clear()
        self.corrections_applied.clear()
        for error_type in self.error_counts:
            self.error_counts[error_type] = 0
        self.logger.info("Все ошибки очищены")
    
    def __str__(self) -> str:
        summary = self.get_error_summary()
        return f"ValidationErrorHandler(errors={summary['total_errors']}, critical={summary['critical_errors']})"
    
    def __repr__(self) -> str:
        return f"ValidationErrorHandler(enable_auto_correction={self.enable_auto_correction}, total_errors={len(self.errors)})"
