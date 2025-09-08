"""
Валидатор протокола SIRIUS-FELINE_BRANCH_PROTOCOL.
Обеспечивает детальную проверку структуры, типов и значений данных протокола.
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import logging


class ValidationError(Exception):
    """Исключение для ошибок валидации."""
    
    def __init__(self, message: str, field_path: str = "", details: List[str] = None):
        super().__init__(message)
        self.message = message
        self.field_path = field_path
        self.details = details or []


class ValidationResult:
    """Результат валидации протокола."""
    
    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.validation_time: datetime = datetime.now()
    
    def add_error(self, message: str, field_path: str = "", details: List[str] = None):
        """Добавление ошибки валидации."""
        self.is_valid = False
        self.errors.append({
            "message": message,
            "field_path": field_path,
            "details": details or [],
            "timestamp": datetime.now()
        })
    
    def add_warning(self, message: str, field_path: str = "", details: List[str] = None):
        """Добавление предупреждения валидации."""
        self.warnings.append({
            "message": message,
            "field_path": field_path,
            "details": details or [],
            "timestamp": datetime.now()
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Получение сводки результатов валидации."""
        return {
            "is_valid": self.is_valid,
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "validation_time": self.validation_time.isoformat(),
            "errors": self.errors,
            "warnings": self.warnings
        }


