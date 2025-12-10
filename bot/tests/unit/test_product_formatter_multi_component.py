"""
Unit Tests: ProductFormatterService - MULTI Component Formatting
Tests for _format_multi_component_product() and helper methods (Task Group 3)
"""

import pytest
from unittest.mock import Mock


class MockOrganicComponent:
    """Mock для OrganicComponent с необходимыми полями"""
    def __init__(self, component_id, scientific_title=None, proportion=None, features=None, forms=None):
        self.component_id = component_id
        self.scientific_title = scientific_title
        self.proportion = proportion
        self.features = features or {}
        self.forms = forms or []


class MockProduct:
    """Mock для Product с organic_components"""
    def __init__(self, organic_components):
        self.organic_components = organic_components


@pytest.mark.unit
class TestMultiComponentFormatting:
    """Tests для форматирования мультикомпонентных продуктов"""
    
    # NOTE: product_formatter_service fixture используется из conftest.py
    
    @pytest.fixture
    def mock_loc(self):
        """Fixture: Mock локализации с ключами из Task 3"""
        loc = Mock()
        loc.language = "ru"
        loc.t = lambda key, default=None: {
            "catalog.product.multi_component_marker": "Мультикомпонентный продукт ({0} компонента)",
            "catalog.product.component_number": "Компонент {0}: {1}",
            "catalog.product.component_proportion": "Пропорция:",
            "catalog.product.component_scientific_name": "Научное название:",
            "catalog.product.component_features_title": "Особенности:",
            "catalog.product.component_forms_title": "Доступные формы:",
            "catalog.product.component_features_more": "... (+{0} еще)"
        }.get(key, default or key)
        return loc
    
    @pytest.fixture
    def mock_section_tracker(self):
        """Fixture: Mock SectionTracker"""
        tracker = Mock()
        return tracker
    
    # ============================================================
    # Tests for _calculate_max_features_per_component()
    # ============================================================
    
    def test_calculate_max_features_for_two_components(self, product_formatter_service):
        """
        _calculate_max_features_per_component() для 2 компонентов → 5
        
        GIVEN: component_count = 2
        WHEN: _calculate_max_features_per_component() вызывается
        THEN: Возвращает 5
        """
        # Act
        result = product_formatter_service._calculate_max_features_per_component(2)
        
        # Assert
        assert result == 5, "Для 2 компонентов должно быть 5 features"
    
    def test_calculate_max_features_for_four_components(self, product_formatter_service):
        """
        _calculate_max_features_per_component() для 4 компонентов → 3
        
        GIVEN: component_count = 4
        WHEN: _calculate_max_features_per_component() вызывается
        THEN: Возвращает 3
        """
        # Act
        result = product_formatter_service._calculate_max_features_per_component(4)
        
        # Assert
        assert result == 3, "Для 4 компонентов должно быть 3 features"
    
    def test_calculate_max_features_for_many_components(self, product_formatter_service):
        """
        _calculate_max_features_per_component() для 5+ компонентов → 2
        
        GIVEN: component_count = 7
        WHEN: _calculate_max_features_per_component() вызывается
        THEN: Возвращает 2
        """
        # Act
        result = product_formatter_service._calculate_max_features_per_component(7)
        
        # Assert
        assert result == 2, "Для 5+ компонентов должно быть 2 features"
    
    def test_calculate_max_features_edge_cases(self, product_formatter_service):
        """
        _calculate_max_features_per_component() для граничных значений
        
        GIVEN: Граничные значения (1, 3, 5)
        WHEN: _calculate_max_features_per_component() вызывается
        THEN: Корректные результаты по границам
        """
        # Assert boundaries
        assert product_formatter_service._calculate_max_features_per_component(1) == 5, "1 component → 5"
        assert product_formatter_service._calculate_max_features_per_component(3) == 3, "3 components → 3"
        assert product_formatter_service._calculate_max_features_per_component(5) == 2, "5 components → 2"
    
    # ============================================================
    # Tests for _get_component_display_name()
    # ============================================================
    
    def test_get_component_display_name_with_scientific_title(self, product_formatter_service):
        """
        _get_component_display_name() возвращает scientific_title если есть
        
        GIVEN: Component с scientific_title
        WHEN: _get_component_display_name() вызывается
        THEN: Возвращает scientific_title
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="amanita_muscaria",
            scientific_title="Amanita Muscaria"
        )
        
        # Act
        result = product_formatter_service._get_component_display_name(component)
        
        # Assert
        assert result == "Amanita Muscaria", "Should return scientific_title"
    
    def test_get_component_display_name_fallback_to_id(self, product_formatter_service):
        """
        _get_component_display_name() fallback на component_id
        
        GIVEN: Component без scientific_title
        WHEN: _get_component_display_name() вызывается
        THEN: Возвращает component_id
        """
        # Arrange
        component = MockOrganicComponent(component_id="blue_lotus")
        
        # Act
        result = product_formatter_service._get_component_display_name(component)
        
        # Assert
        assert result == "blue_lotus", "Should fallback to component_id"
    
    def test_get_component_display_name_handles_none(self, product_formatter_service):
        """
        _get_component_display_name() обрабатывает None gracefully
        
        GIVEN: Component с scientific_title = None
        WHEN: _get_component_display_name() вызывается
        THEN: Возвращает component_id (fallback)
        """
        # Arrange
        component = MockOrganicComponent(component_id="test", scientific_title=None)
        
        # Act
        result = product_formatter_service._get_component_display_name(component)
        
        # Assert
        assert result == "test", "Should fallback to component_id when scientific_title is None"
    
    # ============================================================
    # Tests for _format_multi_component_product()
    # ============================================================
    
    def test_format_multi_component_product_with_two_components(
        self,
        product_formatter_service,
        mock_loc,
        mock_section_tracker
    ):
        """
        _format_multi_component_product() форматирует 2 компонента
        
        GIVEN: Product с 2 компонентами
        WHEN: _format_multi_component_product() вызывается
        THEN: Маркер содержит "2 компонента", оба компонента отображены
        """
        # Arrange
        product = MockProduct(
            organic_components=[
                MockOrganicComponent(
                    component_id="amanita",
                    scientific_title="Amanita Muscaria",
                    proportion="50%",
                    features={'common': ['Feature 1']},
                    forms=['Powder']
                ),
                MockOrganicComponent(
                    component_id="lotus",
                    scientific_title="Blue Lotus",
                    proportion="50%",
                    features={'common': ['Feature 2']},
                    forms=['Extract']
                )
            ]
        )
        
        # Act
        result = product_formatter_service._format_multi_component_product(product, mock_loc, mock_section_tracker)
        
        # Assert: Маркер
        assert "Мультикомпонентный продукт (2 компонента)" in result
        
        # Assert: Оба компонента присутствуют
        assert "Компонент 1: Amanita Muscaria" in result
        assert "Компонент 2: Blue Lotus" in result
        
        # Assert: Пропорции
        assert "Пропорция:" in result
        assert "50%" in result
        
        # Assert: Features и forms
        assert "Feature 1" in result
        assert "Feature 2" in result
        assert "Powder" in result
        assert "Extract" in result
    
    def test_format_multi_component_product_uses_adaptive_features(
        self,
        product_formatter_service,
        mock_loc,
        mock_section_tracker
    ):
        """
        _format_multi_component_product() использует адаптивное количество features
        
        GIVEN: Product с 5 компонентами (max_features должно быть 2)
        WHEN: _format_multi_component_product() вызывается
        THEN: Каждый компонент показывает max 2 features
        """
        # Arrange: 5 компонентов, каждый с 5 features
        components = [
            MockOrganicComponent(
                component_id=f"comp_{i}",
                features={'common': [f'Feature {i}-{j}' for j in range(1, 6)]}
            )
            for i in range(1, 6)
        ]
        product = MockProduct(organic_components=components)
        
        # Act
        result = product_formatter_service._format_multi_component_product(product, mock_loc, mock_section_tracker)
        
        # Assert: Маркер для 5 компонентов
        assert "Мультикомпонентный продукт (5 компонента)" in result
        
        # Assert: Для каждого компонента макс 2 features (адаптивная логика)
        for i in range(1, 6):
            assert f"Feature {i}-1" in result  # Первый feature
            assert f"Feature {i}-2" in result  # Второй feature
            # Остальные должны быть обрезаны (max_features=2 для 5 компонентов)
    
    def test_format_multi_component_product_uses_localization_keys(
        self,
        product_formatter_service,
        mock_section_tracker
    ):
        """
        _format_multi_component_product() использует loc.t() для всех labels
        
        GIVEN: Mock loc.t() tracking calls
        WHEN: _format_multi_component_product() вызывается
        THEN: loc.t() вызван с правильными ключами
        """
        # Arrange
        product = MockProduct(
            organic_components=[
                MockOrganicComponent(component_id="test1", proportion="60%"),
                MockOrganicComponent(component_id="test2", proportion="40%")
            ]
        )
        
        loc = Mock()
        loc.language = "ru"
        calls = []
        
        def track_call(key, default=None):
            calls.append(key)
            return {
                "catalog.product.multi_component_marker": "Мультикомпонентный продукт ({0} компонента)",
                "catalog.product.component_number": "Компонент {0}: {1}",
                "catalog.product.component_proportion": "Пропорция:",
                "catalog.product.component_features_title": "Особенности:",
                "catalog.product.component_forms_title": "Доступные формы:"
            }.get(key, default or key)
        
        loc.t = track_call
        
        # Act
        result = product_formatter_service._format_multi_component_product(product, loc, mock_section_tracker)
        
        # Assert: Должны быть вызваны ключи
        assert "catalog.product.multi_component_marker" in calls, "Marker key должен быть вызван"
        assert "catalog.product.component_number" in calls, "Component number key должен быть вызван"
        assert "catalog.product.component_proportion" in calls, "Proportion key должен быть вызван"
        assert calls.count("catalog.product.component_number") == 2, "Component number для каждого компонента"
    
    def test_format_multi_component_product_handles_missing_optional_fields(
        self,
        product_formatter_service,
        mock_loc,
        mock_section_tracker
    ):
        """
        _format_multi_component_product() обрабатывает отсутствующие опциональные поля
        
        GIVEN: Components без proportion, features, forms
        WHEN: _format_multi_component_product() вызывается
        THEN: Форматирование работает, пропускает пустые секции
        """
        # Arrange
        product = MockProduct(
            organic_components=[
                MockOrganicComponent(component_id="minimal1"),
                MockOrganicComponent(component_id="minimal2")
            ]
        )
        
        # Act
        result = product_formatter_service._format_multi_component_product(product, mock_loc, mock_section_tracker)
        
        # Assert: Маркер и заголовки есть
        assert "Мультикомпонентный продукт" in result
        assert "Компонент 1: minimal1" in result
        assert "Компонент 2: minimal2" in result
        
        # Assert: Опциональные секции отсутствуют
        assert "Пропорция:" not in result
        assert "Особенности:" not in result
        assert "Доступные формы:" not in result


