from typing import Optional, List, Dict, Union
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from .organic_component import OrganicComponent
from .dosage_instruction import DosageInstruction
from bot.validation import ValidationFactory, ValidationResult



@dataclass
class Description:
    """
    Структура для хранения и обработки информации о описании продукта.
    
    Attributes:
        business_id (str): Бизнес-идентификатор продукта
        title (str): Название продукта
        scientific_name (str): Научное название
        generic_description (str): Общее описание
        effects (Optional[str]): Описание эффектов
        shamanic (Optional[str]): Описание шаманской перспективы
        warnings (Optional[str]): Предупреждения
        dosage_instructions (List[DosageInstruction]): Инструкции по дозировке
    """
    business_id: str
    title: str
    scientific_name: str
    generic_description: str
    effects: Optional[str]
    shamanic: Optional[str]
    warnings: Optional[str]
    dosage_instructions: List[DosageInstruction]

    @classmethod
    def from_dict(cls, data: dict) -> "Description":
        """
        Создает объект Description из словаря.
        
        Args:
            data: Словарь с данными описания
            
        Returns:
            Description: Новый объект
            
        Raises:
            ValueError: Если отсутствуют обязательные поля
        """
        if not isinstance(data, dict):
            raise ValueError("Входные данные должны быть словарем")
            
        # Проверяем обязательные поля
        required_fields = ['business_id', 'title', 'scientific_name', 'generic_description']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Отсутствует обязательное поле '{field}'")
        
        # Преобразуем инструкции по дозировке
        dosage_instructions = []
        if 'dosage_instructions' in data:
            if not isinstance(data['dosage_instructions'], list):
                raise ValueError("dosage_instructions должен быть списком")
            dosage_instructions = [
                DosageInstruction.from_dict(instruction)
                for instruction in data['dosage_instructions']
            ]
        
        return cls(
            business_id=data['business_id'],
            title=data['title'],
            scientific_name=data['scientific_name'],
            generic_description=data['generic_description'],
            effects=data.get('effects'),
            shamanic=data.get('shamanic'),
            warnings=data.get('warnings'),
            dosage_instructions=dosage_instructions
        )
    
    def to_dict(self) -> Dict:
        """
        Преобразует объект в словарь.
        
        Returns:
            Dict: Словарь с данными описания
        """
        return {
            'business_id': self.business_id,
            'title': self.title,
            'scientific_name': self.scientific_name,
            'generic_description': self.generic_description,
            'effects': self.effects,
            'shamanic': self.shamanic,
            'warnings': self.warnings,
            'dosage_instructions': [
                instruction.to_dict() 
                for instruction in self.dosage_instructions
            ]
        }

