"""
Квантовые операции протокола SIRUS-FELINE_BRANCH_PROTOCOL.
Выполнение основных операций: выравнивание траекторий, перенастройка среды, 
доступ к регенерации, информационная чистка.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import uuid
import numpy as np

from .participant_manager import ParticipantManager
from .quantum_field import QuantumField


class QuantumOperationError(Exception):
    """Исключение для ошибок квантовых операций."""
    pass


class OperationValidationError(Exception):
    """Исключение для ошибок валидации операций."""
    pass


class QuantumOperations:
    """Система квантовых операций протокола."""
    
    def __init__(self, participant_manager: ParticipantManager, 
                 quantum_field: QuantumField,
                 log_level: int = logging.INFO):
        """Инициализация системы квантовых операций."""
        self.logger = self._setup_logger(log_level)
        self.participant_manager = participant_manager
        self.quantum_field = quantum_field
        
        # Статистика операций
        self.operations_executed: int = 0
        self.successful_operations: int = 0
        self.failed_operations: int = 0
        
        # История операций
        self.operation_history: List[Dict[str, Any]] = []
        
        # Метаданные
        self.created_at: datetime = datetime.now()
        self.last_operation: Optional[datetime] = None
        
        # Параметры операций
        self.operation_parameters = self._initialize_operation_parameters()
        
        self.logger.info("QuantumOperations инициализирована")
    
    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Настройка логгера для квантовых операций."""
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
    
    def _initialize_operation_parameters(self) -> Dict[str, Any]:
        """Инициализация параметров операций."""
        return {
            "OP1": {
                "name": "Выравнивание траекторий",
                "description": "Синхронизация участников с траекторией Сириуса",
                "required_participants": 1,
                "energy_threshold": 0.8,
                "clarity_threshold": 0.7,
                "protection_threshold": 0.6,
                "alignment_threshold": 0.5,
                "execution_time": 30,  # секунды
                "cooldown": 300  # секунды
            },
            "OP2": {
                "name": "Перенастройка среды",
                "description": "Адаптация квантового поля под новые условия",
                "required_participants": 2,
                "energy_threshold": 1.0,
                "clarity_threshold": 0.8,
                "protection_threshold": 0.8,
                "alignment_threshold": 0.7,
                "execution_time": 60,
                "cooldown": 600
            },
            "OP3": {
                "name": "Доступ к регенерации",
                "description": "Активация процессов самовосстановления",
                "required_participants": 1,
                "energy_threshold": 0.6,
                "clarity_threshold": 0.6,
                "protection_threshold": 0.7,
                "alignment_threshold": 0.6,
                "execution_time": 45,
                "cooldown": 450
            },
            "OP4": {
                "name": "Информационная чистка",
                "description": "Очистка от негативных информационных влияний",
                "required_participants": 3,
                "energy_threshold": 1.2,
                "clarity_threshold": 0.9,
                "protection_threshold": 0.9,
                "alignment_threshold": 0.8,
                "execution_time": 90,
                "cooldown": 900
            }
        }
    
    def execute_operation(self, operation_code: str, 
                         participant_ids: List[str],
                         parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Выполнение квантовой операции.
        
        Args:
            operation_code: Код операции (OP1, OP2, OP3, OP4)
            participant_ids: Список ID участников
            parameters: Дополнительные параметры операции
            
        Returns:
            Dict[str, Any]: Результат выполнения операции
        """
        try:
            if operation_code not in self.operation_parameters:
                raise QuantumOperationError(f"Неизвестная операция: {operation_code}")
            
            operation_params = self.operation_parameters[operation_code]
            self.logger.info(f"Начинаю выполнение операции {operation_code}: {operation_params['name']}")
            
            # Валидация операции
            validation_result = self._validate_operation(operation_code, participant_ids)
            if not validation_result["valid"]:
                raise OperationValidationError(f"Операция не прошла валидацию: {validation_result['errors']}")
            
            # Выполнение операции
            operation_result = self._execute_operation_impl(operation_code, participant_ids, parameters)
            
            # Обновление статистики
            self._update_operation_statistics(operation_result["success"])
            
            # Запись в историю
            self._record_operation(operation_code, participant_ids, operation_result)
            
            self.logger.info(f"Операция {operation_code} завершена: {'успешно' if operation_result['success'] else 'с ошибкой'}")
            return operation_result
            
        except Exception as e:
            error_msg = f"Ошибка при выполнении операции {operation_code}: {str(e)}"
            self.logger.error(error_msg)
            self._update_operation_statistics(False)
            return {"success": False, "error": error_msg, "operation_code": operation_code}
    
    def _validate_operation(self, operation_code: str, participant_ids: List[str]) -> Dict[str, Any]:
        """Валидация операции перед выполнением."""
        operation_params = self.operation_parameters[operation_code]
        errors = []
        warnings = []
        
        # Проверка количества участников
        if len(participant_ids) < operation_params["required_participants"]:
            errors.append(f"Недостаточно участников: требуется {operation_params['required_participants']}, предоставлено {len(participant_ids)}")
        
        # Проверка готовности участников
        readiness_check = self.participant_manager.check_group_readiness(participant_ids, "critical_operation")
        if not readiness_check["group_ready"]:
            errors.append("Группа не готова к выполнению операции")
            warnings.extend(readiness_check.get("recommendations", []))
        
        # Проверка согласий
        consent_check = self.participant_manager.validate_participant_consents(participant_ids)
        if not consent_check["all_consented"]:
            errors.append("Не все участники дали согласие на участие")
        
        # Проверка статуса квантового поля
        if not self.quantum_field.is_active:
            errors.append("Квантовое поле неактивно")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "operation_params": operation_params
        }
    
    def _execute_operation_impl(self, operation_code: str, 
                               participant_ids: List[str],
                               parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Выполнение конкретной операции."""
        if operation_code == "OP1":
            return self._execute_op1_alignment(participant_ids, parameters)
        elif operation_code == "OP2":
            return self._execute_op2_environment_restructuring(participant_ids, parameters)
        elif operation_code == "OP3":
            return self._execute_op3_regeneration_access(participant_ids, parameters)
        elif operation_code == "OP4":
            return self._execute_op4_information_cleansing(participant_ids, parameters)
        else:
            raise QuantumOperationError(f"Неизвестная операция: {operation_code}")
    
    def _execute_op1_alignment(self, participant_ids: List[str], 
                              parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Выполнение операции OP1: Выравнивание траекторий.
        
        Синхронизация участников с траекторией Сириуса через канал Zeya888.
        """
        try:
            self.logger.info("Выполняю OP1: Выравнивание траекторий")
            
            # Получение участников
            participants = [self.participant_manager.get_participant(pid) for pid in participant_ids]
            participants = [p for p in participants if p is not None]
            
            if not participants:
                return {"success": False, "error": "Не удалось получить участников"}
            
            # Поиск инициатора (Zeya888)
            initiator = None
            for participant in participants:
                if participant.role == "initiator" or "Zeya888" in participant.name:
                    initiator = participant
                    break
            
            if not initiator:
                return {"success": False, "error": "Инициатор (Zeya888) не найден среди участников"}
            
            # Выполнение выравнивания
            alignment_results = []
            total_alignment_improvement = 0.0
            
            for participant in participants:
                if participant.participant_id == initiator.participant_id:
                    continue  # Инициатор уже выровнен
                
                # Расчет улучшения выравнивания на основе связи с инициатором
                initiator_alignment = initiator.quantum_state.alignment
                current_alignment = participant.quantum_state.alignment
                
                # Улучшение выравнивания через связь с инициатором
                alignment_boost = min(0.3, (initiator_alignment - current_alignment) * 0.5)
                new_alignment = min(1.0, current_alignment + alignment_boost)
                
                # Обновление состояния участника
                old_alignment = participant.quantum_state.alignment
                participant.update_quantum_state(alignment=new_alignment)
                
                # Синхронизация с квантовым полем
                self.participant_manager.update_participant_quantum_state(
                    participant.participant_id,
                    np.array([
                        participant.quantum_state.energy_level,
                        participant.quantum_state.clarity,
                        participant.quantum_state.protection,
                        participant.quantum_state.alignment
                    ], dtype=np.float64)
                )
                
                alignment_improvement = new_alignment - old_alignment
                total_alignment_improvement += alignment_improvement
                
                alignment_results.append({
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "old_alignment": old_alignment,
                    "new_alignment": new_alignment,
                    "improvement": alignment_improvement
                })
            
            # Создание связи с траекторией Сириуса через инициатора
            sirius_connection_strength = min(1.0, 0.8 + (initiator.quantum_state.alignment * 0.2))
            
            # Обновление статистики поля
            self.quantum_field._update_field_statistics()
            
            result = {
                "success": True,
                "operation_code": "OP1",
                "operation_name": "Выравнивание траекторий",
                "initiator": {
                    "participant_id": initiator.participant_id,
                    "name": initiator.name,
                    "alignment": initiator.quantum_state.alignment
                },
                "participants_aligned": len(alignment_results),
                "total_alignment_improvement": round(total_alignment_improvement, 3),
                "sirius_connection_strength": round(sirius_connection_strength, 3),
                "alignment_results": alignment_results,
                "execution_time": datetime.now(),
                "metadata": {
                    "sirius_channel": "Zeya888",
                    "trajectory_sync": True,
                    "quantum_field_updated": True
                }
            }
            
            self.logger.info(f"OP1 завершена успешно: выровнено {len(alignment_results)} участников")
            return result
            
        except Exception as e:
            error_msg = f"Ошибка при выполнении OP1: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg, "operation_code": "OP1"}
    
    def _execute_op2_environment_restructuring(self, participant_ids: List[str], 
                                             parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Выполнение операции OP2: Перенастройка среды.
        
        Адаптация квантового поля под новые условия и требования участников.
        """
        try:
            self.logger.info("Выполняю OP2: Перенастройка среды")
            
            # Получение участников
            participants = [self.participant_manager.get_participant(pid) for pid in participant_ids]
            participants = [p for p in participants if p is not None]
            
            if len(participants) < 2:
                return {"success": False, "error": "Для OP2 требуется минимум 2 участника"}
            
            # Анализ текущего состояния поля
            field_status = self.quantum_field.get_field_status()
            field_health = self.quantum_field.get_field_health_score()
            
            # Расчет необходимых изменений на основе состояний участников
            total_energy = sum(p.quantum_state.energy_level for p in participants)
            avg_clarity = np.mean([p.quantum_state.clarity for p in participants])
            avg_protection = np.mean([p.quantum_state.protection for p in participants])
            
            # Адаптация параметров поля
            old_parameters = self.quantum_field.parameters
            new_parameters = self.quantum_field.parameters
            
            # Адаптация базового уровня энергии
            if total_energy > len(participants) * 1.5:
                new_parameters.base_energy_level = min(2.0, old_parameters.base_energy_level * 1.1)
            elif total_energy < len(participants) * 0.8:
                new_parameters.base_energy_level = max(0.5, old_parameters.base_energy_level * 0.9)
            
            # Адаптация силы связей
            if avg_protection > 0.8:
                new_parameters.connection_strength = min(1.0, old_parameters.connection_strength * 1.05)
            elif avg_protection < 0.6:
                new_parameters.connection_strength = max(0.5, old_parameters.connection_strength * 0.95)
            
            # Адаптация порога стабильности
            if avg_clarity > 0.8:
                new_parameters.stability_threshold = min(0.9, old_parameters.stability_threshold * 1.02)
            elif avg_clarity < 0.6:
                new_parameters.stability_threshold = max(0.5, old_parameters.stability_threshold * 0.98)
            
            # Применение изменений
            changes_applied = []
            if new_parameters.base_energy_level != old_parameters.base_energy_level:
                changes_applied.append(f"Базовый уровень энергии: {old_parameters.base_energy_level} → {new_parameters.base_energy_level}")
            
            if new_parameters.connection_strength != old_parameters.connection_strength:
                changes_applied.append(f"Сила связей: {old_parameters.connection_strength} → {new_parameters.connection_strength}")
            
            if new_parameters.stability_threshold != old_parameters.stability_threshold:
                changes_applied.append(f"Порог стабильности: {old_parameters.stability_threshold} → {new_parameters.stability_threshold}")
            
            # Обновление параметров поля
            self.quantum_field.parameters = new_parameters
            
            # Пересоздание энергетической матрицы с новыми параметрами
            self.quantum_field._create_energy_matrix()
            
            # Обновление статистики
            self.quantum_field._update_field_statistics()
            
            result = {
                "success": True,
                "operation_code": "OP2",
                "operation_name": "Перенастройка среды",
                "participants_involved": len(participants),
                "old_field_health": field_health,
                "new_field_health": self.quantum_field.get_field_health_score(),
                "field_status": self.quantum_field.get_field_status(),
                "changes_applied": changes_applied,
                "parameters_updated": {
                    "base_energy_level": new_parameters.base_energy_level,
                    "connection_strength": new_parameters.connection_strength,
                    "stability_threshold": new_parameters.stability_threshold
                },
                "execution_time": datetime.now(),
                "metadata": {
                    "environment_adapted": True,
                    "field_parameters_updated": True,
                    "energy_matrix_recreated": True
                }
            }
            
            self.logger.info(f"OP2 завершена успешно: применено {len(changes_applied)} изменений")
            return result
            
        except Exception as e:
            error_msg = f"Ошибка при выполнении OP2: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg, "operation_code": "OP2"}
    
    def _execute_op3_regeneration_access(self, participant_ids: List[str], 
                                        parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Выполнение операции OP3: Доступ к регенерации.
        
        Активация процессов самовосстановления и регенерации для участников.
        """
        try:
            self.logger.info("Выполняю OP3: Доступ к регенерации")
            
            # Получение участников
            participants = [self.participant_manager.get_participant(pid) for pid in participant_ids]
            participants = [p for p in participants if p is not None]
            
            if not participants:
                return {"success": False, "error": "Не удалось получить участников"}
            
            # Анализ текущих состояний участников
            regeneration_results = []
            total_regeneration_applied = 0.0
            
            for participant in participants:
                quantum_state = participant.quantum_state
                
                # Определение потребности в регенерации
                regeneration_needs = []
                
                if quantum_state.energy_level < 1.0:
                    regeneration_needs.append("energy")
                if quantum_state.clarity < 0.7:
                    regeneration_needs.append("clarity")
                if quantum_state.protection < 0.7:
                    regeneration_needs.append("protection")
                if quantum_state.alignment < 0.6:
                    regeneration_needs.append("alignment")
                
                if not regeneration_needs:
                    continue  # Участник не нуждается в регенерации
                
                # Применение регенерации
                old_state = {
                    "energy_level": quantum_state.energy_level,
                    "clarity": quantum_state.clarity,
                    "protection": quantum_state.protection,
                    "alignment": quantum_state.alignment
                }
                
                # Регенерация энергии
                if "energy" in regeneration_needs:
                    regeneration_amount = min(0.4, (1.0 - quantum_state.energy_level) * 0.6)
                    quantum_state.energy_level = min(2.0, quantum_state.energy_level + regeneration_amount)
                
                # Регенерация ясности
                if "clarity" in regeneration_needs:
                    regeneration_amount = min(0.3, (1.0 - quantum_state.clarity) * 0.5)
                    quantum_state.clarity = min(1.0, quantum_state.clarity + regeneration_amount)
                
                # Регенерация защиты
                if "protection" in regeneration_needs:
                    regeneration_amount = min(0.3, (1.0 - quantum_state.protection) * 0.5)
                    quantum_state.protection = min(1.0, quantum_state.protection + regeneration_amount)
                
                # Регенерация выравнивания
                if "alignment" in regeneration_needs:
                    regeneration_amount = min(0.3, (1.0 - quantum_state.alignment) * 0.5)
                    quantum_state.alignment = min(1.0, quantum_state.alignment + regeneration_amount)
                
                # Обновление состояния участника
                participant.update_quantum_state(
                    energy_level=quantum_state.energy_level,
                    clarity=quantum_state.clarity,
                    protection=quantum_state.protection,
                    alignment=quantum_state.alignment
                )
                
                # Синхронизация с квантовым полем
                self.participant_manager.update_participant_quantum_state(
                    participant.participant_id,
                    np.array([
                        quantum_state.energy_level,
                        quantum_state.clarity,
                        quantum_state.protection,
                        quantum_state.alignment
                    ], dtype=np.float64)
                )
                
                # Расчет общего улучшения
                improvement = sum([
                    quantum_state.energy_level - old_state["energy_level"],
                    quantum_state.clarity - old_state["clarity"],
                    quantum_state.protection - old_state["protection"],
                    quantum_state.alignment - old_state["alignment"]
                ])
                
                total_regeneration_applied += improvement
                
                regeneration_results.append({
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "regeneration_needs": regeneration_needs,
                    "old_state": old_state,
                    "new_state": {
                        "energy_level": quantum_state.energy_level,
                        "clarity": quantum_state.clarity,
                        "protection": quantum_state.protection,
                        "alignment": quantum_state.alignment
                    },
                    "improvement": improvement
                })
            
            # Обновление статистики поля
            self.quantum_field._update_field_statistics()
            
            result = {
                "success": True,
                "operation_code": "OP3",
                "operation_name": "Доступ к регенерации",
                "participants_regenerated": len(regeneration_results),
                "total_regeneration_applied": round(total_regeneration_applied, 3),
                "regeneration_results": regeneration_results,
                "execution_time": datetime.now(),
                "metadata": {
                    "regeneration_activated": True,
                    "self_healing_enabled": True,
                    "quantum_field_updated": True
                }
            }
            
            self.logger.info(f"OP3 завершена успешно: регенерировано {len(regeneration_results)} участников")
            return result
            
        except Exception as e:
            error_msg = f"Ошибка при выполнении OP3: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg, "operation_code": "OP3"}
    
    def _execute_op4_information_cleansing(self, participant_ids: List[str], 
                                          parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Выполнение операции OP4: Информационная чистка.
        
        Очистка от негативных информационных влияний и восстановление чистоты сознания.
        """
        try:
            self.logger.info("Выполняю OP4: Информационная чистка")
            
            # Получение участников
            participants = [self.participant_manager.get_participant(pid) for pid in participant_ids]
            participants = [p for p in participants if p is not None]
            
            if len(participants) < 3:
                return {"success": False, "error": "Для OP4 требуется минимум 3 участника"}
            
            # Поиск инициатора для координации чистки
            initiator = None
            for participant in participants:
                if participant.role == "initiator" or "Zeya888" in participant.name:
                    initiator = participant
                    break
            
            if not initiator:
                return {"success": False, "error": "Инициатор (Zeya888) не найден среди участников"}
            
            # Создание защитного поля для информационной чистки
            protection_field_strength = min(1.0, 0.8 + (initiator.quantum_state.protection * 0.2))
            
            # Выполнение информационной чистки для каждого участника
            cleansing_results = []
            total_cleansing_applied = 0.0
            
            for participant in participants:
                if participant.participant_id == initiator.participant_id:
                    continue  # Инициатор уже чист
                
                quantum_state = participant.quantum_state
                
                # Анализ информационных загрязнений
                contamination_levels = {
                    "clarity": max(0.0, 1.0 - quantum_state.clarity),
                    "protection": max(0.0, 1.0 - quantum_state.protection),
                    "alignment": max(0.0, 1.0 - quantum_state.alignment)
                }
                
                total_contamination = sum(contamination_levels.values())
                
                if total_contamination < 0.1:
                    continue  # Участник уже достаточно чист
                
                # Применение информационной чистки
                old_state = {
                    "clarity": quantum_state.clarity,
                    "protection": quantum_state.protection,
                    "alignment": quantum_state.alignment
                }
                
                # Очистка ясности сознания
                clarity_cleansing = min(0.4, contamination_levels["clarity"] * 0.8)
                quantum_state.clarity = min(1.0, quantum_state.clarity + clarity_cleansing)
                
                # Усиление защиты
                protection_boost = min(0.3, contamination_levels["protection"] * 0.7)
                quantum_state.protection = min(1.0, quantum_state.protection + protection_boost)
                
                # Восстановление выравнивания
                alignment_restoration = min(0.3, contamination_levels["alignment"] * 0.7)
                quantum_state.alignment = min(1.0, quantum_state.alignment + alignment_restoration)
                
                # Обновление состояния участника
                participant.update_quantum_state(
                    clarity=quantum_state.clarity,
                    protection=quantum_state.protection,
                    alignment=quantum_state.alignment
                )
                
                # Синхронизация с квантовым полем
                self.participant_manager.update_participant_quantum_state(
                    participant.participant_id,
                    np.array([
                        quantum_state.energy_level,
                        quantum_state.clarity,
                        quantum_state.protection,
                        quantum_state.alignment
                    ], dtype=np.float64)
                )
                
                # Расчет общего очищения
                cleansing_applied = sum([
                    quantum_state.clarity - old_state["clarity"],
                    quantum_state.protection - old_state["protection"],
                    quantum_state.alignment - old_state["alignment"]
                ])
                
                total_cleansing_applied += cleansing_applied
                
                cleansing_results.append({
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "contamination_levels": contamination_levels,
                    "old_state": old_state,
                    "new_state": {
                        "clarity": quantum_state.clarity,
                        "protection": quantum_state.protection,
                        "alignment": quantum_state.alignment
                    },
                    "cleansing_applied": cleansing_applied
                })
            
            # Создание защитных связей между участниками
            protection_connections = []
            for i, participant1 in enumerate(participants):
                for j, participant2 in enumerate(participants[i+1:], i+1):
                    connection_id = self.quantum_field.create_connection(
                        participant1.participant_id,
                        participant2.participant_id,
                        strength=protection_field_strength * 0.8,
                        connection_type="protection",
                        metadata={"operation": "OP4", "purpose": "information_cleansing"}
                    )
                    if connection_id:
                        protection_connections.append(connection_id)
            
            # Обновление статистики поля
            self.quantum_field._update_field_statistics()
            
            result = {
                "success": True,
                "operation_code": "OP4",
                "operation_name": "Информационная чистка",
                "initiator": {
                    "participant_id": initiator.participant_id,
                    "name": initiator.name,
                    "protection": initiator.quantum_state.protection
                },
                "participants_cleansed": len(cleansing_results),
                "total_cleansing_applied": round(total_cleansing_applied, 3),
                "protection_field_strength": round(protection_field_strength, 3),
                "protection_connections_created": len(protection_connections),
                "cleansing_results": cleansing_results,
                "execution_time": datetime.now(),
                "metadata": {
                    "information_cleansed": True,
                    "protection_field_created": True,
                    "negative_influences_removed": True,
                    "quantum_field_updated": True
                }
            }
            
            self.logger.info(f"OP4 завершена успешно: очищено {len(cleansing_results)} участников")
            return result
            
        except Exception as e:
            error_msg = f"Ошибка при выполнении OP4: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg, "operation_code": "OP4"}
    
    def _update_operation_statistics(self, success: bool) -> None:
        """Обновление статистики операций."""
        self.operations_executed += 1
        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
        self.last_operation = datetime.now()
    
    def _record_operation(self, operation_code: str, participant_ids: List[str], 
                         result: Dict[str, Any]) -> None:
        """Запись операции в историю."""
        operation_record = {
            "operation_id": str(uuid.uuid4()),
            "operation_code": operation_code,
            "operation_name": self.operation_parameters[operation_code]["name"],
            "participant_ids": participant_ids,
            "execution_time": datetime.now().isoformat(),
            "success": result.get("success", False),
            "result_summary": {
                "participants_involved": result.get("participants_aligned", result.get("participants_regenerated", result.get("participants_cleansed", 0))),
                "total_improvement": result.get("total_alignment_improvement", result.get("total_regeneration_applied", result.get("total_cleansing_applied", 0)),
                "metadata": result.get("metadata", {})
            }
        }
        
        self.operation_history.append(operation_record)
        
        # Ограничение истории последними 100 операциями
        if len(self.operation_history) > 100:
            self.operation_history = self.operation_history[-100:]
    
    def get_operation_statistics(self) -> Dict[str, Any]:
        """Получение статистики операций."""
        return {
            "total_operations": self.operations_executed,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.successful_operations / self.operations_executed if self.operations_executed > 0 else 0.0,
            "last_operation": self.last_operation.isoformat() if self.last_operation else None,
            "operation_parameters": self.operation_parameters
        }
    
    def get_operation_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получение истории операций."""
        if limit is None:
            return self.operation_history.copy()
        else:
            return self.operation_history[-limit:].copy()
    
    def __str__(self) -> str:
        return f"QuantumOperations(executed={self.operations_executed}, success_rate={self.successful_operations/self.operations_executed:.2f})"
    
    def __repr__(self) -> str:
        return f"QuantumOperations(participant_manager={'set' if self.participant_manager else 'not_set'}, quantum_field={'set' if self.quantum_field else 'not_set'})"
