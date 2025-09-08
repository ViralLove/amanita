"""
Загрузчик протокола SIRIUS-FELINE_BRANCH_PROTOCOL.
Обеспечивает загрузку, парсинг и базовую валидацию конфигурации протокола.
"""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging


class ProtocolLoadError(Exception):
    """Исключение для ошибок загрузки протокола."""
    pass


class ProtocolValidationError(Exception):
    """Исключение для ошибок валидации протокола."""
    pass


class ProtocolLoader:
    """Загрузчик и парсер конфигурации протокола."""
    
    def __init__(self, log_level: int = logging.INFO):
        """Инициализация загрузчика протокола."""
        self.logger = self._setup_logger(log_level)
        self.protocol_data: Optional[Dict[str, Any]] = None
        self.loaded_file_path: Optional[str] = None
        
        # Обязательные поля протокола
        self.required_fields = [
            "protocol",
            "participants", 
            "prime_directives",
            "consent_model",
            "protection",
            "operations",
            "update_loop",
            "success_criteria",
            "boundaries",
            "interfaces",
            "logging",
            "rollback_exit",
            "activation"
        ]
        
        # Обязательные подполя для основных разделов
        self.required_subfields = {
            "protocol": ["name", "version", "scope", "intent"],
            "participants": ["initiator", "family"],
            "prime_directives": ["PD1", "PD2", "PD3", "PD4"],
            "operations": ["OP1", "OP2", "OP3", "OP4"]
        }
    
    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Настройка логгера для загрузчика протокола."""
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
    
    def load_protocol(self, file_path: str) -> Dict[str, Any]:
        """
        Загрузка протокола из JSON файла.
        
        Args:
            file_path: Путь к JSON файлу протокола
            
        Returns:
            Dict[str, Any]: Загруженные данные протокола
            
        Raises:
            ProtocolLoadError: При ошибках загрузки файла
            ProtocolValidationError: При ошибках валидации
        """
        self.logger.info(f"Начинаю загрузку протокола из файла: {file_path}")
        
        try:
            # Проверка существования файла
            if not os.path.exists(file_path):
                raise ProtocolLoadError(f"Файл протокола не найден: {file_path}")
            
            # Проверка расширения файла
            if not file_path.lower().endswith('.json'):
                raise ProtocolLoadError(f"Файл должен иметь расширение .json: {file_path}")
            
            # Чтение и парсинг JSON
            with open(file_path, 'r', encoding='utf-8') as file:
                self.logger.debug("Читаю содержимое JSON файла")
                content = file.read()
                
                if not content.strip():
                    raise ProtocolLoadError("JSON файл пуст")
                
                self.logger.debug("Парсинг JSON содержимого")
                self.protocol_data = json.loads(content)
            
            self.loaded_file_path = file_path
            self.logger.info(f"Протокол успешно загружен из файла: {file_path}")
            
            # Базовая валидация загруженных данных
            self._validate_loaded_data()
            
            return self.protocol_data
            
        except json.JSONDecodeError as e:
            error_msg = f"Ошибка парсинга JSON в файле {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ProtocolLoadError(error_msg) from e
            
        except UnicodeDecodeError as e:
            error_msg = f"Ошибка кодировки файла {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ProtocolLoadError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Неожиданная ошибка при загрузке протокола: {str(e)}"
            self.logger.error(error_msg)
            raise ProtocolLoadError(error_msg) from e
    
    def _validate_loaded_data(self) -> None:
        """Базовая валидация загруженных данных протокола."""
        self.logger.debug("Начинаю валидацию загруженных данных")
        
        if not isinstance(self.protocol_data, dict):
            raise ProtocolValidationError("Данные протокола должны быть словарем")
        
        # Проверка обязательных полей
        missing_fields = []
        for field in self.required_fields:
            if field not in self.protocol_data:
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f"Отсутствуют обязательные поля протокола: {missing_fields}"
            self.logger.error(error_msg)
            raise ProtocolValidationError(error_msg)
        
        # Проверка обязательных подполей
        for section, required_fields in self.required_subfields.items():
            if section in self.protocol_data:
                section_data = self.protocol_data[section]
                if isinstance(section_data, dict):
                    missing_subfields = []
                    for subfield in required_fields:
                        if subfield not in section_data:
                            missing_subfields.append(subfield)
                    
                    if missing_subfields:
                        error_msg = f"В разделе '{section}' отсутствуют обязательные поля: {missing_subfields}"
                        self.logger.error(error_msg)
                        raise ProtocolValidationError(error_msg)
        
        self.logger.info("Валидация загруженных данных завершена успешно")
    
    def get_protocol_info(self) -> Dict[str, Any]:
        """Получение основной информации о загруженном протоколе."""
        if not self.protocol_data:
            raise ProtocolLoadError("Протокол не загружен. Сначала вызовите load_protocol()")
        
        return {
            "name": self.protocol_data.get("protocol", {}).get("name", "Unknown"),
            "version": self.protocol_data.get("protocol", {}).get("version", "Unknown"),
            "scope": self.protocol_data.get("protocol", {}).get("scope", "Unknown"),
            "participants_count": len(self.protocol_data.get("participants", {}).get("family", {})),
            "operations_count": len(self.protocol_data.get("operations", {})),
            "loaded_from": self.loaded_file_path,
            "loaded_at": self._get_current_timestamp()
        }
    
    def get_participants(self) -> Dict[str, Any]:
        """Получение информации об участниках протокола."""
        if not self.protocol_data:
            raise ProtocolLoadError("Протокол не загружен. Сначала вызовите load_protocol()")
        
        return self.protocol_data.get("participants", {})
    
    def get_operations(self) -> Dict[str, Any]:
        """Получение операций протокола."""
        if not self.protocol_data:
            raise ProtocolLoadError("Протокол не загружен. Сначала вызовите load_protocol()")
        
        return self.protocol_data.get("operations", {})
    
    def get_safety_metrics(self) -> Dict[str, Any]:
        """Получение метрик безопасности протокола."""
        if not self.protocol_data:
            raise ProtocolLoadError("Протокол не загружен. Сначала вызовите load_protocol()")
        
        return self.protocol_data.get("protection", {})
    
    def _get_current_timestamp(self) -> str:
        """Получение текущего времени в строковом формате."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def reload_protocol(self) -> Dict[str, Any]:
        """Перезагрузка протокола из того же файла."""
        if not self.loaded_file_path:
            raise ProtocolLoadError("Нет загруженного файла для перезагрузки")
        
        self.logger.info(f"Перезагружаю протокол из файла: {self.loaded_file_path}")
        return self.load_protocol(self.loaded_file_path)
    
    def __str__(self) -> str:
        if self.protocol_data:
            return f"ProtocolLoader(loaded: {self.loaded_file_path}, protocol: {self.protocol_data.get('protocol', {}).get('name', 'Unknown')})"
        return "ProtocolLoader(not loaded)"
    
    def __repr__(self) -> str:
        return f"ProtocolLoader(loaded_file_path='{self.loaded_file_path}', protocol_data={'loaded' if self.protocol_data else 'not loaded'})"
