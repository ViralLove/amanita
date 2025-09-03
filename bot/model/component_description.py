from typing import Dict, Optional, List
from dataclasses import dataclass
from .dosage_instruction import DosageInstruction
from ..validation import ValidationFactory, ValidationResult


@dataclass
class ComponentDescription:
    """
    Структура для хранения расширенного описания компонента продукта.
    
    Attributes:
        generic_description (str): Общее описание компонента
        effects (Optional[str]): Описание эффектов и воздействия
        shamanic (Optional[str]): Шаманская перспектива и традиционное использование
        warnings (Optional[str]): Предупреждения и меры безопасности
        dosage_instructions (Optional[List[DosageInstruction]]): Инструкции по дозировке
        features (Optional[List[str]]): Особенности и характеристики компонента
    """
    generic_description: str
    effects: Optional[str] = None
    shamanic: Optional[str] = None
    warnings: Optional[str] = None
    dosage_instructions: Optional[List[DosageInstruction]] = None
    features: Optional[List[str]] = None

    def __post_init__(self):
        """
        Валидация данных после инициализации dataclass.
        Использует единую систему валидации из ValidationFactory.
        
        Raises:
            ValueError: Если валидация не прошла
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 ComponentDescription.__post_init__: начинаем валидацию")
        logger.info(f"📋 Данные для валидации: generic_description='{self.generic_description[:50]}...', effects={bool(self.effects)}, shamanic={bool(self.shamanic)}")
        
        # Валидация обязательного поля generic_description
        if not self.generic_description or not self.generic_description.strip():
            raise ValueError("generic_description не может быть пустым")
        
        # Валидация длины generic_description (от 10 до 1000 символов)
        if len(self.generic_description) < 10:
            raise ValueError(f"generic_description слишком короткий: {len(self.generic_description)} символов. Минимум: 10")
        if len(self.generic_description) > 1000:
            raise ValueError(f"generic_description слишком длинный: {len(self.generic_description)} символов. Максимум: 1000")
        
        # Валидация dosage_instructions если присутствуют
        if self.dosage_instructions is not None:
            if not isinstance(self.dosage_instructions, list):
                raise ValueError("dosage_instructions должен быть списком")
            for i, instruction in enumerate(self.dosage_instructions):
                if not isinstance(instruction, DosageInstruction):
                    raise ValueError(f"dosage_instructions[{i}] должен быть объектом DosageInstruction")
        
        # Валидация features если присутствуют
        if self.features is not None:
            if not isinstance(self.features, list):
                raise ValueError("features должен быть списком")
            for i, feature in enumerate(self.features):
                if not isinstance(feature, str) or not feature.strip():
                    raise ValueError(f"features[{i}] должен быть непустой строкой")
        
        logger.info(f"✅ ComponentDescription валидация прошла успешно")

    @classmethod
    def from_dict(cls, data: dict) -> "ComponentDescription":
        """
        Создает объект ComponentDescription из словаря.
        
        Args:
            data: Словарь с данными описания компонента
            
        Returns:
            ComponentDescription: Новый объект
            
        Raises:
            ValueError: Если отсутствуют обязательные поля или данные некорректны
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 ComponentDescription.from_dict: начинаем создание описания компонента")
        logger.info(f"📋 Входные данные: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        
        if not isinstance(data, dict):
            raise ValueError("Входные данные должны быть словарем")
        
        # Проверяем обязательное поле
        if 'generic_description' not in data:
            raise ValueError("Отсутствует обязательное поле 'generic_description'")
        
        # Преобразуем инструкции по дозировке если присутствуют
        dosage_instructions = None
        if 'dosage_instructions' in data and data['dosage_instructions']:
            if not isinstance(data['dosage_instructions'], list):
                raise ValueError("dosage_instructions должен быть списком")
            try:
                dosage_instructions = [
                    DosageInstruction.from_dict(instruction)
                    for instruction in data['dosage_instructions']
                ]
                logger.info(f"✅ Создано {len(dosage_instructions)} инструкций по дозировке")
            except Exception as e:
                logger.error(f"❌ Ошибка создания инструкций по дозировке: {e}")
                raise ValueError(f"Ошибка создания dosage_instructions: {e}")
        
        # Преобразуем features если присутствуют
        features = None
        if 'features' in data and data['features']:
            if not isinstance(data['features'], list):
                raise ValueError("features должен быть списком")
            features = [str(feature).strip() for feature in data['features'] if feature]
            logger.info(f"✅ Создано {len(features)} особенностей")
        
        logger.info(f"🏗️ Создаем ComponentDescription объект...")
        description = cls(
            generic_description=str(data['generic_description']).strip(),
            effects=data.get('effects'),
            shamanic=data.get('shamanic'),
            warnings=data.get('warnings'),
            dosage_instructions=dosage_instructions,
            features=features
        )
        
        logger.info(f"✅ ComponentDescription объект создан: generic_description='{description.generic_description[:50]}...'")
        return description

    def to_dict(self) -> Dict:
        """
        Преобразует объект в словарь.
        
        Returns:
            Dict: Словарь с данными описания компонента
        """
        result = {
            'generic_description': self.generic_description,
        }
        
        # Добавляем опциональные поля только если они не None
        if self.effects is not None:
            result['effects'] = self.effects
        if self.shamanic is not None:
            result['shamanic'] = self.shamanic
        if self.warnings is not None:
            result['warnings'] = self.warnings
        if self.dosage_instructions is not None:
            result['dosage_instructions'] = [
                instruction.to_dict() for instruction in self.dosage_instructions
            ]
        if self.features is not None:
            result['features'] = self.features
        
        return result

    def __repr__(self) -> str:
        """Строковое представление объекта"""
        return f"ComponentDescription(generic_description='{self.generic_description[:30]}...')"

    def __eq__(self, other) -> bool:
        """Сравнение объектов по содержимому"""
        if not isinstance(other, ComponentDescription):
            return False
        
        return (
            self.generic_description == other.generic_description and
            self.effects == other.effects and
            self.shamanic == other.shamanic and
            self.warnings == other.warnings and
            self.dosage_instructions == other.dosage_instructions and
            self.features == other.features
        )

    def __hash__(self) -> int:
        """Хеш объекта для использования в множествах"""
        return hash((
            self.generic_description,
            self.effects,
            self.shamanic,
            self.warnings,
            tuple(self.dosage_instructions) if self.dosage_instructions else None,
            tuple(self.features) if self.features else None
        ))
