from typing import Dict, Optional, List, Any
from dataclasses import dataclass
import re
from validation import ValidationFactory, ValidationResult
from .component_description import ComponentDescription


@dataclass
class OrganicComponent:
    """
    Структура для хранения информации о компоненте многокомпонентного продукта.
    
    Unified model supporting:
    1. Registry component (standalone): component_id + registry metadata + blockchain data
    2. Product component (in composition): registry component + proportion
    
    Attributes:
        component_id (str): Уникальный идентификатор компонента (primary field)
        
        # Registry metadata (from Arweave)
        scientific_title (Optional[str]): Научное название (e.g., "Amanita muscaria")
        forms (Optional[List[str]]): Доступные формы ["dried", "tincture", "powder"]
        features (Optional[Dict]): Характеристики {"common": [...], "forms": {...}}
        localizations (Optional[Dict]): Мультиязычные CID {"simple_fields": {...}, "complex_fields": {...}}
        
        # Blockchain data (from OrganicComponentRegistry)
        blockchain_id (Optional[int]): Numeric ID в контракте
        creator (Optional[str]): Адрес создателя
        active (Optional[bool]): Активен ли компонент
        created_at (Optional[int]): Timestamp создания
        
        # Product composition (only for product usage)
        proportion (Optional[str]): Пропорция в продукте ("50%", "100g", "30ml")
        
        # Description
        description (Optional[ComponentDescription]): Расширенное описание компонента
        description_cid (Optional[str]): CID описания в IPFS (deprecated, для старых продуктов)
    
    Factory Methods:
        for_product(registry_component, proportion) - Add proportion for product usage
    """
    component_id: str
    
    # Registry metadata fields
    scientific_title: Optional[str] = None
    forms: Optional[List[str]] = None
    features: Optional[Dict[str, Any]] = None
    localizations: Optional[Dict[str, Any]] = None
    
    # Blockchain data fields
    blockchain_id: Optional[int] = None
    creator: Optional[str] = None
    active: Optional[bool] = None
    created_at: Optional[int] = None
    
    # Product composition
    proportion: Optional[str] = None
    
    # Description fields
    description: Optional[ComponentDescription] = None
    description_cid: Optional[str] = None

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
        logger.info(f"📋 Данные для валидации: component_id='{self.component_id}', description_cid='{self.description_cid}', proportion='{self.proportion}', description={self.description is not None}")
        
        # Получаем валидаторы из фабрики
        logger.info("🔧 Получаем валидаторы из ValidationFactory...")
        cid_validator = ValidationFactory.get_cid_validator()
        proportion_validator = ValidationFactory.get_proportion_validator()
        logger.info(f"✅ Валидаторы получены: CID={type(cid_validator).__name__}, Proportion={type(proportion_validator).__name__}")
        
        # Валидация component_id (renamed from biounit_id)
        logger.info(f"🔍 Валидируем component_id: '{self.component_id}'")
        if not self.component_id or not self.component_id.strip():
            raise ValueError("component_id не может быть пустым")
        
        # Проверка формата component_id (буквы, цифры, подчеркивания, дефисы)
        component_pattern = r'^[a-zA-Z0-9_-]+$'
        if not re.match(component_pattern, self.component_id):
            raise ValueError(f"component_id '{self.component_id}' содержит недопустимые символы. Разрешены только буквы, цифры, подчеркивания и дефисы")
        
        # Проверка длины component_id (от 1 до 50 символов)
        if len(self.component_id) > 50:
            raise ValueError(f"component_id '{self.component_id}' слишком длинный. Максимальная длина: 50 символов")
        logger.info(f"✅ component_id валидирован успешно")
        
        # Валидация description_cid (если присутствует, для старых продуктов)
        if self.description_cid:
            logger.info(f"🔍 Валидируем description_cid: '{self.description_cid}'")
            logger.info(f"🔧 Вызываем cid_validator.validate('{self.description_cid}')...")
            cid_result = cid_validator.validate(self.description_cid)
            logger.info(f"📋 Результат валидации CID: {cid_result}")
            if not cid_result.is_valid:
                logger.error(f"❌ Валидация description_cid не прошла: {cid_result.error_message}")
                raise ValueError(f"description_cid: {cid_result.error_message}")
            logger.info(f"✅ description_cid валидирован успешно")
        else:
            logger.info(f"📋 description_cid отсутствует (None) - это OK для новой системы")
        
        # Валидация proportion (если присутствует, для product usage)
        if self.proportion:
            logger.info(f"🔍 Валидируем proportion: '{self.proportion}'")
            proportion_result = proportion_validator.validate(self.proportion)
            if not proportion_result.is_valid:
                raise ValueError(f"proportion: {proportion_result.error_message}")
            logger.info(f"✅ proportion валидирован успешно")
        else:
            logger.info(f"📋 proportion отсутствует (None) - это OK для registry component")
        
        # 🔧 ВАЛИДАЦИЯ DESCRIPTION: Проверяем новое поле description
        if self.description is not None:
            logger.info(f"🔍 Валидируем description: {type(self.description).__name__}")
            if not isinstance(self.description, ComponentDescription):
                raise ValueError(f"description должен быть объектом ComponentDescription, получен: {type(self.description).__name__}")
            logger.info(f"✅ description валидирован успешно")
        else:
            logger.info(f"📋 description отсутствует (None) - это нормально для базовых компонентов")
        
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
    
    def is_registry_component(self) -> bool:
        """
        Проверяет, является ли это registry component (standalone).
        
        Registry component НЕ имеет proportion (не используется в продукте).
        
        Returns:
            bool: True если это registry component, False если product component
        """
        return self.proportion is None
    
    def is_product_component(self) -> bool:
        """
        Проверяет, является ли это product component (используется в продукте).
        
        Product component ИМЕЕТ proportion (указывает количество в продукте).
        
        Returns:
            bool: True если это product component, False если registry component
        """
        return self.proportion is not None

    @classmethod
    def for_product(
        cls,
        registry_component: "OrganicComponent",
        proportion: str,
        description: Optional[ComponentDescription] = None
    ) -> "OrganicComponent":
        """
        Create product component from registry component + proportion.
        
        Args:
            registry_component: Base component from registry
            proportion: Amount in product (e.g., "100g", "50%")
            description: Optional localized description
        
        Returns:
            OrganicComponent: Product component (with proportion)
        
        Example:
            registry_comp = service.get_component_full("amanita_muscaria")
            
            product_comp = OrganicComponent.for_product(
                registry_comp,
                proportion="100g"
            )
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 Creating product component from registry: {registry_component.component_id} + {proportion}")
        
        return cls(
            component_id=registry_component.component_id,
            scientific_title=registry_component.scientific_title,
            forms=registry_component.forms,
            features=registry_component.features,
            localizations=registry_component.localizations,
            blockchain_id=registry_component.blockchain_id,
            creator=registry_component.creator,
            active=registry_component.active,
            created_at=registry_component.created_at,
            proportion=proportion,  # Added for product
            description=description or registry_component.description,
            description_cid=registry_component.description_cid
        )
    
    @classmethod
    def from_dict(cls, data: dict) -> "OrganicComponent":
        """
        Создает объект OrganicComponent из словаря.
        
        Supports both component_id (new) and biounit_id (old) field names.
        
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
        
        # Support both component_id (new) and biounit_id (old)
        component_id = data.get('component_id') or data.get('biounit_id')
        
        if not component_id:
            raise ValueError("Отсутствует component_id или biounit_id")
        
        logger.info(f"✅ Component ID: '{component_id}'")
        
        # 🔧 СОЗДАНИЕ COMPONENTDESCRIPTION: Проверяем наличие поля description
        description = None
        
        if 'description' in data and data['description'] is not None:
            logger.info(f"🔍 Найдено поле 'description': {type(data['description'])}")
            
            if isinstance(data['description'], ComponentDescription):
                # Уже готовый ComponentDescription объект
                description = data['description']
                logger.info(f"✅ Используем готовый ComponentDescription объект")
            elif isinstance(data['description'], dict):
                # Словарь с данными описания
                try:
                    description = ComponentDescription.from_dict(data['description'])
                    logger.info(f"✅ ComponentDescription создан из словаря")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось создать ComponentDescription из словаря: {e}")
                    description = None
            else:
                logger.warning(f"⚠️ Поле 'description' имеет неожиданный тип: {type(data['description'])}")
                description = None
        else:
            # 🔧 ОБРАТНАЯ СОВМЕСТИМОСТЬ: Проверяем старые поля описания
            description_fields = ['generic_description', 'effects', 'shamanic', 'warnings', 'dosage_instructions', 'features']
            has_description_data = any(field in data for field in description_fields)
            
            if has_description_data:
                logger.info(f"🔍 Найдены старые поля описания: {[field for field in description_fields if field in data]}")
                try:
                    # Создаем ComponentDescription из доступных полей
                    description_data = {field: data[field] for field in description_fields if field in data}
                    description = ComponentDescription.from_dict(description_data)
                    logger.info(f"✅ ComponentDescription создан из старых полей (обратная совместимость)")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось создать ComponentDescription из старых полей: {e}")
                    description = None
            else:
                logger.info(f"📋 Поля описания не найдены, description остается None")
        
        logger.info(f"🏗️ Создаем OrganicComponent объект...")
        
        # Get optional fields with safe defaults
        description_cid = data.get('description_cid')
        proportion = data.get('proportion')
        
        # Registry metadata fields
        scientific_title = data.get('scientific_title')
        forms = data.get('forms', []) if data.get('forms') else None
        features = data.get('features', {}) if data.get('features') else None
        localizations = data.get('localizations', {}) if data.get('localizations') else None
        
        # Blockchain data fields
        blockchain_id = data.get('blockchain_id')
        creator = data.get('creator')
        active = data.get('active')
        created_at = data.get('created_at')
        
        component = cls(
            component_id=str(component_id).strip(),
            scientific_title=scientific_title,
            forms=forms,
            features=features,
            localizations=localizations,
            blockchain_id=blockchain_id,
            creator=creator,
            active=active,
            created_at=created_at,
            proportion=str(proportion).strip() if proportion else None,
            description=description,
            description_cid=str(description_cid).strip() if description_cid else None
        )
        logger.info(f"✅ OrganicComponent объект создан: component_id='{component.component_id}', scientific_title='{component.scientific_title}', proportion='{component.proportion}', description={component.description is not None}")
        
        return component

    def to_dict(self) -> Dict:
        """
        Преобразует объект в словарь.
        
        Returns:
            Dict: Словарь с данными компонента (все присутствующие поля)
        """
        result = {
            "component_id": self.component_id
        }
        
        # Registry metadata fields
        if self.scientific_title:
            result["scientific_title"] = self.scientific_title
        
        if self.forms:
            result["forms"] = self.forms
        
        if self.features:
            result["features"] = self.features
        
        if self.localizations:
            result["localizations"] = self.localizations
        
        # Blockchain data fields
        if self.blockchain_id is not None:
            result["blockchain_id"] = self.blockchain_id
        
        if self.creator:
            result["creator"] = self.creator
        
        if self.active is not None:
            result["active"] = self.active
        
        if self.created_at is not None:
            result["created_at"] = self.created_at
        
        # Product composition fields
        if self.proportion:
            result["proportion"] = self.proportion
        
        # Legacy field
        if self.description_cid:
            result["description_cid"] = self.description_cid
        
        # 🔧 СЕРИАЛИЗАЦИЯ ОПИСАНИЯ: Добавляем description если оно есть
        if self.description is not None:
            description_dict = self.description.to_dict()
            result.update(description_dict)
        
        return result

    def __repr__(self) -> str:
        """Строковое представление объекта"""
        description_info = f", description={self.description is not None}" if self.description is not None else ""
        proportion_info = f", proportion='{self.proportion}'" if self.proportion else ""
        return f"OrganicComponent(component_id='{self.component_id}'{proportion_info}{description_info})"

    def __eq__(self, other) -> bool:
        """Сравнение объектов по содержимому"""
        if not isinstance(other, OrganicComponent):
            return False
        
        return (
            self.component_id == other.component_id and
            self.description_cid == other.description_cid and
            self.proportion == other.proportion and
            self.description == other.description
        )

    def __hash__(self) -> int:
        """Хеш объекта для использования в множествах"""
        return hash((self.component_id, self.description_cid, self.proportion, self.description))