class ProtocolValidator:
    """Детальный валидатор протокола."""
    
    def __init__(self, log_level: int = logging.INFO):
        """Инициализация валидатора протокола."""
        self.logger = self._setup_logger(log_level)
        
        # Схема валидации для основных разделов
        self.validation_schema = {
            "protocol": {
                "type": dict,
                "required_fields": ["name", "version", "scope", "intent"],
                "field_validators": {
                    "name": {"type": str, "min_length": 1, "pattern": r"^[A-Z0-9_-]+$"},
                    "version": {"type": str, "pattern": r"^\d+\.\d+$"},
                    "scope": {"type": str, "min_length": 10},
                    "intent": {"type": list, "min_items": 1, "item_type": str}
                }
            },
            "participants": {
                "type": dict,
                "required_fields": ["initiator", "family"],
                "field_validators": {
                    "initiator": {"type": str, "min_length": 1},
                    "family": {"type": dict, "required_fields": ["husband", "children", "parents"]}
                }
            },
            "prime_directives": {
                "type": dict,
                "required_fields": ["PD1", "PD2", "PD3", "PD4"],
                "field_validators": {
                    "PD1": {"type": dict, "required_fields": ["description", "priority"]},
                    "PD2": {"type": dict, "required_fields": ["description", "approach"]},
                    "PD3": {"type": dict, "required_fields": ["description", "filters"]},
                    "PD4": {"type": dict, "required_fields": ["description", "access_control"]}
                }
            },
            "operations": {
                "type": dict,
                "required_fields": ["OP1", "OP2", "OP3", "OP4"],
                "field_validators": {
                    "OP1": {"type": dict, "required_fields": ["description", "priority", "focus"]},
                    "OP2": {"type": dict, "required_fields": ["description", "environment"]},
                    "OP3": {"type": dict, "required_fields": ["description", "access", "constraint"]},
                    "OP4": {"type": dict, "required_fields": ["description", "approach", "priority"]}
                }
            },
            "protection": {
                "type": dict,
                "required_fields": ["ring_of_safety", "shield", "trace"],
                "field_validators": {
                    "ring_of_safety": {"type": dict, "required_fields": ["description", "aspects"]},
                    "shield": {"type": dict, "required_fields": ["description", "functions"]},
                    "trace": {"type": dict, "required_fields": ["description", "filter"]}
                }
            }
        }
    
    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Настройка логгера для валидатора."""
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
    
    def validate_protocol(self, protocol_data: Dict[str, Any]) -> ValidationResult:
        """
        Полная валидация протокола.
        
        Args:
            protocol_data: Данные протокола для валидации
            
        Returns:
            ValidationResult: Результат валидации
        """
        self.logger.info("Начинаю полную валидацию протокола")
        result = ValidationResult()
        
        try:
            # Проверка базовой структуры
            self._validate_basic_structure(protocol_data, result)
            
            # Детальная валидация каждого раздела
            for section_name, section_schema in self.validation_schema.items():
                if section_name in protocol_data:
                    self._validate_section(
                        protocol_data[section_name], 
                        section_schema, 
                        section_name, 
                        result
                    )
                else:
                    result.add_error(
                        f"Отсутствует обязательный раздел: {section_name}",
                        section_name
                    )
            
            # Валидация логических связей
            self._validate_logical_connections(protocol_data, result)
            
            # Валидация бизнес-правил
            self._validate_business_rules(protocol_data, result)
            
        except Exception as e:
            result.add_error(f"Критическая ошибка валидации: {str(e)}")
            self.logger.error(f"Критическая ошибка валидации: {str(e)}")
        
        self.logger.info(f"Валидация завершена. Ошибок: {len(result.errors)}, Предупреждений: {len(result.warnings)}")
        return result
    
    def _validate_basic_structure(self, data: Any, result: ValidationResult, field_path: str = ""):
        """Валидация базовой структуры данных."""
        if not isinstance(data, dict):
            result.add_error(
                f"Ожидается словарь, получено: {type(data).__name__}",
                field_path
            )
            return
        
        if not data:
            result.add_error("Протокол не может быть пустым", field_path)
            return
    
    def _validate_section(self, section_data: Any, schema: Dict[str, Any], 
                         section_name: str, result: ValidationResult, field_path: str = ""):
        """Валидация конкретного раздела протокола."""
        current_path = f"{field_path}.{section_name}" if field_path else section_name
        
        # Проверка типа
        if not isinstance(section_data, schema["type"]):
            result.add_error(
                f"Раздел '{section_name}' должен быть типа {schema['type'].__name__}, "
                f"получено: {type(section_data).__name__}",
                current_path
            )
            return
        
        # Проверка обязательных полей
        if "required_fields" in schema:
            for required_field in schema["required_fields"]:
                if required_field not in section_data:
                    result.add_error(
                        f"В разделе '{section_name}' отсутствует обязательное поле: {required_field}",
                        current_path
                    )
        
        # Валидация полей согласно схеме
        if "field_validators" in schema:
            for field_name, field_schema in schema["field_validators"].items():
                if field_name in section_data:
                    self._validate_field(
                        section_data[field_name],
                        field_schema,
                        field_name,
                        result,
                        current_path
                    )
    
    def _validate_field(self, field_value: Any, field_schema: Dict[str, Any], 
                       field_name: str, result: ValidationResult, field_path: str = ""):
        """Валидация конкретного поля."""
        current_path = f"{field_path}.{field_name}" if field_path else field_name
        
        # Проверка типа
        if "type" in field_schema:
            expected_type = field_schema["type"]
            if not isinstance(field_value, expected_type):
                result.add_error(
                    f"Поле '{field_name}' должно быть типа {expected_type.__name__}, "
                    f"получено: {type(field_value).__name__}",
                    current_path
                )
                return
        
        # Проверка длины строки
        if isinstance(field_value, str) and "min_length" in field_schema:
            if len(field_value) < field_schema["min_length"]:
                result.add_error(
                    f"Поле '{field_name}' должно содержать минимум {field_schema['min_length']} символов",
                    current_path
                )
        
        # Проверка количества элементов списка
        if isinstance(field_value, list) and "min_items" in field_schema:
            if len(field_value) < field_schema["min_items"]:
                result.add_error(
                    f"Список '{field_name}' должен содержать минимум {field_schema['min_items']} элементов",
                    current_path
                )
        
        # Проверка типа элементов списка
        if isinstance(field_value, list) and "item_type" in field_schema:
            for i, item in enumerate(field_value):
                if not isinstance(item, field_schema["item_type"]):
                    result.add_error(
                        f"Элемент {i} списка '{field_name}' должен быть типа "
                        f"{field_schema['item_type'].__name__}, получено: {type(item).__name__}",
                        f"{current_path}[{i}]"
                    )
        
        # Проверка по регулярному выражению
        if isinstance(field_value, str) and "pattern" in field_schema:
            if not re.match(field_schema["pattern"], field_value):
                result.add_error(
                    f"Поле '{field_name}' не соответствует требуемому формату",
                    current_path
                )
        
        # Рекурсивная валидация для вложенных объектов
        if isinstance(field_value, dict) and "required_fields" in field_schema:
            for required_field in field_schema["required_fields"]:
                if required_field not in field_value:
                    result.add_error(
                        f"В поле '{field_name}' отсутствует обязательное подполе: {required_field}",
                        current_path
                    )
    
    def _validate_logical_connections(self, protocol_data: Dict[str, Any], result: ValidationResult):
        """Валидация логических связей между разделами протокола."""
        self.logger.debug("Проверяю логические связи протокола")
        
        # Проверка соответствия количества операций и директив
        operations = protocol_data.get("operations", {})
        directives = protocol_data.get("prime_directives", {})
        
        if len(operations) != len(directives):
            result.add_warning(
                f"Количество операций ({len(operations)}) не соответствует количеству директив ({len(directives)})",
                "logical_consistency"
            )
        
        # Проверка соответствия участников и операций
        participants = protocol_data.get("participants", {}).get("family", {})
        if participants:
            children = participants.get("children", [])
            if children and "OP1" in operations:
                op1 = operations["OP1"]
                if "priority" in op1 and op1["priority"] != "children_first":
                    result.add_warning(
                        "Операция OP1 должна иметь приоритет 'children_first' согласно протоколу",
                        "operations.OP1.priority"
                    )
    
    def _validate_business_rules(self, protocol_data: Dict[str, Any], result: ValidationResult):
        """Валидация бизнес-правил протокола."""
        self.logger.debug("Проверяю бизнес-правила протокола")
        
        # Проверка ключевой фразы активации
        activation = protocol_data.get("activation", {})
        key_phrase = activation.get("key_phrase", "")
        if "Сириуса" not in key_phrase or "свободы воли" not in key_phrase:
            result.add_warning(
                "Ключевая фраза активации должна содержать упоминание Сириуса и свободы воли",
                "activation.key_phrase"
            )
        
        # Проверка критериев успеха
        success_criteria = protocol_data.get("success_criteria", {})
        if len(success_criteria) < 3:
            result.add_warning(
                "Рекомендуется иметь минимум 3 критерия успеха для полноты протокола",
                "success_criteria"
            )
    
    def get_validation_report(self, result: ValidationResult) -> str:
        """Получение текстового отчета о валидации."""
        report = []
        report.append("=" * 60)
        report.append("ОТЧЕТ О ВАЛИДАЦИИ ПРОТОКОЛА")
        report.append("=" * 60)
        report.append(f"Время валидации: {result.validation_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Статус: {'ПРОЙДЕНА' if result.is_valid else 'НЕ ПРОЙДЕНА'}")
        report.append(f"Ошибок: {len(result.errors)}")
        report.append(f"Предупреждений: {len(result.warnings)}")
        report.append("")
        
        if result.errors:
            report.append("ОШИБКИ ВАЛИДАЦИИ:")
            report.append("-" * 30)
            for i, error in enumerate(result.errors, 1):
                report.append(f"{i}. {error['message']}")
                if error['field_path']:
                    report.append(f"   Поле: {error['field_path']}")
                if error['details']:
                    for detail in error['details']:
                        report.append(f"   Детали: {detail}")
                report.append("")
        
        if result.warnings:
            report.append("ПРЕДУПРЕЖДЕНИЯ:")
            report.append("-" * 30)
            for i, warning in enumerate(result.warnings, 1):
                report.append(f"{i}. {warning['message']}")
                if warning['field_path']:
                    report.append(f"   Поле: {warning['field_path']}")
                report.append("")
        
        report.append("=" * 60)
        return "\n".join(report)
