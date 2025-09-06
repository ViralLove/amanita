"""
Миксин для валидации данных в обработчиках каталога.
Содержит логику валидации callback данных, прав пользователя и ID продуктов.
"""

import logging
import re
from typing import Optional, Dict, Any, List, Callable
from aiogram.types import CallbackQuery
from services.common.localization import Localization

logger = logging.getLogger(__name__)


class ValidationMixin:
    """Миксин для валидации данных в обработчиках каталога"""
    
    def __init__(self):
        """Инициализация миксина валидации"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.custom_validators: Dict[str, Callable] = {}
        self.logger.info(f"[{self.__class__.__name__}] ValidationMixin инициализирован")
    
    def validate_callback_data(self, callback: CallbackQuery, expected_patterns: List[str]) -> bool:
        """
        Валидирует данные callback
        
        Args:
            callback: Callback запрос от пользователя
            expected_patterns: Список ожидаемых паттернов
            
        Returns:
            bool: True если данные валидны
        """
        try:
            data = callback.data
            if not data:
                self.logger.warning(f"[{self.__class__.__name__}] Пустые данные callback")
                return False
            
            # Проверяем соответствие хотя бы одному паттерну
            for pattern in expected_patterns:
                if re.match(pattern, data):
                    self.logger.debug(f"[{self.__class__.__name__}] Данные callback валидны: {data} соответствует паттерну {pattern}")
                    return True
            
            self.logger.warning(f"[{self.__class__.__name__}] Данные callback не соответствуют ожидаемым паттернам: {data}")
            return False
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка валидации данных callback: {e}")
            return False
    
    def validate_user_permissions(self, callback: CallbackQuery, required_permissions: List[str]) -> bool:
        """
        Проверяет права пользователя
        
        Args:
            callback: Callback запрос от пользователя
            required_permissions: Список требуемых прав
            
        Returns:
            bool: True если у пользователя есть все права
        """
        try:
            user_id = callback.from_user.id
            
            # TODO: Интегрировать с системой прав пользователей
            # Пока что возвращаем True для всех пользователей
            # В будущем здесь будет проверка реальных прав
            
            self.logger.debug(f"[{self.__class__.__name__}] Проверка прав пользователя {user_id}: {required_permissions}")
            
            # Базовая проверка - пользователь должен быть авторизован
            if not user_id:
                self.logger.warning(f"[{self.__class__.__name__}] Пользователь не авторизован")
                return False
            
            # TODO: Добавить реальную проверку прав
            # Например, проверка роли пользователя, блокировки и т.д.
            
            self.logger.debug(f"[{self.__class__.__name__}] Права пользователя {user_id} валидны")
            return True
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка проверки прав пользователя: {e}")
            return False
    
    def validate_product_id(self, product_id: str) -> bool:
        """
        Валидирует ID продукта
        
        Args:
            product_id: ID продукта для валидации
            
        Returns:
            bool: True если ID валиден
        """
        try:
            if not product_id:
                self.logger.warning(f"[{self.__class__.__name__}] Пустой ID продукта")
                return False
            
            if not isinstance(product_id, str):
                self.logger.warning(f"[{self.__class__.__name__}] ID продукта должен быть строкой: {type(product_id)}")
                return False
            
            if len(product_id.strip()) == 0:
                self.logger.warning(f"[{self.__class__.__name__}] ID продукта не может быть пустой строкой")
                return False
            
            # Проверяем, что ID содержит только допустимые символы
            if not re.match(r'^[a-zA-Z0-9_-]+$', product_id):
                self.logger.warning(f"[{self.__class__.__name__}] ID продукта содержит недопустимые символы: {product_id}")
                return False
            
            # Проверяем длину ID
            if len(product_id) > 100:
                self.logger.warning(f"[{self.__class__.__name__}] ID продукта слишком длинный: {len(product_id)}")
                return False
            
            self.logger.debug(f"[{self.__class__.__name__}] ID продукта валиден: {product_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка валидации ID продукта: {e}")
            return False
    
    def validate_user_id(self, user_id: int) -> bool:
        """
        Валидирует ID пользователя
        
        Args:
            user_id: ID пользователя для валидации
            
        Returns:
            bool: True если ID валиден
        """
        try:
            if not user_id:
                self.logger.warning(f"[{self.__class__.__name__}] Пустой ID пользователя")
                return False
            
            if not isinstance(user_id, int):
                self.logger.warning(f"[{self.__class__.__name__}] ID пользователя должен быть числом: {type(user_id)}")
                return False
            
            if user_id <= 0:
                self.logger.warning(f"[{self.__class__.__name__}] ID пользователя должен быть положительным: {user_id}")
                return False
            
            self.logger.debug(f"[{self.__class__.__name__}] ID пользователя валиден: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка валидации ID пользователя: {e}")
            return False
    
    def validate_language_code(self, language: str) -> bool:
        """
        Валидирует код языка
        
        Args:
            language: Код языка для валидации
            
        Returns:
            bool: True если код языка валиден
        """
        try:
            if not language:
                self.logger.warning(f"[{self.__class__.__name__}] Пустой код языка")
                return False
            
            if not isinstance(language, str):
                self.logger.warning(f"[{self.__class__.__name__}] Код языка должен быть строкой: {type(language)}")
                return False
            
            # Проверяем формат кода языка (2 символа)
            if not re.match(r'^[a-z]{2}$', language):
                self.logger.warning(f"[{self.__class__.__name__}] Неверный формат кода языка: {language}")
                return False
            
            # Список поддерживаемых языков
            supported_languages = ["ru", "en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko"]
            if language not in supported_languages:
                self.logger.warning(f"[{self.__class__.__name__}] Неподдерживаемый язык: {language}")
                return False
            
            self.logger.debug(f"[{self.__class__.__name__}] Код языка валиден: {language}")
            return True
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка валидации кода языка: {e}")
            return False
    
    def register_custom_validator(self, name: str, validator_func: Callable) -> None:
        """
        Регистрирует кастомный валидатор
        
        Args:
            name: Название валидатора
            validator_func: Функция валидации
        """
        try:
            self.custom_validators[name] = validator_func
            self.logger.info(f"[{self.__class__.__name__}] Зарегистрирован кастомный валидатор: {name}")
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка регистрации кастомного валидатора: {e}")
    
    def validate_with_custom_validator(self, name: str, data: Any) -> bool:
        """
        Валидирует данные с использованием кастомного валидатора
        
        Args:
            name: Название валидатора
            data: Данные для валидации
            
        Returns:
            bool: True если данные валидны
        """
        try:
            if name not in self.custom_validators:
                self.logger.warning(f"[{self.__class__.__name__}] Кастомный валидатор не найден: {name}")
                return False
            
            validator_func = self.custom_validators[name]
            result = validator_func(data)
            
            self.logger.debug(f"[{self.__class__.__name__}] Кастомный валидатор {name} вернул: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка выполнения кастомного валидатора: {e}")
            return False
    
    def validate_all(self, callback: CallbackQuery, validations: Dict[str, Any]) -> Dict[str, bool]:
        """
        Выполняет все валидации и возвращает результаты
        
        Args:
            callback: Callback запрос от пользователя
            validations: Словарь с валидациями для выполнения
            
        Returns:
            Dict[str, bool]: Результаты валидаций
        """
        try:
            results = {}
            
            for validation_name, validation_data in validations.items():
                if validation_name == "callback_data":
                    results[validation_name] = self.validate_callback_data(
                        callback, validation_data.get("patterns", [])
                    )
                elif validation_name == "user_permissions":
                    results[validation_name] = self.validate_user_permissions(
                        callback, validation_data.get("permissions", [])
                    )
                elif validation_name == "product_id":
                    results[validation_name] = self.validate_product_id(validation_data)
                elif validation_name == "user_id":
                    results[validation_name] = self.validate_user_id(validation_data)
                elif validation_name == "language":
                    results[validation_name] = self.validate_language_code(validation_data)
                elif validation_name.startswith("custom_"):
                    validator_name = validation_name[7:]  # Убираем префикс "custom_"
                    results[validation_name] = self.validate_with_custom_validator(
                        validator_name, validation_data
                    )
                else:
                    self.logger.warning(f"[{self.__class__.__name__}] Неизвестный тип валидации: {validation_name}")
                    results[validation_name] = False
            
            self.logger.debug(f"[{self.__class__.__name__}] Результаты валидаций: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка выполнения валидаций: {e}")
            return {}
    
    def get_validation_errors(self, results: Dict[str, bool]) -> List[str]:
        """
        Возвращает список ошибок валидации
        
        Args:
            results: Результаты валидаций
            
        Returns:
            List[str]: Список ошибок валидации
        """
        try:
            errors = []
            for validation_name, is_valid in results.items():
                if not is_valid:
                    errors.append(f"Валидация {validation_name} не прошла")
            
            if errors:
                self.logger.warning(f"[{self.__class__.__name__}] Найдены ошибки валидации: {errors}")
            
            return errors
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка получения ошибок валидации: {e}")
            return []
