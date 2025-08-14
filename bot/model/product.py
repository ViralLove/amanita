from typing import Optional, List, Dict, Union
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from .organic_component import OrganicComponent

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

@dataclass
class Description:
    """
    Структура для хранения и обработки информации о описании продукта.
    
    Attributes:
        id (str): Уникальный идентификатор продукта
        title (str): Название продукта
        scientific_name (str): Научное название
        generic_description (str): Общее описание
        effects (Optional[str]): Описание эффектов
        shamanic (Optional[str]): Описание шаманской перспективы
        warnings (Optional[str]): Предупреждения
        dosage_instructions (List[DosageInstruction]): Инструкции по дозировке
    """
    id: str
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
        required_fields = ['id', 'title', 'scientific_name', 'generic_description']
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
            id=data['id'],
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
            'id': self.id,
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

    def __init__(
        self,
        price: Union[int, float, str, Decimal],
        weight: Optional[Union[int, float, str]] = None,
        weight_unit: Optional[str] = None,
        volume: Optional[Union[int, float, str]] = None,
        volume_unit: Optional[str] = None,
        currency: str = 'EUR',
        form: Optional[str] = None
    ):
        """
        Инициализирует объект PriceInfo.

        Args:
            price: Цена в указанной валюте
            weight: Вес продукта (если применимо)
            weight_unit: Единица измерения веса (g, kg, oz, lb)
            volume: Объем продукта (если применимо)
            volume_unit: Единица измерения объема (ml, l, oz_fl)
            currency: Код валюты
            form: Форма продукта (например, "powder", "whole")

        Raises:
            ValueError: Если переданы некорректные значения
        """
        # Валидация и установка цены
        self.price = self._validate_price(price)
        self.currency = self._validate_currency(currency)

        # Валидация веса/объема
        if weight is not None and volume is not None:
            raise ValueError("Нельзя одновременно указывать вес и объем")

        # Обработка веса
        if weight is not None:
            if weight_unit not in self.SUPPORTED_WEIGHT_UNITS:
                raise ValueError(f"Неподдерживаемая единица веса: {weight_unit}. "
                               f"Поддерживаемые единицы: {', '.join(self.SUPPORTED_WEIGHT_UNITS)}")
            self.weight = self._validate_numeric("weight", weight)
            self.weight_unit = weight_unit
            self.volume = None
            self.volume_unit = None
        
        # Обработка объема
        elif volume is not None:
            if volume_unit not in self.SUPPORTED_VOLUME_UNITS:
                raise ValueError(f"Неподдерживаемая единица объема: {volume_unit}. "
                               f"Поддерживаемые единицы: {', '.join(self.SUPPORTED_VOLUME_UNITS)}")
            self.volume = self._validate_numeric("volume", volume)
            self.volume_unit = volume_unit
            self.weight = None
            self.weight_unit = None
        
        # Если ни вес, ни объем не указаны
        else:
            self.weight = None
            self.weight_unit = None
            self.volume = None
            self.volume_unit = None

        self.form = form

    def _validate_price(self, price: Union[int, float, str, Decimal]) -> Decimal:
        """Проверяет и конвертирует цену в Decimal."""
        try:
            price_decimal = Decimal(str(price))
            if price_decimal <= 0:
                raise ValueError("Цена должна быть положительным числом")
            return price_decimal
        except (ValueError, TypeError, ArithmeticError) as e:
            raise ValueError(f"Некорректное значение цены: {price}") from e

    def _validate_numeric(self, field: str, value: Union[int, float, str]) -> Decimal:
        """Проверяет и конвертирует числовое значение в Decimal."""
        try:
            numeric_value = Decimal(str(value))
            if numeric_value <= 0:
                raise ValueError(f"{field} должен быть положительным числом")
            return numeric_value
        except (ValueError, TypeError, ArithmeticError) as e:
            raise ValueError(f"Некорректное значение для {field}: {value}") from e

    def _validate_currency(self, currency: str) -> str:
        """Проверяет и нормализует код валюты."""
        currency = currency.upper()
        if currency not in self.SUPPORTED_CURRENCIES:
            raise ValueError(f"Неподдерживаемая валюта: {currency}. "
                           f"Поддерживаемые валюты: {', '.join(self.SUPPORTED_CURRENCIES.keys())}")
        return currency

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

