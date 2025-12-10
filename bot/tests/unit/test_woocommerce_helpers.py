"""
Unit Tests: Helper Functions для WooCommerce Export

КОНЦЕПЦИЯ:
==========
- Только unit-тесты с моками (быстрые, изолированные)
- Тестирование логики helper функций без зависимостей от блокчейна
- Edge cases и error scenarios
- Проверка реюза логики через HTMLFormatAdapter
- Проверка обработки ошибок и fallback механизмов

Quality Gates:
- NO_FALSE_SUCCESSES: Tests fail when logic broken
- VALIDATE_REAL_FUNCTIONALITY: Check actual function behavior
- CORRECT_LOGIC: Valid assertions, not tautologies
- MINIMAL_MOCK_OVERUSE: Mock только зависимости (HTMLFormatAdapter), тестируем реальные функции
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List, Optional, Union

# Импорт тестируемых функций
from services.woocommerce.export import (
    get_localized_title,
    format_product_description_html,
    prepare_images_list,
    validate_sku_uniqueness
)


# Mock classes для тестирования
@dataclass
class MockProduct:
    """Mock Product для тестов"""
    business_id: str = "test_product_001"
    blockchain_id: Union[int, str] = 123
    title: str = "Test Product"
    cover_image_url: Optional[str] = "https://example.com/image.jpg"
    forms: List[str] = None
    categories: List[str] = None
    status: int = 1
    
    def __post_init__(self):
        if self.forms is None:
            self.forms = ["dried", "powder"]
        if self.categories is None:
            self.categories = ["mushrooms"]


class MockHTMLFormatAdapter:
    """Mock HTMLFormatAdapter для тестов"""
    def __init__(self):
        self.get_product_title_calls = []
        self.format_product_html_calls = []
        self.get_product_title_side_effect = None
        self.format_product_html_side_effect = None
    
    def get_product_title(self, product, language: str) -> str:
        """Mock метод get_product_title"""
        self.get_product_title_calls.append((product, language))
        if self.get_product_title_side_effect:
            if isinstance(self.get_product_title_side_effect, Exception):
                raise self.get_product_title_side_effect
            return self.get_product_title_side_effect
        return f"Локализованное название для {product.business_id} ({language})"
    
    def format_product_html(self, product, loc) -> str:
        """Mock метод format_product_html"""
        self.format_product_html_calls.append((product, loc))
        if self.format_product_html_side_effect:
            if isinstance(self.format_product_html_side_effect, Exception):
                raise self.format_product_html_side_effect
            return self.format_product_html_side_effect
        return f"<p>HTML описание для {product.business_id}</p>"


@pytest.mark.unit
class TestGetLocalizedTitle:
    """Unit тесты для get_localized_title()"""
    
    # ============================================================
    # Tests for get_localized_title() - Success scenarios
    # ============================================================
    
    def test_get_localized_title_success(self):
        """
        get_localized_title() успешно возвращает локализованное название
        
        GIVEN: Product с business_id="test_001", HTMLFormatAdapter возвращает "Локализованное название"
        WHEN: get_localized_title(product, "ru", html_adapter) вызывается
        THEN: Возвращается "Локализованное название"
        """
        # Arrange
        product = MockProduct(business_id="test_001")
        html_adapter = MockHTMLFormatAdapter()
        
        # Act
        result = get_localized_title(product, "ru", html_adapter)
        
        # Assert
        assert result == "Локализованное название для test_001 (ru)"
        assert len(html_adapter.get_product_title_calls) == 1
        assert html_adapter.get_product_title_calls[0] == (product, "ru")
    
    def test_get_localized_title_different_languages(self):
        """
        get_localized_title() работает с разными языками
        
        GIVEN: Product, HTMLFormatAdapter, language="en"
        WHEN: get_localized_title(product, "en", html_adapter) вызывается
        THEN: Возвращается локализованное название для "en"
        """
        # Arrange
        product = MockProduct()
        html_adapter = MockHTMLFormatAdapter()
        
        # Act
        result = get_localized_title(product, "en", html_adapter)
        
        # Assert
        assert result == "Локализованное название для test_product_001 (en)"
        assert html_adapter.get_product_title_calls[0][1] == "en"
    
    # ============================================================
    # Tests for get_localized_title() - Error handling
    # ============================================================
    
    def test_get_localized_title_error_in_adapter(self):
        """
        get_localized_title() обрабатывает ошибку в HTMLFormatAdapter
        
        GIVEN: HTMLFormatAdapter.get_product_title() выбрасывает Exception
        WHEN: get_localized_title(product, "ru", html_adapter) вызывается
        THEN: Возвращается fallback значение (product.title)
        """
        # Arrange
        product = MockProduct(title="Fallback Title")
        html_adapter = MockHTMLFormatAdapter()
        html_adapter.get_product_title_side_effect = Exception("Test error")
        
        # Act
        with patch('services.woocommerce.export.logger') as mock_logger:
            result = get_localized_title(product, "ru", html_adapter)
        
        # Assert
        assert result == "Fallback Title"
        assert mock_logger.error.called
        assert "test_product_001" in str(mock_logger.error.call_args)
    
    def test_get_localized_title_error_no_title(self):
        """
        get_localized_title() возвращает "Продукт" если product.title отсутствует
        
        GIVEN: HTMLFormatAdapter выбрасывает ошибку, product не имеет title
        WHEN: get_localized_title(product, "ru", html_adapter) вызывается
        THEN: Возвращается "Продукт"
        """
        # Arrange
        # Создаем продукт без title через object (не dataclass)
        product_without_title = type('Product', (), {'business_id': 'test_product_001'})()
        html_adapter = MockHTMLFormatAdapter()
        html_adapter.get_product_title_side_effect = Exception("Test error")
        
        # Act
        result = get_localized_title(product_without_title, "ru", html_adapter)
        
        # Assert
        assert result == "Продукт"


@pytest.mark.unit
class TestFormatProductDescriptionHtml:
    """Unit тесты для format_product_description_html()"""
    
    # ============================================================
    # Tests for format_product_description_html() - Success scenarios
    # ============================================================
    
    def test_format_product_description_html_success(self):
        """
        format_product_description_html() успешно форматирует описание
        
        GIVEN: Product, HTMLFormatAdapter возвращает HTML, language="ru"
        WHEN: format_product_description_html(product, "ru", html_adapter) вызывается
        THEN: Возвращается HTML описание
        """
        # Arrange
        product = MockProduct()
        html_adapter = MockHTMLFormatAdapter()
        expected_html = "<p>HTML описание для test_product_001</p>"
        
        # Act
        result = format_product_description_html(product, "ru", html_adapter)
        
        # Assert
        assert result == expected_html
        assert len(html_adapter.format_product_html_calls) == 1
        # Проверяем что был создан Localization объект
        call_args = html_adapter.format_product_html_calls[0]
        assert call_args[0] == product
        assert call_args[1].lang == "ru"  # Localization объект (использует .lang, не .language)
    
    def test_format_product_description_html_different_languages(self):
        """
        format_product_description_html() работает с разными языками
        
        GIVEN: Product, HTMLFormatAdapter, language="en"
        WHEN: format_product_description_html(product, "en", html_adapter) вызывается
        THEN: Создается Localization("en") и передается в адаптер
        """
        # Arrange
        product = MockProduct()
        html_adapter = MockHTMLFormatAdapter()
        
        # Act
        result = format_product_description_html(product, "en", html_adapter)
        
        # Assert
        assert html_adapter.format_product_html_calls[0][1].lang == "en"  # Localization использует .lang
    
    # ============================================================
    # Tests for format_product_description_html() - Error handling
    # ============================================================
    
    def test_format_product_description_html_error_in_adapter(self):
        """
        format_product_description_html() обрабатывает ошибку в HTMLFormatAdapter
        
        GIVEN: HTMLFormatAdapter.format_product_html() выбрасывает Exception
        WHEN: format_product_description_html(product, "ru", html_adapter) вызывается
        THEN: Возвращается fallback значение (f"<p>{product.title}</p>")
        """
        # Arrange
        product = MockProduct(title="Test Product")
        html_adapter = MockHTMLFormatAdapter()
        html_adapter.format_product_html_side_effect = Exception("Test error")
        
        # Act
        with patch('services.woocommerce.export.logger') as mock_logger:
            result = format_product_description_html(product, "ru", html_adapter)
        
        # Assert
        assert result == "<p>Test Product</p>"
        assert mock_logger.error.called
    
    def test_format_product_description_html_error_creating_localization(self):
        """
        format_product_description_html() обрабатывает ошибку при создании Localization
        
        GIVEN: Localization(language) выбрасывает Exception
        WHEN: format_product_description_html(product, "ru", html_adapter) вызывается
        THEN: Возвращается fallback значение
        """
        # Arrange
        product = MockProduct(title="Test Product")
        html_adapter = MockHTMLFormatAdapter()
        
        # Act
        with patch('services.woocommerce.export.Localization', side_effect=Exception("Localization error")):
            with patch('services.woocommerce.export.logger') as mock_logger:
                result = format_product_description_html(product, "ru", html_adapter)
        
        # Assert
        assert result == "<p>Test Product</p>"
        assert mock_logger.error.called


@pytest.mark.unit
class TestPrepareImagesList:
    """Unit тесты для prepare_images_list()"""
    
    # ============================================================
    # Tests for prepare_images_list() - Success scenarios
    # ============================================================
    
    def test_prepare_images_list_with_images(self):
        """
        prepare_images_list() возвращает список изображений для продуктов с cover_image_url
        
        GIVEN: Список продуктов с cover_image_url и формами
        WHEN: prepare_images_list(products, "ru", html_adapter) вызывается
        THEN: Возвращается список словарей с метаданными изображений
        """
        # Arrange
        products = [
            MockProduct(
                business_id="prod_001",
                blockchain_id=123,
                cover_image_url="https://example.com/img1.jpg",
                forms=["dried", "powder"]
            ),
            MockProduct(
                business_id="prod_002",
                blockchain_id=456,
                cover_image_url="https://example.com/img2.jpg",
                forms=["capsules"]
            )
        ]
        html_adapter = MockHTMLFormatAdapter()
        
        # Act
        result = prepare_images_list(products, "ru", html_adapter)
        
        # Assert
        assert len(result) == 3  # 2 формы для prod_001 + 1 форма для prod_002
        assert result[0]["product_sku"] == "123_dried"
        assert result[0]["product_name"] == "Локализованное название для prod_001 (ru)"
        assert result[0]["image_url"] == "https://example.com/img1.jpg"
        assert result[0]["form"] == "dried"
        assert result[0]["blockchain_id"] == 123
        assert result[0]["business_id"] == "prod_001"
    
    def test_prepare_images_list_without_images(self):
        """
        prepare_images_list() пропускает продукты без изображений
        
        GIVEN: Список продуктов, некоторые без cover_image_url
        WHEN: prepare_images_list(products, "ru", html_adapter) вызывается
        THEN: Продукты без изображений не включаются в результат
        """
        # Arrange
        products = [
            MockProduct(
                business_id="prod_001",
                cover_image_url="https://example.com/img1.jpg",
                forms=["dried"]
            ),
            MockProduct(
                business_id="prod_002",
                cover_image_url=None,  # Нет изображения
                forms=["powder"]
            ),
            MockProduct(
                business_id="prod_003",
                cover_image_url="",  # Пустая строка
                forms=["capsules"]
            ),
            MockProduct(
                business_id="prod_004",
                cover_image_url="   ",  # Только пробелы
                forms=["tincture"]
            )
        ]
        html_adapter = MockHTMLFormatAdapter()
        
        # Act
        result = prepare_images_list(products, "ru", html_adapter)
        
        # Assert
        assert len(result) == 1  # Только prod_001 с изображением
        assert result[0]["business_id"] == "prod_001"
    
    def test_prepare_images_list_empty_list(self):
        """
        prepare_images_list() возвращает пустой список для пустого входа
        
        GIVEN: Пустой список продуктов
        WHEN: prepare_images_list([], "ru", html_adapter) вызывается
        THEN: Возвращается пустой список
        """
        # Arrange
        html_adapter = MockHTMLFormatAdapter()
        
        # Act
        result = prepare_images_list([], "ru", html_adapter)
        
        # Assert
        assert result == []
        assert len(html_adapter.get_product_title_calls) == 0
    
    # ============================================================
    # Tests for prepare_images_list() - Edge cases
    # ============================================================
    
    def test_prepare_images_list_no_forms(self):
        """
        prepare_images_list() обрабатывает продукты без форм
        
        GIVEN: Продукт с изображением но без форм
        WHEN: prepare_images_list(products, "ru", html_adapter) вызывается
        THEN: Продукт не включается в результат (нет форм для итерации)
        """
        # Arrange
        product = MockProduct(
            business_id="prod_001",
            cover_image_url="https://example.com/img1.jpg",
            forms=[]  # Пустой список форм
        )
        html_adapter = MockHTMLFormatAdapter()
        
        # Act
        result = prepare_images_list([product], "ru", html_adapter)
        
        # Assert
        assert result == []
    
    def test_prepare_images_list_multiple_forms(self):
        """
        prepare_images_list() создает отдельную запись для каждой формы
        
        GIVEN: Продукт с 3 формами и изображением
        WHEN: prepare_images_list(products, "ru", html_adapter) вызывается
        THEN: Возвращается 3 записи с разными form и product_sku
        """
        # Arrange
        product = MockProduct(
            business_id="prod_001",
            blockchain_id=123,
            cover_image_url="https://example.com/img1.jpg",
            forms=["dried", "powder", "capsules"]
        )
        html_adapter = MockHTMLFormatAdapter()
        
        # Act
        result = prepare_images_list([product], "ru", html_adapter)
        
        # Assert
        assert len(result) == 3
        assert result[0]["form"] == "dried"
        assert result[0]["product_sku"] == "123_dried"
        assert result[1]["form"] == "powder"
        assert result[1]["product_sku"] == "123_powder"
        assert result[2]["form"] == "capsules"
        assert result[2]["product_sku"] == "123_capsules"


@pytest.mark.unit
class TestValidateSkuUniqueness:
    """Unit тесты для validate_sku_uniqueness()"""
    
    # ============================================================
    # Tests for validate_sku_uniqueness() - Unique SKUs
    # ============================================================
    
    def test_validate_sku_uniqueness_unique_skus(self):
        """
        validate_sku_uniqueness() не изменяет уникальные SKU
        
        GIVEN: Список CSV строк с уникальными SKU
        WHEN: validate_sku_uniqueness(csv_rows) вызывается
        THEN: Все SKU остаются без изменений
        """
        # Arrange
        csv_rows = [
            {"SKU": "123_dried", "Name": "Product 1"},
            {"SKU": "456_powder", "Name": "Product 2"},
            {"SKU": "789_capsules", "Name": "Product 3"}
        ]
        
        # Act
        result = validate_sku_uniqueness(csv_rows)
        
        # Assert
        assert len(result) == 3
        assert result[0]["SKU"] == "123_dried"
        assert result[1]["SKU"] == "456_powder"
        assert result[2]["SKU"] == "789_capsules"
    
    # ============================================================
    # Tests for validate_sku_uniqueness() - Duplicate SKUs
    # ============================================================
    
    def test_validate_sku_uniqueness_duplicate_skus(self):
        """
        validate_sku_uniqueness() добавляет суффиксы к дубликатам
        
        GIVEN: Список CSV строк с дубликатами SKU
        WHEN: validate_sku_uniqueness(csv_rows) вызывается
        THEN: Дубликаты получают суффиксы (_1, _2, и т.д.)
        """
        # Arrange
        csv_rows = [
            {"SKU": "123_dried", "Name": "Product 1"},
            {"SKU": "123_dried", "Name": "Product 2"},
            {"SKU": "123_dried", "Name": "Product 3"}
        ]
        
        # Act
        with patch('services.woocommerce.export.logger') as mock_logger:
            result = validate_sku_uniqueness(csv_rows)
        
        # Assert
        assert len(result) == 3
        assert result[0]["SKU"] == "123_dried"  # Первое вхождение без суффикса
        assert result[1]["SKU"] == "123_dried_1"  # Первый дубликат
        assert result[2]["SKU"] == "123_dried_2"  # Второй дубликат
        assert mock_logger.warning.call_count == 2  # 2 предупреждения для дубликатов
    
    def test_validate_sku_uniqueness_duplicate_variation_skus(self):
        """
        validate_sku_uniqueness() обрабатывает дубликаты в Variation SKU
        
        GIVEN: Список CSV строк с дубликатами Variation SKU
        WHEN: validate_sku_uniqueness(csv_rows) вызывается
        THEN: Дубликаты Variation SKU получают суффиксы
        """
        # Arrange
        csv_rows = [
            {"Variation SKU": "123_dried_100g_EUR", "Parent": "123_dried"},
            {"Variation SKU": "123_dried_100g_EUR", "Parent": "123_dried"}
        ]
        
        # Act
        result = validate_sku_uniqueness(csv_rows)
        
        # Assert
        assert len(result) == 2
        assert result[0]["Variation SKU"] == "123_dried_100g_EUR"
        assert result[1]["Variation SKU"] == "123_dried_100g_EUR_1"
    
    def test_validate_sku_uniqueness_update_parent(self):
        """
        validate_sku_uniqueness() обновляет Parent если он ссылается на дубликат
        
        GIVEN: CSV строки с дубликатами SKU, Parent ссылается на дубликат
        WHEN: validate_sku_uniqueness(csv_rows) вызывается
        THEN: Parent обновляется на новый SKU с суффиксом
        """
        # Arrange
        csv_rows = [
            {"SKU": "123_dried", "Name": "Product 1"},
            {"SKU": "123_dried", "Name": "Product 2", "Parent": "123_dried"}
        ]
        
        # Act
        result = validate_sku_uniqueness(csv_rows)
        
        # Assert
        assert len(result) == 2
        assert result[0]["SKU"] == "123_dried"
        assert result[1]["SKU"] == "123_dried_1"
        assert result[1]["Parent"] == "123_dried_1"  # Parent обновлен
    
    # ============================================================
    # Tests for validate_sku_uniqueness() - Edge cases
    # ============================================================
    
    def test_validate_sku_uniqueness_no_sku(self):
        """
        validate_sku_uniqueness() обрабатывает строки без SKU
        
        GIVEN: Список CSV строк, некоторые без SKU
        WHEN: validate_sku_uniqueness(csv_rows) вызывается
        THEN: Строки без SKU добавляются без изменений
        """
        # Arrange
        csv_rows = [
            {"SKU": "123_dried", "Name": "Product 1"},
            {"Name": "Product 2"},  # Нет SKU
            {"SKU": "", "Name": "Product 3"},  # Пустой SKU
            {"Variation SKU": "", "Name": "Product 4"}  # Пустой Variation SKU
        ]
        
        # Act
        result = validate_sku_uniqueness(csv_rows)
        
        # Assert
        assert len(result) == 4
        assert result[0]["SKU"] == "123_dried"
        assert "SKU" not in result[1] or result[1].get("SKU") == ""
        assert result[2]["SKU"] == ""
        assert result[3].get("Variation SKU") == ""
    
    def test_validate_sku_uniqueness_mixed_sku_types(self):
        """
        validate_sku_uniqueness() обрабатывает смешанные SKU и Variation SKU
        
        GIVEN: Список CSV строк с SKU и Variation SKU
        WHEN: validate_sku_uniqueness(csv_rows) вызывается
        THEN: Оба типа обрабатываются корректно
        """
        # Arrange
        csv_rows = [
            {"SKU": "123_dried", "Name": "Product 1"},
            {"Variation SKU": "123_dried_100g_EUR", "Parent": "123_dried"},
            {"SKU": "456_powder", "Name": "Product 2"}
        ]
        
        # Act
        result = validate_sku_uniqueness(csv_rows)
        
        # Assert
        assert len(result) == 3
        assert result[0]["SKU"] == "123_dried"
        assert result[1]["Variation SKU"] == "123_dried_100g_EUR"
        assert result[2]["SKU"] == "456_powder"
    
    def test_validate_sku_uniqueness_multiple_duplicate_groups(self):
        """
        validate_sku_uniqueness() обрабатывает множественные группы дубликатов
        
        GIVEN: Список CSV строк с несколькими группами дубликатов
        WHEN: validate_sku_uniqueness(csv_rows) вызывается
        THEN: Каждая группа обрабатывается независимо
        """
        # Arrange
        csv_rows = [
            {"SKU": "123_dried", "Name": "Product 1"},
            {"SKU": "123_dried", "Name": "Product 2"},
            {"SKU": "456_powder", "Name": "Product 3"},
            {"SKU": "456_powder", "Name": "Product 4"},
            {"SKU": "456_powder", "Name": "Product 5"}
        ]
        
        # Act
        result = validate_sku_uniqueness(csv_rows)
        
        # Assert
        assert len(result) == 5
        assert result[0]["SKU"] == "123_dried"
        assert result[1]["SKU"] == "123_dried_1"
        assert result[2]["SKU"] == "456_powder"
        assert result[3]["SKU"] == "456_powder_1"
        assert result[4]["SKU"] == "456_powder_2"

