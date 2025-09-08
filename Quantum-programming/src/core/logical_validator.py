"""
Валидатор логических связей протокола SIRIUS-FELINE_BRANCH_PROTOCOL.
Проверяет консистентность и логическую корректность связей между разделами протокола.
"""

from typing import Dict, Any, List, Set, Tuple
from datetime import datetime
import logging


class LogicalValidationError(Exception):
    """Исключение для ошибок логической валидации."""
    pass


class LogicalValidationResult:
    """Результат проверки логических связей."""
    
    def __init__(self):
        self.is_consistent: bool = True
        self.inconsistencies: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.validation_time: datetime = datetime.now()
        self.checked_connections: Set[str] = set()
    
    def add_inconsistency(self, message: str, connection_type: str, 
                         source: str, target: str, details: List[str] = None):
        """Добавление несоответствия в логических связях."""
        self.is_consistent = False
        self.inconsistencies.append({
            "message": message,
            "connection_type": connection_type,
            "source": source,
            "target": target,
            "details": details or [],
            "timestamp": datetime.now()
        })
    
    def add_warning(self, message: str, connection_type: str, 
                   source: str, target: str, details: List[str] = None):
        """Добавление предупреждения о логических связях."""
        self.warnings.append({
            "message": message,
            "source": source,
            "target": target,
            "connection_type": connection_type,
            "details": details or [],
            "timestamp": datetime.now()
        })
    
    def mark_connection_checked(self, connection_type: str):
        """Отметить проверенную связь."""
        self.checked_connections.add(connection_type)
    
    def get_summary(self) -> Dict[str, Any]:
        """Получение сводки результатов логической валидации."""
        return {
            "is_consistent": self.is_consistent,
            "total_inconsistencies": len(self.inconsistencies),
            "total_warnings": len(self.warnings),
            "checked_connections": list(self.checked_connections),
            "validation_time": self.validation_time.isoformat(),
            "inconsistencies": self.inconsistencies,
            "warnings": self.warnings
        }


