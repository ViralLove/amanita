"""
Квантовое поле для протокола SIRUS-FELINE_BRANCH_PROTOCOL.
Управляет квантовым пространством, состояниями участников и их связями.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import logging

from ..core.participant import Participant, QuantumState


@dataclass
class QuantumFieldParameters:
    """Параметры квантового поля."""
    
    # Размерность поля
    dimensions: int = 4  # 4D пространство: x, y, z, время
    
    # Размеры поля по каждой оси
    field_size: Tuple[int, int, int, int] = (100, 100, 100, 1000)
    
    # Разрешение поля (минимальный размер кванта)
    resolution: float = 0.1
    
    # Энергетические параметры
    base_energy_level: float = 1.0
    energy_fluctuation: float = 0.1
    
    # Параметры связности
    connection_strength: float = 0.8
    max_connections: int = 10
    
    # Параметры стабильности
    stability_threshold: float = 0.7
    decay_rate: float = 0.01
    
    def __post_init__(self):
        """Валидация параметров поля."""
        if self.dimensions <= 0:
            raise ValueError("Размерность поля должна быть положительной")
        if self.resolution <= 0:
            raise ValueError("Разрешение поля должно быть положительным")
        if not 0 <= self.connection_strength <= 1:
            raise ValueError("Сила связи должна быть в диапазоне [0, 1]")
        if self.stability_threshold <= 0 or self.stability_threshold >= 1:
            raise ValueError("Порог стабильности должен быть в диапазоне (0, 1)")


@dataclass
class QuantumConnection:
    """Квантовая связь между участниками."""
    
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_participant_id: str = ""
    target_participant_id: str = ""
    strength: float = 0.0  # Сила связи (0.0 - 1.0)
    connection_type: str = "standard"  # Тип связи
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    # Энергетические характеристики связи
    energy_flow: float = 0.0
    stability: float = 1.0
    
    # Метаданные связи
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Валидация параметров связи."""
        if not 0 <= self.strength <= 1:
            raise ValueError("Сила связи должна быть в диапазоне [0, 1]")
        if not 0 <= self.stability <= 1:
            raise ValueError("Стабильность должна быть в диапазоне [0, 1]")
    
    def update_strength(self, new_strength: float) -> None:
        """Обновление силы связи."""
        if not 0 <= new_strength <= 1:
            raise ValueError("Сила связи должна быть в диапазоне [0, 1]")
        
        self.strength = new_strength
        self.last_updated = datetime.now()
    
    def update_stability(self, new_stability: float) -> None:
        """Обновление стабильности связи."""
        if not 0 <= new_stability <= 1:
            raise ValueError("Стабильность должна быть в диапазоне [0, 1]")
        
        self.stability = new_stability
        self.last_updated = datetime.now()
    
    def is_stable(self, threshold: float = 0.5) -> bool:
        """Проверка стабильности связи."""
        return self.stability >= threshold
    
    def get_connection_health(self) -> float:
        """Получение оценки здоровья связи (0.0 - 1.0)."""
        return (self.strength + self.stability) / 2.0


