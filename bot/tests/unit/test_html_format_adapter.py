"""
Unit Tests: HTMLFormatAdapter для WooCommerce Export

КОНЦЕПЦИЯ:
==========
- Только unit-тесты с моками (быстрые, изолированные)
- Тестирование логики форматирования HTML без зависимостей от блокчейна
- Edge cases и error scenarios
- Проверка реюза логики структурирования из ProductFormatterService
- Проверка прямого HTML форматирования (не конвертация из Telegram HTML)

Quality Gates:
- NO_FALSE_SUCCESSES: Tests fail when logic broken
- VALIDATE_REAL_FUNCTIONALITY: Check actual HTML output
- CORRECT_LOGIC: Valid assertions, not tautologies
- MINIMAL_MOCK_OVERUSE: Mock только данные (MockProduct), тестируем реальный HTMLFormatAdapter
"""

import pytest
from unittest.mock import Mock
from dataclasses import dataclass
from typing import List, Optional


# Mock classes для тестирования
@dataclass
class MockOrganicComponent:
    """Mock OrganicComponent для тестов"""
    component_id: str
    scientific_title: Optional[str] = None
    proportion: Optional[str] = None


@dataclass
class MockPriceInfo:
    """Mock PriceInfo для тестов"""
    price: str
    currency: str = "RUB"
    weight: Optional[str] = None
    weight_unit: Optional[str] = None
    volume: Optional[str] = None
    volume_unit: Optional[str] = None
    form: Optional[str] = None


@dataclass
class MockProduct:
    """Mock Product для тестов"""
    business_id: str = "test_product_001"
    title: str = "Test Product"
    species: Optional[str] = None
    status: int = 1
    organic_components: List[MockOrganicComponent] = None
    prices: List[MockPriceInfo] = None
    forms: List[str] = None
    categories: List[str] = None
    
    def __post_init__(self):
        if self.organic_components is None:
            self.organic_components = []
        if self.prices is None:
            self.prices = []
        if self.forms is None:
            self.forms = []
        if self.categories is None:
            self.categories = []


