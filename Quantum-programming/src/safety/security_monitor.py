"""
Система мониторинга безопасности протокола SIRUS-FELINE_BRANCH_PROTOCOL.
Постоянный мониторинг целостности участников, детекция аномалий и автоматические реакции.
"""

import logging
import threading
import time
from typing import Dict, Any, List, Optional, Tuple, Union, Set
from datetime import datetime, timedelta
import uuid
import numpy as np
from dataclasses import dataclass, field
import json

from .safety_system import SafetySystem
from ..quantum.participant_manager import ParticipantManager
from ..quantum.quantum_field import QuantumField


class MonitoringError(Exception):
    """Исключение для ошибок мониторинга."""
    pass


class IntegrityViolationError(Exception):
    """Исключение для нарушений целостности."""
    pass


@dataclass
class IntegrityCheck:
    """Результат проверки целостности участника."""
    
    check_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    check_type: str = ""  # quantum_state, protection_level, connection_stability
    
    # Результаты проверки
    is_integrity_maintained: bool = True
    integrity_score: float = 1.0  # 0.0 - 1.0
    violations_detected: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Детали проверки
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Валидация результатов проверки."""
        if not 0 <= self.integrity_score <= 1:
            raise ValueError("Оценка целостности должна быть в диапазоне [0, 1]")


@dataclass
class AnomalyDetection:
    """Обнаруженная аномалия в системе."""
    
    anomaly_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    anomaly_type: str = ""  # state_change, protection_breach, connection_loss
    
    # Характеристики аномалии
    severity: float = 0.0  # 0.0 - 1.0
    source: str = ""  # participant_id или "system"
    description: str = ""
    
    # Контекст аномалии
    context: Dict[str, Any] = field(default_factory=dict)
    related_events: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Валидация аномалии."""
        if not 0 <= self.severity <= 1:
            raise ValueError("Серьезность аномалии должна быть в диапазоне [0, 1]")


