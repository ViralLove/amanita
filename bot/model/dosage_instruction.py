from typing import Dict
from dataclasses import dataclass


@dataclass
class DosageInstruction:
    """
    Структура для хранения информации об инструкциях по дозировке.
    
    Attributes:
        type (str): Тип дозировки (например, "dried", "tincture")
        title (str): Заголовок инструкции
        description (str): Подробное описание дозировки
    """
    type: str
    title: str
    description: str

    @classmethod
    def from_dict(cls, data: dict) -> "DosageInstruction":
        """
        Создает объект DosageInstruction из словаря.
        
        Args:
            data: Словарь с данными инструкции
            
        Returns:
            DosageInstruction: Новый объект
            
        Raises:
            ValueError: Если отсутствуют обязательные поля
        """
        if not isinstance(data, dict):
            raise ValueError("Входные данные должны быть словарем")
            
        if 'type' not in data:
            raise ValueError("Отсутствует обязательное поле 'type'")
            
        return cls(
            type=data.get("type", ""),
            title=data.get("title", ""),
            description=data.get("description", "")
        )
    
    def to_dict(self) -> Dict:
        """
        Преобразует объект в словарь.
        
        Returns:
            Dict: Словарь с данными инструкции
        """
        return {
            "type": self.type,
            "title": self.title,
            "description": self.description
        }
