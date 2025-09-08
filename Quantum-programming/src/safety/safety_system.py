"""
Система безопасности протокола SIRUS-FELINE_BRANCH_PROTOCOL.
Реализация защитных механизмов: RING-OF-SAFETY, SHIELD, TRACE.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union, Set
from datetime import datetime
import uuid
import numpy as np
import json
from dataclasses import dataclass, field

from ..quantum.participant_manager import ParticipantManager
from ..quantum.quantum_field import QuantumField


class SafetyViolationError(Exception):
    """Исключение для нарушений безопасности."""
    pass


class ProtectionLevelError(Exception):
    """Исключение для ошибок уровня защиты."""
    pass


class ThreatDetectionError(Exception):
    """Исключение для ошибок обнаружения угроз."""
    pass


@dataclass
class ProtectionRing:
    """Защитное кольцо безопасности."""
    
    ring_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ring_type: str = ""  # emotional, mental, energetic
    protection_level: float = 0.0  # 0.0 - 1.0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Параметры защиты
    emotional_protection: float = 0.0
    mental_protection: float = 0.0
    energetic_protection: float = 0.0
    
    # Метаданные кольца
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Валидация параметров защитного кольца."""
        if not 0 <= self.protection_level <= 1:
            raise ValueError("Уровень защиты должен быть в диапазоне [0, 1]")
        if not 0 <= self.emotional_protection <= 1:
            raise ValueError("Эмоциональная защита должна быть в диапазоне [0, 1]")
        if not 0 <= self.mental_protection <= 1:
            raise ValueError("Психическая защита должна быть в диапазоне [0, 1]")
        if not 0 <= self.energetic_protection <= 1:
            raise ValueError("Энергетическая защита должна быть в диапазоне [0, 1]")
    
    def update_protection_levels(self, emotional: Optional[float] = None,
                                mental: Optional[float] = None,
                                energetic: Optional[float] = None) -> None:
        """Обновление уровней защиты."""
        if emotional is not None:
            if not 0 <= emotional <= 1:
                raise ValueError("Эмоциональная защита должна быть в диапазоне [0, 1]")
            self.emotional_protection = emotional
        
        if mental is not None:
            if not 0 <= mental <= 1:
                raise ValueError("Психическая защита должна быть в диапазоне [0, 1]")
            self.mental_protection = mental
        
        if energetic is not None:
            if not 0 <= energetic <= 1:
                raise ValueError("Энергетическая защита должна быть в диапазоне [0, 1]")
            self.energetic_protection = energetic
        
        # Обновление общего уровня защиты
        self.protection_level = (self.emotional_protection + self.mental_protection + self.energetic_protection) / 3.0
        self.last_updated = datetime.now()
    
    def get_ring_health(self) -> float:
        """Получение здоровья защитного кольца."""
        return (self.emotional_protection + self.mental_protection + self.energetic_protection) / 3.0


@dataclass
class ThreatPattern:
    """Шаблон угрозы для системы безопасности."""
    
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    threat_type: str = ""  # emotional, mental, energetic, combined
    severity: float = 0.0  # 0.0 - 1.0
    detection_signatures: List[str] = field(default_factory=list)
    protection_requirements: Dict[str, float] = field(default_factory=dict)
    
    # Метаданные угрозы
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Валидация шаблона угрозы."""
        if not 0 <= self.severity <= 1:
            raise ValueError("Серьезность угрозы должна быть в диапазоне [0, 1]")
        if not self.name.strip():
            raise ValueError("Название угрозы не может быть пустым")


@dataclass
class SecurityEvent:
    """Событие безопасности для системы TRACE."""
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = ""  # threat_detected, protection_activated, violation_attempted
    severity: float = 0.0  # 0.0 - 1.0
    source: str = ""  # external, internal, system
    target: str = ""  # participant_id или "system"
    
    # Детали события
    description: str = ""
    threat_pattern: Optional[str] = None
    protection_response: Optional[str] = None
    outcome: str = ""  # blocked, mitigated, allowed
    
    # Метаданные события
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Валидация события безопасности."""
        if not 0 <= self.severity <= 1:
            raise ValueError("Серьезность события должна быть в диапазоне [0, 1]")