@dataclass
class SecurityReport:
    """Отчет о безопасности системы."""
    
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    report_period: str = ""  # hourly, daily, weekly
    
    # Общая статистика
    total_participants: int = 0
    participants_monitored: int = 0
    integrity_violations: int = 0
    anomalies_detected: int = 0
    threats_blocked: int = 0
    
    # Детали отчета
    integrity_summary: Dict[str, Any] = field(default_factory=dict)
    anomaly_summary: Dict[str, Any] = field(default_factory=dict)
    threat_summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    # Метаданные
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityMonitor:
    """Система мониторинга безопасности."""
    
    def __init__(self, safety_system: SafetySystem,
                 participant_manager: ParticipantManager,
                 quantum_field: QuantumField,
                 monitoring_interval: float = 30.0,  # секунды
                 log_level: int = logging.INFO):
        """Инициализация системы мониторинга безопасности."""
        self.logger = self._setup_logger(log_level)
        self.safety_system = safety_system
        self.participant_manager = participant_manager
        self.quantum_field = quantum_field
        
        # Параметры мониторинга
        self.monitoring_interval = monitoring_interval
        self.is_monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # Данные мониторинга
        self.integrity_checks: List[IntegrityCheck] = []
        self.anomalies_detected: List[AnomalyDetection] = []
        self.monitoring_history: List[Dict[str, Any]] = []
        
        # Статистика мониторинга
        self.total_checks_performed: int = 0
        self.violations_found: int = 0
        self.anomalies_found: int = 0
        self.last_check_time: Optional[datetime] = None
        
        # Метаданные
        self.created_at: datetime = datetime.now()
        self.last_report_generated: Optional[datetime] = None
        
        # Инициализация системы мониторинга
        self._initialize_monitoring_system()
        
        self.logger.info("SecurityMonitor инициализирован")
    
    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Настройка логгера для системы мониторинга."""
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
    
    def _initialize_monitoring_system(self) -> None:
        """Инициализация системы мониторинга."""
        # Установка базовых параметров мониторинга
        self.monitoring_interval = max(10.0, self.monitoring_interval)  # Минимум 10 секунд
        
        # Инициализация базовых проверок
        self.logger.info("Система мониторинга инициализирована")
    
    # Методы постоянного мониторинга
    
    def start_monitoring(self) -> bool:
        """Запуск постоянного мониторинга безопасности."""
        if self.is_monitoring_active:
            self.logger.warning("Мониторинг уже активен")
            return False
        
        try:
            self.is_monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="SecurityMonitor"
            )
            self.monitoring_thread.start()
            
            self.logger.info("Постоянный мониторинг безопасности запущен")
            return True
            
        except Exception as e:
            error_msg = f"Ошибка при запуске мониторинга: {str(e)}"
            self.logger.error(error_msg)
            self.is_monitoring_active = False
            return False
    
    def stop_monitoring(self) -> bool:
        """Остановка постоянного мониторинга безопасности."""
        if not self.is_monitoring_active:
            self.logger.warning("Мониторинг не активен")
            return False
        
        try:
            self.is_monitoring_active = False
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5.0)
            
            self.logger.info("Постоянный мониторинг безопасности остановлен")
            return True
            
        except Exception as e:
            error_msg = f"Ошибка при остановке мониторинга: {str(e)}"
            self.logger.error(error_msg)
            return False
    
    def _monitoring_loop(self) -> None:
        """Основной цикл мониторинга безопасности."""
        self.logger.info("Цикл мониторинга безопасности запущен")
        
        while self.is_monitoring_active:
            try:
                start_time = time.time()
                
                # Выполнение проверок безопасности
                self._perform_security_checks()
                
                # Обновление времени последней проверки
                self.last_check_time = datetime.now()
                
                # Расчет времени до следующей проверки
                elapsed_time = time.time() - start_time
                sleep_time = max(0.0, self.monitoring_interval - elapsed_time)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                error_msg = f"Ошибка в цикле мониторинга: {str(e)}"
                self.logger.error(error_msg)
                time.sleep(5.0)  # Пауза при ошибке
        
        self.logger.info("Цикл мониторинга безопасности завершен")
    
    def _perform_security_checks(self) -> None:
        """Выполнение всех проверок безопасности."""
        try:
            # Получение списка всех участников
            all_participants = list(self.participant_manager.participants.keys())
            
            if not all_participants:
                return
            
            # Проверка целостности каждого участника
            for participant_id in all_participants:
                self._check_participant_integrity(participant_id)
            
            # Проверка целостности квантового поля
            self._check_quantum_field_integrity()
            
            # Проверка системы безопасности
            self._check_safety_system_integrity()
            
            # Обновление статистики
            self.total_checks_performed += 1
            
        except Exception as e:
            error_msg = f"Ошибка при выполнении проверок безопасности: {str(e)}"
            self.logger.error(error_msg)
    
    def _check_participant_integrity(self, participant_id: str) -> None:
        """Проверка целостности конкретного участника."""
        try:
            participant = self.participant_manager.get_participant(participant_id)
            if not participant:
                return
            
            # Проверка квантового состояния
            quantum_state = participant.quantum_state
            integrity_violations = []
            warnings = []
            integrity_score = 1.0
            
            # Проверка диапазонов значений
            if not 0 <= quantum_state.energy_level <= 2.0:
                integrity_violations.append(f"energy_level_out_of_range: {quantum_state.energy_level}")
                integrity_score *= 0.7
            
            if not 0 <= quantum_state.clarity <= 1.0:
                integrity_violations.append(f"clarity_out_of_range: {quantum_state.clarity}")
                integrity_score *= 0.8
            
            if not 0 <= quantum_state.protection <= 1.0:
                integrity_violations.append(f"protection_out_of_range: {quantum_state.protection}")
                integrity_score *= 0.8
            
            if not 0 <= quantum_state.alignment <= 1.0:
                integrity_violations.append(f"alignment_out_of_range: {quantum_state.alignment}")
                integrity_score *= 0.8
            
            # Проверка критических значений
            if quantum_state.energy_level < 0.1:
                integrity_violations.append("critical_energy_depletion")
                integrity_score *= 0.5
            
            if quantum_state.protection < 0.2:
                integrity_violations.append("critical_protection_weakness")
                integrity_score *= 0.6
            
            if quantum_state.clarity < 0.3:
                warnings.append("low_clarity_level")
                integrity_score *= 0.9
            
            # Проверка согласованности состояний
            state_consistency = self._check_state_consistency(quantum_state)
            if not state_consistency["consistent"]:
                integrity_violations.extend(state_consistency["inconsistencies"])
                integrity_score *= 0.8
            
            # Создание записи о проверке
            integrity_check = IntegrityCheck(
                participant_id=participant_id,
                check_type="quantum_state",
                is_integrity_maintained=len(integrity_violations) == 0,
                integrity_score=max(0.0, integrity_score),
                violations_detected=integrity_violations,
                warnings=warnings,
                details={
                    "energy_level": quantum_state.energy_level,
                    "clarity": quantum_state.clarity,
                    "protection": quantum_state.protection,
                    "alignment": quantum_state.alignment,
                    "state_consistency": state_consistency
                }
            )
            
            self.integrity_checks.append(integrity_check)
            
            # Ограничение истории последними 1000 проверок
            if len(self.integrity_checks) > 1000:
                self.integrity_checks = self.integrity_checks[-1000:]
            
            # Реакция на нарушения целостности
            if not integrity_check.is_integrity_maintained:
                self.violations_found += 1
                self._handle_integrity_violation(integrity_check)
            
        except Exception as e:
            error_msg = f"Ошибка при проверке целостности участника {participant_id}: {str(e)}"
            self.logger.error(error_msg)
    
    def _check_state_consistency(self, quantum_state) -> Dict[str, Any]:
        """Проверка согласованности квантового состояния."""
        inconsistencies = []
        
        # Проверка логической согласованности
        if quantum_state.energy_level > 1.5 and quantum_state.clarity < 0.5:
            inconsistencies.append("high_energy_low_clarity")
        
        if quantum_state.protection > 0.8 and quantum_state.alignment < 0.3:
            inconsistencies.append("high_protection_low_alignment")
        
        if quantum_state.clarity > 0.9 and quantum_state.energy_level < 0.5:
            inconsistencies.append("high_clarity_low_energy")
        
        return {
            "consistent": len(inconsistencies) == 0,
            "inconsistencies": inconsistencies
        }
    
    def _check_quantum_field_integrity(self) -> None:
        """Проверка целостности квантового поля."""
        try:
            # Проверка активности поля
            if not self.quantum_field.is_active:
                self._detect_anomaly(
                    anomaly_type="field_inactive",
                    severity=0.8,
                    source="system",
                    description="Квантовое поле неактивно"
                )
            
            # Проверка энергетической матрицы
            if self.quantum_field.energy_matrix is None:
                self._detect_anomaly(
                    anomaly_type="energy_matrix_missing",
                    severity=0.7,
                    source="system",
                    description="Энергетическая матрица отсутствует"
                )
            
            # Проверка связей между участниками
            connections = self.quantum_field.connections
            if connections:
                unstable_connections = []
                for conn_id, connection in connections.items():
                    if connection.stability < 0.3:
                        unstable_connections.append(conn_id)
                
                if unstable_connections:
                    self._detect_anomaly(
                        anomaly_type="unstable_connections",
                        severity=0.6,
                        source="system",
                        description=f"Обнаружены нестабильные связи: {len(unstable_connections)}"
                    )
            
        except Exception as e:
            error_msg = f"Ошибка при проверке целостности квантового поля: {str(e)}"
            self.logger.error(error_msg)
    
    def _check_safety_system_integrity(self) -> None:
        """Проверка целостности системы безопасности."""
        try:
            # Получение статуса системы безопасности
            security_status = self.safety_system.get_security_report()
            
            # Проверка здоровья системы
            system_health = security_status.get("system_health", 0.0)
            if system_health < 0.6:
                self._detect_anomaly(
                    anomaly_type="low_security_health",
                    severity=0.7,
                    source="system",
                    description=f"Низкое здоровье системы безопасности: {system_health}"
                )
            
            # Проверка активных угроз
            active_threats = security_status.get("active_threats", 0)
            if active_threats > 5:
                self._detect_anomaly(
                    anomaly_type="high_threat_count",
                    severity=0.8,
                    source="system",
                    description=f"Высокое количество активных угроз: {active_threats}"
                )
            
            # Проверка защитных колец
            protection_status = security_status.get("protection_status", {})
            active_rings = protection_status.get("active_rings", 0)
            if active_rings < 2:
                self._detect_anomaly(
                    anomaly_type="insufficient_protection_rings",
                    severity=0.6,
                    source="system",
                    description=f"Недостаточно активных защитных колец: {active_rings}"
                )
            
        except Exception as e:
            error_msg = f"Ошибка при проверке целостности системы безопасности: {str(e)}"
            self.logger.error(error_msg)
    
    # Методы детекции аномалий
    
    def _detect_anomaly(self, anomaly_type: str, severity: float, source: str, 
                        description: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Обнаружение аномалии в системе."""
        try:
            anomaly = AnomalyDetection(
                anomaly_type=anomaly_type,
                severity=severity,
                source=source,
                description=description,
                context=context or {}
            )
            
            self.anomalies_detected.append(anomaly)
            self.anomalies_found += 1
            
            # Ограничение истории последними 500 аномалий
            if len(self.anomalies_detected) > 500:
                self.anomalies_detected = self.anomalies_detected[-500:]
            
            # Логирование аномалии
            self.logger.warning(f"Обнаружена аномалия: {description} (серьезность: {severity})")
            
            # Автоматическая реакция на аномалию
            self._handle_anomaly(anomaly)
            
        except Exception as e:
            error_msg = f"Ошибка при обнаружении аномалии: {str(e)}"
            self.logger.error(error_msg)
    
    # Методы автоматических защитных реакций
    
    def _handle_integrity_violation(self, integrity_check: IntegrityCheck) -> None:
        """Обработка нарушения целостности участника."""
        try:
            participant_id = integrity_check.participant_id
            violations = integrity_check.violations_detected
            
            self.logger.warning(f"Нарушение целостности участника {participant_id}: {violations}")
            
            # Автоматическое восстановление при критических нарушениях
            if integrity_check.integrity_score < 0.5:
                self._auto_repair_participant(participant_id, violations)
            
            # Уведомление системы безопасности
            self._notify_safety_system(integrity_check)
            
        except Exception as e:
            error_msg = f"Ошибка при обработке нарушения целостности: {str(e)}"
            self.logger.error(error_msg)
    
    def _handle_anomaly(self, anomaly: AnomalyDetection) -> None:
        """Обработка обнаруженной аномалии."""
        try:
            self.logger.warning(f"Обработка аномалии: {anomaly.description}")
            
            # Автоматические реакции на основе типа аномалии
            if anomaly.anomaly_type == "field_inactive":
                self._reactivate_quantum_field()
            elif anomaly.anomaly_type == "low_security_health":
                self._enhance_security_protection()
            elif anomaly.anomaly_type == "high_threat_count":
                self._escalate_security_response()
            
            # Уведомление системы безопасности
            self._notify_safety_system_anomaly(anomaly)
            
        except Exception as e:
            error_msg = f"Ошибка при обработке аномалии: {str(e)}"
            self.logger.error(error_msg)
    
    def _auto_repair_participant(self, participant_id: str, violations: List[str]) -> None:
        """Автоматическое восстановление участника."""
        try:
            participant = self.participant_manager.get_participant(participant_id)
            if not participant:
                return
            
            self.logger.info(f"Автоматическое восстановление участника {participant_id}")
            
            # Восстановление критических параметров
            quantum_state = participant.quantum_state
            
            if "critical_energy_depletion" in violations:
                quantum_state.energy_level = max(0.5, quantum_state.energy_level + 0.3)
            
            if "critical_protection_weakness" in violations:
                quantum_state.protection = max(0.4, quantum_state.protection + 0.2)
            
            # Нормализация состояний
            quantum_state.energy_level = min(2.0, max(0.0, quantum_state.energy_level))
            quantum_state.clarity = min(1.0, max(0.0, quantum_state.clarity))
            quantum_state.protection = min(1.0, max(0.0, quantum_state.protection))
            quantum_state.alignment = min(1.0, max(0.0, quantum_state.alignment))
            
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
            
            self.logger.info(f"Участник {participant_id} автоматически восстановлен")
            
        except Exception as e:
            error_msg = f"Ошибка при автоматическом восстановлении участника: {str(e)}"
            self.logger.error(error_msg)
    
    def _reactivate_quantum_field(self) -> None:
        """Реактивация квантового поля."""
        try:
            self.logger.info("Попытка реактивации квантового поля")
            
            # Переинициализация поля
            if self.quantum_field.initialize_field():
                self.logger.info("Квантовое поле успешно реактивировано")
            else:
                self.logger.error("Не удалось реактивировать квантовое поле")
                
        except Exception as e:
            error_msg = f"Ошибка при реактивации квантового поля: {str(e)}"
            self.logger.error(error_msg)
    
    def _enhance_security_protection(self) -> None:
        """Усиление защиты безопасности."""
        try:
            self.logger.info("Усиление защиты безопасности")
            
            # Создание дополнительного защитного кольца
            enhanced_ring = self.safety_system.create_protection_ring(
                ring_type="monitoring_enhanced",
                protection_levels={
                    "emotional_protection": 0.9,
                    "mental_protection": 0.9,
                    "energetic_protection": 0.9
                },
                metadata={"purpose": "monitoring_response", "auto_created": True}
            )
            
            self.logger.info(f"Создано усиленное защитное кольцо: {enhanced_ring}")
            
        except Exception as e:
            error_msg = f"Ошибка при усилении защиты безопасности: {str(e)}"
            self.logger.error(error_msg)
    
    def _escalate_security_response(self) -> None:
        """Эскалация ответа безопасности."""
        try:
            self.logger.warning("Эскалация ответа безопасности")
            
            # Активация всех доступных защитных колец
            for ring_id in self.safety_system.protection_rings:
                if not self.safety_system.protection_rings[ring_id].is_active:
                    self.safety_system.activate_protection_ring(ring_id)
            
            # Создание экстренного защитного кольца
            emergency_ring = self.safety_system.create_protection_ring(
                ring_type="emergency_response",
                protection_levels={
                    "emotional_protection": 1.0,
                    "mental_protection": 1.0,
                    "energetic_protection": 1.0
                },
                metadata={"purpose": "emergency_response", "auto_created": True}
            )
            
            self.logger.info(f"Создано экстренное защитное кольцо: {emergency_ring}")
            
        except Exception as e:
            error_msg = f"Ошибка при эскалации ответа безопасности: {str(e)}"
            self.logger.error(error_msg)
    
    def _notify_safety_system(self, integrity_check: IntegrityCheck) -> None:
        """Уведомление системы безопасности о нарушении целостности."""
        try:
            # Регистрация события в системе безопасности
            self.safety_system._log_security_event(
                event_type="integrity_violation_detected",
                severity=1.0 - integrity_check.integrity_score,
                source="monitor",
                target=integrity_check.participant_id,
                description=f"Нарушение целостности: {integrity_check.violations_detected}",
                outcome="detected",
                metadata={
                    "check_id": integrity_check.check_id,
                    "integrity_score": integrity_check.integrity_score,
                    "violations": integrity_check.violations_detected
                }
            )
            
        except Exception as e:
            error_msg = f"Ошибка при уведомлении системы безопасности: {str(e)}"
            self.logger.error(error_msg)
    
    def _notify_safety_system_anomaly(self, anomaly: AnomalyDetection) -> None:
        """Уведомление системы безопасности об аномалии."""
        try:
            # Регистрация события в системе безопасности
            self.safety_system._log_security_event(
                event_type="anomaly_detected",
                severity=anomaly.severity,
                source="monitor",
                target=anomaly.source,
                description=f"Аномалия: {anomaly.description}",
                outcome="detected",
                metadata={
                    "anomaly_id": anomaly.anomaly_id,
                    "anomaly_type": anomaly.anomaly_type,
                    "context": anomaly.context
                }
            )
            
        except Exception as e:
            error_msg = f"Ошибка при уведомлении системы безопасности об аномалии: {str(e)}"
            self.logger.error(error_msg)
    
    # Методы генерации отчетов безопасности
    
    def generate_security_report(self, report_type: str = "current") -> SecurityReport:
        """
        Генерация отчета о безопасности.
        
        Args:
            report_type: Тип отчета (current, hourly, daily, weekly)
            
        Returns:
            SecurityReport: Сгенерированный отчет
        """
        try:
            # Получение текущих данных
            all_participants = list(self.participant_manager.participants.keys())
            current_time = datetime.now()
            
            # Анализ последних проверок целостности
            recent_checks = [check for check in self.integrity_checks 
                           if (current_time - check.timestamp).seconds < 3600]
            
            integrity_violations = len([check for check in recent_checks 
                                     if not check.is_integrity_maintained])
            
            # Анализ последних аномалий
            recent_anomalies = [anomaly for anomaly in self.anomalies_detected 
                              if (current_time - anomaly.timestamp).seconds < 3600]
            
            # Получение статистики безопасности
            security_status = self.safety_system.get_security_report()
            
            # Генерация рекомендаций
            recommendations = self._generate_recommendations(
                integrity_violations, recent_anomalies, security_status
            )
            
            # Создание отчета
            report = SecurityReport(
                report_period=report_type,
                total_participants=len(all_participants),
                participants_monitored=len(all_participants),
                integrity_violations=integrity_violations,
                anomalies_detected=len(recent_anomalies),
                threats_blocked=security_status.get("threats_blocked", 0),
                integrity_summary={
                    "total_checks": len(recent_checks),
                    "violations_rate": integrity_violations / len(recent_checks) if recent_checks else 0.0,
                    "average_integrity_score": np.mean([check.integrity_score for check in recent_checks]) if recent_checks else 1.0
                },
                anomaly_summary={
                    "total_anomalies": len(recent_anomalies),
                    "severity_distribution": self._analyze_anomaly_severity(recent_anomalies),
                    "type_distribution": self._analyze_anomaly_types(recent_anomalies)
                },
                threat_summary=security_status,
                recommendations=recommendations,
                metadata={
                    "generated_by": "SecurityMonitor",
                    "monitoring_active": self.is_monitoring_active,
                    "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None
                }
            )
            
            self.last_report_generated = current_time
            
            self.logger.info(f"Отчет о безопасности сгенерирован: {report_type}")
            return report
            
        except Exception as e:
            error_msg = f"Ошибка при генерации отчета о безопасности: {str(e)}"
            self.logger.error(error_msg)
            raise MonitoringError(error_msg) from e
    
    def _generate_recommendations(self, integrity_violations: int, 
                                recent_anomalies: List[AnomalyDetection],
                                security_status: Dict[str, Any]) -> List[str]:
        """Генерация рекомендаций по безопасности."""
        recommendations = []
        
        # Рекомендации по целостности
        if integrity_violations > 5:
            recommendations.append("Критический уровень нарушений целостности - требуется немедленное вмешательство")
        elif integrity_violations > 2:
            recommendations.append("Повышенный уровень нарушений целостности - рекомендуется усилить мониторинг")
        
        # Рекомендации по аномалиям
        high_severity_anomalies = [a for a in recent_anomalies if a.severity > 0.7]
        if high_severity_anomalies:
            recommendations.append(f"Обнаружены {len(high_severity_anomalies)} высокоуровневых аномалий - активировать экстренную защиту")
        
        # Рекомендации по безопасности
        system_health = security_status.get("system_health", 1.0)
        if system_health < 0.6:
            recommendations.append("Низкое здоровье системы безопасности - требуется диагностика и восстановление")
        
        # Общие рекомендации
        if not recommendations:
            recommendations.append("Система безопасности функционирует нормально")
        
        return recommendations
    
    def _analyze_anomaly_severity(self, anomalies: List[AnomalyDetection]) -> Dict[str, int]:
        """Анализ распределения серьезности аномалий."""
        severity_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        for anomaly in anomalies:
            if anomaly.severity <= 0.3:
                severity_distribution["low"] += 1
            elif anomaly.severity <= 0.6:
                severity_distribution["medium"] += 1
            elif anomaly.severity <= 0.8:
                severity_distribution["high"] += 1
            else:
                severity_distribution["critical"] += 1
        
        return severity_distribution
    
    def _analyze_anomaly_types(self, anomalies: List[AnomalyDetection]) -> Dict[str, int]:
        """Анализ распределения типов аномалий."""
        type_distribution = {}
        
        for anomaly in anomalies:
            anomaly_type = anomaly.anomaly_type
            type_distribution[anomaly_type] = type_distribution.get(anomaly_type, 0) + 1
        
        return type_distribution
    
    # Дополнительные методы мониторинга
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Получение статуса системы мониторинга."""
        return {
            "is_active": self.is_monitoring_active,
            "monitoring_interval": self.monitoring_interval,
            "total_checks_performed": self.total_checks_performed,
            "violations_found": self.violations_found,
            "anomalies_found": self.anomalies_found,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "last_report_generated": self.last_report_generated.isoformat() if self.last_report_generated else None,
            "monitoring_thread_alive": self.monitoring_thread.is_alive() if self.monitoring_thread else False
        }
    
    def get_recent_integrity_checks(self, limit: int = 100) -> List[IntegrityCheck]:
        """Получение последних проверок целостности."""
        return self.integrity_checks[-limit:] if self.integrity_checks else []
    
    def get_recent_anomalies(self, limit: int = 100) -> List[AnomalyDetection]:
        """Получение последних аномалий."""
        return self.anomalies_detected[-limit:] if self.anomalies_detected else []
    
    def __str__(self) -> str:
        return f"SecurityMonitor(active={self.is_monitoring_active}, checks={self.total_checks_performed})"
    
    def __repr__(self) -> str:
        return f"SecurityMonitor(safety_system={'set' if self.safety_system else 'not_set'}, participant_manager={'set' if self.participant_manager else 'not_set'})"
