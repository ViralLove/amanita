"""
Test Data Factory для создания тестовых данных продуктов.

Централизованное управление тестовыми данными с синхронизацией схемы.
Обеспечивает единый формат данных для всех типов тестов (unit, integration, e2e).

Использование:
    from tests.fixtures.test_data_factory import TestDataFactory
    
    # Создать валидный продукт
    product = TestDataFactory.create_valid_product()
    
    # Создать продукт с переопределениями
    product = TestDataFactory.create_valid_product(
        business_id="custom_id",
        title="Custom Title"
    )
    
    # Создать невалидный продукт (без поля)
    invalid_product = TestDataFactory.create_invalid_product("forms")
    
    # Создать продукт с пустым полем
    empty_product = TestDataFactory.create_product_with_empty_field("title")
"""

from typing import Dict, Any, List, Optional


class TestDataFactory:
    """
    Фабрика тестовых данных для продуктов.
    
    Обеспечивает:
    - Единый источник тестовых данных
    - Автоматическую синхронизацию с схемой валидатора
    - Легкое создание вариаций для разных сценариев
    - Отсутствие legacy полей
    """
    
    # Обязательные поля согласно ProductValidator (validators.py:333)
    REQUIRED_FIELDS = [
        'business_id',
        'title',
        'cover_image_url',
        'species',
        'organic_components',
        'forms'
    ]
    
    # Legacy поля, которые НЕ должны присутствовать
    LEGACY_FIELDS = [
        'description_cid',  # В компонентах (legacy)
        'form',  # Единственное число (legacy, должно быть forms)
        'component_id'  # На уровне продукта (legacy, должно быть в organic_components)
    ]
    
    @staticmethod
    def create_valid_product(**overrides) -> Dict[str, Any]:
        """
        Создает валидный продукт в едином формате.
        
        Все обязательные поля присутствуют, legacy поля отсутствуют.
        Продукт проходит валидацию через ProductValidator.
        
        Args:
            **overrides: Переопределения полей продукта.
                        Позволяет кастомизировать отдельные поля для конкретных тестов.
        
        Returns:
            Dict[str, Any]: Валидный продукт со всеми обязательными полями.
        
        Example:
            >>> product = TestDataFactory.create_valid_product()
            >>> product = TestDataFactory.create_valid_product(
            ...     business_id="custom_id",
            ...     title="Custom Title"
            ... )
        """
        # Базовый валидный продукт в едином формате
        base_product = {
            "business_id": "test_product_1",
            "title": "Test Product",
            "cover_image_url": "Qm123456789abcdefghijklmnopqrstuvwxyz1234567890",
            "species": "Amanita muscaria",
            # ✅ forms всегда массив (даже для одного элемента)
            "forms": ["powder"],
            # ✅ organic_components всегда массив
            "organic_components": [
                {
                    "component_id": "amanita_muscaria",
                    "proportion": "100%"
                    # ✅ НЕТ description_cid (legacy поле удалено в Этапе 5)
                }
            ]
        }
        
        # Применяем переопределения
        base_product.update(overrides)
        
        return base_product
    
    @staticmethod
    def create_invalid_product(missing_field: str, **overrides) -> Dict[str, Any]:
        """
        Создает невалидный продукт с отсутствующим полем.
        
        Используется для тестирования валидации обязательных полей.
        Продукт НЕ проходит валидацию через ProductValidator.
        
        Args:
            missing_field: Название поля для удаления из продукта.
                          Должно быть одним из REQUIRED_FIELDS.
            **overrides: Дополнительные переопределения полей.
        
        Returns:
            Dict[str, Any]: Невалидный продукт без указанного поля.
        
        Example:
            >>> invalid_product = TestDataFactory.create_invalid_product("forms")
            >>> # Продукт без поля forms
            >>> invalid_product = TestDataFactory.create_invalid_product(
            ...     "business_id",
            ...     title="Custom Title"
            ... )
        """
        # Создаем валидный продукт
        product = TestDataFactory.create_valid_product(**overrides)
        
        # Удаляем указанное поле
        product.pop(missing_field, None)
        
        return product
    
    @staticmethod
    def create_product_with_empty_field(empty_field: str, **overrides) -> Dict[str, Any]:
        """
        Создает продукт с пустым полем.
        
        Используется для тестирования валидации пустых значений.
        Продукт НЕ проходит валидацию через ProductValidator.
        
        Args:
            empty_field: Название поля для обнуления.
                        Для массивов (organic_components, forms) устанавливает [].
                        Для строк устанавливает "".
            **overrides: Дополнительные переопределения полей.
        
        Returns:
            Dict[str, Any]: Продукт с пустым указанным полем.
        
        Example:
            >>> empty_product = TestDataFactory.create_product_with_empty_field("title")
            >>> # Продукт с пустым title
            >>> empty_product = TestDataFactory.create_product_with_empty_field(
            ...     "organic_components",
            ...     business_id="custom_id"
            ... )
            >>> # Продукт с пустым массивом organic_components
        """
        # Создаем валидный продукт
        product = TestDataFactory.create_valid_product(**overrides)
        
        # Обрабатываем пустые значения в зависимости от типа поля
        if empty_field == "organic_components":
            product[empty_field] = []
        elif empty_field == "forms":
            product[empty_field] = []
        else:
            # Для строковых полей устанавливаем пустую строку
            product[empty_field] = ""
        
        return product
    
    @staticmethod
    def create_product_with_multiple_components(**overrides) -> Dict[str, Any]:
        """
        Создает валидный продукт с несколькими компонентами (MULTI формат).
        
        Демонстрирует единый формат для MULTI продуктов:
        - organic_components всегда массив (даже для одного компонента)
        - forms всегда массив
        - Разница только в количестве элементов в organic_components
        
        Args:
            **overrides: Переопределения полей продукта.
        
        Returns:
            Dict[str, Any]: Валидный MULTI продукт.
        
        Example:
            >>> multi_product = TestDataFactory.create_product_with_multiple_components()
        """
        base_product = TestDataFactory.create_valid_product(**overrides)
        
        # Обновляем organic_components для MULTI формата
        base_product["organic_components"] = [
            {
                "component_id": "amanita_muscaria",
                "proportion": "50%"
            },
            {
                "component_id": "blue_lotus",
                "proportion": "30%"
            },
            {
                "component_id": "lions_mane",
                "proportion": "20%"
            }
        ]
        
        return base_product
    
    @staticmethod
    def create_product_with_prices(**overrides) -> Dict[str, Any]:
        """
        Создает валидный продукт с ценами.
        
        Args:
            **overrides: Переопределения полей продукта.
        
        Returns:
            Dict[str, Any]: Валидный продукт с ценами.
        
        Example:
            >>> product = TestDataFactory.create_product_with_prices()
        """
        base_product = TestDataFactory.create_valid_product(**overrides)
        
        # Добавляем цены
        base_product["prices"] = [
            {
                "price": "50.00",
                "currency": "EUR",
                "weight": "100",
                "weight_unit": "g"
            }
        ]
        
        return base_product

