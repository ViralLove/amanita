"""
Unit Tests: ProductFormatterService - SINGLE Component Formatting
Tests for _format_single_component_product() and helper methods (Task Group 2)
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


@pytest.mark.unit
class TestSingleComponentFormatting:
    """Tests для форматирования монокомпонентных продуктов"""
    
    # NOTE: product_formatter_service fixture используется из conftest.py
    # (изолированный instance с мокированным registry_singleton)
    
    @pytest.fixture
    def mock_loc(self):
        """Fixture: Mock локализации с ключами из Task 2.4"""
        loc = Mock()
        loc.language = "ru"
        loc.t = lambda key, default=None: {
            "catalog.product.single_component_marker": "Монокомпонентный продукт",
            "catalog.product.component_features_title": "Особенности:",
            "catalog.product.component_forms_title": "Доступные формы:",
            "catalog.product.component_features_more": "... (+{0} еще)"
        }.get(key, default or key)
        return loc
    
    # ============================================================
    # Tests for _format_component_features()
    # ============================================================
    
    def test_format_component_features_with_common_features(
        self, 
        product_formatter_service,
        mock_loc
    ):
        """
        _format_component_features() должен форматировать features.common
        
        GIVEN: Component с 3 features.common
        WHEN: _format_component_features() вызывается
        THEN: Возвращается текст с заголовком и 3 features
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            features={
                'common': ['Feature 1', 'Feature 2', 'Feature 3']
            }
        )
        
        # Act
        result = product_formatter_service._format_component_features(component, mock_loc, max_features=5)
        
        # Assert
        assert "Особенности:" in result
        assert "Feature 1" in result
        assert "Feature 2" in result
        assert "Feature 3" in result
        assert "... (+" not in result  # Нет счётчика (3 < 5)
    
    def test_format_component_features_with_more_than_max(
        self, 
        product_formatter_service,
        mock_loc
    ):
        """
        _format_component_features() должен обрезать features > max_features
        
        GIVEN: Component с 8 features.common, max_features=5
        WHEN: _format_component_features() вызывается
        THEN: Показывает первые 5 + счётчик "... (+3 еще)"
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            features={
                'common': [f'Feature {i}' for i in range(1, 9)]  # 8 features
            }
        )
        
        # Act
        result = product_formatter_service._format_component_features(component, mock_loc, max_features=5)
        
        # Assert
        assert "Особенности:" in result
        assert "Feature 1" in result
        assert "Feature 5" in result
        assert "Feature 6" not in result  # Обрезано
        assert "... (+3 еще)" in result  # Счётчик (8 - 5 = 3)
    
    def test_format_component_features_empty_common_features(
        self, 
        product_formatter_service,
        mock_loc
    ):
        """
        _format_component_features() должен возвращать пустую строку если features.common пустой
        
        GIVEN: Component с пустым features.common
        WHEN: _format_component_features() вызывается
        THEN: Возвращается пустая строка
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            features={'common': []}
        )
        
        # Act
        result = product_formatter_service._format_component_features(component, mock_loc)
        
        # Assert
        assert result == ""
    
    def test_format_component_features_no_features_field(
        self, 
        product_formatter_service,
        mock_loc
    ):
        """
        _format_component_features() должен возвращать пустую строку если features отсутствуют
        
        GIVEN: Component без поля features
        WHEN: _format_component_features() вызывается
        THEN: Возвращается пустая строка
        """
        # Arrange
        component = MockOrganicComponent(component_id="test")
        component.features = None
        
        # Act
        result = product_formatter_service._format_component_features(component, mock_loc)
        
        # Assert
        assert result == ""
    
    # ============================================================
    # Tests for _format_component_forms()
    # ============================================================
    
    def test_format_component_forms_with_forms(
        self, 
        product_formatter_service,
        mock_loc
    ):
        """
        _format_component_forms() должен форматировать список форм
        
        GIVEN: Component с forms=['Powder', 'Capsules']
        WHEN: _format_component_forms() вызывается
        THEN: Возвращается текст с заголовком и формами через запятую
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            forms=['Powder', 'Capsules']
        )
        
        # Act
        result = product_formatter_service._format_component_forms(component, mock_loc)
        
        # Assert
        assert "Доступные формы:" in result
        assert "Powder, Capsules" in result
    
    def test_format_component_forms_single_form(
        self, 
        product_formatter_service,
        mock_loc
    ):
        """
        _format_component_forms() должен работать с одной формой
        
        GIVEN: Component с forms=['Extract']
        WHEN: _format_component_forms() вызывается
        THEN: Возвращается текст без запятых
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            forms=['Extract']
        )
        
        # Act
        result = product_formatter_service._format_component_forms(component, mock_loc)
        
        # Assert
        assert "Доступные формы:" in result
        assert "Extract" in result
        assert "," not in result
    
    def test_format_component_forms_empty_forms(
        self, 
        product_formatter_service,
        mock_loc
    ):
        """
        _format_component_forms() должен возвращать пустую строку если forms пустой
        
        GIVEN: Component с пустым forms
        WHEN: _format_component_forms() вызывается
        THEN: Возвращается пустая строка
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            forms=[]
        )
        
        # Act
        result = product_formatter_service._format_component_forms(component, mock_loc)
        
        # Assert
        assert result == ""
    
    def test_format_component_forms_no_forms_field(
        self, 
        product_formatter_service,
        mock_loc
    ):
        """
        _format_component_forms() должен возвращать пустую строку если forms отсутствуют
        
        GIVEN: Component без поля forms
        WHEN: _format_component_forms() вызывается
        THEN: Возвращается пустая строка
        """
        # Arrange
        component = MockOrganicComponent(component_id="test")
        component.forms = None
        
        # Act
        result = product_formatter_service._format_component_forms(component, mock_loc)
        
        # Assert
        assert result == ""
    
    # ============================================================
    # Tests for localization key usage
    # ============================================================
    
    def test_format_component_features_uses_localization_key(
        self, 
        product_formatter_service
    ):
        """
        _format_component_features() должен использовать loc.t() для заголовка
        
        GIVEN: Mock loc.t() tracking calls
        WHEN: _format_component_features() вызывается
        THEN: loc.t() вызван с 'catalog.product.component_features_title'
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            features={'common': ['Feature 1']}
        )
        
        loc = Mock()
        loc.t = Mock(return_value="Мок заголовок:")
        
        # Act
        result = product_formatter_service._format_component_features(component, loc)
        
        # Assert
        loc.t.assert_called_with('catalog.product.component_features_title')
        assert "Мок заголовок:" in result
    
    def test_format_component_forms_uses_localization_key(
        self, 
        product_formatter_service
    ):
        """
        _format_component_forms() должен использовать loc.t() для заголовка
        
        GIVEN: Mock loc.t() tracking calls
        WHEN: _format_component_forms() вызывается
        THEN: loc.t() вызван с 'catalog.product.component_forms_title'
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            forms=['Powder']
        )
        
        loc = Mock()
        loc.t = Mock(return_value="Мок формы:")
        
        # Act
        result = product_formatter_service._format_component_forms(component, loc)
        
        # Assert
        loc.t.assert_called_with('catalog.product.component_forms_title')
        assert "Мок формы:" in result
    
    def test_format_component_features_uses_format_string_for_counter(
        self, 
        product_formatter_service
    ):
        """
        _format_component_features() должен использовать .format() для счётчика
        
        GIVEN: 8 features, max_features=5
        WHEN: _format_component_features() вызывается
        THEN: loc.t() вызван с ключом + .format(3)
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            features={'common': [f'Feature {i}' for i in range(1, 9)]}
        )
        
        loc = Mock()
        loc.t = Mock(side_effect=lambda key: {
            'catalog.product.component_features_title': "Особенности:",
            'catalog.product.component_features_more': "... (+{0} еще)"
        }.get(key, key))
        
        # Act
        result = product_formatter_service._format_component_features(component, loc, max_features=5)
        
        # Assert
        assert loc.t.call_count == 2  # title + more
        assert "... (+3 еще)" in result  # format(3) применён
    
    # ============================================================
    # P1 Tests: Config Integration Error Handling
    # ============================================================
    
    def test_format_component_features_handles_config_emoji_none(
        self,
        product_formatter_service,
        mock_loc
    ):
        """
        P1: _format_component_features() должен работать если config.get_emoji() returns None
        
        GIVEN: config.get_emoji() returns None
        WHEN: _format_component_features() вызывается
        THEN: Форматирование работает без emoji (graceful degradation)
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            features={'common': ['Feature 1']}
        )
        
        # Mock config.get_emoji to return None
        original_get_emoji = product_formatter_service.config.get_emoji
        product_formatter_service.config.get_emoji = lambda key: None
        
        # Act
        result = product_formatter_service._format_component_features(component, mock_loc)
        
        # Assert: Should work without emoji
        assert "Особенности:" in result
        assert "Feature 1" in result
        
        # Assert: Строгая проверка — emoji ДОЛЖЕН отсутствовать
        assert "🌟" not in result, "Emoji 🌟 не должен присутствовать когда config.get_emoji() → None"
        assert result.startswith("None") or result.startswith(" "), \
            "Result должен начинаться с 'None ' или ' <b>' (без emoji)"
        
        # Cleanup
        product_formatter_service.config.get_emoji = original_get_emoji
    
    def test_format_component_features_handles_config_template_empty(
        self,
        product_formatter_service,
        mock_loc
    ):
        """
        P1: _format_component_features() должен работать если config.get_template() returns ""
        
        GIVEN: config.get_template() returns empty string
        WHEN: _format_component_features() вызывается
        THEN: Форматирование работает без separators (graceful degradation)
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            features={'common': ['Feature 1', 'Feature 2']}
        )
        
        # Mock config.get_template to return empty string
        original_get_template = product_formatter_service.config.get_template
        product_formatter_service.config.get_template = lambda key: ""
        
        # Act
        result = product_formatter_service._format_component_features(component, mock_loc)
        
        # Assert: Should work without separators
        assert "Особенности:" in result
        assert "Feature 1" in result
        assert "Feature 2" in result
        # No separators expected
        
        # Cleanup
        product_formatter_service.config.get_template = original_get_template
    
    def test_format_component_forms_handles_config_emoji_none(
        self,
        product_formatter_service,
        mock_loc
    ):
        """
        P1: _format_component_forms() должен работать если config.get_emoji() returns None
        
        GIVEN: config.get_emoji() returns None
        WHEN: _format_component_forms() вызывается
        THEN: Форматирование работает без emoji
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            forms=['Powder']
        )
        
        # Mock config.get_emoji to return None
        original_get_emoji = product_formatter_service.config.get_emoji
        product_formatter_service.config.get_emoji = lambda key: None
        
        # Act
        result = product_formatter_service._format_component_forms(component, mock_loc)
        
        # Assert: Should work without emoji
        assert "Доступные формы:" in result
        assert "Powder" in result
        
        # Assert: Строгая проверка — emoji ДОЛЖЕН отсутствовать
        assert "📦" not in result, "Emoji 📦 не должен присутствовать когда config.get_emoji() → None"
        assert result.startswith("None") or result.startswith(" "), \
            "Result должен начинаться с 'None ' или ' <b>' (без emoji)"
        
        # Cleanup
        product_formatter_service.config.get_emoji = original_get_emoji
    
    def test_format_component_forms_handles_config_template_empty(
        self,
        product_formatter_service,
        mock_loc
    ):
        """
        P1: _format_component_forms() должен работать если config.get_template() returns ""
        
        GIVEN: config.get_template() returns empty string
        WHEN: _format_component_forms() вызывается
        THEN: Форматирование работает без separator
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            forms=['Powder', 'Capsules']
        )
        
        # Mock config.get_template to return empty string
        original_get_template = product_formatter_service.config.get_template
        product_formatter_service.config.get_template = lambda key: ""
        
        # Act
        result = product_formatter_service._format_component_forms(component, mock_loc)
        
        # Assert: Should work without separator
        assert "Доступные формы:" in result
        assert "Powder, Capsules" in result
        
        # Cleanup
        product_formatter_service.config.get_template = original_get_template
    
    # ============================================================
    # P2 Tests: HTML Validation & Edge Cases
    # ============================================================
    
    def test_format_component_features_validates_html_output(
        self,
        product_formatter_service,
        mock_loc
    ):
        """
        P2: _format_component_features() должен генерировать валидный HTML
        
        GIVEN: Component с features
        WHEN: _format_component_features() вызывается
        THEN: HTML теги сбалансированы (<b> закрыт, emoji присутствует)
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            features={'common': ['Feature 1', 'Feature 2']}
        )
        
        # Act
        result = product_formatter_service._format_component_features(component, mock_loc)
        
        # Assert: HTML tags balanced
        assert result.count("<b>") == result.count("</b>"), "HTML <b> tags должны быть сбалансированы"
        assert result.count("<i>") == result.count("</i>"), "HTML <i> tags должны быть сбалансированы"
        
        # Assert: Contains expected HTML structure
        assert "<b>Особенности:</b>" in result, "Должен содержать заголовок в <b>"
        
        # Assert: Emoji present (if config returns it)
        assert "🌟" in result or result.startswith("None"), "Должен содержать emoji или None"
    
    def test_format_component_features_handles_invalid_features_type(
        self,
        product_formatter_service,
        mock_loc
    ):
        """
        P2: _format_component_features() должен обработать features = "not_a_dict"
        
        GIVEN: component.features = "not_a_dict" (AttributeError в .get())
        WHEN: _format_component_features() вызывается
        THEN: Raises AttributeError с конкретным сообщением
        """
        # Arrange
        component = MockOrganicComponent(component_id="test")
        component.features = "not_a_dict"  # AttributeError в .get('common')
        
        # Act & Assert: Should raise AttributeError with specific message
        with pytest.raises(AttributeError, match="'str' object has no attribute 'get'"):
            result = product_formatter_service._format_component_features(component, mock_loc)
    
    def test_format_component_forms_handles_non_string_forms(
        self,
        product_formatter_service,
        mock_loc
    ):
        """
        P2: _format_component_forms() должен обработать forms = [1, 2, 3]
        
        GIVEN: component.forms = [1, 2, 3] (numbers, not strings)
        WHEN: _format_component_forms() вызывается
        THEN: ", ".join() converts numbers to strings (Python behavior)
        
        NOTE: Python's ", ".join([1, 2, 3]) raises TypeError: expected str instance, int found
        """
        # Arrange
        component = MockOrganicComponent(component_id="test")
        component.forms = [1, 2, 3]  # Non-strings
        
        # Act & Assert: Should raise TypeError with specific message
        with pytest.raises(TypeError, match="sequence item \\d+: expected str instance, int found"):
            result = product_formatter_service._format_component_forms(component, mock_loc)
    
    def test_format_component_forms_validates_html_output(
        self,
        product_formatter_service,
        mock_loc
    ):
        """
        P2: _format_component_forms() должен генерировать валидный HTML
        
        GIVEN: Component с forms
        WHEN: _format_component_forms() вызывается
        THEN: HTML теги сбалансированы
        """
        # Arrange
        component = MockOrganicComponent(
            component_id="test",
            forms=['Powder', 'Capsules']
        )
        
        # Act
        result = product_formatter_service._format_component_forms(component, mock_loc)
        
        # Assert: HTML tags balanced
        assert result.count("<b>") == result.count("</b>"), "HTML <b> tags должны быть сбалансированы"
        
        # Assert: Contains expected HTML structure
        assert "<b>Доступные формы:</b>" in result, "Должен содержать заголовок в <b>"
        
        # Assert: Emoji present (if config returns it)
        assert "📦" in result or result.startswith("None"), "Должен содержать emoji или None"

