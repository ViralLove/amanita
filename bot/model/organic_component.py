from typing import Dict, Optional
from dataclasses import dataclass
import re
from bot.validation import ValidationFactory, ValidationResult


@dataclass
class OrganicComponent:
    """
    Структура для хранения информации о компоненте многокомпонентного продукта.
    
    Attributes:
        biounit_id (str): Уникальный идентификатор биологической единицы
        description_cid (str): CID описания биоединицы в IPFS
        proportion (str): Пропорция компонента (например, "50%", "100g", "30ml")
    """
    biounit_id: str
    description_cid: str
    proportion: str

    def __post_init__(self):
        """
        Валидация данных после инициализации dataclass.
        Использует единую систему валидации из ValidationFactory.
        
        Raises:
            ValueError: Если валидация не прошла
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 OrganicComponent.__post_init__: начинаем валидацию")
        logger.info(f"📋 Данные для валидации: biounit_id='{self.biounit_id}', description_cid='{self.description_cid}', proportion='{self.proportion}'")
        
        # Получаем валидаторы из фабрики
        logger.info("🔧 Получаем валидаторы из ValidationFactory...")
        cid_validator = ValidationFactory.get_cid_validator()
        proportion_validator = ValidationFactory.get_proportion_validator()
        logger.info(f"✅ Валидаторы получены: CID={type(cid_validator).__name__}, Proportion={type(proportion_validator).__name__}")
        
        # Валидация biounit_id
        logger.info(f"🔍 Валидируем biounit_id: '{self.biounit_id}'")
        if not self.biounit_id or not self.biounit_id.strip():
            raise ValueError("biounit_id не может быть пустым")
        
        # Проверка формата biounit_id (должен содержать только буквы, цифры и подчеркивания)
        biounit_pattern = r'^[a-zA-Z0-9_]+$'
        if not re.match(biounit_pattern, self.biounit_id):
            raise ValueError(f"biounit_id '{self.biounit_id}' содержит недопустимые символы. Разрешены только буквы, цифры и подчеркивания")
        
        # Проверка длины biounit_id (от 1 до 50 символов)
        if len(self.biounit_id) > 50:
            raise ValueError(f"biounit_id '{self.biounit_id}' слишком длинный. Максимальная длина: 50 символов")
        logger.info(f"✅ biounit_id валидирован успешно")
        
        # Валидация description_cid с использованием единого валидатора
        logger.info(f"🔍 Валидируем description_cid: '{self.description_cid}'")
        logger.info(f"🔧 Вызываем cid_validator.validate('{self.description_cid}')...")
        cid_result = cid_validator.validate(self.description_cid)
        logger.info(f"📋 Результат валидации CID: {cid_result}")
        if not cid_result.is_valid:
            logger.error(f"❌ Валидация description_cid не прошла: {cid_result.error_message}")
            raise ValueError(f"description_cid: {cid_result.error_message}")
        logger.info(f"✅ description_cid валидирован успешно")
        
        # Валидация proportion с использованием единого валидатора
        logger.info(f"🔍 Валидируем proportion: '{self.proportion}'")
        proportion_result = proportion_validator.validate(self.proportion)
        if not proportion_result.is_valid:
            raise ValueError(f"proportion: {proportion_result.error_message}")
        logger.info(f"✅ proportion валидирован успешно")
        
        logger.info(f"🎉 Все валидации прошли успешно!")

    # Устаревшие методы валидации удалены - теперь используется единая система валидации

    def validate_proportion(self) -> bool:
        """
        Валидация корректности пропорции с использованием единого валидатора.
        
        Returns:
            bool: True если пропорция корректна, False если нет
        """
        try:
            proportion_validator = ValidationFactory.get_proportion_validator()
            result = proportion_validator.validate(self.proportion)
            return result.is_valid
        except Exception:
            return False

    def get_proportion_value(self) -> float:
        """
        Получает числовое значение пропорции.
        
        Returns:
            float: Числовое значение пропорции
            
        Raises:
            ValueError: Если не удается извлечь числовое значение
        """
        match = re.match(r'^(\d+(?:\.\d+)?)', self.proportion)
        if not match:
            raise ValueError(f"Не удается извлечь числовое значение из пропорции: {self.proportion}")
        
        return float(match.group(1))

    def get_proportion_unit(self) -> str:
        """
        Получает единицу измерения пропорции.
        
        Returns:
            str: Единица измерения (%, g, ml, kg, l, oz, lb, fl_oz)
            
        Raises:
            ValueError: Если не удается извлечь единицу измерения
        """
        match = re.match(r'^(\d+(?:\.\d+)?)(%|g|ml|kg|l|oz|lb|fl_oz)$', self.proportion)
        if not match:
            raise ValueError(f"Не удается извлечь единицу измерения из пропорции: {self.proportion}")
        
        return match.group(2)

    def is_percentage(self) -> bool:
        """
        Проверяет, является ли пропорция процентной.
        
        Returns:
            bool: True если пропорция в процентах, False если нет
        """
        return self.proportion.endswith('%')

    def is_weight_based(self) -> bool:
        """
        Проверяет, является ли пропорция весовой.
        
        Returns:
            bool: True если пропорция весовая, False если нет
        """
        weight_units = ['g', 'kg', 'oz', 'lb']
        return any(self.proportion.endswith(unit) for unit in weight_units)

    def is_volume_based(self) -> bool:
        """
        Проверяет, является ли пропорция объемной.
        
        Returns:
            bool: True если пропорция объемная, False если нет
        """
        volume_units = ['ml', 'l', 'fl_oz']
        return any(self.proportion.endswith(unit) for unit in volume_units)

    @classmethod
    def from_dict(cls, data: dict) -> "OrganicComponent":
        """
        Создает объект OrganicComponent из словаря.
        
        Args:
            data: Словарь с данными компонента
            
        Returns:
            OrganicComponent: Новый объект
            
        Raises:
            ValueError: Если отсутствуют обязательные поля или данные некорректны
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 OrganicComponent.from_dict: начинаем создание компонента")
        logger.info(f"📋 Входные данные: {data}")
        
        if not isinstance(data, dict):
            raise ValueError("Входные данные должны быть словарем")
        
        # Проверяем обязательные поля
        required_fields = ['biounit_id', 'description_cid', 'proportion']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
            logger.info(f"  ✅ Поле '{field}' = '{data[field]}'")
        
        logger.info(f"🏗️ Создаем OrganicComponent объект...")
        component = cls(
            biounit_id=str(data['biounit_id']).strip(),
            description_cid=str(data['description_cid']).strip(),
            proportion=str(data['proportion']).strip()
        )
        logger.info(f"✅ OrganicComponent объект создан: biounit_id='{component.biounit_id}', description_cid='{component.description_cid}', proportion='{component.proportion}'")
        
        return component

    def to_dict(self) -> Dict:
        """
        Преобразует объект в словарь.
        
        Returns:
            Dict: Словарь с данными компонента
        """
        return {
            "biounit_id": self.biounit_id,
            "description_cid": self.description_cid,
            "proportion": self.proportion
        }

    def __repr__(self) -> str:
        """Строковое представление объекта"""
        return f"OrganicComponent(biounit_id='{self.biounit_id}', proportion='{self.proportion}')"

    def __eq__(self, other) -> bool:
        """Сравнение объектов по содержимому"""
        if not isinstance(other, OrganicComponent):
            return False
        
        return (
            self.biounit_id == other.biounit_id and
            self.description_cid == other.description_cid and
            self.proportion == other.proportion
        )

    def __hash__(self) -> int:
        """Хеш объекта для использования в множествах"""
        return hash((self.biounit_id, self.description_cid, self.proportion))
