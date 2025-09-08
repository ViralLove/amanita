"""
Класс для управления состоянием протокола SIRIUS-FELINE_BRANCH_PROTOCOL.
Отслеживает текущий этап выполнения, статус активации и историю изменений.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class ProtocolStage(Enum):
    """Этапы выполнения протокола."""
    
    INITIALIZATION = "initialization"      # Инициализация
    VALIDATION = "validation"             # Валидация
    PARTICIPANT_SETUP = "participant_setup"  # Настройка участников
    QUANTUM_FIELD_CREATION = "quantum_field_creation"  # Создание квантового поля
    ACTIVATION = "activation"             # Активация
    OPERATIONS_RUNNING = "operations_running"  # Выполнение операций
    MONITORING = "monitoring"             # Мониторинг
    ADAPTATION = "adaptation"             # Адаптация
    COMPLETION = "completion"             # Завершение
    ERROR = "error"                       # Ошибка
    PAUSED = "paused"                    # Приостановлен


class ActivationStatus(Enum):
    """Статусы активации протокола."""
    
    NOT_ACTIVATED = "not_activated"      # Не активирован
    ACTIVATION_IN_PROGRESS = "activation_in_progress"  # Активация в процессе
    ACTIVATED = "activated"               # Активирован
    ACTIVATION_FAILED = "activation_failed"  # Ошибка активации
    DEACTIVATED = "deactivated"          # Деактивирован


@dataclass
class ChangeRecord:
    """Запись об изменении состояния протокола."""
    
    timestamp: datetime = field(default_factory=datetime.now)
    change_type: str = ""                 # Тип изменения
    field_name: str = ""                  # Имя измененного поля
    old_value: Any = None                 # Старое значение
    new_value: Any = None                 # Новое значение
    description: str = ""                 # Описание изменения
    user_id: Optional[str] = None         # ID пользователя, внесшего изменение
    metadata: Dict[str, Any] = field(default_factory=dict)  # Дополнительные данные
    
    def __post_init__(self):
        """Валидация после инициализации."""
        if not self.change_type:
            raise ValueError("Тип изменения не может быть пустым")
        if not self.field_name:
            raise ValueError("Имя поля не может быть пустым")
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование записи в словарь."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "change_type": self.change_type,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "description": self.description,
            "user_id": self.user_id,
            "metadata": self.metadata
        }


@dataclass
class ProtocolState:
    """Состояние протокола ветки реальности."""
    
    # Основные атрибуты состояния
    current_stage: ProtocolStage = ProtocolStage.INITIALIZATION
    activation_status: ActivationStatus = ActivationStatus.NOT_ACTIVATED
    
    # Идентификация и метаданные
    protocol_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    protocol_name: str = "SIRUS-FELINE_BRANCH_PROTOCOL"
    protocol_version: str = "1.0"
    
    # Временные метки
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None
    last_stage_change: Optional[datetime] = None
    
    # История изменений
    change_history: List[ChangeRecord] = field(default_factory=list)
    
    # Дополнительные атрибуты состояния
    is_paused: bool = False
    pause_reason: Optional[str] = None
    error_count: int = 0
    warning_count: int = 0
    success_count: int = 0
    
    # Метаданные
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Валидация после инициализации."""
        if not self.protocol_name:
            raise ValueError("Название протокола не может быть пустым")
        if not self.protocol_version:
            raise ValueError("Версия протокола не может быть пустой")
    
    def update_stage(self, new_stage: ProtocolStage, description: str = "", 
                    user_id: Optional[str] = None, metadata: Dict[str, Any] = None) -> None:
        """
        Обновление текущего этапа протокола.
        
        Args:
            new_stage: Новый этап
            description: Описание изменения
            user_id: ID пользователя
            metadata: Дополнительные данные
        """
        if new_stage == self.current_stage:
            return  # Нет изменений
        
        old_stage = self.current_stage
        self.current_stage = new_stage
        self.last_stage_change = datetime.now()
        self.last_updated = datetime.now()
        
        # Создание записи об изменении
        change_record = ChangeRecord(
            change_type="stage_change",
            field_name="current_stage",
            old_value=old_stage.value,
            new_value=new_stage.value,
            description=description or f"Изменение этапа с {old_stage.value} на {new_stage.value}",
            user_id=user_id,
            metadata=metadata or {}
        )
        
        self.change_history.append(change_record)
        
        # Обновление метаданных
        if metadata:
            self.metadata.update(metadata)
    
    def update_activation_status(self, new_status: ActivationStatus, description: str = "", 
                               user_id: Optional[str] = None, metadata: Dict[str, Any] = None) -> None:
        """
        Обновление статуса активации протокола.
        
        Args:
            new_status: Новый статус активации
            description: Описание изменения
            user_id: ID пользователя
            metadata: Дополнительные данные
        """
        if new_status == self.activation_status:
            return  # Нет изменений
        
        old_status = self.activation_status
        self.activation_status = new_status
        self.last_updated = datetime.now()
        
        # Обновление временных меток
        if new_status == ActivationStatus.ACTIVATED:
            self.activated_at = datetime.now()
        elif new_status == ActivationStatus.DEACTIVATED:
            self.activated_at = None
        
        # Создание записи об изменении
        change_record = ChangeRecord(
            change_type="activation_status_change",
            field_name="activation_status",
            old_value=old_status.value,
            new_value=new_status.value,
            description=description or f"Изменение статуса активации с {old_status.value} на {new_status.value}",
            user_id=user_id,
            metadata=metadata or {}
        )
        
        self.change_history.append(change_record)
        
        # Обновление метаданных
        if metadata:
            self.metadata.update(metadata)
    
    def add_change_record(self, change_type: str, field_name: str, old_value: Any, 
                         new_value: Any, description: str = "", user_id: Optional[str] = None, 
                         metadata: Dict[str, Any] = None) -> None:
        """
        Добавление записи об изменении.
        
        Args:
            change_type: Тип изменения
            field_name: Имя измененного поля
            old_value: Старое значение
            new_value: Новое значение
            description: Описание изменения
            user_id: ID пользователя
            metadata: Дополнительные данные
        """
        change_record = ChangeRecord(
            change_type=change_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=description,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        self.change_history.append(change_record)
        self.last_updated = datetime.now()
    
    def pause_protocol(self, reason: str, user_id: Optional[str] = None) -> None:
        """Приостановка протокола."""
        if self.is_paused:
            return  # Уже приостановлен
        
        self.is_paused = True
        self.pause_reason = reason
        self.last_updated = datetime.now()
        
        self.add_change_record(
            change_type="protocol_paused",
            field_name="is_paused",
            old_value=False,
            new_value=True,
            description=f"Протокол приостановлен. Причина: {reason}",
            user_id=user_id
        )
    
    def resume_protocol(self, user_id: Optional[str] = None) -> None:
        """Возобновление протокола."""
        if not self.is_paused:
            return  # Не приостановлен
        
        old_reason = self.pause_reason
        self.is_paused = False
        self.pause_reason = None
        self.last_updated = datetime.now()
        
        self.add_change_record(
            change_type="protocol_resumed",
            field_name="is_paused",
            old_value=True,
            new_value=False,
            description=f"Протокол возобновлен. Была приостановлен по причине: {old_reason}",
            user_id=user_id
        )
    
    def increment_error_count(self, error_description: str = "", user_id: Optional[str] = None) -> None:
        """Увеличение счетчика ошибок."""
        old_count = self.error_count
        self.error_count += 1
        self.last_updated = datetime.now()
        
        self.add_change_record(
            change_type="error_count_increment",
            field_name="error_count",
            old_value=old_count,
            new_value=self.error_count,
            description=f"Ошибка #{self.error_count}: {error_description}",
            user_id=user_id
        )
    
    def increment_warning_count(self, warning_description: str = "", user_id: Optional[str] = None) -> None:
        """Увеличение счетчика предупреждений."""
        old_count = self.warning_count
        self.warning_count += 1
        self.last_updated = datetime.now()
        
        self.add_change_record(
            change_type="warning_count_increment",
            field_name="warning_count",
            old_value=old_count,
            new_value=self.warning_count,
            description=f"Предупреждение #{self.warning_count}: {warning_description}",
            user_id=user_id
        )
    
    def increment_success_count(self, success_description: str = "", user_id: Optional[str] = None) -> None:
        """Увеличение счетчика успешных операций."""
        old_count = self.success_count
        self.success_count += 1
        self.last_updated = datetime.now()
        
        self.add_change_record(
            change_type="success_count_increment",
            field_name="success_count",
            old_value=old_count,
            new_value=self.success_count,
            description=f"Успешная операция #{self.success_count}: {success_description}",
            user_id=user_id
        )
    
    def get_current_status_summary(self) -> Dict[str, Any]:
        """Получение сводки текущего состояния протокола."""
        return {
            "protocol_id": self.protocol_id,
            "protocol_name": self.protocol_name,
            "protocol_version": self.protocol_version,
            "current_stage": self.current_stage.value,
            "activation_status": self.activation_status.value,
            "is_paused": self.is_paused,
            "pause_reason": self.pause_reason,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "success_count": self.success_count,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "last_stage_change": self.last_stage_change.isoformat() if self.last_stage_change else None,
            "total_changes": len(self.change_history)
        }
    
    def get_change_history_summary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение сводки истории изменений."""
        recent_changes = self.change_history[-limit:] if limit > 0 else self.change_history
        return [change.to_dict() for change in recent_changes]
    
    def can_proceed_to_stage(self, target_stage: ProtocolStage) -> bool:
        """Проверка возможности перехода к целевому этапу."""
        if self.is_paused:
            return False
        
        if self.activation_status == ActivationStatus.ACTIVATION_FAILED:
            return False
        
        # Логика проверки переходов между этапами
        stage_transitions = {
            ProtocolStage.INITIALIZATION: [ProtocolStage.VALIDATION],
            ProtocolStage.VALIDATION: [ProtocolStage.PARTICIPANT_SETUP, ProtocolStage.ERROR],
            ProtocolStage.PARTICIPANT_SETUP: [ProtocolStage.QUANTUM_FIELD_CREATION, ProtocolStage.ERROR],
            ProtocolStage.QUANTUM_FIELD_CREATION: [ProtocolStage.ACTIVATION, ProtocolStage.ERROR],
            ProtocolStage.ACTIVATION: [ProtocolStage.OPERATIONS_RUNNING, ProtocolStage.ACTIVATION_FAILED],
            ProtocolStage.OPERATIONS_RUNNING: [ProtocolStage.MONITORING, ProtocolStage.ERROR],
            ProtocolStage.MONITORING: [ProtocolStage.ADAPTATION, ProtocolStage.COMPLETION],
            ProtocolStage.ADAPTATION: [ProtocolStage.OPERATIONS_RUNNING, ProtocolStage.MONITORING],
            ProtocolStage.ERROR: [ProtocolStage.INITIALIZATION],  # Возврат к началу
            ProtocolStage.PAUSED: [ProtocolStage.INITIALIZATION]  # Возврат к началу
        }
        
        allowed_transitions = stage_transitions.get(self.current_stage, [])
        return target_stage in allowed_transitions
    
    def get_protocol_health_score(self) -> float:
        """Получение оценки здоровья протокола (0.0 - 1.0)."""
        if self.error_count == 0 and self.warning_count == 0:
            return 1.0
        
        total_issues = self.error_count + self.warning_count
        total_operations = self.success_count + total_issues
        
        if total_operations == 0:
            return 1.0
        
        # Веса для разных типов проблем
        error_weight = 0.7
        warning_weight = 0.3
        
        weighted_issues = (self.error_count * error_weight) + (self.warning_count * warning_weight)
        health_score = max(0.0, 1.0 - (weighted_issues / total_operations))
        
        return round(health_score, 2)
    
    def __str__(self) -> str:
        return f"ProtocolState(stage={self.current_stage.value}, activation={self.activation_status.value}, paused={self.is_paused})"
    
    def __repr__(self) -> str:
        return f"ProtocolState(protocol_id='{self.protocol_id}', current_stage={self.current_stage.value}, activation_status={self.activation_status.value})"