class Product:
    """
    Модель продукта, представляющая товар в каталоге.
    
    Attributes:
        id (Union[int, str]): Уникальный идентификатор продукта (блокчейн ID)
        alias (str): Бизнес-идентификатор продукта из метаданных
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

    def __init__(
        self,
        id: Union[int, str],
        alias: str,
        status: int,
        cid: str,
        title: str,
        organic_components: List[OrganicComponent],
        cover_image_url: str,
        categories: List[str],
        forms: List[str],
        species: str,
        prices: List[PriceInfo]
    ):
        """
        Инициализирует объект Product.
        
        Args:
            id: Уникальный идентификатор продукта (блокчейн ID)
            alias: Бизнес-идентификатор продукта из метаданных
            status: Статус продукта (0 - неактивен, 1 - активен)
            cid: Content Identifier
            title: Название продукта
            organic_components: Список компонентов продукта
            cover_image_url: Ссылка на основное изображение
            categories: Список категорий
            forms: Список форм продукта
            species: Биологический вид
            prices: Список цен
        
        Raises:
            ValueError: Если переданы некорректные значения полей
        """
        # Валидация id
        if isinstance(id, (int, str)):
            self.id = id
        else:
            raise ValueError("ID должен быть числом или строкой")

        # Валидация alias
        if not alias:
            raise ValueError("Alias не может быть пустым")
        self.alias = alias

        # Валидация status
        if status not in [0, 1]:
            raise ValueError("Status должен быть 0 или 1")
        self.status = status

        # Валидация cid
        if not cid:
            raise ValueError("CID не может быть пустым")
        self.cid = cid

        # Валидация title
        if not title:
            raise ValueError("Title не может быть пустым")
        self.title = title

        # Валидация organic_components
        if not isinstance(organic_components, list):
            raise ValueError("Organic components должен быть списком")
        if not organic_components:
            raise ValueError("Organic components не может быть пустым")
        
        # Валидация каждого компонента
        for component in organic_components:
            if not isinstance(component, OrganicComponent):
                raise ValueError("Каждый элемент organic_components должен быть объектом OrganicComponent")
        
        self.organic_components = organic_components

        # Валидация cover_image_url
        if not cover_image_url:
            raise ValueError("Cover image URL не может быть пустым")
        self.cover_image_url = cover_image_url

        # Валидация categories
        if not isinstance(categories, list):
            raise ValueError("Categories должен быть списком")
        self.categories = categories

        # Валидация forms
        if not isinstance(forms, list):
            raise ValueError("Forms должен быть списком")
        self.forms = forms

        # Валидация species
        if not species:
            raise ValueError("Species не может быть пустым")
        self.species = species

        # Валидация prices
        if not isinstance(prices, list):
            raise ValueError("Prices должен быть списком")
        for price in prices:
            if not isinstance(price, PriceInfo):
                raise ValueError("Каждый элемент prices должен быть объектом PriceInfo")
        self.prices = prices

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

    @classmethod
    def from_json(cls, data: Dict) -> 'Product':
        """
        Создает объект Product из JSON-данных.
        
        Args:
            data: Словарь с данными продукта
            
        Returns:
            Product: Новый объект продукта
            
        Raises:
            ValueError: Если в данных отсутствуют обязательные поля
        """
        if not isinstance(data, dict):
            raise ValueError("Входные данные должны быть словарем")

        # Обязательные поля
        required_fields = ['id', 'title', 'cover_image_url', 'species']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Отсутствует обязательное поле '{field}'")

        # Обратная совместимость: поддержка старого формата с description
        if 'organic_components' in data:
            # Новый формат с компонентами
            organic_components_data = data['organic_components']
            if not isinstance(organic_components_data, list):
                raise ValueError("organic_components должен быть списком")
            
            organic_components = [OrganicComponent.from_dict(comp) for comp in organic_components_data]
        elif 'description' in data and 'description_cid' in data:
            # Старый формат: создаем один компонент из description
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
            id=data['id'],
            alias=data.get('alias', str(data['id'])),  # Используем id как alias по умолчанию
            status=data.get('status', 0),  # Продукт создается неактивным по умолчанию
            cid=data.get('cid', str(data['id'])),  # Используем id как CID по умолчанию
            title=data['title'],
            organic_components=organic_components,
            cover_image_url=data['cover_image_url'],
            categories=data.get('categories', []),
            forms=forms_value,
            species=data['species'],
            prices=prices
        )

    def to_json(self) -> Dict:
        """
        Преобразует объект Product в JSON-формат.
        
        Returns:
            Dict: Словарь с данными продукта
        """
        return {
            'id': self.id,
            'alias': self.alias,
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