class QuantumField:
    """Квантовое поле для управления состояниями участников."""
    
    def __init__(self, parameters: Optional[QuantumFieldParameters] = None, 
                 log_level: int = logging.INFO):
        """Инициализация квантового поля."""
        self.logger = self._setup_logger(log_level)
        self.parameters = parameters or QuantumFieldParameters()
        
        # Идентификация поля
        self.field_id: str = str(uuid.uuid4())
        self.created_at: datetime = datetime.now()
        self.last_updated: datetime = datetime.now()
        
        # Состояние поля
        self.is_initialized: bool = False
        self.is_active: bool = False
        self.field_stability: float = 1.0
        
        # Структуры данных
        self.participants: Dict[str, Participant] = {}
        self.quantum_states: Dict[str, np.ndarray] = {}
        self.connections: Dict[str, QuantumConnection] = {}
        self.energy_matrix: Optional[np.ndarray] = None
        
        # Статистика поля
        self.total_energy: float = 0.0
        self.energy_variance: float = 0.0
        self.connection_count: int = 0
        
        self.logger.info(f"Квантовое поле создано с ID: {self.field_id}")
    
    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Настройка логгера для квантового поля."""
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
    
    def initialize_field(self) -> bool:
        """
        Инициализация квантового поля.
        
        Returns:
            bool: True если инициализация прошла успешно
        """
        try:
            self.logger.info("Начинаю инициализацию квантового поля")
            
            # Создание энергетической матрицы
            self._create_energy_matrix()
            
            # Инициализация базовых параметров
            self.field_stability = 1.0
            self.total_energy = self.parameters.base_energy_level
            self.energy_variance = 0.0
            
            # Установка флагов
            self.is_initialized = True
            self.is_active = True
            self.last_updated = datetime.now()
            
            self.logger.info("Квантовое поле успешно инициализировано")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации поля: {str(e)}")
            self.is_initialized = False
            return False
    
    def _create_energy_matrix(self) -> None:
        """Создание энергетической матрицы поля."""
        dims = self.parameters.field_size[:self.parameters.dimensions]
        
        # Создание базовой энергетической матрицы
        self.energy_matrix = np.full(dims, self.parameters.base_energy_level, dtype=np.float64)
        
        # Добавление случайных флуктуаций
        noise = np.random.normal(0, self.parameters.energy_fluctuation, dims)
        self.energy_matrix += noise
        
        # Нормализация значений
        self.energy_matrix = np.clip(self.energy_matrix, 0, 2 * self.parameters.base_energy_level)
        
        self.logger.debug(f"Создана энергетическая матрица размером {dims}")
    
    def create_connection(self, source_id: str, target_id: str, 
                         strength: Optional[float] = None, 
                         connection_type: str = "standard",
                         metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Создание квантовой связи между участниками.
        
        Args:
            source_id: ID исходного участника
            target_id: ID целевого участника
            strength: Сила связи (если None, используется базовая сила поля)
            connection_type: Тип связи
            metadata: Дополнительные данные связи
            
        Returns:
            Optional[str]: ID созданной связи или None при ошибке
        """
        try:
            # Проверка существования участников
            if source_id not in self.participants:
                self.logger.error(f"Исходный участник {source_id} не найден")
                return None
            
            if target_id not in self.participants:
                self.logger.error(f"Целевой участник {target_id} не найден")
                return None
            
            # Проверка на самосвязь
            if source_id == target_id:
                self.logger.error("Нельзя создать связь участника с самим собой")
                return None
            
            # Проверка существующей связи
            existing_connection = self._find_existing_connection(source_id, target_id)
            if existing_connection:
                self.logger.warning(f"Связь между {source_id} и {target_id} уже существует")
                return existing_connection.connection_id
            
            # Проверка лимита связей
            if self._get_participant_connection_count(source_id) >= self.parameters.max_connections:
                self.logger.error(f"Участник {source_id} достиг лимита связей")
                return None
            
            if self._get_participant_connection_count(target_id) >= self.parameters.max_connections:
                self.logger.error(f"Участник {target_id} достиг лимита связей")
                return None
            
            # Создание связи
            connection_strength = strength or self.parameters.connection_strength
            connection = QuantumConnection(
                source_participant_id=source_id,
                target_participant_id=target_id,
                strength=connection_strength,
                connection_type=connection_type,
                metadata=metadata or {}
            )
            
            # Сохранение связи
            self.connections[connection.connection_id] = connection
            
            # Обновление статистики
            self._update_field_statistics()
            
            self.logger.info(f"Создана связь {connection.connection_id} между {source_id} и {target_id}")
            return connection.connection_id
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании связи: {str(e)}")
            return None
    
    def _find_existing_connection(self, source_id: str, target_id: str) -> Optional[QuantumConnection]:
        """Поиск существующей связи между участниками."""
        for connection in self.connections.values():
            if ((connection.source_participant_id == source_id and 
                 connection.target_participant_id == target_id) or
                (connection.source_participant_id == target_id and 
                 connection.target_participant_id == source_id)):
                return connection
        return None
    
    def _get_participant_connection_count(self, participant_id: str) -> int:
        """Получение количества связей участника."""
        count = 0
        for connection in self.connections.values():
            if (connection.source_participant_id == participant_id or 
                connection.target_participant_id == participant_id):
                count += 1
        return count
    
    def update_connection_strength(self, connection_id: str, new_strength: float) -> bool:
        """
        Обновление силы связи.
        
        Args:
            connection_id: ID связи
            new_strength: Новая сила связи
            
        Returns:
            bool: True если сила успешно обновлена
        """
        try:
            if connection_id not in self.connections:
                self.logger.error(f"Связь {connection_id} не найдена")
                return False
            
            connection = self.connections[connection_id]
            connection.update_strength(new_strength)
            
            # Обновление статистики
            self._update_field_statistics()
            
            self.logger.debug(f"Сила связи {connection_id} обновлена до {new_strength}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении силы связи: {str(e)}")
            return False
    
    def update_connection_stability(self, connection_id: str, new_stability: float) -> bool:
        """
        Обновление стабильности связи.
        
        Args:
            connection_id: ID связи
            new_stability: Новая стабильность связи
            
        Returns:
            bool: True если стабильность успешно обновлена
        """
        try:
            if connection_id not in self.connections:
                self.logger.error(f"Связь {connection_id} не найдена")
                return False
            
            connection = self.connections[connection_id]
            connection.update_stability(new_stability)
            
            # Обновление статистики
            self._update_field_statistics()
            
            self.logger.debug(f"Стабильность связи {connection_id} обновлена до {new_stability}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении стабильности связи: {str(e)}")
            return False
    
    def remove_connection(self, connection_id: str) -> bool:
        """
        Удаление квантовой связи.
        
        Args:
            connection_id: ID связи для удаления
            
        Returns:
            bool: True если связь успешно удалена
        """
        try:
            if connection_id not in self.connections:
                self.logger.warning(f"Связь {connection_id} не найдена")
                return False
            
            connection = self.connections[connection_id]
            source_id = connection.source_participant_id
            target_id = connection.target_participant_id
            
            # Удаление связи
            del self.connections[connection_id]
            
            # Обновление статистики
            self._update_field_statistics()
            
            self.logger.info(f"Связь {connection_id} между {source_id} и {target_id} удалена")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при удалении связи: {str(e)}")
            return False
    
    def get_participant_connections(self, participant_id: str) -> List[QuantumConnection]:
        """
        Получение всех связей участника.
        
        Args:
            participant_id: ID участника
            
        Returns:
            List[QuantumConnection]: Список связей участника
        """
        connections = []
        for connection in self.connections.values():
            if (connection.source_participant_id == participant_id or 
                connection.target_participant_id == participant_id):
                connections.append(connection)
        return connections
    
    def get_connection_analysis(self) -> Dict[str, Any]:
        """
        Анализ связности поля.
        
        Returns:
            Dict[str, Any]: Анализ связности
        """
        if not self.connections:
            return {
                "total_connections": 0,
                "average_strength": 0.0,
                "average_stability": 0.0,
                "strongest_connection": None,
                "weakest_connection": None,
                "most_stable_connection": None,
                "least_stable_connection": None
            }
        
        strengths = [conn.strength for conn in self.connections.values()]
        stabilities = [conn.stability for conn in self.connections.values()]
        
        # Поиск экстремальных значений
        strongest_conn = max(self.connections.values(), key=lambda x: x.strength)
        weakest_conn = min(self.connections.values(), key=lambda x: x.strength)
        most_stable_conn = max(self.connections.values(), key=lambda x: x.stability)
        least_stable_conn = min(self.connections.values(), key=lambda x: x.stability)
        
        return {
            "total_connections": len(self.connections),
            "average_strength": np.mean(strengths),
            "average_stability": np.mean(stabilities),
            "strength_variance": np.var(strengths),
            "stability_variance": np.var(stabilities),
            "strongest_connection": {
                "id": strongest_conn.connection_id,
                "strength": strongest_conn.strength,
                "participants": [strongest_conn.source_participant_id, strongest_conn.target_participant_id]
            },
            "weakest_connection": {
                "id": weakest_conn.connection_id,
                "strength": weakest_conn.strength,
                "participants": [weakest_conn.source_participant_id, weakest_conn.target_participant_id]
            },
            "most_stable_connection": {
                "id": most_stable_conn.connection_id,
                "stability": most_stable_conn.stability,
                "participants": [most_stable_conn.source_participant_id, most_stable_conn.target_participant_id]
            },
            "least_stable_connection": {
                "id": least_stable_conn.connection_id,
                "stability": least_stable_conn.stability,
                "participants": [least_stable_conn.source_participant_id, least_stable_conn.target_participant_id]
            }
        }
    
    def add_participant(self, participant: Participant) -> bool:
        """
        Добавление участника в квантовое поле.
        
        Args:
            participant: Участник для добавления
            
        Returns:
            bool: True если участник успешно добавлен
        """
        try:
            if not self.is_initialized:
                self.logger.error("Нельзя добавить участника в неинициализированное поле")
                return False
            
            if not self.is_active:
                self.logger.error("Нельзя добавить участника в неактивное поле")
                return False
            
            participant_id = participant.participant_id
            
            # Проверка, что участник еще не добавлен
            if participant_id in self.participants:
                self.logger.warning(f"Участник {participant.name} уже существует в поле")
                return False
            
            # Добавление участника
            self.participants[participant_id] = participant
            
            # Создание квантового состояния для участника
            self._create_participant_quantum_state(participant_id)
            
            # Обновление статистики поля
            self._update_field_statistics()
            
            self.logger.info(f"Участник {participant.name} успешно добавлен в поле")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении участника: {str(e)}")
            return False
    
    def _create_participant_quantum_state(self, participant_id: str) -> None:
        """Создание квантового состояния для участника."""
        participant = self.participants[participant_id]
        quantum_state = participant.quantum_state
        
        # Создание базового квантового состояния
        state_vector = np.array([
            quantum_state.energy_level,
            quantum_state.clarity,
            quantum_state.protection,
            quantum_state.alignment
        ], dtype=np.float64)
        
        # Нормализация состояния
        norm = np.linalg.norm(state_vector)
        if norm > 0:
            state_vector = state_vector / norm
        
        # Сохранение состояния
        self.quantum_states[participant_id] = state_vector
        
        self.logger.debug(f"Создано квантовое состояние для участника {participant_id}")
    
    def remove_participant(self, participant_id: str) -> bool:
        """
        Удаление участника из квантового поля.
        
        Args:
            participant_id: ID участника для удаления
            
        Returns:
            bool: True если участник успешно удален
        """
        try:
            if participant_id not in self.participants:
                self.logger.warning(f"Участник {participant_id} не найден в поле")
                return False
            
            participant_name = self.participants[participant_id].name
            
            # Удаление участника
            del self.participants[participant_id]
            
            # Удаление квантового состояния
            if participant_id in self.quantum_states:
                del self.quantum_states[participant_id]
            
            # Удаление связей с этим участником
            self._remove_participant_connections(participant_id)
            
            # Обновление статистики поля
            self._update_field_statistics()
            
            self.logger.info(f"Участник {participant_name} успешно удален из поля")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при удалении участника: {str(e)}")
            return False
    
    def _remove_participant_connections(self, participant_id: str) -> None:
        """Удаление всех связей с участником."""
        connections_to_remove = []
        
        for conn_id, connection in self.connections.items():
            if (connection.source_participant_id == participant_id or 
                connection.target_participant_id == participant_id):
                connections_to_remove.append(conn_id)
        
        for conn_id in connections_to_remove:
            del self.connections[conn_id]
        
        if connections_to_remove:
            self.logger.debug(f"Удалено {len(connections_to_remove)} связей для участника {participant_id}")
    
    def get_participant_quantum_state(self, participant_id: str) -> Optional[np.ndarray]:
        """
        Получение квантового состояния участника.
        
        Args:
            participant_id: ID участника
            
        Returns:
            Optional[np.ndarray]: Квантовое состояние или None если не найдено
        """
        return self.quantum_states.get(participant_id)
    
    def update_participant_quantum_state(self, participant_id: str, 
                                       new_state: np.ndarray) -> bool:
        """
        Обновление квантового состояния участника.
        
        Args:
            participant_id: ID участника
            new_state: Новое квантовое состояние
            
        Returns:
            bool: True если состояние успешно обновлено
        """
        try:
            if participant_id not in self.participants:
                self.logger.error(f"Участник {participant_id} не найден в поле")
                return False
            
            if not isinstance(new_state, np.ndarray):
                self.logger.error("Новое состояние должно быть numpy массивом")
                return False
            
            # Нормализация нового состояния
            norm = np.linalg.norm(new_state)
            if norm > 0:
                new_state = new_state / norm
            
            # Обновление состояния
            self.quantum_states[participant_id] = new_state.copy()
            
            # Обновление состояния участника
            participant = self.participants[participant_id]
            participant.update_quantum_state(
                energy_level=float(new_state[0]),
                clarity=float(new_state[1]),
                protection=float(new_state[2]),
                alignment=float(new_state[3])
            )
            
            self.logger.debug(f"Квантовое состояние участника {participant_id} обновлено")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении состояния участника: {str(e)}")
            return False
    
    def get_all_participant_states(self) -> Dict[str, np.ndarray]:
        """Получение всех квантовых состояний участников."""
        return self.quantum_states.copy()
    
    def get_participant_count(self) -> int:
        """Получение количества участников в поле."""
        return len(self.participants)
    
    def get_field_dimensions(self) -> Tuple[int, ...]:
        """Получение размеров поля."""
        if self.energy_matrix is not None:
            return self.energy_matrix.shape
        return self.parameters.field_size[:self.parameters.dimensions]
    
    def get_field_parameters(self) -> Dict[str, Any]:
        """Получение параметров поля."""
        return {
            "field_id": self.field_id,
            "dimensions": self.parameters.dimensions,
            "field_size": self.parameters.field_size,
            "resolution": self.parameters.resolution,
            "base_energy_level": self.parameters.base_energy_level,
            "connection_strength": self.parameters.connection_strength,
            "stability_threshold": self.parameters.stability_threshold,
            "is_initialized": self.is_initialized,
            "is_active": self.is_active,
            "field_stability": self.field_stability,
            "total_energy": self.total_energy,
            "connection_count": len(self.connections),
            "participant_count": len(self.participants)
        }
    
    def get_field_status(self) -> str:
        """Получение статуса поля."""
        if not self.is_initialized:
            return "не инициализировано"
        elif not self.is_active:
            return "неактивно"
        elif self.field_stability < self.parameters.stability_threshold:
            return "нестабильно"
        else:
            return "активно и стабильно"
    
    def deactivate_field(self) -> None:
        """Деактивация квантового поля."""
        if self.is_active:
            self.is_active = False
            self.last_updated = datetime.now()
            self.logger.info("Квантовое поле деактивировано")
    
    def reactivate_field(self) -> bool:
        """Реактивация квантового поля."""
        if not self.is_initialized:
            self.logger.warning("Нельзя реактивировать неинициализированное поле")
            return False
        
        if self.is_active:
            self.logger.info("Поле уже активно")
            return True
        
        self.is_active = True
        self.last_updated = datetime.now()
        self.logger.info("Квантовое поле реактивировано")
        return True
    
    def _update_field_statistics(self) -> None:
        """Обновление статистики поля."""
        if not self.participants:
            return
        
        # Обновление общей энергии
        total_energy = 0.0
        for participant_id, state in self.quantum_states.items():
            total_energy += np.sum(state)
        
        self.total_energy = total_energy
        
        # Обновление дисперсии энергии
        if len(self.quantum_states) > 1:
            energies = [np.sum(state) for state in self.quantum_states.values()]
            self.energy_variance = np.var(energies)
        
        # Обновление количества связей
        self.connection_count = len(self.connections)
        
        self.last_updated = datetime.now()
    
    def get_field_health_score(self) -> float:
        """Получение оценки здоровья поля (0.0 - 1.0)."""
        if not self.is_initialized or not self.is_active:
            return 0.0
        
        # Базовый показатель здоровья
        health_score = self.field_stability
        
        # Учет количества участников
        if self.participants:
            participant_ratio = min(len(self.participants) / 10, 1.0)  # Нормализация к 10 участникам
            health_score = (health_score + participant_ratio) / 2
        
        # Учет стабильности связей
        if self.connections:
            connection_stability = np.mean([conn.stability for conn in self.connections.values()])
            health_score = (health_score + connection_stability) / 2
        
        return round(health_score, 2)
    
    # Методы управления энергетическими потоками
    
    def analyze_energy_flows(self) -> Dict[str, Any]:
        """Анализ энергетических потоков в поле."""
        if not self.participants or not self.connections:
            return {"total_energy": 0.0, "energy_flows": [], "balance_score": 0.0}
        
        energy_flows = []
        total_flow = 0.0
        
        for connection in self.connections.values():
            source_state = self.quantum_states.get(connection.source_participant_id)
            target_state = self.quantum_states.get(connection.target_participant_id)
            
            if source_state is not None and target_state is not None:
                # Расчет потока энергии на основе силы связи и состояний
                energy_flow = connection.strength * np.sum(source_state) * connection.stability
                energy_flows.append({
                    "connection_id": connection.connection_id,
                    "source": connection.source_participant_id,
                    "target": connection.target_participant_id,
                    "energy_flow": energy_flow,
                    "strength": connection.strength,
                    "stability": connection.stability
                })
                total_flow += energy_flow
        
        # Расчет баланса энергии
        balance_score = self._calculate_energy_balance()
        
        return {
            "total_energy": self.total_energy,
            "total_flow": total_flow,
            "energy_flows": energy_flows,
            "balance_score": balance_score,
            "participant_energies": {pid: float(np.sum(state)) for pid, state in self.quantum_states.items()}
        }
    
    def _calculate_energy_balance(self) -> float:
        """Расчет энергетического баланса поля."""
        if not self.participants:
            return 0.0
        
        energies = [np.sum(state) for state in self.quantum_states.values()]
        mean_energy = np.mean(energies)
        variance = np.var(energies)
        
        # Нормализованный баланс (0.0 - 1.0)
        balance = max(0.0, 1.0 - (variance / (mean_energy ** 2 + 1e-6)))
        return round(balance, 3)
    
    def balance_energy_between_participants(self, source_id: str, target_id: str, 
                                          energy_amount: float) -> bool:
        """Балансировка энергии между двумя участниками."""
        try:
            if source_id not in self.participants or target_id not in self.participants:
                self.logger.error("Один или оба участника не найдены")
                return False
            
            source_state = self.quantum_states[source_id]
            target_state = self.quantum_states[target_id]
            
            # Проверка достаточности энергии у источника
            source_energy = np.sum(source_state)
            if source_energy < energy_amount:
                self.logger.error(f"Недостаточно энергии у участника {source_id}")
                return False
            
            # Передача энергии
            transfer_ratio = energy_amount / source_energy
            source_state *= (1 - transfer_ratio)
            target_state += source_state * transfer_ratio
            
            # Нормализация состояний
            self.quantum_states[source_id] = source_state / np.linalg.norm(source_state)
            self.quantum_states[target_id] = target_state / np.linalg.norm(target_state)
            
            # Обновление статистики
            self._update_field_statistics()
            
            self.logger.info(f"Энергия {energy_amount} передана от {source_id} к {target_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при балансировке энергии: {str(e)}")
            return False
    
    def optimize_energy_transitions(self) -> Dict[str, Any]:
        """Оптимизация энергетических переходов в поле."""
        if not self.connections:
            return {"optimizations_applied": 0, "energy_saved": 0.0}
        
        optimizations = 0
        energy_saved = 0.0
        
        for connection in self.connections.values():
            if connection.strength < 0.3:  # Слабые связи
                # Усиление слабых связей
                new_strength = min(connection.strength * 1.2, 1.0)
                if new_strength > connection.strength:
                    connection.update_strength(new_strength)
                    optimizations += 1
                    energy_saved += (new_strength - connection.strength) * 0.1
            
            if connection.stability < 0.5:  # Нестабильные связи
                # Стабилизация связей
                new_stability = min(connection.stability * 1.15, 1.0)
                if new_stability > connection.stability:
                    connection.update_stability(new_stability)
                    optimizations += 1
        
        if optimizations > 0:
            self._update_field_statistics()
            self.logger.info(f"Применено {optimizations} оптимизаций, сэкономлено энергии: {energy_saved:.3f}")
        
        return {
            "optimizations_applied": optimizations,
            "energy_saved": round(energy_saved, 3)
        }
    
    def monitor_energy_balance(self) -> Dict[str, Any]:
        """Мониторинг энергетического баланса поля."""
        if not self.participants:
            return {"status": "no_participants", "balance_score": 0.0}
        
        balance_score = self._calculate_energy_balance()
        
        # Определение статуса баланса
        if balance_score >= 0.8:
            status = "excellent"
        elif balance_score >= 0.6:
            status = "good"
        elif balance_score >= 0.4:
            status = "fair"
        else:
            status = "poor"
        
        # Анализ энергетических аномалий
        anomalies = []
        mean_energy = np.mean([np.sum(state) for state in self.quantum_states.values()])
        
        for participant_id, state in self.quantum_states.items():
            energy = np.sum(state)
            if abs(energy - mean_energy) > 2 * np.std([np.sum(s) for s in self.quantum_states.values()]):
                anomalies.append({
                    "participant_id": participant_id,
                    "energy": float(energy),
                    "deviation": float(abs(energy - mean_energy))
                })
        
        return {
            "status": status,
            "balance_score": balance_score,
            "total_energy": self.total_energy,
            "mean_participant_energy": float(mean_energy),
            "energy_variance": self.energy_variance,
            "anomalies": anomalies,
            "recommendations": self._get_energy_recommendations(balance_score, anomalies)
        }
    
    def _get_energy_recommendations(self, balance_score: float, 
                                   anomalies: List[Dict[str, Any]]) -> List[str]:
        """Получение рекомендаций по энергетическому балансу."""
        recommendations = []
        
        if balance_score < 0.5:
            recommendations.append("Критически низкий энергетический баланс - требуется немедленное вмешательство")
        
        if balance_score < 0.7:
            recommendations.append("Рекомендуется оптимизация энергетических переходов")
        
        if anomalies:
            recommendations.append(f"Обнаружено {len(anomalies)} энергетических аномалий - требуется анализ")
        
        if self.connection_count < len(self.participants) * 0.5:
            recommendations.append("Недостаточно связей между участниками - рекомендуется создание дополнительных связей")
        
        return recommendations
    
    def __str__(self) -> str:
        status = self.get_field_status()
        return f"QuantumField(id={self.field_id[:8]}, status={status}, participants={len(self.participants)})"
    
    def __repr__(self) -> str:
        return f"QuantumField(field_id='{self.field_id}', is_initialized={self.is_initialized}, is_active={self.is_active})"
