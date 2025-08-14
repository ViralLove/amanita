from typing import Dict, Optional
from dataclasses import dataclass
import re


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
        """Валидация данных после инициализации"""
        self._validate_fields()
        self._validate_proportion_format()

    def _validate_fields(self):
        """Валидация обязательных полей"""
        if not self.biounit_id or not self.biounit_id.strip():
            raise ValueError("biounit_id не может быть пустым")
        
        if not self.description_cid or not self.description_cid.strip():
            raise ValueError("description_cid не может быть пустым")
        
        if not self.proportion or not self.proportion.strip():
            raise ValueError("proportion не может быть пустым")

    def _validate_proportion_format(self):
        """Валидация формата пропорции"""
        # Поддерживаемые форматы: "50%", "100g", "30ml", "25%"
        proportion_pattern = r'^(\d+(?:\.\d+)?)(%|g|ml|kg|l|oz|lb|fl_oz)$'
        
        if not re.match(proportion_pattern, self.proportion):
            raise ValueError(
                f"Некорректный формат пропорции: {self.proportion}. "
                f"Поддерживаемые форматы: 50%, 100g, 30ml, 25%"
            )

    def validate_proportion(self) -> bool:
        """
        Валидация корректности пропорции.
        
        Returns:
            bool: True если пропорция корректна, False если нет
        """
        try:
            self._validate_proportion_format()
            return True
        except ValueError:
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
        if not isinstance(data, dict):
            raise ValueError("Входные данные должны быть словарем")
        
        # Проверяем обязательные поля
        required_fields = ['biounit_id', 'description_cid', 'proportion']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        return cls(
            biounit_id=str(data['biounit_id']).strip(),
            description_cid=str(data['description_cid']).strip(),
            proportion=str(data['proportion']).strip()
        )

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