@dataclass
class PriceInfo:
    """
    Структура для хранения и обработки информации о цене продукта.
    Поддерживает работу с весом, объемом и различными валютами.
    """
    
    # Поддерживаемые валюты и их символы
    SUPPORTED_CURRENCIES = {
        'EUR': '€',  # Евро
        'USD': '$',  # Доллар США
        'GBP': '£',  # Фунт стерлингов
        'JPY': '¥',  # Йена
        'RUB': '₽',  # Рубль
        'CNY': '¥',  # Юань
        'USDT': '₮', # Tether
        'ETH': 'Ξ',  # Ethereum
        'BTC': '₿',  # Bitcoin
    }

    # Поддерживаемые единицы измерения
    SUPPORTED_WEIGHT_UNITS = {'g', 'kg', 'oz', 'lb'}
    SUPPORTED_VOLUME_UNITS = {'ml', 'l', 'oz_fl'}

    # Коэффициенты конвертации для единиц измерения (к базовой единице)
    WEIGHT_CONVERSION = {
        'g': Decimal('1'),
        'kg': Decimal('1000'),
        'oz': Decimal('28.35'),
        'lb': Decimal('453.59237')
    }

    VOLUME_CONVERSION = {
        'ml': Decimal('1'),
        'l': Decimal('1000'),
        'oz_fl': Decimal('29.5735')
    }

    # Поля dataclass
    price: Union[int, float, str, Decimal]
    currency: str = 'EUR'
    weight: Optional[Union[int, float, str]] = None
    weight_unit: Optional[str] = None
    volume: Optional[Union[int, float, str]] = None
    volume_unit: Optional[str] = None
    form: Optional[str] = None

    def __post_init__(self):
        """
        Валидация данных после инициализации dataclass.
        Использует единую систему валидации из ValidationFactory.
        
        Raises:
            ValueError: Если валидация не прошла
        """
        # Получаем валидаторы из фабрики
        price_validator = ValidationFactory.get_price_validator()
        
        # Валидация цены с использованием единого валидатора
        price_result = price_validator.validate(self.price)
        if not price_result.is_valid:
            raise ValueError(f"price: {price_result.error_message}")
        
        # Конвертируем цену в Decimal для внутреннего использования
        self.price = Decimal(str(self.price))
        
        # Валидация валюты
        if not self.currency:
            raise ValueError("currency: Поле обязательно для заполнения")
        
        # Проверяем, что currency является строкой
        if not isinstance(self.currency, str):
            raise ValueError(f"currency: Должен быть строкой, получен {type(self.currency).__name__}")
        
        if not self.currency.strip():
            raise ValueError("currency: Поле обязательно для заполнения")
        
        currency = self.currency.upper().strip()
        if currency not in self.SUPPORTED_CURRENCIES:
            raise ValueError(f"currency: Неподдерживаемая валюта '{currency}'. "
                           f"Поддерживаемые валюты: {', '.join(self.SUPPORTED_CURRENCIES.keys())}")
        self.currency = currency

        # Валидация веса/объема
        if self.weight is not None and self.volume is not None:
            raise ValueError("Нельзя одновременно указывать вес и объем")

        # Обработка веса
        if self.weight is not None:
            if not self.weight_unit:
                raise ValueError("weight_unit: Должен быть указан при указании веса")
            
            if self.weight_unit not in self.SUPPORTED_WEIGHT_UNITS:
                raise ValueError(f"weight_unit: Неподдерживаемая единица веса '{self.weight_unit}'. "
                               f"Поддерживаемые единицы: {', '.join(self.SUPPORTED_WEIGHT_UNITS)}")
            
            # Валидация числового значения веса
            try:
                self.weight = Decimal(str(self.weight))
                if self.weight <= 0:
                    raise ValueError("weight: Должен быть положительным числом")
            except (ValueError, TypeError, ArithmeticError) as e:
                raise ValueError(f"weight: Некорректное значение '{self.weight}'") from e
            
            # Сбрасываем объем
            self.volume = None
            self.volume_unit = None
        
        # Обработка объема
        elif self.volume is not None:
            if not self.volume_unit:
                raise ValueError("volume_unit: Должен быть указан при указании объема")
            
            if self.volume_unit not in self.SUPPORTED_VOLUME_UNITS:
                raise ValueError(f"volume_unit: Неподдерживаемая единица объема '{self.volume_unit}'. "
                               f"Поддерживаемые единицы: {', '.join(self.SUPPORTED_VOLUME_UNITS)}")
            
            # Валидация числового значения объема
            try:
                self.volume = Decimal(str(self.volume))
                if self.volume <= 0:
                    raise ValueError("volume: Должен быть положительным числом")
            except (ValueError, TypeError, ArithmeticError) as e:
                raise ValueError(f"volume: Некорректное значение '{self.volume}'") from e
            
            # Сбрасываем вес
            self.weight = None
            self.weight_unit = None
        
        # Если ни вес, ни объем не указаны - это нормально для простых цен
        else:
            self.weight = None
            self.weight_unit = None
            self.volume = None
            self.volume_unit = None

    # Устаревшие методы валидации удалены - теперь используется единая система валидации

    @property
    def currency_symbol(self) -> str:
        """Возвращает символ валюты."""
        return self.SUPPORTED_CURRENCIES[self.currency]

    @property
    def is_weight_based(self) -> bool:
        """Проверяет, основана ли цена на весе."""
        return self.weight is not None and self.weight_unit is not None

    @property
    def is_volume_based(self) -> bool:
        """Проверяет, основана ли цена на объеме."""
        return self.volume is not None and self.volume_unit is not None

    def convert_weight(self, target_unit: str) -> Decimal:
        """
        Конвертирует вес в указанную единицу измерения.

        Args:
            target_unit: Целевая единица измерения

        Returns:
            Decimal: Сконвертированное значение веса

        Raises:
            ValueError: Если конвертация невозможна
        """
        if not self.is_weight_based:
            raise ValueError("Цена не основана на весе")
        if target_unit not in self.SUPPORTED_WEIGHT_UNITS:
            raise ValueError(f"Неподдерживаемая единица веса: {target_unit}")

        # Конвертируем в базовую единицу (граммы), затем в целевую
        base_value = self.weight * self.WEIGHT_CONVERSION[self.weight_unit]
        return base_value / self.WEIGHT_CONVERSION[target_unit]

    def convert_volume(self, target_unit: str) -> Decimal:
        """
        Конвертирует объем в указанную единицу измерения.

        Args:
            target_unit: Целевая единица измерения

        Returns:
            Decimal: Сконвертированное значение объема

        Raises:
            ValueError: Если конвертация невозможна
        """
        if not self.is_volume_based:
            raise ValueError("Цена не основана на объеме")
        if target_unit not in self.SUPPORTED_VOLUME_UNITS:
            raise ValueError(f"Неподдерживаемая единица объема: {target_unit}")

        # Конвертируем в базовую единицу (миллилитры), затем в целевую
        base_value = self.volume * self.VOLUME_CONVERSION[self.volume_unit]
        return base_value / self.VOLUME_CONVERSION[target_unit]

    def convert_currency(self, target_currency: str, rate: Decimal) -> 'PriceInfo':
        """
        Создает новый объект PriceInfo с ценой в другой валюте.

        Args:
            target_currency: Целевая валюта
            rate: Курс конвертации (сколько единиц целевой валюты за 1 единицу текущей)

        Returns:
            PriceInfo: Новый объект с сконвертированной ценой

        Raises:
            ValueError: Если конвертация невозможна
        """
        if target_currency not in self.SUPPORTED_CURRENCIES:
            raise ValueError(f"Неподдерживаемая валюта: {target_currency}")
        
        new_price = self.price * Decimal(str(rate))
        
        return PriceInfo(
            price=new_price,
            weight=self.weight,
            weight_unit=self.weight_unit,
            volume=self.volume,
            volume_unit=self.volume_unit,
            currency=target_currency,
            form=self.form
        )

    def get_unit_price(self, target_unit: Optional[str] = None) -> Decimal:
        """
        Вычисляет цену за единицу измерения.

        Args:
            target_unit: Целевая единица измерения (если нужна конвертация)

        Returns:
            Decimal: Цена за единицу измерения

        Raises:
            ValueError: Если вычисление невозможно
        """
        if self.is_weight_based:
            quantity = self.convert_weight(target_unit) if target_unit else self.weight
        elif self.is_volume_based:
            quantity = self.convert_volume(target_unit) if target_unit else self.volume
        else:
            return self.price

        return self.price / quantity

    def format_amount(self) -> str:
        """
        Форматирует количество товара для отображения.

        Returns:
            str: Отформатированная строка с количеством и единицей измерения
        """
        if self.is_weight_based:
            return f"{float(self.weight):.0f}{self.weight_unit}"
        if self.is_volume_based:
            return f"{float(self.volume):.0f}{self.volume_unit}"
        return "1 шт"

    def format_price(self, use_symbol: bool = True) -> str:
        """
        Форматирует цену для отображения.

        Args:
            use_symbol: Использовать символ валюты вместо кода

        Returns:
            str: Отформатированная строка с ценой и валютой
        """
        # Округляем до 2 знаков после запятой для обычных валют
        # и до 8 знаков для криптовалют
        decimals = 8 if self.currency in ['BTC', 'ETH'] else 2
        price_str = f"{float(self.price):.{decimals}f}"
        
        if use_symbol:
            return f"{price_str}{self.currency_symbol}"
        return f"{price_str} {self.currency}"

    def format_full(self, use_symbol: bool = True, include_form: bool = False) -> str:
        """
        Полное форматирование цены с количеством.

        Args:
            use_symbol: Использовать символ валюты вместо кода
            include_form: Включать форму продукта в строку

        Returns:
            str: Полностью отформатированная строка
        """
        base = f"{self.format_price(use_symbol)} за {self.format_amount()}"
        if include_form and self.form:
            base += f" ({self.form})"
        return base

    @classmethod
    def from_dict(cls, data: Dict) -> 'PriceInfo':
        """
        Создает объект PriceInfo из словаря.

        Args:
            data: Словарь с данными о цене

        Returns:
            PriceInfo: Новый объект

        Raises:
            ValueError: Если данные некорректны
        """
        if not isinstance(data, dict):
            raise ValueError(f"Входные данные должны быть словарем: {data}")

        return cls(
            price=data['price'],
            weight=data.get('weight'),
            weight_unit=data.get('weight_unit'),
            volume=data.get('volume'),
            volume_unit=data.get('volume_unit'),
            currency=data.get('currency', 'EUR')
        )

    def to_dict(self) -> Dict:
        """
        Конвертирует объект в словарь для сохранения.

        Returns:
            Dict: Словарь с данными о цене
        """
        data = {
            'price': str(self.price),
            'currency': self.currency
        }
        
        if self.form:
            data['form'] = self.form

        if self.is_weight_based:
            data.update({
                'weight': str(self.weight),
                'weight_unit': self.weight_unit
            })
        elif self.is_volume_based:
            data.update({
                'volume': str(self.volume),
                'volume_unit': self.volume_unit
            })
        
        return data

    def __eq__(self, other: object) -> bool:
        """Сравнивает два объекта PriceInfo."""
        if not isinstance(other, PriceInfo):
            return NotImplemented
        return (
            self.price == other.price and
            self.currency == other.currency and
            self.weight == other.weight and
            self.weight_unit == other.weight_unit and
            self.volume == other.volume and
            self.volume_unit == other.volume_unit
        )

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта."""
        return f"PriceInfo({self.format_full(include_form=True)})"

@dataclass
class Product:
    """
    Модель продукта, представляющая товар в каталоге.
    
    Attributes:
        business_id (str): Бизнес-идентификатор продукта из метаданных
        blockchain_id (Union[int, str]): Уникальный идентификатор продукта в блокчейне
        status (int): Статус продукта (0 - неактивен, 1 - активен)
        cid (str): Content Identifier - ссылка на контент в IPFS/Arweave
        title (str): Название продукта
        organic_components (List[OrganicComponent]): Список компонентов продукта
        cover_image_url (str): Ссылка на основное изображение
        categories (List[str]): Список категорий
        forms (List[str]): Список форм продукта
        species (str): Биологический вид
        prices (List[PriceInfo]): Список цен
    """
    business_id: str
    blockchain_id: Union[int, str]
    status: int
    cid: str
    title: str
    organic_components: List[OrganicComponent]
    cover_image_url: str
    categories: List[str]
    forms: List[str]
    species: str
    prices: List[PriceInfo]

    def __post_init__(self):
        """
        Валидация данных после инициализации dataclass.
        Использует единую систему валидации из ValidationFactory.
        
        Raises:
            ValueError: Если валидация не прошла
        """
        # Получаем валидаторы из фабрики
        cid_validator = ValidationFactory.get_cid_validator()
        
        # Валидация business_id (НЕ как CID!)
        if not self.business_id or not isinstance(self.business_id, str):
            raise ValueError("business_id должен быть непустой строкой")
        
        # Валидация cover_image_url как CID
        cid_result = cid_validator.validate(self.cover_image_url)
        if not cid_result.is_valid:
            raise ValueError(f"cover_image_url: {cid_result.error_message}")
        
        # Валидация organic_components
        if not self.organic_components:
            raise ValueError("organic_components не может быть пустым")
        
        # Валидация prices
        if not self.prices:
            raise ValueError("prices не может быть пустым")
        
        # Валидация title
        if not self.title or not self.title.strip():
            raise ValueError("title не может быть пустым")
        
        # Валидация species
        if not self.species or not self.species.strip():
            raise ValueError("species не может быть пустым")

    @classmethod
    def from_dict(cls, data: Dict) -> 'Product':
        """
        Создает объект Product из словаря.
        
        Args:
            data: Словарь с данными продукта
            
        Returns:
            Product: Новый объект продукта
            
        Raises:
            ValueError: Если в данных отсутствуют обязательные поля
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 Product.from_dict: начинаем создание продукта")
        logger.info(f"📋 Доступные поля: {list(data.keys())}")
        
        if not isinstance(data, dict):
            raise ValueError("Входные данные должны быть словарем")

        # Обязательные поля
        required_fields = ['business_id', 'title', 'cover_image_url', 'species']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Отсутствует обязательное поле '{field}'")

        # Обратная совместимость: поддержка старого формата с description
        if 'organic_components' in data:
            # Новый формат с компонентами
            logger.info(f"🔬 Используем новый формат с organic_components")
            organic_components_data = data['organic_components']
            if not isinstance(organic_components_data, list):
                raise ValueError("organic_components должен быть списком")
            
            logger.info(f"🏗️ Создаем {len(organic_components_data)} OrganicComponent объектов...")
            organic_components = []
            for i, comp in enumerate(organic_components_data):
                logger.info(f"  Создаем компонент {i+1}: {comp}")
                try:
                    component = OrganicComponent.from_dict(comp)
                    organic_components.append(component)
                    logger.info(f"  ✅ Компонент {i+1} создан успешно")
                except Exception as e:
                    logger.error(f"  ❌ Ошибка создания компонента {i+1}: {e}")
                    raise
        elif 'description' in data and 'description_cid' in data:
            # Старый формат: создаем один компонент из description
            logger.info(f"🔬 Используем старый формат с description")
            organic_components = [OrganicComponent(
                biounit_id=data.get('species', 'unknown'),
                description_cid=data['description_cid'],
                proportion='100%'
            )]
        else:
            raise ValueError("Должны быть указаны либо organic_components, либо description + description_cid")

        # Создаем объекты PriceInfo
        prices = [PriceInfo.from_dict(p) for p in data.get('prices', [])]

        # Обратная совместимость: поддержка поля 'form' (единственное число)
        if 'forms' in data:
            forms_value = data.get('forms', [])
        else:
            single_form = data.get('form')
            forms_value = [single_form] if single_form else []

        return cls(
            business_id=data['business_id'],
            blockchain_id=data.get('blockchain_id', 0),  # Блокчейн ID по умолчанию
            status=data.get('status', 0),  # Продукт создается неактивным по умолчанию
            cid=data.get('cid', ''),  # CID метаданных
            title=data['title'],
            organic_components=organic_components,
            cover_image_url=data['cover_image_url'],
            categories=data.get('categories', []),
            forms=forms_value,
            species=data['species'],
            prices=prices
        )

    def to_dict(self) -> Dict:
        """
        Преобразует объект Product в словарь.
        
        Returns:
            Dict: Словарь с данными продукта
        """
        return {
            'business_id': self.business_id,
            'blockchain_id': self.blockchain_id,
            'status': self.status,
            'cid': self.cid,
            'title': self.title,
            'organic_components': [comp.to_dict() for comp in self.organic_components],
            'cover_image_url': self.cover_image_url,
            'categories': self.categories,
            'forms': self.forms,
            'species': self.species,
            'prices': [price.to_dict() for price in self.prices]
        }

    @property
    def price_infos(self) -> List[PriceInfo]:
        """
        Возвращает список объектов PriceInfo.
        
        Returns:
            List[PriceInfo]: Список объектов с информацией о ценах
        """
        return self.prices

    @property
    def price(self) -> float:
        """
        Возвращает минимальную цену из всех вариантов.
        
        Returns:
            float: Минимальная цена продукта
        """
        return min((p.price for p in self.price_infos), default=0)

    def get_price(self, weight: Optional[Union[int, str]] = None,
                weight_unit: Optional[str] = None,
                volume: Optional[Union[int, str]] = None,
                volume_unit: Optional[str] = None,
                currency: str = 'EUR') -> float:
        """
        Получает конкретную цену по параметрам.
        
        Args:
            weight: Вес продукта
            weight_unit: Единица измерения веса
            volume: Объем продукта
            volume_unit: Единица измерения объема
            currency: Валюта цены
        
        Returns:
            float: Цена продукта для указанных параметров или 0, если не найдена
        """
        for price_info in self.price_infos:
            if weight and volume:
                continue  # Нельзя искать одновременно по весу и объему
            
            if weight and price_info.is_weight_based:
                if (price_info.weight == str(weight) and 
                    price_info.weight_unit == weight_unit and 
                    price_info.currency == currency):
                    return price_info.price
                    
            if volume and price_info.is_volume_based:
                if (price_info.volume == str(volume) and 
                    price_info.volume_unit == volume_unit and 
                    price_info.currency == currency):
                    return price_info.price
                    
        return 0

    def get_formatted_prices(self) -> List[str]:
        """
        Возвращает список отформатированных цен для отображения.
        
        Returns:
            List[str]: Список строк с отформатированными ценами
        """
        return [price_info.format_full() for price_info in self.price_infos]

    def get_price_info(self, weight: Optional[Union[int, str]] = None,
                    weight_unit: Optional[str] = None,
                    volume: Optional[Union[int, str]] = None,
                    volume_unit: Optional[str] = None) -> Optional[PriceInfo]:
        """
        Получает объект PriceInfo по параметрам.
        
        Args:
            weight: Вес продукта
            weight_unit: Единица измерения веса
            volume: Объем продукта
            volume_unit: Единица измерения объема
        
        Returns:
            Optional[PriceInfo]: Объект с информацией о цене или None, если не найден
        """
        for price_info in self.price_infos:
            if weight and price_info.is_weight_based:
                if price_info.weight == str(weight) and price_info.weight_unit == weight_unit:
                    return price_info
            if volume and price_info.is_volume_based:
                if price_info.volume == str(volume) and price_info.volume_unit == volume_unit:
                    return price_info
        return None

    def get_component_by_biounit_id(self, biounit_id: str) -> Optional[OrganicComponent]:
        """
        Получает компонент по biounit_id.
        
        Args:
            biounit_id: Идентификатор биологической единицы
            
        Returns:
            Optional[OrganicComponent]: Компонент или None, если не найден
        """
        for component in self.organic_components:
            if component.biounit_id == biounit_id:
                return component
        return None

    def get_components_by_proportion_type(self, proportion_type: str) -> List[OrganicComponent]:
        """
        Получает компоненты по типу пропорции.
        
        Args:
            proportion_type: Тип пропорции ('percentage', 'weight', 'volume')
            
        Returns:
            List[OrganicComponent]: Список компонентов с указанным типом пропорции
        """
        if proportion_type == 'percentage':
            return [comp for comp in self.organic_components if comp.is_percentage()]
        elif proportion_type == 'weight':
            return [comp for comp in self.organic_components if comp.is_weight_based()]
        elif proportion_type == 'volume':
            return [comp for comp in self.organic_components if comp.is_volume_based()]
        else:
            return []

    def validate_proportions(self) -> bool:
        """
        Валидирует корректность пропорций компонентов.
        
        Returns:
            bool: True если пропорции корректны, False если нет
        """
        # Проверяем, что все компоненты имеют одинаковый тип пропорции
        proportion_types = set()
        for component in self.organic_components:
            if component.is_percentage():
                proportion_types.add('percentage')
            elif component.is_weight_based():
                proportion_types.add('weight')
            elif component.is_volume_based():
                proportion_types.add('volume')
        
        # Если смешанные типы пропорций, валидация не проходит
        if len(proportion_types) > 1:
            return False
        
        # Для процентных пропорций проверяем, что сумма = 100%
        if 'percentage' in proportion_types:
            total_percentage = sum(comp.get_proportion_value() for comp in self.organic_components)
            return abs(total_percentage - 100.0) < 0.01  # Допуск 0.01%
        
        # Для весовых/объемных пропорций проверяем, что все > 0
        return all(comp.get_proportion_value() > 0 for comp in self.organic_components)

    def get_total_proportion(self) -> str:
        """
        Получает общую пропорцию продукта.
        
        Returns:
            str: Общая пропорция (например, "100%", "500g", "1L")
        """
        if not self.organic_components:
            return "0"
        
        first_component = self.organic_components[0]
        if first_component.is_percentage():
            return "100%"
        elif first_component.is_weight_based():
            total_weight = sum(comp.get_proportion_value() for comp in self.organic_components)
            return f"{total_weight}{first_component.get_proportion_unit()}"
        elif first_component.is_volume_based():
            total_volume = sum(comp.get_proportion_value() for comp in self.organic_components)
            return f"{total_volume}{first_component.get_proportion_unit()}"
        else:
            return "0"

    # 🔧 УНИФИКАЦИЯ: Убраны дублирующие методы from_json/to_json
    # Используйте from_dict() и to_dict() для единообразного интерфейса сериализации

    def __eq__(self, other: object) -> bool:
        """Сравнивает два объекта Product."""
        if not isinstance(other, Product):
            return NotImplemented
        return (
            self.id == other.id and
            self.alias == other.alias and
            self.status == other.status and
            self.cid == other.cid and
            self.title == other.title and
            self.organic_components == other.organic_components and
            self.cover_image_url == other.cover_image_url and
            self.categories == other.categories and
            self.forms == other.forms and
            self.species == other.species and
            self.prices == other.prices
        )

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта."""
        return f"Product(business_id={self.business_id}, blockchain_id={self.blockchain_id}, title={self.title})"
