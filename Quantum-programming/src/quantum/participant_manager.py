"""
Менеджер участников протокола SIRUS-FELINE_BRANCH_PROTOCOL.
Централизованное управление созданием, жизненным циклом и синхронизацией участников.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import uuid
import numpy as np

from ..core.participant import Participant, QuantumState
from .quantum_field import QuantumField


class ParticipantCreationError(Exception):
    """Исключение для ошибок создания участников."""
    pass


class ParticipantSyncError(Exception):
    """Исключение для ошибок синхронизации участников."""
    pass


class ParticipantManager:
    """Менеджер для управления участниками протокола."""
    
    def __init__(self, quantum_field: Optional[QuantumField] = None, 
                 log_level: int = logging.INFO):
        """Инициализация менеджера участников."""
        self.logger = self._setup_logger(log_level)
        self.quantum_field = quantum_field
        
        # Хранилище участников
        self.participants: Dict[str, Participant] = {}
        self.participants_by_role: Dict[str, List[str]] = {}
        self.participants_by_status: Dict[str, List[str]] = {}
        
        # Статистика
        self.total_participants: int = 0
        self.active_participants: int = 0
        self.paused_participants: int = 0
        self.exited_participants: int = 0
        
        # Метаданные
        self.created_at: datetime = datetime.now()
        self.last_updated: datetime = datetime.now()
        
        self.logger.info("ParticipantManager инициализирован")
    
    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Настройка логгера для менеджера участников."""
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
    
    def set_quantum_field(self, quantum_field: QuantumField) -> None:
        """Установка квантового поля для менеджера."""
        self.quantum_field = quantum_field
        self.logger.info("Квантовое поле установлено для менеджера участников")
    
    def create_participant(self, name: str, role: str, 
                          initial_quantum_state: Optional[QuantumState] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> Participant:
        """
        Создание нового участника протокола.
        
        Args:
            name: Имя участника
            role: Роль участника
            initial_quantum_state: Начальное квантовое состояние
            metadata: Дополнительные метаданные
            
        Returns:
            Participant: Созданный участник
            
        Raises:
            ParticipantCreationError: При ошибке создания участника
        """
        try:
            self.logger.info(f"Создаю участника: {name} с ролью: {role}")
            
            # Создание участника
            participant = Participant(
                name=name,
                role=role,
                quantum_state=initial_quantum_state or QuantumState(),
                metadata=metadata or {}
            )
            
            # Добавление в хранилище
            self._add_participant_to_storage(participant)
            
            # Добавление в квантовое поле, если оно доступно
            if self.quantum_field and self.quantum_field.is_initialized:
                if self.quantum_field.add_participant(participant):
                    self.logger.info(f"Участник {name} добавлен в квантовое поле")
                else:
                    self.logger.warning(f"Не удалось добавить участника {name} в квантовое поле")
            
            # Обновление статистики
            self._update_statistics()
            
            self.logger.info(f"Участник {name} успешно создан с ID: {participant.participant_id}")
            return participant
            
        except Exception as e:
            error_msg = f"Ошибка при создании участника {name}: {str(e)}"
            self.logger.error(error_msg)
            raise ParticipantCreationError(error_msg) from e
    
    def create_participant_from_template(self, template_name: str, 
                                       custom_name: Optional[str] = None,
                                       custom_metadata: Optional[Dict[str, Any]] = None) -> Participant:
        """
        Создание участника из шаблона.
        
        Args:
            template_name: Название шаблона
            custom_name: Кастомное имя (если не указано, используется имя шаблона)
            custom_metadata: Дополнительные метаданные
            
        Returns:
            Participant: Созданный участник
        """
        templates = self._get_participant_templates()
        
        if template_name not in templates:
            raise ParticipantCreationError(f"Шаблон {template_name} не найден")
        
        template = templates[template_name]
        name = custom_name or template["name"]
        
        # Создание квантового состояния из шаблона
        quantum_state = QuantumState(
            energy_level=template["quantum_state"]["energy_level"],
            clarity=template["quantum_state"]["clarity"],
            protection=template["quantum_state"]["protection"],
            alignment=template["quantum_state"]["alignment"]
        )
        
        # Объединение метаданных
        metadata = template.get("metadata", {}).copy()
        if custom_metadata:
            metadata.update(custom_metadata)
        
        return self.create_participant(
            name=name,
            role=template["role"],
            initial_quantum_state=quantum_state,
            metadata=metadata
        )
    
    def _get_participant_templates(self) -> Dict[str, Any]:
        """Получение шаблонов участников."""
        return {
            "initiator": {
                "name": "Zeya888",
                "role": "initiator",
                "quantum_state": {
                    "energy_level": 1.8,
                    "clarity": 0.9,
                    "protection": 0.95,
                    "alignment": 0.95
                },
                "metadata": {
                    "channel_type": "primary",
                    "sirius_connection": True,
                    "activation_privileges": True
                }
            },
            "husband": {
                "name": "Мигель",
                "role": "family_member",
                "quantum_state": {
                    "energy_level": 1.2,
                    "clarity": 0.7,
                    "protection": 0.8,
                    "alignment": 0.6
                },
                "metadata": {
                    "family_role": "husband",
                    "support_level": "high"
                }
            },
            "child": {
                "name": "Тристан",
                "role": "family_member",
                "quantum_state": {
                    "energy_level": 1.5,
                    "clarity": 0.8,
                    "protection": 0.9,
                    "alignment": 0.7
                },
                "metadata": {
                    "family_role": "child",
                    "age_group": "young",
                    "priority_level": "highest"
                }
            },
            "parent": {
                "name": "Фаина",
                "role": "family_member",
                "quantum_state": {
                    "energy_level": 1.0,
                    "clarity": 0.6,
                    "protection": 0.7,
                    "alignment": 0.5
                },
                "metadata": {
                    "family_role": "parent",
                    "generation": "elder"
                }
            }
        }
    
    def _add_participant_to_storage(self, participant: Participant) -> None:
        """Добавление участника в хранилище."""
        participant_id = participant.participant_id
        
        # Основное хранилище
        self.participants[participant_id] = participant
        
        # Хранилище по ролям
        role = participant.role
        if role not in self.participants_by_role:
            self.participants_by_role[role] = []
        self.participants_by_role[role].append(participant_id)
        
        # Хранилище по статусам
        status = participant.status
        if status not in self.participants_by_status:
            self.participants_by_status[status] = []
        self.participants_by_status[status].append(participant_id)
        
        self.total_participants += 1
        self.last_updated = datetime.now()
    
    def get_participant(self, participant_id: str) -> Optional[Participant]:
        """Получение участника по ID."""
        return self.participants.get(participant_id)
    
    def get_participants_by_role(self, role: str) -> List[Participant]:
        """Получение участников по роли."""
        participant_ids = self.participants_by_role.get(role, [])
        return [self.participants[pid] for pid in participant_ids if pid in self.participants]
    
    def get_participants_by_status(self, status: str) -> List[Participant]:
        """Получение участников по статусу."""
        participant_ids = self.participants_by_status.get(status, [])
        return [self.participants[pid] for pid in participant_ids if pid in self.participants]
    
    def get_all_participants(self) -> List[Participant]:
        """Получение всех участников."""
        return list(self.participants.values())
    
    def remove_participant(self, participant_id: str) -> bool:
        """
        Удаление участника.
        
        Args:
            participant_id: ID участника для удаления
            
        Returns:
            bool: True если участник успешно удален
        """
        try:
            if participant_id not in self.participants:
                self.logger.warning(f"Участник {participant_id} не найден")
                return False
            
            participant = self.participants[participant_id]
            participant_name = participant.name
            
            # Удаление из квантового поля
            if self.quantum_field:
                self.quantum_field.remove_participant(participant_id)
            
            # Удаление из хранилищ
            self._remove_participant_from_storage(participant_id)
            
            # Обновление статистики
            self._update_statistics()
            
            self.logger.info(f"Участник {participant_name} успешно удален")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при удалении участника: {str(e)}")
            return False
    
    def _remove_participant_from_storage(self, participant_id: str) -> None:
        """Удаление участника из всех хранилищ."""
        # Основное хранилище
        if participant_id in self.participants:
            del self.participants[participant_id]
        
        # Хранилище по ролям
        for role, participant_ids in self.participants_by_role.items():
            if participant_id in participant_ids:
                participant_ids.remove(participant_id)
        
        # Хранилище по статусам
        for status, participant_ids in self.participants_by_status.items():
            if participant_id in participant_ids:
                participant_ids.remove(participant_id)
        
        self.total_participants = max(0, self.total_participants - 1)
        self.last_updated = datetime.now()
    
    def update_participant_status(self, participant_id: str, new_status: str) -> bool:
        """
        Обновление статуса участника.
        
        Args:
            participant_id: ID участника
            new_status: Новый статус
            
        Returns:
            bool: True если статус успешно обновлен
        """
        try:
            participant = self.get_participant(participant_id)
            if not participant:
                self.logger.error(f"Участник {participant_id} не найден")
                return False
            
            old_status = participant.status
            
            # Обновление статуса участника
            if new_status == "active":
                participant.resume_participation()
            elif new_status == "paused":
                participant.pause_participation()
            elif new_status == "exited":
                participant.exit_protocol()
            else:
                participant.status = new_status
            
            # Обновление хранилищ
            if old_status in self.participants_by_status:
                if participant_id in self.participants_by_status[old_status]:
                    self.participants_by_status[old_status].remove(participant_id)
            
            if new_status not in self.participants_by_status:
                self.participants_by_status[new_status] = []
            self.participants_by_status[new_status].append(participant_id)
            
            self.last_updated = datetime.now()
            self.logger.info(f"Статус участника {participant.name} изменен с {old_status} на {new_status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении статуса участника: {str(e)}")
            return False
    
    def get_participant_statistics(self) -> Dict[str, Any]:
        """Получение статистики по участникам."""
        return {
            "total_participants": self.total_participants,
            "active_participants": len(self.get_participants_by_status("active")),
            "paused_participants": len(self.get_participants_by_status("paused")),
            "exited_participants": len(self.get_participants_by_status("exited")),
            "inactive_participants": len(self.get_participants_by_status("inactive")),
            "participants_by_role": {role: len(participants) for role, participants in self.participants_by_role.items()},
            "last_updated": self.last_updated.isoformat()
        }
    
    def _update_statistics(self) -> None:
        """Обновление статистики участников."""
        self.active_participants = len(self.get_participants_by_status("active"))
        self.paused_participants = len(self.get_participants_by_status("paused"))
        self.exited_participants = len(self.get_participants_by_status("exited"))
        self.last_updated = datetime.now()
    
    # Методы управления квантовыми состояниями
    
    def update_participant_quantum_state(self, participant_id: str, 
                                       energy_level: Optional[float] = None,
                                       clarity: Optional[float] = None,
                                       protection: Optional[float] = None,
                                       alignment: Optional[float] = None) -> bool:
        """
        Обновление квантового состояния участника.
        
        Args:
            participant_id: ID участника
            energy_level: Новый уровень энергии
            clarity: Новая ясность
            protection: Новый уровень защиты
            alignment: Новое выравнивание
            
        Returns:
            bool: True если состояние успешно обновлено
        """
        try:
            participant = self.get_participant(participant_id)
            if not participant:
                self.logger.error(f"Участник {participant_id} не найден")
                return False
            
            # Обновление состояния участника
            participant.update_quantum_state(
                energy_level=energy_level,
                clarity=clarity,
                protection=protection,
                alignment=alignment
            )
            
            # Синхронизация с квантовым полем
            if self.quantum_field and self.quantum_field.is_initialized:
                new_state = np.array([
                    participant.quantum_state.energy_level,
                    participant.quantum_state.clarity,
                    participant.quantum_state.protection,
                    participant.quantum_state.alignment
                ], dtype=np.float64)
                
                if self.quantum_field.update_participant_quantum_state(participant_id, new_state):
                    self.logger.debug(f"Квантовое состояние участника {participant.name} синхронизировано с полем")
                else:
                    self.logger.warning(f"Не удалось синхронизировать состояние участника {participant.name} с полем")
            
            self.last_updated = datetime.now()
            self.logger.info(f"Квантовое состояние участника {participant.name} обновлено")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении квантового состояния: {str(e)}")
            return False
    
    def get_participant_quantum_state(self, participant_id: str) -> Optional[Dict[str, float]]:
        """
        Получение квантового состояния участника.
        
        Args:
            participant_id: ID участника
            
        Returns:
            Optional[Dict[str, float]]: Квантовое состояние или None если не найдено
        """
        participant = self.get_participant(participant_id)
        if not participant:
            return None
        
        return {
            "energy_level": participant.quantum_state.energy_level,
            "clarity": participant.quantum_state.clarity,
            "protection": participant.quantum_state.protection,
            "alignment": participant.quantum_state.alignment
        }
    
    def get_all_quantum_states(self) -> Dict[str, Dict[str, float]]:
        """Получение всех квантовых состояний участников."""
        states = {}
        for participant_id, participant in self.participants.items():
            states[participant_id] = {
                "name": participant.name,
                "role": participant.role,
                "energy_level": participant.quantum_state.energy_level,
                "clarity": participant.quantum_state.clarity,
                "protection": participant.quantum_state.protection,
                "alignment": participant.quantum_state.alignment
            }
        return states
    
    def validate_quantum_state(self, participant_id: str) -> Dict[str, Any]:
        """
        Валидация квантового состояния участника.
        
        Args:
            participant_id: ID участника
            
        Returns:
            Dict[str, Any]: Результат валидации
        """
        participant = self.get_participant(participant_id)
        if not participant:
            return {"valid": False, "errors": ["Участник не найден"]}
        
        quantum_state = participant.quantum_state
        errors = []
        warnings = []
        
        # Проверка диапазонов значений
        if not 0.0 <= quantum_state.energy_level <= 2.0:
            errors.append(f"Уровень энергии {quantum_state.energy_level} вне диапазона [0.0, 2.0]")
        
        if not 0.0 <= quantum_state.clarity <= 1.0:
            errors.append(f"Ясность {quantum_state.clarity} вне диапазона [0.0, 1.0]")
        
        if not 0.0 <= quantum_state.protection <= 1.0:
            errors.append(f"Защита {quantum_state.protection} вне диапазона [0.0, 1.0]")
        
        if not 0.0 <= quantum_state.alignment <= 1.0:
            errors.append(f"Выравнивание {quantum_state.alignment} вне диапазона [0.0, 1.0]")
        
        # Проверка критических значений
        if quantum_state.energy_level < 0.3:
            warnings.append("Критически низкий уровень энергии")
        
        if quantum_state.clarity < 0.3:
            warnings.append("Критически низкая ясность")
        
        if quantum_state.protection < 0.4:
            warnings.append("Недостаточный уровень защиты")
        
        if quantum_state.alignment < 0.3:
            warnings.append("Критически низкое выравнивание")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "participant_name": participant.name,
            "state_summary": {
                "energy_level": quantum_state.energy_level,
                "clarity": quantum_state.clarity,
                "protection": quantum_state.protection,
                "alignment": quantum_state.alignment
            }
        }
    
    def normalize_quantum_state(self, participant_id: str) -> bool:
        """
        Нормализация квантового состояния участника.
        
        Args:
            participant_id: ID участника
            
        Returns:
            bool: True если нормализация прошла успешно
        """
        try:
            participant = self.get_participant(participant_id)
            if not participant:
                self.logger.error(f"Участник {participant_id} не найден")
                return False
            
            quantum_state = participant.quantum_state
            
            # Нормализация значений в допустимые диапазоны
            quantum_state.energy_level = max(0.0, min(2.0, quantum_state.energy_level))
            quantum_state.clarity = max(0.0, min(1.0, quantum_state.clarity))
            quantum_state.protection = max(0.0, min(1.0, quantum_state.protection))
            quantum_state.alignment = max(0.0, min(1.0, quantum_state.alignment))
            
            # Синхронизация с квантовым полем
            if self.quantum_field and self.quantum_field.is_initialized:
                new_state = np.array([
                    quantum_state.energy_level,
                    quantum_state.clarity,
                    quantum_state.protection,
                    quantum_state.alignment
                ], dtype=np.float64)
                
                self.quantum_field.update_participant_quantum_state(participant_id, new_state)
            
            self.logger.info(f"Квантовое состояние участника {participant.name} нормализовано")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при нормализации квантового состояния: {str(e)}")
            return False
    
    def analyze_quantum_states(self) -> Dict[str, Any]:
        """Анализ всех квантовых состояний участников."""
        if not self.participants:
            return {"total_participants": 0, "analysis": {}}
        
        analysis = {
            "total_participants": len(self.participants),
            "energy_analysis": {},
            "clarity_analysis": {},
            "protection_analysis": {},
            "alignment_analysis": {},
            "overall_health": {},
            "recommendations": []
        }
        
        # Сбор данных по всем состояниям
        energy_levels = []
        clarity_levels = []
        protection_levels = []
        alignment_levels = []
        
        for participant in self.participants.values():
            quantum_state = participant.quantum_state
            energy_levels.append(quantum_state.energy_level)
            clarity_levels.append(quantum_state.clarity)
            protection_levels.append(quantum_state.protection)
            alignment_levels.append(quantum_state.alignment)
        
        # Анализ энергии
        analysis["energy_analysis"] = {
            "mean": np.mean(energy_levels),
            "std": np.std(energy_levels),
            "min": np.min(energy_levels),
            "max": np.max(energy_levels),
            "low_energy_count": sum(1 for e in energy_levels if e < 0.5)
        }
        
        # Анализ ясности
        analysis["clarity_analysis"] = {
            "mean": np.mean(clarity_levels),
            "std": np.std(clarity_levels),
            "min": np.min(clarity_levels),
            "max": np.max(clarity_levels),
            "low_clarity_count": sum(1 for c in clarity_levels if c < 0.4)
        }
        
        # Анализ защиты
        analysis["protection_analysis"] = {
            "mean": np.mean(protection_levels),
            "std": np.std(protection_levels),
            "min": np.min(protection_levels),
            "max": np.max(protection_levels),
            "low_protection_count": sum(1 for p in protection_levels if p < 0.5)
        }
        
        # Анализ выравнивания
        analysis["alignment_analysis"] = {
            "mean": np.mean(alignment_levels),
            "std": np.std(alignment_levels),
            "min": np.min(alignment_levels),
            "max": np.max(alignment_levels),
            "low_alignment_count": sum(1 for a in alignment_levels if a < 0.4)
        }
        
        # Общая оценка здоровья
        overall_health_scores = []
        for i in range(len(self.participants)):
            health_score = (
                energy_levels[i] / 2.0 +  # Нормализация к [0, 1]
                clarity_levels[i] +
                protection_levels[i] +
                alignment_levels[i]
            ) / 4.0
            overall_health_scores.append(health_score)
        
        analysis["overall_health"] = {
            "mean": np.mean(overall_health_scores),
            "std": np.std(overall_health_scores),
            "min": np.min(overall_health_scores),
            "max": np.max(overall_health_scores),
            "excellent_count": sum(1 for h in overall_health_scores if h >= 0.8),
            "good_count": sum(1 for h in overall_health_scores if 0.6 <= h < 0.8),
            "fair_count": sum(1 for h in overall_health_scores if 0.4 <= h < 0.6),
            "poor_count": sum(1 for h in overall_health_scores if h < 0.4)
        }
        
        # Генерация рекомендаций
        recommendations = []
        
        if analysis["energy_analysis"]["low_energy_count"] > len(self.participants) * 0.3:
            recommendations.append("Более 30% участников имеют низкий уровень энергии - требуется энергетическая поддержка")
        
        if analysis["clarity_analysis"]["low_clarity_count"] > len(self.participants) * 0.4:
            recommendations.append("Более 40% участников имеют низкую ясность - требуется работа с сознанием")
        
        if analysis["protection_analysis"]["low_protection_count"] > len(self.participants) * 0.3:
            recommendations.append("Более 30% участников имеют недостаточную защиту - требуется усиление защитных механизмов")
        
        if analysis["overall_health"]["poor_count"] > 0:
            recommendations.append(f"{analysis['overall_health']['poor_count']} участников имеют критически низкое здоровье - требуется немедленное вмешательство")
        
        analysis["recommendations"] = recommendations
        
        return analysis
    
    def monitor_quantum_states(self) -> Dict[str, Any]:
        """Мониторинг квантовых состояний участников."""
        monitoring_data = {
            "timestamp": datetime.now().isoformat(),
            "total_participants": len(self.participants),
            "active_participants": self.active_participants,
            "quantum_field_status": "unknown",
            "state_validation": {},
            "critical_issues": [],
            "warnings": []
        }
        
        # Проверка статуса квантового поля
        if self.quantum_field:
            monitoring_data["quantum_field_status"] = self.quantum_field.get_field_status()
        
        # Валидация состояний всех участников
        for participant_id, participant in self.participants.items():
            validation_result = self.validate_quantum_state(participant_id)
            monitoring_data["state_validation"][participant_id] = {
                "name": participant.name,
                "valid": validation_result["valid"],
                "errors": validation_result["errors"],
                "warnings": validation_result["warnings"]
            }
            
            # Сбор критических проблем
            if not validation_result["valid"]:
                monitoring_data["critical_issues"].append({
                    "participant_id": participant_id,
                    "name": participant.name,
                    "errors": validation_result["errors"]
                })
            
            # Сбор предупреждений
            if validation_result["warnings"]:
                monitoring_data["warnings"].append({
                    "participant_id": participant_id,
                    "name": participant.name,
                    "warnings": validation_result["warnings"]
                })
        
        return monitoring_data
    
    # Методы синхронизации между участниками
    
    def synchronize_participants(self, participant_ids: List[str], 
                               sync_type: str = "energy_balance") -> Dict[str, Any]:
        """
        Синхронизация группы участников.
        
        Args:
            participant_ids: Список ID участников для синхронизации
            sync_type: Тип синхронизации (energy_balance, clarity_boost, protection_sync, alignment_group)
            
        Returns:
            Dict[str, Any]: Результат синхронизации
        """
        try:
            if not participant_ids:
                return {"success": False, "error": "Список участников пуст"}
            
            # Проверка существования всех участников
            participants = []
            for participant_id in participant_ids:
                participant = self.get_participant(participant_id)
                if not participant:
                    return {"success": False, "error": f"Участник {participant_id} не найден"}
                participants.append(participant)
            
            self.logger.info(f"Начинаю синхронизацию {len(participants)} участников по типу: {sync_type}")
            
            sync_result = {"success": True, "sync_type": sync_type, "participants": [], "changes": []}
            
            if sync_type == "energy_balance":
                sync_result = self._synchronize_energy_balance(participants)
            elif sync_type == "clarity_boost":
                sync_result = self._synchronize_clarity_boost(participants)
            elif sync_type == "protection_sync":
                sync_result = self._synchronize_protection(participants)
            elif sync_type == "alignment_group":
                sync_result = self._synchronize_alignment(participants)
            else:
                return {"success": False, "error": f"Неизвестный тип синхронизации: {sync_type}"}
            
            # Обновление статистики
            self._update_statistics()
            
            self.logger.info(f"Синхронизация завершена успешно для {len(participants)} участников")
            return sync_result
            
        except Exception as e:
            error_msg = f"Ошибка при синхронизации участников: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _synchronize_energy_balance(self, participants: List[Participant]) -> Dict[str, Any]:
        """Синхронизация энергетического баланса между участниками."""
        if len(participants) < 2:
            return {"success": False, "error": "Для синхронизации требуется минимум 2 участника"}
        
        # Расчет среднего уровня энергии
        energy_levels = [p.quantum_state.energy_level for p in participants]
        mean_energy = np.mean(energy_levels)
        
        changes = []
        for participant in participants:
            old_energy = participant.quantum_state.energy_level
            new_energy = max(0.0, min(2.0, mean_energy * 0.9 + old_energy * 0.1))  # Плавная корректировка
            
            if abs(new_energy - old_energy) > 0.1:  # Только значимые изменения
                participant.update_quantum_state(energy_level=new_energy)
                changes.append({
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "old_energy": old_energy,
                    "new_energy": new_energy,
                    "change": new_energy - old_energy
                })
        
        return {
            "success": True,
            "sync_type": "energy_balance",
            "mean_energy": mean_energy,
            "changes": changes,
            "participants_synced": len(participants)
        }
    
    def _synchronize_clarity_boost(self, participants: List[Participant]) -> Dict[str, Any]:
        """Синхронизация ясности сознания между участниками."""
        if len(participants) < 2:
            return {"success": False, "error": "Для синхронизации требуется минимум 2 участника"}
        
        # Нахождение участника с наивысшей ясностью
        max_clarity_participant = max(participants, key=lambda p: p.quantum_state.clarity)
        max_clarity = max_clarity_participant.quantum_state.clarity
        
        changes = []
        for participant in participants:
            if participant.participant_id == max_clarity_participant.participant_id:
                continue  # Пропускаем источник ясности
            
            old_clarity = participant.quantum_state.clarity
            new_clarity = min(1.0, old_clarity + (max_clarity - old_clarity) * 0.3)  # Умеренное повышение
            
            if new_clarity > old_clarity:
                participant.update_quantum_state(clarity=new_clarity)
                changes.append({
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "old_clarity": old_clarity,
                    "new_clarity": new_clarity,
                    "boost": new_clarity - old_clarity
                })
        
        return {
            "success": True,
            "sync_type": "clarity_boost",
            "source_participant": max_clarity_participant.name,
            "source_clarity": max_clarity,
            "changes": changes,
            "participants_synced": len(changes)
        }
    
    def _synchronize_protection(self, participants: List[Participant]) -> Dict[str, Any]:
        """Синхронизация защитных механизмов между участниками."""
        if len(participants) < 2:
            return {"success": False, "error": "Для синхронизации требуется минимум 2 участника"}
        
        # Расчет среднего уровня защиты
        protection_levels = [p.quantum_state.protection for p in participants]
        mean_protection = np.mean(protection_levels)
        
        changes = []
        for participant in participants:
            old_protection = participant.quantum_state.protection
            new_protection = max(0.0, min(1.0, mean_protection * 0.8 + old_protection * 0.2))
            
            if abs(new_protection - old_protection) > 0.05:
                participant.update_quantum_state(protection=new_protection)
                changes.append({
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "old_protection": old_protection,
                    "new_protection": new_protection,
                    "change": new_protection - old_protection
                })
        
        return {
            "success": True,
            "sync_type": "protection_sync",
            "mean_protection": mean_protection,
            "changes": changes,
            "participants_synced": len(participants)
        }
    
    def _synchronize_alignment(self, participants: List[Participant]) -> Dict[str, Any]:
        """Синхронизация выравнивания с траекторией между участниками."""
        if len(participants) < 2:
            return {"success": False, "error": "Для синхронизации требуется минимум 2 участника"}
        
        # Нахождение участника с наивысшим выравниванием
        max_alignment_participant = max(participants, key=lambda p: p.quantum_state.alignment)
        max_alignment = max_alignment_participant.quantum_state.alignment
        
        changes = []
        for participant in participants:
            if participant.participant_id == max_alignment_participant.participant_id:
                continue  # Пропускаем источник выравнивания
            
            old_alignment = participant.quantum_state.alignment
            new_alignment = min(1.0, old_alignment + (max_alignment - old_alignment) * 0.25)
            
            if new_alignment > old_alignment:
                participant.update_quantum_state(alignment=new_alignment)
                changes.append({
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "old_alignment": old_alignment,
                    "new_alignment": new_alignment,
                    "improvement": new_alignment - old_alignment
                })
        
        return {
            "success": True,
            "sync_type": "alignment_group",
            "source_participant": max_alignment_participant.name,
            "source_alignment": max_alignment,
            "changes": changes,
            "participants_synced": len(changes)
        }
    
    def coordinate_group_activity(self, activity_type: str, 
                                participant_ids: List[str],
                                parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Координация групповой активности участников.
        
        Args:
            activity_type: Тип активности
            participant_ids: Список ID участников
            parameters: Параметры активности
            
        Returns:
            Dict[str, Any]: Результат координации
        """
        try:
            if not participant_ids:
                return {"success": False, "error": "Список участников пуст"}
            
            participants = [self.get_participant(pid) for pid in participant_ids if self.get_participant(pid)]
            if len(participants) != len(participant_ids):
                return {"success": False, "error": "Некоторые участники не найдены"}
            
            self.logger.info(f"Координирую групповую активность: {activity_type} для {len(participants)} участников")
            
            if activity_type == "meditation_session":
                return self._coordinate_meditation_session(participants, parameters)
            elif activity_type == "energy_healing":
                return self._coordinate_energy_healing(participants, parameters)
            elif activity_type == "group_protection":
                return self._coordinate_group_protection(participants, parameters)
            elif activity_type == "collective_intention":
                return self._coordinate_collective_intention(participants, parameters)
            else:
                return {"success": False, "error": f"Неизвестный тип активности: {activity_type}"}
                
        except Exception as e:
            error_msg = f"Ошибка при координации групповой активности: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _coordinate_meditation_session(self, participants: List[Participant], 
                                     parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Координация сессии медитации."""
        duration = parameters.get("duration", 15) if parameters else 15
        
        # Повышение ясности и выравнивания для всех участников
        changes = []
        for participant in participants:
            old_clarity = participant.quantum_state.clarity
            old_alignment = participant.quantum_state.alignment
            
            new_clarity = min(1.0, old_clarity + 0.1)
            new_alignment = min(1.0, old_alignment + 0.08)
            
            participant.update_quantum_state(clarity=new_clarity, alignment=new_alignment)
            
            changes.append({
                "participant_id": participant.participant_id,
                "name": participant.name,
                "clarity_boost": new_clarity - old_clarity,
                "alignment_boost": new_alignment - old_alignment
            })
        
        return {
            "success": True,
            "activity_type": "meditation_session",
            "duration_minutes": duration,
            "participants_involved": len(participants),
            "changes": changes
        }
    
    def _coordinate_energy_healing(self, participants: List[Participant], 
                                  parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Координация энергетического исцеления."""
        healing_focus = parameters.get("focus", "general") if parameters else "general"
        
        changes = []
        for participant in participants:
            old_energy = participant.quantum_state.energy_level
            old_protection = participant.quantum_state.protection
            
            # Исцеление в зависимости от фокуса
            if healing_focus == "energy":
                new_energy = min(2.0, old_energy + 0.3)
                participant.update_quantum_state(energy_level=new_energy)
                changes.append({
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "energy_healed": new_energy - old_energy
                })
            elif healing_focus == "protection":
                new_protection = min(1.0, old_protection + 0.2)
                participant.update_quantum_state(protection=new_protection)
                changes.append({
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "protection_enhanced": new_protection - old_protection
                })
            else:  # general healing
                new_energy = min(2.0, old_energy + 0.2)
                new_protection = min(1.0, old_protection + 0.15)
                participant.update_quantum_state(energy_level=new_energy, protection=new_protection)
                changes.append({
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "energy_healed": new_energy - old_energy,
                    "protection_enhanced": new_protection - old_protection
                })
        
        return {
            "success": True,
            "activity_type": "energy_healing",
            "healing_focus": healing_focus,
            "participants_healed": len(participants),
            "changes": changes
        }
    
    def _coordinate_group_protection(self, participants: List[Participant], 
                                   parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Координация групповой защиты."""
        protection_level = parameters.get("level", "standard") if parameters else "standard"
        
        # Усиление защиты для всех участников
        protection_boost = {"standard": 0.15, "enhanced": 0.25, "maximum": 0.4}[protection_level]
        
        changes = []
        for participant in participants:
            old_protection = participant.quantum_state.protection
            new_protection = min(1.0, old_protection + protection_boost)
            
            participant.update_quantum_state(protection=new_protection)
            
            changes.append({
                "participant_id": participant.participant_id,
                "name": participant.name,
                "protection_boost": new_protection - old_protection
            })
        
        return {
            "success": True,
            "activity_type": "group_protection",
            "protection_level": protection_level,
            "protection_boost": protection_boost,
            "participants_protected": len(participants),
            "changes": changes
        }
    
    def _coordinate_collective_intention(self, participants: List[Participant], 
                                       parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Координация коллективного намерения."""
        intention_type = parameters.get("type", "harmony") if parameters else "harmony"
        
        # Усиление выравнивания для всех участников
        alignment_boost = {"harmony": 0.2, "growth": 0.25, "transformation": 0.3}[intention_type]
        
        changes = []
        for participant in participants:
            old_alignment = participant.quantum_state.alignment
            new_alignment = min(1.0, old_alignment + alignment_boost)
            
            participant.update_quantum_state(alignment=new_alignment)
            
            changes.append({
                "participant_id": participant.participant_id,
                "name": participant.name,
                "alignment_boost": new_alignment - old_alignment
            })
        
        return {
            "success": True,
            "activity_type": "collective_intention",
            "intention_type": intention_type,
            "alignment_boost": alignment_boost,
            "participants_aligned": len(participants),
            "changes": changes
        }
    
    def get_group_synchronization_status(self, participant_ids: List[str]) -> Dict[str, Any]:
        """
        Получение статуса синхронизации группы участников.
        
        Args:
            participant_ids: Список ID участников
            
        Returns:
            Dict[str, Any]: Статус синхронизации
        """
        if not participant_ids:
            return {"synchronized": False, "error": "Список участников пуст"}
        
        participants = [self.get_participant(pid) for pid in participant_ids if self.get_participant(pid)]
        if len(participants) != len(participant_ids):
            return {"synchronized": False, "error": "Некоторые участники не найдены"}
        
        # Анализ синхронизации по различным параметрам
        energy_levels = [p.quantum_state.energy_level for p in participants]
        clarity_levels = [p.quantum_state.clarity for p in participants]
        protection_levels = [p.quantum_state.protection for p in participants]
        alignment_levels = [p.quantum_state.alignment for p in participants]
        
        # Расчет коэффициентов синхронизации (0.0 - 1.0)
        energy_sync = 1.0 - (np.std(energy_levels) / (np.mean(energy_levels) + 1e-6))
        clarity_sync = 1.0 - np.std(clarity_levels)
        protection_sync = 1.0 - np.std(protection_levels)
        alignment_sync = 1.0 - np.std(alignment_levels)
        
        # Общая оценка синхронизации
        overall_sync = (energy_sync + clarity_sync + protection_sync + alignment_sync) / 4.0
        
        return {
            "synchronized": overall_sync >= 0.7,
            "overall_sync_score": round(overall_sync, 3),
            "energy_sync": round(energy_sync, 3),
            "clarity_sync": round(clarity_sync, 3),
            "protection_sync": round(protection_sync, 3),
            "alignment_sync": round(alignment_sync, 3),
            "participants_count": len(participants),
            "sync_quality": "excellent" if overall_sync >= 0.8 else "good" if overall_sync >= 0.6 else "fair" if overall_sync >= 0.4 else "poor"
        }
    
    # Методы проверки готовности к операциям
    
    def check_participant_readiness(self, participant_id: str, 
                                   operation_type: str = "general") -> Dict[str, Any]:
        """
        Проверка готовности участника к операциям.
        
        Args:
            participant_id: ID участника
            operation_type: Тип операции
            
        Returns:
            Dict[str, Any]: Результат проверки готовности
        """
        try:
            participant = self.get_participant(participant_id)
            if not participant:
                return {"ready": False, "error": "Участник не найден"}
            
            # Базовые проверки
            basic_checks = self._perform_basic_readiness_checks(participant)
            
            # Специфичные проверки для типа операции
            operation_checks = self._perform_operation_specific_checks(participant, operation_type)
            
            # Общая оценка готовности
            overall_ready = basic_checks["ready"] and operation_checks["ready"]
            
            readiness_score = self._calculate_readiness_score(basic_checks, operation_checks)
            
            result = {
                "ready": overall_ready,
                "readiness_score": readiness_score,
                "participant_id": participant_id,
                "participant_name": participant.name,
                "operation_type": operation_type,
                "basic_checks": basic_checks,
                "operation_checks": operation_checks,
                "recommendations": self._generate_readiness_recommendations(basic_checks, operation_checks)
            }
            
            self.logger.info(f"Проверка готовности участника {participant.name} к операции {operation_type}: {'готов' if overall_ready else 'не готов'}")
            return result
            
        except Exception as e:
            error_msg = f"Ошибка при проверке готовности участника: {str(e)}"
            self.logger.error(error_msg)
            return {"ready": False, "error": error_msg}
    
    def _perform_basic_readiness_checks(self, participant: Participant) -> Dict[str, Any]:
        """Выполнение базовых проверок готовности."""
        checks = {
            "ready": True,
            "checks": {},
            "issues": []
        }
        
        # Проверка статуса участия
        if participant.status != "active":
            checks["ready"] = False
            checks["issues"].append(f"Участник неактивен (статус: {participant.status})")
        checks["checks"]["status"] = participant.status == "active"
        
        # Проверка согласия
        if not participant.consent_given:
            checks["ready"] = False
            checks["issues"].append("Участник не дал согласие на участие")
        checks["checks"]["consent"] = participant.consent_given
        
        # Проверка квантового состояния
        quantum_state = participant.quantum_state
        
        # Проверка энергии
        if quantum_state.energy_level < 0.5:
            checks["ready"] = False
            checks["issues"].append(f"Недостаточный уровень энергии: {quantum_state.energy_level}")
        checks["checks"]["energy_sufficient"] = quantum_state.energy_level >= 0.5
        
        # Проверка ясности
        if quantum_state.clarity < 0.4:
            checks["ready"] = False
            checks["issues"].append(f"Недостаточная ясность сознания: {quantum_state.clarity}")
        checks["checks"]["clarity_sufficient"] = quantum_state.clarity >= 0.4
        
        # Проверка защиты
        if quantum_state.protection < 0.5:
            checks["ready"] = False
            checks["issues"].append(f"Недостаточная защита: {quantum_state.protection}")
        checks["checks"]["protection_sufficient"] = quantum_state.protection >= 0.5
        
        # Проверка выравнивания
        if quantum_state.alignment < 0.4:
            checks["ready"] = False
            checks["issues"].append(f"Недостаточное выравнивание: {quantum_state.alignment}")
        checks["checks"]["alignment_sufficient"] = quantum_state.alignment >= 0.4
        
        return checks
    
    def _perform_operation_specific_checks(self, participant: Participant, 
                                         operation_type: str) -> Dict[str, Any]:
        """Выполнение специфичных для операции проверок."""
        checks = {
            "ready": True,
            "checks": {},
            "issues": []
        }
        
        quantum_state = participant.quantum_state
        
        if operation_type == "energy_operation":
            # Операции с энергией требуют высокого уровня энергии
            if quantum_state.energy_level < 1.0:
                checks["ready"] = False
                checks["issues"].append("Для энергетических операций требуется уровень энергии >= 1.0")
            checks["checks"]["energy_operation_ready"] = quantum_state.energy_level >= 1.0
            
        elif operation_type == "consciousness_operation":
            # Операции с сознанием требуют высокой ясности
            if quantum_state.clarity < 0.7:
                checks["ready"] = False
                checks["issues"].append("Для операций с сознанием требуется ясность >= 0.7")
            checks["checks"]["consciousness_operation_ready"] = quantum_state.clarity >= 0.7
            
        elif operation_type == "protection_operation":
            # Операции защиты требуют высокого уровня защиты
            if quantum_state.protection < 0.8:
                checks["ready"] = False
                checks["issues"].append("Для операций защиты требуется уровень защиты >= 0.8")
            checks["checks"]["protection_operation_ready"] = quantum_state.protection >= 0.8
            
        elif operation_type == "alignment_operation":
            # Операции выравнивания требуют высокого выравнивания
            if quantum_state.alignment < 0.7:
                checks["ready"] = False
                checks["issues"].append("Для операций выравнивания требуется выравнивание >= 0.7")
            checks["checks"]["alignment_operation_ready"] = quantum_state.alignment >= 0.7
            
        elif operation_type == "critical_operation":
            # Критические операции требуют всех параметров на высоком уровне
            if quantum_state.energy_level < 1.2:
                checks["ready"] = False
                checks["issues"].append("Для критических операций требуется уровень энергии >= 1.2")
            if quantum_state.clarity < 0.8:
                checks["ready"] = False
                checks["issues"].append("Для критических операций требуется ясность >= 0.8")
            if quantum_state.protection < 0.9:
                checks["ready"] = False
                checks["issues"].append("Для критических операций требуется уровень защиты >= 0.9")
            if quantum_state.alignment < 0.8:
                checks["ready"] = False
                checks["issues"].append("Для критических операций требуется выравнивание >= 0.8")
            
            checks["checks"]["critical_operation_ready"] = (
                quantum_state.energy_level >= 1.2 and
                quantum_state.clarity >= 0.8 and
                quantum_state.protection >= 0.9 and
                quantum_state.alignment >= 0.8
            )
        
        return checks
    
    def _calculate_readiness_score(self, basic_checks: Dict[str, Any], 
                                 operation_checks: Dict[str, Any]) -> float:
        """Расчет общего балла готовности."""
        if not basic_checks["ready"]:
            return 0.0
        
        # Подсчет пройденных проверок
        basic_passed = sum(1 for check in basic_checks["checks"].values() if check)
        basic_total = len(basic_checks["checks"])
        
        operation_passed = sum(1 for check in operation_checks["checks"].values() if check)
        operation_total = len(operation_checks["checks"])
        
        # Взвешенный расчет (базовые проверки важнее)
        if operation_total == 0:
            return basic_passed / basic_total
        else:
            return (basic_passed / basic_total * 0.7) + (operation_passed / operation_total * 0.3)
    
    def _generate_readiness_recommendations(self, basic_checks: Dict[str, Any], 
                                         operation_checks: Dict[str, Any]) -> List[str]:
        """Генерация рекомендаций по улучшению готовности."""
        recommendations = []
        
        # Рекомендации по базовым проверкам
        if not basic_checks["checks"].get("energy_sufficient", False):
            recommendations.append("Повысить уровень энергии через медитацию или энергетические практики")
        
        if not basic_checks["checks"].get("clarity_sufficient", False):
            recommendations.append("Улучшить ясность сознания через практики осознанности")
        
        if not basic_checks["checks"].get("protection_sufficient", False):
            recommendations.append("Усилить защитные механизмы через энергетическую защиту")
        
        if not basic_checks["checks"].get("alignment_sufficient", False):
            recommendations.append("Улучшить выравнивание с траекторией через намерение и фокус")
        
        # Рекомендации по операционным проверкам
        for check_name, check_passed in operation_checks["checks"].items():
            if not check_passed:
                if "energy_operation" in check_name:
                    recommendations.append("Для энергетических операций требуется дополнительная подготовка энергии")
                elif "consciousness_operation" in check_name:
                    recommendations.append("Для операций с сознанием требуется углубленная работа с ясностью")
                elif "protection_operation" in check_name:
                    recommendations.append("Для операций защиты требуется усиление защитных механизмов")
                elif "alignment_operation" in check_name:
                    recommendations.append("Для операций выравнивания требуется работа с намерением")
                elif "critical_operation" in check_name:
                    recommendations.append("Для критических операций требуется комплексная подготовка всех параметров")
        
        return recommendations
    
    def check_group_readiness(self, participant_ids: List[str], 
                            operation_type: str = "general") -> Dict[str, Any]:
        """
        Проверка готовности группы участников к операциям.
        
        Args:
            participant_ids: Список ID участников
            operation_type: Тип операции
            
        Returns:
            Dict[str, Any]: Результат проверки готовности группы
        """
        try:
            if not participant_ids:
                return {"group_ready": False, "error": "Список участников пуст"}
            
            individual_results = []
            ready_count = 0
            total_score = 0.0
            
            for participant_id in participant_ids:
                result = self.check_participant_readiness(participant_id, operation_type)
                individual_results.append(result)
                
                if result.get("ready", False):
                    ready_count += 1
                
                total_score += result.get("readiness_score", 0.0)
            
            group_ready = ready_count == len(participant_ids)
            average_score = total_score / len(participant_ids) if participant_ids else 0.0
            
            # Анализ групповой готовности
            group_analysis = self._analyze_group_readiness(individual_results, operation_type)
            
            result = {
                "group_ready": group_ready,
                "total_participants": len(participant_ids),
                "ready_participants": ready_count,
                "not_ready_participants": len(participant_ids) - ready_count,
                "average_readiness_score": round(average_score, 3),
                "operation_type": operation_type,
                "individual_results": individual_results,
                "group_analysis": group_analysis,
                "recommendations": self._generate_group_readiness_recommendations(individual_results, group_analysis)
            }
            
            self.logger.info(f"Проверка готовности группы: {ready_count}/{len(participant_ids)} участников готовы к операции {operation_type}")
            return result
            
        except Exception as e:
            error_msg = f"Ошибка при проверке готовности группы: {str(e)}"
            self.logger.error(error_msg)
            return {"group_ready": False, "error": error_msg}
    
    def _analyze_group_readiness(self, individual_results: List[Dict[str, Any]], 
                                operation_type: str) -> Dict[str, Any]:
        """Анализ готовности группы."""
        if not individual_results:
            return {}
        
        # Анализ по ролям
        role_readiness = {}
        for result in individual_results:
            participant = self.get_participant(result["participant_id"])
            if participant:
                role = participant.role
                if role not in role_readiness:
                    role_readiness[role] = {"ready": 0, "total": 0, "avg_score": 0.0}
                
                role_readiness[role]["total"] += 1
                if result.get("ready", False):
                    role_readiness[role]["ready"] += 1
                role_readiness[role]["avg_score"] += result.get("readiness_score", 0.0)
        
        # Нормализация средних баллов
        for role_data in role_readiness.values():
            if role_data["total"] > 0:
                role_data["avg_score"] = role_data["avg_score"] / role_data["total"]
        
        # Анализ критических участников
        critical_participants = []
        for result in individual_results:
            if not result.get("ready", False):
                participant = self.get_participant(result["participant_id"])
                if participant:
                    critical_participants.append({
                        "participant_id": result["participant_id"],
                        "name": participant.name,
                        "role": participant.role,
                        "issues": result.get("basic_checks", {}).get("issues", []) + 
                                 result.get("operation_checks", {}).get("issues", [])
                    })
        
        return {
            "role_readiness": role_readiness,
            "critical_participants": critical_participants,
            "critical_count": len(critical_participants),
            "success_rate": ready_count / len(individual_results) if individual_results else 0.0
        }
    
    def _generate_group_readiness_recommendations(self, individual_results: List[Dict[str, Any]], 
                                               group_analysis: Dict[str, Any]) -> List[str]:
        """Генерация рекомендаций по улучшению групповой готовности."""
        recommendations = []
        
        # Рекомендации по критическим участникам
        if group_analysis.get("critical_count", 0) > 0:
            recommendations.append(f"Требуется работа с {group_analysis['critical_count']} критическими участниками")
        
        # Рекомендации по ролям
        for role, role_data in group_analysis.get("role_readiness", {}).items():
            if role_data["ready"] < role_data["total"]:
                recommendations.append(f"Роль '{role}': {role_data['ready']}/{role_data['total']} готовы - требуется синхронизация")
        
        # Общие рекомендации
        ready_count = sum(1 for r in individual_results if r.get("ready", False))
        total_count = len(individual_results)
        
        if ready_count < total_count * 0.8:
            recommendations.append("Менее 80% участников готовы - рекомендуется групповая подготовка")
        
        if ready_count < total_count * 0.5:
            recommendations.append("Менее 50% участников готовы - требуется отложить операцию")
        
        return recommendations
    
    def validate_participant_consents(self, participant_ids: List[str]) -> Dict[str, Any]:
        """
        Валидация согласий участников на участие.
        
        Args:
            participant_ids: Список ID участников
            
        Returns:
            Dict[str, Any]: Результат валидации согласий
        """
        try:
            if not participant_ids:
                return {"all_consented": False, "error": "Список участников пуст"}
            
            consent_results = []
            all_consented = True
            
            for participant_id in participant_ids:
                participant = self.get_participant(participant_id)
                if not participant:
                    consent_results.append({
                        "participant_id": participant_id,
                        "consented": False,
                        "error": "Участник не найден"
                    })
                    all_consented = False
                    continue
                
                consent_results.append({
                    "participant_id": participant_id,
                    "name": participant.name,
                    "role": participant.role,
                    "consented": participant.consent_given,
                    "consent_timestamp": participant.created_at.isoformat() if participant.consent_given else None
                })
                
                if not participant.consent_given:
                    all_consented = False
            
            return {
                "all_consented": all_consented,
                "total_participants": len(participant_ids),
                "consented_count": sum(1 for r in consent_results if r.get("consented", False)),
                "not_consented_count": len(participant_ids) - sum(1 for r in consent_results if r.get("consented", False)),
                "consent_results": consent_results
            }
            
        except Exception as e:
            error_msg = f"Ошибка при валидации согласий: {str(e)}"
            self.logger.error(error_msg)
            return {"all_consented": False, "error": error_msg}
    
    def generate_readiness_report(self, participant_ids: List[str], 
                                operation_type: str = "general") -> Dict[str, Any]:
        """
        Генерация комплексного отчета о готовности.
        
        Args:
            participant_ids: Список ID участников
            operation_type: Тип операции
            
        Returns:
            Dict[str, Any]: Комплексный отчет о готовности
        """
        try:
            # Проверка готовности группы
            group_readiness = self.check_group_readiness(participant_ids, operation_type)
            
            # Валидация согласий
            consent_validation = self.validate_participant_consents(participant_ids)
            
            # Анализ квантовых состояний
            quantum_analysis = self.analyze_quantum_states()
            
            # Статус синхронизации
            sync_status = self.get_group_synchronization_status(participant_ids)
            
            # Формирование отчета
            report = {
                "timestamp": datetime.now().isoformat(),
                "operation_type": operation_type,
                "participants_count": len(participant_ids),
                "overall_readiness": group_readiness["group_ready"],
                "readiness_score": group_readiness["average_readiness_score"],
                "consent_status": consent_validation["all_consented"],
                "synchronization_status": sync_status["synchronized"],
                "synchronization_score": sync_status["overall_sync_score"],
                "group_readiness": group_readiness,
                "consent_validation": consent_validation,
                "quantum_analysis": quantum_analysis,
                "synchronization_status": sync_status,
                "recommendations": self._generate_comprehensive_recommendations(
                    group_readiness, consent_validation, sync_status
                )
            }
            
            self.logger.info(f"Сгенерирован отчет о готовности для операции {operation_type}")
            return report
            
        except Exception as e:
            error_msg = f"Ошибка при генерации отчета о готовности: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def _generate_comprehensive_recommendations(self, group_readiness: Dict[str, Any],
                                             consent_validation: Dict[str, Any],
                                             sync_status: Dict[str, Any]) -> List[str]:
        """Генерация комплексных рекомендаций."""
        recommendations = []
        
        # Рекомендации по готовности
        if not group_readiness["group_ready"]:
            recommendations.append("Группа не готова к операции - требуется подготовка участников")
        
        if group_readiness["average_readiness_score"] < 0.7:
            recommendations.append("Низкий средний балл готовности - рекомендуется дополнительная подготовка")
        
        # Рекомендации по согласиям
        if not consent_validation["all_consented"]:
            recommendations.append("Не все участники дали согласие - требуется получение согласий")
        
        # Рекомендации по синхронизации
        if not sync_status["synchronized"]:
            recommendations.append("Группа не синхронизирована - рекомендуется групповая синхронизация")
        
        if sync_status["overall_sync_score"] < 0.6:
            recommendations.append("Низкий уровень синхронизации - требуется групповая работа")
        
        return recommendations
    
    def __str__(self) -> str:
        return f"ParticipantManager(participants={self.total_participants}, active={self.active_participants})"
    
    def __repr__(self) -> str:
        return f"ParticipantManager(quantum_field={'set' if self.quantum_field else 'not_set'}, total_participants={self.total_participants})"