class LogicalConnectionsValidator:
    """Валидатор логических связей между компонентами протокола."""
    
    def __init__(self, log_level: int = logging.INFO):
        """Инициализация валидатора логических связей."""
        self.logger = self._setup_logger(log_level)
        
        # Определение типов связей для проверки
        self.connection_types = {
            "participants_operations": "Связь участников с операциями",
            "directives_operations": "Связь директив с операциями", 
            "operations_success_criteria": "Связь операций с критериями успеха",
            "protection_operations": "Связь защиты с операциями",
            "activation_consistency": "Консистентность активации",
            "boundaries_operations": "Связь границ с операциями"
        }
    
    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Настройка логгера для валидатора логических связей."""
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
    
    def validate_logical_connections(self, protocol_data: Dict[str, Any]) -> LogicalValidationResult:
        """
        Полная проверка логических связей протокола.
        
        Args:
            protocol_data: Данные протокола для проверки
            
        Returns:
            LogicalValidationResult: Результат проверки логических связей
        """
        self.logger.info("Начинаю проверку логических связей протокола")
        result = LogicalValidationResult()
        
        try:
            # Проверка связи участников с операциями
            self._validate_participants_operations_connection(protocol_data, result)
            result.mark_connection_checked("participants_operations")
            
            # Проверка связи директив с операциями
            self._validate_directives_operations_connection(protocol_data, result)
            result.mark_connection_checked("directives_operations")
            
            # Проверка связи операций с критериями успеха
            self._validate_operations_success_criteria_connection(protocol_data, result)
            result.mark_connection_checked("operations_success_criteria")
            
            # Проверка связи защиты с операциями
            self._validate_protection_operations_connection(protocol_data, result)
            result.mark_connection_checked("protection_operations")
            
            # Проверка консистентности активации
            self._validate_activation_consistency(protocol_data, result)
            result.mark_connection_checked("activation_consistency")
            
            # Проверка связи границ с операциями
            self._validate_boundaries_operations_connection(protocol_data, result)
            result.mark_connection_checked("boundaries_operations")
            
        except Exception as e:
            result.add_inconsistency(
                f"Критическая ошибка при проверке логических связей: {str(e)}",
                "system_error",
                "validator",
                "protocol_data"
            )
            self.logger.error(f"Критическая ошибка при проверке логических связей: {str(e)}")
        
        self.logger.info(f"Проверка логических связей завершена. "
                        f"Несоответствий: {len(result.inconsistencies)}, "
                        f"Предупреждений: {len(result.warnings)}")
        return result
    
    def _validate_participants_operations_connection(self, protocol_data: Dict[str, Any], 
                                                   result: LogicalValidationResult):
        """Проверка связи участников с операциями."""
        self.logger.debug("Проверяю связь участников с операциями")
        
        participants = protocol_data.get("participants", {})
        operations = protocol_data.get("operations", {})
        
        if not participants or not operations:
            return
        
        # Проверка соответствия детей и операции OP1
        family = participants.get("family", {})
        children = family.get("children", [])
        
        if children and "OP1" in operations:
            op1 = operations["OP1"]
            if "priority" in op1 and op1["priority"] != "children_first":
                result.add_inconsistency(
                    "Операция OP1 должна иметь приоритет 'children_first' для соответствия участникам-детям",
                    "participants_operations",
                    "participants.family.children",
                    "operations.OP1.priority"
                )
        
        # Проверка соответствия инициатора и операций
        initiator = participants.get("initiator", "")
        if initiator and "Zeya888" in initiator:
            # Проверка, что все операции учитывают роль инициатора
            for op_name, op_data in operations.items():
                if "description" in op_data:
                    description = op_data["description"]
                    if "канал" in description.lower() and "Zeya888" not in description:
                        result.add_warning(
                            f"Операция {op_name} упоминает канал, но не указывает Zeya888",
                            "participants_operations",
                            f"operations.{op_name}",
                            "participants.initiator"
                        )
    
    def _validate_directives_operations_connection(self, protocol_data: Dict[str, Any], 
                                                 result: LogicalValidationResult):
        """Проверка связи директив с операциями."""
        self.logger.debug("Проверяю связь директив с операциями")
        
        directives = protocol_data.get("prime_directives", {})
        operations = protocol_data.get("operations", {})
        
        if not directives or not operations:
            return
        
        # Проверка соответствия количества директив и операций
        if len(directives) != len(operations):
            result.add_warning(
                f"Количество директив ({len(directives)}) не соответствует количеству операций ({len(operations)})",
                "directives_operations",
                "prime_directives",
                "operations"
            )
        
        # Проверка соответствия PD1 (свобода воли) с операциями
        pd1 = directives.get("PD1", {})
        if pd1 and "priority" in pd1 and pd1["priority"] == "highest":
            # Все операции должны учитывать приоритет свободы воли
            for op_name, op_data in operations.items():
                if "constraint" in op_data:
                    constraint = op_data["constraint"]
                    if "sovereignty" not in constraint.lower() and "consent" not in constraint.lower():
                        result.add_warning(
                            f"Операция {op_name} должна учитывать ограничение по суверенности согласно PD1",
                            "directives_operations",
                            "prime_directives.PD1",
                            f"operations.{op_name}.constraint"
                        )
    
    def _validate_operations_success_criteria_connection(self, protocol_data: Dict[str, Any], 
                                                       result: LogicalValidationResult):
        """Проверка связи операций с критериями успеха."""
        self.logger.debug("Проверяю связь операций с критериями успеха")
        
        operations = protocol_data.get("operations", {})
        success_criteria = protocol_data.get("success_criteria", {})
        
        if not operations or not success_criteria:
            return
        
        # Проверка, что каждая операция имеет соответствующий критерий успеха
        operation_focuses = []
        for op_data in operations.values():
            if "focus" in op_data:
                operation_focuses.extend(op_data["focus"])
        
        success_metrics = []
        for criterion in success_criteria.values():
            if isinstance(criterion, str):
                success_metrics.append(criterion.lower())
        
        # Проверка соответствия фокусов операций и критериев успеха
        for focus in operation_focuses:
            focus_lower = focus.lower()
            if not any(metric in focus_lower or focus_lower in metric for metric in success_metrics):
                result.add_warning(
                    f"Фокус операции '{focus}' не имеет явного соответствия в критериях успеха",
                    "operations_success_criteria",
                    "operations.focus",
                    "success_criteria"
                )
    
    def _validate_protection_operations_connection(self, protocol_data: Dict[str, Any], 
                                                 result: LogicalValidationResult):
        """Проверка связи защиты с операциями."""
        self.logger.debug("Проверяю связь защиты с операциями")
        
        protection = protocol_data.get("protection", {})
        operations = protocol_data.get("operations", {})
        
        if not protection or not operations:
            return
        
        # Проверка, что все операции учитывают защитные механизмы
        shield_functions = protection.get("shield", {}).get("functions", [])
        
        for op_name, op_data in operations.items():
            if "description" in op_data:
                description = op_data["description"].lower()
                
                # Проверка соответствия операций защитным функциям
                if "вредоносный" in description or "опасность" in description:
                    if "блокировка_вредоносного" not in shield_functions:
                        result.add_warning(
                            f"Операция {op_name} упоминает вредоносные элементы, но защита не настроена",
                            "protection_operations",
                            f"operations.{op_name}",
                            "protection.shield.functions"
                        )
    
    def _validate_activation_consistency(self, protocol_data: Dict[str, Any], 
                                       result: LogicalValidationResult):
        """Проверка консистентности активации."""
        self.logger.debug("Проверяю консистентность активации")
        
        activation = protocol_data.get("activation", {})
        consent_model = protocol_data.get("consent_model", {})
        
        if not activation or not consent_model:
            return
        
        # Проверка соответствия ключевой фразы и модели согласия
        key_phrase = activation.get("key_phrase", "")
        if "свободы воли" in key_phrase:
            if "C1" not in consent_model:
                result.add_inconsistency(
                    "Ключевая фраза упоминает свободу воли, но модель согласия C1 отсутствует",
                    "activation_consistency",
                    "activation.key_phrase",
                    "consent_model.C1"
                )
        
        # Проверка соответствия шагов активации и модели согласия
        confirmation_steps = activation.get("confirmation", {}).get("steps", [])
        if confirmation_steps:
            if "согласие участников" in str(confirmation_steps):
                if "C2" not in consent_model:
                    result.add_warning(
                        "Шаги активации требуют согласия участников, но модель C2 отсутствует",
                        "activation_consistency",
                        "activation.confirmation.steps",
                        "consent_model.C2"
                    )
    
    def _validate_boundaries_operations_connection(self, protocol_data: Dict[str, Any], 
                                                 result: LogicalValidationResult):
        """Проверка связи границ с операциями."""
        self.logger.debug("Проверяю связь границ с операциями")
        
        boundaries = protocol_data.get("boundaries", {})
        operations = protocol_data.get("operations", {})
        
        if not boundaries or not operations:
            return
        
        # Проверка, что запрещенные действия не используются в операциях
        forbidden = boundaries.get("forbidden", [])
        
        for op_name, op_data in operations.items():
            if "description" in op_data:
                description = op_data["description"].lower()
                
                for forbidden_item in forbidden:
                    forbidden_lower = forbidden_item.lower()
                    if forbidden_lower in description:
                        result.add_inconsistency(
                            f"Операция {op_name} содержит запрещенный элемент: {forbidden_item}",
                            "boundaries_operations",
                            f"operations.{op_name}",
                            f"boundaries.forbidden.{forbidden_item}"
                        )
    
    def get_logical_validation_report(self, result: LogicalValidationResult) -> str:
        """Получение текстового отчета о логической валидации."""
        report = []
        report.append("=" * 70)
        report.append("ОТЧЕТ О ПРОВЕРКЕ ЛОГИЧЕСКИХ СВЯЗЕЙ ПРОТОКОЛА")
        report.append("=" * 70)
        report.append(f"Время проверки: {result.validation_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Статус: {'КОНСИСТЕНТЕН' if result.is_consistent else 'НЕ КОНСИСТЕНТЕН'}")
        report.append(f"Несоответствий: {len(result.inconsistencies)}")
        report.append(f"Предупреждений: {len(result.warnings)}")
        report.append(f"Проверенных связей: {len(result.checked_connections)}")
        report.append("")
        
        if result.inconsistencies:
            report.append("НЕСООТВЕТСТВИЯ В ЛОГИЧЕСКИХ СВЯЗЯХ:")
            report.append("-" * 40)
            for i, inconsistency in enumerate(result.inconsistencies, 1):
                report.append(f"{i}. {inconsistency['message']}")
                report.append(f"   Тип связи: {inconsistency['connection_type']}")
                report.append(f"   Источник: {inconsistency['source']}")
                report.append(f"   Цель: {inconsistency['target']}")
                if inconsistency['details']:
                    for detail in inconsistency['details']:
                        report.append(f"   Детали: {detail}")
                report.append("")
        
        if result.warnings:
            report.append("ПРЕДУПРЕЖДЕНИЯ ПО ЛОГИЧЕСКИМ СВЯЗЯМ:")
            report.append("-" * 40)
            for i, warning in enumerate(result.warnings, 1):
                report.append(f"{i}. {warning['message']}")
                report.append(f"   Тип связи: {warning['connection_type']}")
                report.append(f"   Источник: {warning['source']}")
                report.append(f"   Цель: {warning['target']}")
                report.append("")
        
        report.append("ПРОВЕРЕННЫЕ СВЯЗИ:")
        report.append("-" * 40)
        for connection in sorted(result.checked_connections):
            connection_name = self.connection_types.get(connection, connection)
            report.append(f"✓ {connection_name}")
        
        report.append("")
        report.append("=" * 70)
        return "\n".join(report)