class SafetySystem:
    """Система безопасности протокола."""
    
    def __init__(self, participant_manager: ParticipantManager, 
                 quantum_field: QuantumField,
                 log_level: int = logging.INFO):
        """Инициализация системы безопасности."""
        self.logger = self._setup_logger(log_level)
        self.participant_manager = participant_manager
        self.quantum_field = quantum_field
        
        # Защитные кольца
        self.protection_rings: Dict[str, ProtectionRing] = {}
        self.active_rings: Set[str] = set()
        
        # Система обнаружения угроз
        self.threat_patterns: Dict[str, ThreatPattern] = {}
        self.active_threats: Dict[str, Dict[str, Any]] = {}
        
        # Система TRACE
        self.security_events: List[SecurityEvent] = []
        self.external_influences: List[Dict[str, Any]] = []
        
        # Статистика безопасности
        self.threats_blocked: int = 0
        self.threats_mitigated: int = 0
        self.violations_prevented: int = 0
        
        # Метаданные
        self.created_at: datetime = datetime.now()
        self.last_security_check: Optional[datetime] = None
        
        # Инициализация защитных систем
        self._initialize_protection_systems()
        self._initialize_threat_patterns()
        
        self.logger.info("SafetySystem инициализирована")
    
    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Настройка логгера для системы безопасности."""
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
    
    def _initialize_protection_systems(self) -> None:
        """Инициализация защитных систем."""
        # Создание основного защитного кольца
        main_ring = ProtectionRing(
            ring_type="main",
            protection_level=0.8,
            emotional_protection=0.8,
            mental_protection=0.8,
            energetic_protection=0.8,
            metadata={"purpose": "main_protection", "auto_adapt": True}
        )
        
        self.protection_rings[main_ring.ring_id] = main_ring
        self.active_rings.add(main_ring.ring_id)
        
        # Создание специализированных колец
        emotional_ring = ProtectionRing(
            ring_type="emotional",
            protection_level=0.9,
            emotional_protection=0.9,
            mental_protection=0.7,
            energetic_protection=0.7,
            metadata={"purpose": "emotional_protection", "sensitivity": "high"}
        )
        
        mental_ring = ProtectionRing(
            ring_type="mental",
            protection_level=0.9,
            emotional_protection=0.7,
            mental_protection=0.9,
            energetic_protection=0.7,
            metadata={"purpose": "mental_protection", "sensitivity": "high"}
        )
        
        energetic_ring = ProtectionRing(
            ring_type="energetic",
            protection_level=0.9,
            emotional_protection=0.7,
            mental_protection=0.7,
            energetic_protection=0.9,
            metadata={"purpose": "energetic_protection", "sensitivity": "high"}
        )
        
        self.protection_rings[emotional_ring.ring_id] = emotional_ring
        self.protection_rings[mental_ring.ring_id] = mental_ring
        self.protection_rings[energetic_ring.ring_id] = energetic_ring
        
        self.active_rings.add(emotional_ring.ring_id)
        self.active_rings.add(mental_ring.ring_id)
        self.active_rings.add(energetic_ring.ring_id)
        
        self.logger.info("Защитные кольца инициализированы")
    
    def _initialize_threat_patterns(self) -> None:
        """Инициализация шаблонов угроз."""
        # Эмоциональные угрозы
        emotional_threats = [
            ThreatPattern(
                name="Эмоциональная манипуляция",
                description="Попытки эмоционального воздействия и манипуляции",
                threat_type="emotional",
                severity=0.7,
                detection_signatures=["sudden_emotion_change", "unusual_emotional_response", "emotional_manipulation_attempt"],
                protection_requirements={"emotional_protection": 0.8}
            ),
            ThreatPattern(
                name="Энергетический вампиризм",
                description="Попытки высасывания эмоциональной энергии",
                threat_type="emotional",
                severity=0.8,
                detection_signatures=["energy_drain", "emotional_exhaustion", "vampiric_behavior"],
                protection_requirements={"emotional_protection": 0.9, "energetic_protection": 0.8}
            )
        ]
        
        # Психические угрозы
        mental_threats = [
            ThreatPattern(
                name="Психическое программирование",
                description="Попытки внедрения вредоносных программ в сознание",
                threat_type="mental",
                severity=0.9,
                detection_signatures=["thought_insertion", "mental_programming", "consciousness_hijack"],
                protection_requirements={"mental_protection": 0.9, "emotional_protection": 0.7}
            ),
            ThreatPattern(
                name="Информационная атака",
                description="Атаки на информационную структуру сознания",
                threat_type="mental",
                severity=0.8,
                detection_signatures=["information_bombardment", "cognitive_overload", "mental_confusion"],
                protection_requirements={"mental_protection": 0.8, "energetic_protection": 0.6}
            )
        ]
        
        # Энергетические угрозы
        energetic_threats = [
            ThreatPattern(
                name="Энергетическая атака",
                description="Прямые атаки на энергетическое поле",
                threat_type="energetic",
                severity=0.8,
                detection_signatures=["energy_attack", "field_penetration", "energy_destruction"],
                protection_requirements={"energetic_protection": 0.9, "mental_protection": 0.7}
            ),
            ThreatPattern(
                name="Энергетический паразитизм",
                description="Паразитическое использование энергетических ресурсов",
                threat_type="energetic",
                severity=0.7,
                detection_signatures=["energy_parasitism", "resource_drain", "field_weakening"],
                protection_requirements={"energetic_protection": 0.8}
            )
        ]
        
        # Комбинированные угрозы
        combined_threats = [
            ThreatPattern(
                name="Комплексная атака",
                description="Многоуровневая атака на все системы защиты",
                threat_type="combined",
                severity=1.0,
                detection_signatures=["multi_layer_attack", "coordinated_assault", "system_breach_attempt"],
                protection_requirements={"emotional_protection": 0.9, "mental_protection": 0.9, "energetic_protection": 0.9}
            )
        ]
        
        # Добавление всех шаблонов
        all_threats = emotional_threats + mental_threats + energetic_threats + combined_threats
        for threat in all_threats:
            self.threat_patterns[threat.pattern_id] = threat
        
        self.logger.info(f"Инициализировано {len(self.threat_patterns)} шаблонов угроз")
    
    # RING-OF-SAFETY методы
    
    def create_protection_ring(self, ring_type: str, protection_levels: Dict[str, float],
                              metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Создание нового защитного кольца.
        
        Args:
            ring_type: Тип защитного кольца
            protection_levels: Уровни защиты (emotional, mental, energetic)
            metadata: Дополнительные метаданные
            
        Returns:
            str: ID созданного защитного кольца
        """
        try:
            # Валидация уровней защиты
            for protection_type, level in protection_levels.items():
                if not 0 <= level <= 1:
                    raise ProtectionLevelError(f"Уровень {protection_type} должен быть в диапазоне [0, 1]")
            
            # Создание защитного кольца
            ring = ProtectionRing(
                ring_type=ring_type,
                emotional_protection=protection_levels.get("emotional", 0.0),
                mental_protection=protection_levels.get("mental", 0.0),
                energetic_protection=protection_levels.get("energetic", 0.0),
                metadata=metadata or {}
            )
            
            # Добавление кольца в систему
            self.protection_rings[ring.ring_id] = ring
            self.active_rings.add(ring.ring_id)
            
            # Логирование события
            self._log_security_event(
                event_type="protection_ring_created",
                severity=0.3,
                source="system",
                target="system",
                description=f"Создано защитное кольцо типа {ring_type}",
                metadata={"ring_id": ring.ring_id, "protection_levels": protection_levels}
            )
            
            self.logger.info(f"Создано защитное кольцо {ring_type} с ID: {ring.ring_id}")
            return ring.ring_id
            
        except Exception as e:
            error_msg = f"Ошибка при создании защитного кольца: {str(e)}"
            self.logger.error(error_msg)
            raise ProtectionLevelError(error_msg) from e
    
    def activate_protection_ring(self, ring_id: str) -> bool:
        """Активация защитного кольца."""
        if ring_id not in self.protection_rings:
            self.logger.error(f"Защитное кольцо {ring_id} не найдено")
            return False
        
        ring = self.protection_rings[ring_id]
        ring.is_active = True
        self.active_rings.add(ring_id)
        
        self._log_security_event(
            event_type="protection_ring_activated",
            severity=0.2,
            source="system",
            target="system",
            description=f"Активировано защитное кольцо {ring.ring_type}",
            metadata={"ring_id": ring_id}
        )
        
        self.logger.info(f"Защитное кольцо {ring_id} активировано")
        return True
    
    def deactivate_protection_ring(self, ring_id: str) -> bool:
        """Деактивация защитного кольца."""
        if ring_id not in self.protection_rings:
            self.logger.error(f"Защитное кольцо {ring_id} не найдено")
            return False
        
        ring = self.protection_rings[ring_id]
        ring.is_active = False
        self.active_rings.discard(ring_id)
        
        self._log_security_event(
            event_type="protection_ring_deactivated",
            severity=0.4,
            source="system",
            target="system",
            description=f"Деактивировано защитное кольцо {ring.ring_type}",
            metadata={"ring_id": ring_id}
        )
        
        self.logger.info(f"Защитное кольцо {ring_id} деактивировано")
        return True
    
    def update_protection_ring(self, ring_id: str, protection_levels: Dict[str, float]) -> bool:
        """Обновление уровней защиты кольца."""
        if ring_id not in self.protection_rings:
            self.logger.error(f"Защитное кольцо {ring_id} не найдено")
            return False
        
        try:
            ring = self.protection_rings[ring_id]
            ring.update_protection_levels(**protection_levels)
            
            self._log_security_event(
                event_type="protection_ring_updated",
                severity=0.2,
                source="system",
                target="system",
                description=f"Обновлено защитное кольцо {ring.ring_type}",
                metadata={"ring_id": ring_id, "new_levels": protection_levels}
            )
            
            self.logger.info(f"Защитное кольцо {ring_id} обновлено")
            return True
            
        except Exception as e:
            error_msg = f"Ошибка при обновлении защитного кольца: {str(e)}"
            self.logger.error(error_msg)
            return False
    
    def get_protection_status(self) -> Dict[str, Any]:
        """Получение статуса всех защитных колец."""
        status = {
            "total_rings": len(self.protection_rings),
            "active_rings": len(self.active_rings),
            "overall_protection": 0.0,
            "ring_details": {}
        }
        
        if self.active_rings:
            total_protection = 0.0
            for ring_id in self.active_rings:
                ring = self.protection_rings[ring_id]
                total_protection += ring.protection_level
                
                status["ring_details"][ring_id] = {
                    "type": ring.ring_type,
                    "protection_level": ring.protection_level,
                    "emotional_protection": ring.emotional_protection,
                    "mental_protection": ring.mental_protection,
                    "energetic_protection": ring.energetic_protection,
                    "is_active": ring.is_active,
                    "health": ring.get_ring_health()
                }
            
            status["overall_protection"] = total_protection / len(self.active_rings)
        
        return status
    
    # SHIELD методы
    
    def detect_threat(self, threat_signatures: List[str], source: str = "external",
                     target: str = "system") -> Optional[ThreatPattern]:
        """
        Обнаружение угрозы на основе сигнатур.
        
        Args:
            threat_signatures: Сигнатуры угрозы
            source: Источник угрозы
            target: Цель угрозы
            
        Returns:
            Optional[ThreatPattern]: Обнаруженная угроза или None
        """
        try:
            detected_threats = []
            
            # Поиск совпадающих шаблонов угроз
            for pattern in self.threat_patterns.values():
                matches = 0
                for signature in threat_signatures:
                    if any(sig in signature for sig in pattern.detection_signatures):
                        matches += 1
                
                # Если найдено достаточно совпадений
                if matches >= len(pattern.detection_signatures) * 0.7:
                    detected_threats.append((pattern, matches))
            
            if not detected_threats:
                return None
            
            # Выбор наиболее подходящей угрозы
            best_match = max(detected_threats, key=lambda x: (x[1], x[0].severity))
            threat_pattern = best_match[0]
            
            # Логирование обнаружения угрозы
            self._log_security_event(
                event_type="threat_detected",
                severity=threat_pattern.severity,
                source=source,
                target=target,
                description=f"Обнаружена угроза: {threat_pattern.name}",
                threat_pattern=threat_pattern.pattern_id,
                metadata={"signatures": threat_signatures, "confidence": best_match[1] / len(threat_pattern.detection_signatures)}
            )
            
            # Добавление в активные угрозы
            self.active_threats[threat_pattern.pattern_id] = {
                "pattern": threat_pattern,
                "detected_at": datetime.now(),
                "source": source,
                "target": target,
                "status": "detected"
            }
            
            self.logger.warning(f"Обнаружена угроза: {threat_pattern.name} (серьезность: {threat_pattern.severity})")
            return threat_pattern
            
        except Exception as e:
            error_msg = f"Ошибка при обнаружении угрозы: {str(e)}"
            self.logger.error(error_msg)
            return None
    
    def activate_shield_protection(self, threat_pattern: ThreatPattern, 
                                 target_participants: List[str]) -> Dict[str, Any]:
        """
        Активация защиты SHIELD против конкретной угрозы.
        
        Args:
            threat_pattern: Шаблон угрозы
            target_participants: Список ID участников для защиты
            
        Returns:
            Dict[str, Any]: Результат активации защиты
        """
        try:
            self.logger.info(f"Активирую SHIELD защиту против угрозы: {threat_pattern.name}")
            
            # Проверка требований защиты
            protection_requirements = threat_pattern.protection_requirements
            current_protection = self.get_protection_status()
            
            # Анализ достаточности защиты
            protection_gaps = []
            for protection_type, required_level in protection_requirements.items():
                current_level = 0.0
                for ring_id in self.active_rings:
                    ring = self.protection_rings[ring_id]
                    if hasattr(ring, protection_type):
                        current_level = max(current_level, getattr(ring, protection_type))
                
                if current_level < required_level:
                    protection_gaps.append({
                        "type": protection_type,
                        "required": required_level,
                        "current": current_level,
                        "gap": required_level - current_level
                    })
            
            # Активация дополнительной защиты при необходимости
            additional_protection_activated = False
            if protection_gaps:
                self.logger.warning(f"Обнаружены пробелы в защите: {protection_gaps}")
                
                # Создание временного усиленного кольца защиты
                enhanced_ring = self.create_protection_ring(
                    ring_type="enhanced_shield",
                    protection_levels={
                        "emotional_protection": max(0.9, protection_requirements.get("emotional_protection", 0.0)),
                        "mental_protection": max(0.9, protection_requirements.get("mental_protection", 0.0)),
                        "energetic_protection": max(0.9, protection_requirements.get("energetic_protection", 0.0))
                    },
                    metadata={"purpose": "threat_response", "threat_id": threat_pattern.pattern_id}
                )
                
                additional_protection_activated = True
            
            # Применение защиты к участникам
            protected_participants = []
            for participant_id in target_participants:
                participant = self.participant_manager.get_participant(participant_id)
                if participant:
                    # Усиление защиты участника
                    quantum_state = participant.quantum_state
                    
                    # Адаптивная защита на основе типа угрозы
                    if threat_pattern.threat_type == "emotional":
                        quantum_state.protection = min(1.0, quantum_state.protection + 0.2)
                    elif threat_pattern.threat_type == "mental":
                        quantum_state.clarity = min(1.0, quantum_state.clarity + 0.1)
                        quantum_state.protection = min(1.0, quantum_state.protection + 0.15)
                    elif threat_pattern.threat_type == "energetic":
                        quantum_state.protection = min(1.0, quantum_state.protection + 0.25)
                    elif threat_pattern.threat_type == "combined":
                        quantum_state.protection = min(1.0, quantum_state.protection + 0.3)
                        quantum_state.clarity = min(1.0, quantum_state.clarity + 0.15)
                    
                    # Обновление состояния участника
                    self.participant_manager.update_participant_quantum_state(
                        participant_id,
                        np.array([
                            quantum_state.energy_level,
                            quantum_state.clarity,
                            quantum_state.protection,
                            quantum_state.alignment
                        ], dtype=np.float64)
                    )
                    
                    protected_participants.append(participant_id)
            
            # Обновление статуса угрозы
            if threat_pattern.pattern_id in self.active_threats:
                self.active_threats[threat_pattern.pattern_id]["status"] = "shielded"
                self.active_threats[threat_pattern.pattern_id]["protected_participants"] = protected_participants
            
            # Логирование активации защиты
            self._log_security_event(
                event_type="shield_protection_activated",
                severity=threat_pattern.severity,
                source="system",
                target="multiple",
                description=f"Активирована SHIELD защита против угрозы: {threat_pattern.name}",
                threat_pattern=threat_pattern.pattern_id,
                protection_response="shield_activated",
                outcome="blocked",
                metadata={
                    "protected_participants": protected_participants,
                    "additional_protection": additional_protection_activated,
                    "protection_gaps": protection_gaps
                }
            )
            
            self.threats_blocked += 1
            
            result = {
                "success": True,
                "threat_pattern": threat_pattern.name,
                "protection_activated": True,
                "protected_participants": len(protected_participants),
                "additional_protection_activated": additional_protection_activated,
                "protection_gaps": protection_gaps,
                "outcome": "blocked"
            }
            
            self.logger.info(f"SHIELD защита активирована: заблокировано {len(protected_participants)} участников")
            return result
            
        except Exception as e:
            error_msg = f"Ошибка при активации SHIELD защиты: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    # TRACE методы
    
    def trace_external_influence(self, influence_data: Dict[str, Any]) -> str:
        """
        Логирование и анализ внешнего влияния.
        
        Args:
            influence_data: Данные о внешнем влиянии
            
        Returns:
            str: ID зарегистрированного влияния
        """
        try:
            influence_id = str(uuid.uuid4())
            
            # Анализ влияния
            influence_analysis = self._analyze_external_influence(influence_data)
            
            # Регистрация влияния
            influence_record = {
                "influence_id": influence_id,
                "timestamp": datetime.now().isoformat(),
                "source": influence_data.get("source", "unknown"),
                "type": influence_data.get("type", "unknown"),
                "intensity": influence_data.get("intensity", 0.0),
                "target": influence_data.get("target", "system"),
                "data": influence_data,
                "analysis": influence_analysis
            }
            
            self.external_influences.append(influence_record)
            
            # Проверка на угрозы
            if influence_analysis.get("threat_level", 0.0) > 0.5:
                threat_signatures = influence_analysis.get("threat_signatures", [])
                detected_threat = self.detect_threat(threat_signatures, influence_data.get("source", "external"))
                
                if detected_threat:
                    # Автоматическая активация защиты
                    target_participants = [influence_data.get("target")] if influence_data.get("target") != "system" else []
                    self.activate_shield_protection(detected_threat, target_participants)
            
            # Логирование события TRACE
            self._log_security_event(
                event_type="external_influence_traced",
                severity=influence_analysis.get("threat_level", 0.0),
                source=influence_data.get("source", "external"),
                target=influence_data.get("target", "system"),
                description=f"Зарегистрировано внешнее влияние: {influence_data.get('type', 'unknown')}",
                metadata={
                    "influence_id": influence_id,
                    "threat_level": influence_analysis.get("threat_level", 0.0),
                    "analysis": influence_analysis
                }
            )
            
            self.logger.info(f"Внешнее влияние зарегистрировано: {influence_id}")
            return influence_id
            
        except Exception as e:
            error_msg = f"Ошибка при регистрации внешнего влияния: {str(e)}"
            self.logger.error(error_msg)
            return ""
    
    def _analyze_external_influence(self, influence_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ внешнего влияния."""
        analysis = {
            "threat_level": 0.0,
            "threat_signatures": [],
            "recommendations": []
        }
        
        # Анализ типа влияния
        influence_type = influence_data.get("type", "").lower()
        intensity = influence_data.get("intensity", 0.0)
        
        # Определение уровня угрозы
        if "attack" in influence_type or "assault" in influence_type:
            analysis["threat_level"] = min(1.0, intensity + 0.6)
            analysis["threat_signatures"].extend(["attack_detected", "assault_pattern"])
        elif "manipulation" in influence_type or "control" in influence_type:
            analysis["threat_level"] = min(1.0, intensity + 0.4)
            analysis["threat_signatures"].extend(["manipulation_attempt", "control_attempt"])
        elif "parasitism" in influence_type or "drain" in influence_type:
            analysis["threat_level"] = min(1.0, intensity + 0.5)
            analysis["threat_signatures"].extend(["parasitic_behavior", "energy_drain"])
        
        # Анализ интенсивности
        if intensity > 0.8:
            analysis["threat_level"] = min(1.0, analysis["threat_level"] + 0.2)
            analysis["threat_signatures"].append("high_intensity")
        elif intensity > 0.5:
            analysis["threat_level"] = min(1.0, analysis["threat_level"] + 0.1)
            analysis["threat_signatures"].append("medium_intensity")
        
        # Генерация рекомендаций
        if analysis["threat_level"] > 0.7:
            analysis["recommendations"].append("Немедленная активация максимальной защиты")
        elif analysis["threat_level"] > 0.5:
            analysis["recommendations"].append("Активация усиленной защиты")
        elif analysis["threat_level"] > 0.3:
            analysis["recommendations"].append("Мониторинг и готовность к защите")
        
        return analysis
    
    def _log_security_event(self, event_type: str, severity: float, source: str, target: str,
                           description: str, threat_pattern: Optional[str] = None,
                           protection_response: Optional[str] = None, outcome: str = "",
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """Логирование события безопасности."""
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            source=source,
            target=target,
            description=description,
            threat_pattern=threat_pattern,
            protection_response=protection_response,
            outcome=outcome,
            metadata=metadata or {}
        )
        
        self.security_events.append(event)
        
        # Ограничение истории последними 1000 событиями
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
    
    def get_security_report(self) -> Dict[str, Any]:
        """Получение отчета о безопасности системы."""
        return {
            "timestamp": datetime.now().isoformat(),
            "protection_status": self.get_protection_status(),
            "active_threats": len(self.active_threats),
            "threats_blocked": self.threats_blocked,
            "threats_mitigated": self.threats_mitigated,
            "violations_prevented": self.violations_prevented,
            "recent_events": len([e for e in self.security_events if (datetime.now() - e.timestamp).seconds < 3600]),
            "external_influences": len(self.external_influences),
            "system_health": self._calculate_system_health()
        }
    
    def _calculate_system_health(self) -> float:
        """Расчет общего здоровья системы безопасности."""
        if not self.active_rings:
            return 0.0
        
        # Средний уровень защиты активных колец
        protection_levels = [self.protection_rings[ring_id].protection_level for ring_id in self.active_rings]
        avg_protection = np.mean(protection_levels)
        
        # Фактор угроз (чем меньше угроз, тем лучше)
        threat_factor = max(0.0, 1.0 - (len(self.active_threats) * 0.1))
        
        # Фактор событий (баланс между блокировкой и попытками)
        if self.threats_blocked + self.threats_mitigated > 0:
            success_rate = self.threats_blocked / (self.threats_blocked + self.threats_mitigated)
        else:
            success_rate = 1.0
        
        # Общее здоровье
        health = (avg_protection * 0.5 + threat_factor * 0.3 + success_rate * 0.2)
        return round(health, 3)
    
    def __str__(self) -> str:
        return f"SafetySystem(rings={len(self.active_rings)}, threats={len(self.active_threats)})"
    
    def __repr__(self) -> str:
        return f"SafetySystem(participant_manager={'set' if self.participant_manager else 'not_set'}, quantum_field={'set' if self.quantum_field else 'not_set'})"