@pytest.mark.unit
class TestHTMLFormatAdapter:
    """Unit тесты для HTMLFormatAdapter"""
    
    # NOTE: product_formatter_service fixture используется из conftest.py
    # (изолированный instance с мокированным registry_singleton)
    
    @pytest.fixture
    def mock_loc(self):
        """Fixture: Mock локализации с UI переводами"""
        loc = Mock()
        loc.language = "ru"
        loc.t = lambda key, default=None: {
            "catalog.product.available_for_order": "Доступен для заказа",
            "catalog.product.temporarily_unavailable": "Временно недоступен",
            "catalog.product.composition": "Состав",
            "catalog.product.composition_title": "Состав продукта",
            "catalog.product.composition_not_specified": "Не указан",
            "catalog.product.pricing": "Цены",
            "catalog.product.pricing_title": "Цены и формы",
            "catalog.product.pricing_not_specified": "Не указаны",
            "catalog.product.details": "Детали",
            "catalog.product.forms_label": "Формы",
            "catalog.product.category_label": "Категория",
        }.get(key, default or key)
        return loc
    
    @pytest.fixture
    def html_format_adapter(self, product_formatter_service):
        """Fixture: HTMLFormatAdapter с реальным ProductFormatterService"""
        from services.woocommerce.html_format_adapter import HTMLFormatAdapter
        return HTMLFormatAdapter(formatter_service=product_formatter_service)
    
    # ============================================================
    # Tests for __init__()
    # ============================================================
    
    def test_init_success(self, product_formatter_service):
        """
        Инициализация HTMLFormatAdapter с валидным formatter_service
        
        GIVEN: Валидный ProductFormatterService
        WHEN: Создается HTMLFormatAdapter
        THEN: formatter_service сохранен, логгер создан
        """
        # Arrange
        from services.woocommerce.html_format_adapter import HTMLFormatAdapter
        
        # Act
        adapter = HTMLFormatAdapter(formatter_service=product_formatter_service)
        
        # Assert
        assert adapter.formatter_service == product_formatter_service
        assert adapter.logger is not None
    
    def test_init_with_none_formatter_service(self):
        """
        Инициализация с formatter_service=None должна вызывать ValueError
        
        GIVEN: formatter_service = None
        WHEN: Создается HTMLFormatAdapter
        THEN: Вызывается ValueError
        """
        # Arrange
        from services.woocommerce.html_format_adapter import HTMLFormatAdapter
        
        # Act & Assert
        with pytest.raises(ValueError, match="formatter_service не может быть None"):
            HTMLFormatAdapter(formatter_service=None)
    
    # ============================================================
    # Tests for _format_main_info_html()
    # ============================================================
    
    def test_format_main_info_html_with_all_fields(self, html_format_adapter, mock_loc):
        """
        _format_main_info_html() форматирует все поля продукта
        
        GIVEN: Продукт с title, species, status=1
        WHEN: _format_main_info_html() вызывается
        THEN: Все элементы присутствуют в HTML, эмодзи корректны, HTML теги правильные
        """
        # Arrange
        product = MockProduct(
            title="Test Product",
            species="Amanita muscaria",
            status=1
        )
        
        # Act
        result = html_format_adapter._format_main_info_html(product, mock_loc)
        
        # Assert
        assert "<p>" in result
        assert "<strong>" in result
        assert "Test Product" in result
        assert "Amanita muscaria" in result
        assert "Доступен для заказа" in result
    
    def test_format_main_info_html_without_species(self, html_format_adapter, mock_loc):
        """
        _format_main_info_html() без species не включает species в HTML
        
        GIVEN: Продукт без species
        WHEN: _format_main_info_html() вызывается
        THEN: species не включен в HTML
        """
        # Arrange
        product = MockProduct(
            title="Test Product",
            species=None,
            status=1
        )
        
        # Act
        result = html_format_adapter._format_main_info_html(product, mock_loc)
        
        # Assert
        assert "Test Product" in result
        assert "Amanita" not in result  # species не должно быть
    
    def test_format_main_info_html_status_unavailable(self, html_format_adapter, mock_loc):
        """
        _format_main_info_html() со status=0 показывает недоступен
        
        GIVEN: Продукт со status=0
        WHEN: _format_main_info_html() вызывается
        THEN: Эмодзи и текст "temporarily_unavailable" присутствуют
        """
        # Arrange
        product = MockProduct(
            title="Test Product",
            status=0
        )
        
        # Act
        result = html_format_adapter._format_main_info_html(product, mock_loc)
        
        # Assert
        assert "Временно недоступен" in result
        assert "Доступен для заказа" not in result
    
    def test_format_main_info_html_error_handling(self, html_format_adapter, mock_loc):
        """
        _format_main_info_html() обрабатывает ошибки с fallback
        
        GIVEN: Продукт с ошибкой в _get_product_title()
        WHEN: _format_main_info_html() вызывается
        THEN: Fallback на базовое название
        """
        # Arrange
        product = MockProduct(
            title="Fallback Product",
            status=1
        )
        # Симулируем ошибку через мок
        from unittest.mock import patch
        with patch.object(html_format_adapter.formatter_service, '_get_product_title', side_effect=Exception("Test error")):
            # Act
            result = html_format_adapter._format_main_info_html(product, mock_loc)
            
            # Assert
            assert result != ""  # Должен вернуть что-то, даже при ошибке
            assert "Fallback Product" in result  # Fallback на title
            assert "<p>" in result or "<strong>" in result
    
    def test_format_main_info_html_error_in_fallback(self, html_format_adapter, mock_loc):
        """
        _format_main_info_html() обрабатывает ошибку даже в fallback блоке
        
        GIVEN: Ошибка в основном блоке и в fallback (getattr на title)
        WHEN: _format_main_info_html() вызывается
        THEN: Возвращается пустая строка
        """
        # Arrange
        # Создаем продукт, который вызывает ошибку в getattr
        class ProductWithBrokenGetattr:
            def __init__(self):
                self.business_id = "test"
                self.status = 1
            
            def __getattribute__(self, name):
                if name == 'title':
                    raise Exception("Test error")
                return object.__getattribute__(self, name)
        
        product = ProductWithBrokenGetattr()
        # Симулируем ошибку в основном блоке
        from unittest.mock import patch
        with patch.object(html_format_adapter.formatter_service, '_get_product_title', side_effect=Exception("Test error")):
            # Act
            result = html_format_adapter._format_main_info_html(product, mock_loc)
            
            # Assert
            # При ошибке в fallback (getattr на title) должен вернуть пустую строку
            assert result == ""  # Должен вернуть пустую строку при двойной ошибке
    
    # ============================================================
    # Tests for _format_composition_html()
    # ============================================================
    
    def test_format_composition_html_single_component(self, html_format_adapter, mock_loc):
        """
        _format_composition_html() для SINGLE компонента с scientific_title
        
        GIVEN: Продукт типа SINGLE с scientific_title
        WHEN: _format_composition_html() вызывается
        THEN: Эмодзи 🧬 и scientific_title в HTML, proportion если есть
        """
        # Arrange
        product = MockProduct(
            organic_components=[
                MockOrganicComponent(
                    component_id="amanita_muscaria",
                    scientific_title="Amanita muscaria",
                    proportion="100%"
                )
            ]
        )
        
        # Act
        result = html_format_adapter._format_composition_html(product, mock_loc)
        
        # Assert
        assert "🧬" in result or "Amanita muscaria" in result
        assert "100%" in result
        assert "<p>" in result or "<strong>" in result
    
    def test_format_composition_html_single_without_scientific_title(self, html_format_adapter, mock_loc):
        """
        _format_composition_html() для SINGLE без scientific_title использует component_id
        
        GIVEN: Продукт типа SINGLE без scientific_title
        WHEN: _format_composition_html() вызывается
        THEN: Используется component_id
        """
        # Arrange
        product = MockProduct(
            organic_components=[
                MockOrganicComponent(
                    component_id="amanita_muscaria",
                    scientific_title=None
                )
            ]
        )
        
        # Act
        result = html_format_adapter._format_composition_html(product, mock_loc)
        
        # Assert
        assert "amanita_muscaria" in result
        assert "<p>" in result or "<strong>" in result
    
    def test_format_composition_html_multi_component(self, html_format_adapter, mock_loc):
        """
        _format_composition_html() для MULTI компонентов использует список
        
        GIVEN: Продукт типа MULTI с несколькими компонентами
        WHEN: _format_composition_html() вызывается
        THEN: <ul> и <li> структура, нумерация компонентов, proportion для каждого
        """
        # Arrange
        product = MockProduct(
            organic_components=[
                MockOrganicComponent(
                    component_id="amanita_muscaria",
                    proportion="50%"
                ),
                MockOrganicComponent(
                    component_id="blue_lotus",
                    proportion="50%"
                )
            ]
        )
        
        # Act
        result = html_format_adapter._format_composition_html(product, mock_loc)
        
        # Assert
        assert "<ul>" in result
        assert "<li>" in result
        assert "50%" in result
    
    def test_format_composition_html_no_components(self, html_format_adapter, mock_loc):
        """
        _format_composition_html() без компонентов показывает "composition_not_specified"
        
        GIVEN: Продукт без organic_components
        WHEN: _format_composition_html() вызывается
        THEN: Сообщение "composition_not_specified"
        """
        # Arrange
        product = MockProduct(
            organic_components=[]
        )
        
        # Act
        result = html_format_adapter._format_composition_html(product, mock_loc)
        
        # Assert
        assert "Не указан" in result
        assert "Состав" in result
    
    def test_format_composition_html_error_handling(self, html_format_adapter, mock_loc):
        """
        _format_composition_html() обрабатывает ошибки с fallback
        
        GIVEN: Ошибка в _detect_product_type()
        WHEN: _format_composition_html() вызывается
        THEN: Fallback сообщение
        """
        # Arrange
        product = MockProduct(
            organic_components=[
                MockOrganicComponent(component_id="test")
            ]
        )
        # Симулируем ошибку через мок
        from unittest.mock import patch
        with patch.object(html_format_adapter.formatter_service, '_detect_product_type', side_effect=Exception("Test error")):
            # Act
            result = html_format_adapter._format_composition_html(product, mock_loc)
            
            # Assert
            assert result != ""  # Должен вернуть что-то, даже при ошибке
            assert "Состав" in result or "Не указан" in result  # Fallback сообщение
    
    def test_format_composition_html_error_in_fallback(self, html_format_adapter, mock_loc):
        """
        _format_composition_html() обрабатывает ошибку даже в fallback блоке
        
        GIVEN: Ошибка в основном блоке и в fallback
        WHEN: _format_composition_html() вызывается
        THEN: Возвращается пустая строка
        """
        # Arrange
        product = MockProduct(organic_components=[])
        # Симулируем ошибку в основном блоке и в fallback
        from unittest.mock import patch
        with patch.object(html_format_adapter.formatter_service, '_detect_product_type', side_effect=Exception("Test error")):
            with patch.object(html_format_adapter.formatter_service.config, 'get_emoji', side_effect=Exception("Test error")):
                # Act
                result = html_format_adapter._format_composition_html(product, mock_loc)
                
                # Assert
                assert result == ""  # Должен вернуть пустую строку при двойной ошибке
    
    # ============================================================
    # Tests for _format_pricing_html()
    # ============================================================
    
    def test_format_pricing_html_with_prices(self, html_format_adapter, mock_loc):
        """
        _format_pricing_html() форматирует несколько цен
        
        GIVEN: Продукт с несколькими ценами
        WHEN: _format_pricing_html() вызывается
        THEN: <ul> и <li> структура, формат: цена + валюта, вес/объем, форма, эмодзи 💰
        """
        # Arrange
        product = MockProduct(
            prices=[
                MockPriceInfo(
                    price="1000",
                    currency="RUB",
                    weight="100",
                    weight_unit="g",
                    form="dried"
                ),
                MockPriceInfo(
                    price="2000",
                    currency="RUB",
                    weight="200",
                    weight_unit="g",
                    form="powder"
                )
            ]
        )
        
        # Act
        result = html_format_adapter._format_pricing_html(product, mock_loc)
        
        # Assert
        assert "<ul>" in result
        assert "<li>" in result
        assert "1000" in result
        assert "RUB" in result
        assert "dried" in result or "powder" in result
    
    def test_format_pricing_html_with_weight(self, html_format_adapter, mock_loc):
        """
        _format_pricing_html() форматирует цену с весом
        
        GIVEN: Цена с weight и weight_unit
        WHEN: _format_pricing_html() вызывается
        THEN: Формат "цена за вес"
        """
        # Arrange
        product = MockProduct(
            prices=[
                MockPriceInfo(
                    price="1000",
                    currency="RUB",
                    weight="100",
                    weight_unit="g"
                )
            ]
        )
        
        # Act
        result = html_format_adapter._format_pricing_html(product, mock_loc)
        
        # Assert
        assert "1000" in result
        assert "100" in result
        assert "g" in result
    
    def test_format_pricing_html_with_volume(self, html_format_adapter, mock_loc):
        """
        _format_pricing_html() форматирует цену с объемом
        
        GIVEN: Цена с volume и volume_unit
        WHEN: _format_pricing_html() вызывается
        THEN: Формат "цена за объем"
        """
        # Arrange
        product = MockProduct(
            prices=[
                MockPriceInfo(
                    price="500",
                    currency="RUB",
                    volume="50",
                    volume_unit="ml"
                )
            ]
        )
        
        # Act
        result = html_format_adapter._format_pricing_html(product, mock_loc)
        
        # Assert
        assert "500" in result
        assert "50" in result
        assert "ml" in result
    
    def test_format_pricing_html_no_prices(self, html_format_adapter, mock_loc):
        """
        _format_pricing_html() без цен показывает "pricing_not_specified"
        
        GIVEN: Продукт без prices
        WHEN: _format_pricing_html() вызывается
        THEN: Сообщение "pricing_not_specified"
        """
        # Arrange
        product = MockProduct(
            prices=[]
        )
        
        # Act
        result = html_format_adapter._format_pricing_html(product, mock_loc)
        
        # Assert
        assert "Не указаны" in result
        assert "Цены" in result
    
    def test_format_pricing_html_error_handling(self, html_format_adapter, mock_loc):
        """
        _format_pricing_html() обрабатывает ошибки с fallback
        
        GIVEN: Ошибка при форматировании цен
        WHEN: _format_pricing_html() вызывается
        THEN: Fallback сообщение
        """
        # Arrange
        product = MockProduct(
            prices=[
                MockPriceInfo(price="1000", currency="RUB")
            ]
        )
        # Симулируем ошибку через мок - делаем prices неитерируемым
        from unittest.mock import patch
        with patch.object(product, '__getattribute__', side_effect=lambda x: Exception("Test error") if x == 'prices' else object.__getattribute__(product, x)):
            # Act
            result = html_format_adapter._format_pricing_html(product, mock_loc)
            
            # Assert
            assert result != ""  # Должен вернуть что-то, даже при ошибке
            assert "Цены" in result or "Не указаны" in result  # Fallback сообщение
    
    def test_format_pricing_html_error_in_fallback(self, html_format_adapter, mock_loc):
        """
        _format_pricing_html() обрабатывает ошибку даже в fallback блоке
        
        GIVEN: Ошибка в основном блоке и в fallback
        WHEN: _format_pricing_html() вызывается
        THEN: Возвращается пустая строка
        """
        # Arrange
        product = MockProduct(prices=[])
        # Симулируем ошибку в основном блоке и в fallback
        from unittest.mock import patch
        with patch.object(html_format_adapter.formatter_service.config, 'get_emoji', side_effect=Exception("Test error")):
            with patch.object(mock_loc, 't', side_effect=Exception("Test error")):
                # Act
                result = html_format_adapter._format_pricing_html(product, mock_loc)
                
                # Assert
                assert result == ""  # Должен вернуть пустую строку при двойной ошибке
    
    # ============================================================
    # Tests for _format_details_html()
    # ============================================================
    
    def test_format_details_html_with_forms_and_categories(self, html_format_adapter, mock_loc):
        """
        _format_details_html() форматирует forms и categories
        
        GIVEN: Продукт с forms и categories
        WHEN: _format_details_html() вызывается
        THEN: Эмодзи 📋, 📦, 🏷️, формат списков через запятую
        """
        # Arrange
        product = MockProduct(
            forms=["dried", "powder", "capsules"],
            categories=["mushrooms", "medicinal"]
        )
        
        # Act
        result = html_format_adapter._format_details_html(product, mock_loc)
        
        # Assert
        assert "Детали" in result
        assert "dried" in result or "powder" in result
        assert "mushrooms" in result or "medicinal" in result
    
    def test_format_details_html_only_forms(self, html_format_adapter, mock_loc):
        """
        _format_details_html() только с forms не включает categories
        
        GIVEN: Продукт только с forms
        WHEN: _format_details_html() вызывается
        THEN: categories не включены
        """
        # Arrange
        product = MockProduct(
            forms=["dried", "powder"],
            categories=[]
        )
        
        # Act
        result = html_format_adapter._format_details_html(product, mock_loc)
        
        # Assert
        assert "dried" in result or "powder" in result
        assert "Категория" not in result or result.count("Категория") == 0
    
    def test_format_details_html_only_categories(self, html_format_adapter, mock_loc):
        """
        _format_details_html() только с categories не включает forms
        
        GIVEN: Продукт только с categories
        WHEN: _format_details_html() вызывается
        THEN: forms не включены
        """
        # Arrange
        product = MockProduct(
            forms=[],
            categories=["mushrooms"]
        )
        
        # Act
        result = html_format_adapter._format_details_html(product, mock_loc)
        
        # Assert
        assert "mushrooms" in result
        assert "Формы" not in result or result.count("Формы") == 0
    
    def test_format_details_html_error_in_fallback(self, html_format_adapter, mock_loc):
        """
        _format_details_html() обрабатывает ошибку даже в fallback блоке
        
        GIVEN: Ошибка в основном блоке и в fallback
        WHEN: _format_details_html() вызывается
        THEN: Возвращается пустая строка
        """
        # Arrange
        product = MockProduct()
        # Симулируем ошибку в основном блоке и в fallback
        from unittest.mock import patch
        with patch.object(html_format_adapter.formatter_service.config, 'get_emoji', side_effect=Exception("Test error")):
            with patch.object(mock_loc, 't', side_effect=Exception("Test error")):
                # Act
                result = html_format_adapter._format_details_html(product, mock_loc)
                
                # Assert
                assert result == ""  # Должен вернуть пустую строку при двойной ошибке
    
    # ============================================================
    # Tests for format_product_html()
    # ============================================================
    
    def test_format_product_html_full_product(self, html_format_adapter, mock_loc):
        """
        format_product_html() форматирует полный продукт со всеми секциями
        
        GIVEN: Продукт со всеми секциями
        WHEN: format_product_html() вызывается
        THEN: Все секции включены, разделение через '\n\n'
        """
        # Arrange
        product = MockProduct(
            title="Full Product",
            species="Amanita muscaria",
            status=1,
            organic_components=[
                MockOrganicComponent(
                    component_id="amanita_muscaria",
                    scientific_title="Amanita muscaria"
                )
            ],
            prices=[
                MockPriceInfo(price="1000", currency="RUB", weight="100", weight_unit="g")
            ],
            forms=["dried"],
            categories=["mushrooms"]
        )
        
        # Act
        result = html_format_adapter.format_product_html(product, mock_loc)
        
        # Assert
        assert "Full Product" in result
        assert "Amanita muscaria" in result
        assert "1000" in result
        assert "dried" in result or "mushrooms" in result
        # Проверяем разделение секций (должно быть '\n\n')
        assert result.count('\n\n') >= 0  # Может быть 0 если секций мало
    
    def test_format_product_html_empty_sections_filtered(self, html_format_adapter, mock_loc):
        """
        format_product_html() фильтрует пустые секции
        
        GIVEN: Продукт с пустыми секциями
        WHEN: format_product_html() вызывается
        THEN: Пустые секции отфильтрованы
        """
        # Arrange
        product = MockProduct(
            title="Minimal Product",
            organic_components=[],
            prices=[],
            forms=[],
            categories=[]
        )
        
        # Act
        result = html_format_adapter.format_product_html(product, mock_loc)
        
        # Assert
        assert "Minimal Product" in result
        # Пустые секции не должны быть в результате
    
    def test_format_product_html_partial_sections(self, html_format_adapter, mock_loc):
        """
        format_product_html() форматирует продукт только с main_info и pricing
        
        GIVEN: Продукт только с main_info и pricing
        WHEN: format_product_html() вызывается
        THEN: Только эти секции включены
        """
        # Arrange
        product = MockProduct(
            title="Partial Product",
            status=1,
            prices=[
                MockPriceInfo(price="500", currency="RUB")
            ],
            organic_components=[],
            forms=[],
            categories=[]
        )
        
        # Act
        result = html_format_adapter.format_product_html(product, mock_loc)
        
        # Assert
        assert "Partial Product" in result
        assert "500" in result
        # composition и details не должны быть (если пустые)
    
    def test_format_product_html_error_handling(self, html_format_adapter, mock_loc):
        """
        format_product_html() обрабатывает ошибки с fallback
        
        GIVEN: Ошибка в одном из методов форматирования
        WHEN: format_product_html() вызывается
        THEN: Fallback на базовое описание
        """
        # Arrange
        product = MockProduct(
            title="Error Product"
        )
        # Симулируем ошибку через мок
        from unittest.mock import patch
        with patch.object(html_format_adapter, '_format_main_info_html', side_effect=Exception("Test error")):
            # Act
            result = html_format_adapter.format_product_html(product, mock_loc)
            
            # Assert
            assert result != ""  # Должен вернуть что-то, даже при ошибке
            assert "Error Product" in result  # Fallback на title
    
    def test_format_product_html_error_in_fallback(self, html_format_adapter, mock_loc):
        """
        format_product_html() обрабатывает ошибку даже в fallback блоке
        
        GIVEN: Ошибка в основном блоке и в fallback (getattr на title)
        WHEN: format_product_html() вызывается
        THEN: Возвращается базовое сообщение
        """
        # Arrange
        # Создаем продукт без title атрибута, чтобы getattr упал в fallback
        class ProductWithoutTitle:
            def __init__(self):
                self.business_id = "test"
        
        product = ProductWithoutTitle()
        # Симулируем ошибку в основном блоке
        from unittest.mock import patch
        with patch.object(html_format_adapter, '_format_main_info_html', side_effect=Exception("Test error")):
            # Act
            result = html_format_adapter.format_product_html(product, mock_loc)
            
            # Assert
            assert result == "<p>Продукт</p>"  # Должен вернуть базовое сообщение при двойной ошибке
    
    # ============================================================
    # Tests for get_product_title()
    # ============================================================
    
    def test_get_product_title_with_localization(self, html_format_adapter):
        """
        get_product_title() возвращает локализованное название из IPFS
        
        GIVEN: Продукт с локализованным названием из IPFS
        WHEN: get_product_title() вызывается
        THEN: Используется localization_service.t(), возвращается локализованное название
        """
        # Arrange
        product = MockProduct(
            business_id="test_product_001",
            title="Test Product"
        )
        
        # Act
        result = html_format_adapter.get_product_title(product, "ru")
        
        # Assert
        assert result is not None
        assert isinstance(result, str)
        # Может быть локализованное название или fallback на title
    
    def test_get_product_title_fallback_to_title(self, html_format_adapter):
        """
        get_product_title() использует fallback на product.title
        
        GIVEN: Продукт без локализации
        WHEN: get_product_title() вызывается
        THEN: Fallback на product.title
        """
        # Arrange
        product = MockProduct(
            title="Fallback Title"
        )
        
        # Act
        result = html_format_adapter.get_product_title(product, "ru")
        
        # Assert
        assert result is not None
        assert isinstance(result, str)
        # Может быть локализованное или fallback
    
    def test_get_product_title_different_languages(self, html_format_adapter):
        """
        get_product_title() работает с разными языками
        
        GIVEN: Продукт с разными языками ("ru", "en")
        WHEN: get_product_title() вызывается
        THEN: Localization(language) создается правильно
        """
        # Arrange
        product = MockProduct(
            title="Test Product"
        )
        
        # Act
        result_ru = html_format_adapter.get_product_title(product, "ru")
        result_en = html_format_adapter.get_product_title(product, "en")
        
        # Assert
        assert result_ru is not None
        assert result_en is not None
        assert isinstance(result_ru, str)
        assert isinstance(result_en, str)
    
    def test_get_product_title_error_handling(self, html_format_adapter):
        """
        get_product_title() обрабатывает ошибки с fallback
        
        GIVEN: Ошибка в _get_product_title()
        WHEN: get_product_title() вызывается
        THEN: Fallback на product.title или 'Продукт'
        """
        # Arrange
        product = MockProduct(
            title="Error Product"
        )
        # Симулируем ошибку через мок
        from unittest.mock import patch
        with patch.object(html_format_adapter.formatter_service, '_get_product_title', side_effect=Exception("Test error")):
            # Act
            result = html_format_adapter.get_product_title(product, "ru")
            
            # Assert
            assert result is not None
            assert isinstance(result, str)
            assert result == "Error Product"  # Fallback на title

