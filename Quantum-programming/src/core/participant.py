"""
Базовый класс для участников протокола SIRIUS-FELINE_BRANCH_PROTOCOL.
Управляет квантовым состоянием и статусом участника.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class QuantumState:
    """Квантовое состояние участника в поле реальности."""
    
    energy_level: float = 1.0  # Уровень энергии (0.0 - 2.0)
    clarity: float = 0.5       # Ясность сознания (0.0 - 1.0)
    protection: float = 0.8    # Уровень защиты (0.0 - 1.0)
    alignment: float = 0.6     # Выравнивание с траекторией (0.0 - 1.0)
    
    def __post_init__(self):
        """Валидация значений после инициализации."""
        for field_name, value in self.__dict__.items():
            if not 0.0 <= value <= 2.0:
                raise ValueError(f"{field_name} должен быть в диапазоне [0.0, 2.0], получено: {value}")


@dataclass
class Participant:
    """Участник протокола ветки реальности."""
    
    name: str
    role: str
    status: str = "inactive"  # inactive, active, paused, exited
    quantum_state: QuantumState = field(default_factory=QuantumState)
    consent_given: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    participant_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Дополнительные атрибуты
    metadata: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Валидация после инициализации."""
        if not self.name.strip():
            raise ValueError("Имя участника не может быть пустым")
        if not self.role.strip():
            raise ValueError("Роль участника не может быть пустой")
    
    def update_quantum_state(self, **kwargs) -> None:
        """Обновление квантового состояния участника."""
        for key, value in kwargs.items():
            if hasattr(self.quantum_state, key):
                setattr(self.quantum_state, key, value)
            else:
                raise ValueError(f"Неизвестный атрибут квантового состояния: {key}")
        
        self.updated_at = datetime.now()
        self._log_event("quantum_state_updated", kwargs)
    
    def give_consent(self) -> None:
        """Дать согласие на участие в протоколе."""
        self.consent_given = True
        self.updated_at = datetime.now()
        self._log_event("consent_given", {"timestamp": self.updated_at})
    
    def revoke_consent(self) -> None:
        """Отозвать согласие на участие в протоколе."""
        self.consent_given = False
        self.updated_at = datetime.now()
        self._log_event("consent_revoked", {"timestamp": self.updated_at})
    
    def pause_participation(self) -> None:
        """Приостановить участие в протоколе."""
        self.status = "paused"
        self.updated_at = datetime.now()
        self._log_event("participation_paused", {"timestamp": self.updated_at})
    
    def resume_participation(self) -> None:
        """Возобновить участие в протоколе."""
        if self.consent_given:
            self.status = "active"
            self.updated_at = datetime.now()
            self._log_event("participation_resumed", {"timestamp": self.updated_at})
        else:
            raise ValueError("Нельзя возобновить участие без согласия")
    
    def exit_protocol(self) -> None:
        """Выйти из протокола."""
        self.status = "exited"
        self.updated_at = datetime.now()
        self._log_event("protocol_exited", {"timestamp": self.updated_at})
    
    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Логирование события участника."""
        event = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "data": data,
            "participant_id": self.participant_id
        }
        self.events.append(event)
    
    def get_health_metrics(self) -> Dict[str, float]:
        """Получение метрик здоровья участника."""
        return {
            "energy_level": self.quantum_state.energy_level,
            "clarity": self.quantum_state.clarity,
            "protection": self.quantum_state.protection,
            "alignment": self.quantum_state.alignment,
            "consent_status": 1.0 if self.consent_given else 0.0
        }
    
    def __str__(self) -> str:
        return f"Participant({self.name}, {self.role}, {self.status})"
    
    def __repr__(self) -> str:
        return f"Participant(name='{self.name}', role='{self.role}', status='{self.status}', id='{self.participant_id}')"
