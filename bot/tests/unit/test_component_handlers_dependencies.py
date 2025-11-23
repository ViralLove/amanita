"""
Unit tests for component_handlers.py dependency injection fix.

Tests that component_handlers.py correctly uses get_product_formatter_service()
instead of direct ProductFormatterService() instantiation.

Focus: Verify that formatter is created with LocalizationService via DI.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sys
import os
import importlib.util


class TestComponentHandlersDependencies:
    """Tests for component_handlers.py dependency injection"""
    
    def test_get_product_formatter_service_creates_formatter_with_localization_service(self):
        """
        Проверка: get_product_formatter_service() создаёт formatter с LocalizationService.
        
        AC: formatter.localization_service не равен None.
        """
        # Импортируем напрямую из модуля, избегая импорта handlers.__init__
        # Это важно, так как handlers.__init__ импортирует catalog_handlers, 
        # который создаёт ProductRegistryService, который создаёт BlockchainService
        
        # Патчим dependencies.get_localization_service, чтобы избежать реальной инициализации
        with patch('dependencies.get_localization_service') as mock_get_loc:
            # Создаём мок LocalizationService
            from services.common.localization_service import LocalizationService
            mock_loc_service = MagicMock(spec=LocalizationService)
            mock_get_loc.return_value = mock_loc_service
            
            # Импортируем factory метод напрямую из модуля
            # Используем importlib для прямого импорта, минуя __init__.py
            spec = importlib.util.spec_from_file_location(
                "handlers.dependencies",
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "handlers", "dependencies.py"
                )
            )
            handlers_deps = importlib.util.module_from_spec(spec)
            sys.modules['handlers.dependencies'] = handlers_deps
            spec.loader.exec_module(handlers_deps)
            
            get_product_formatter_service = handlers_deps.get_product_formatter_service
            
            # Создаём formatter через factory (как в component_handlers.py строка 212)
            formatter = get_product_formatter_service()
            
            # Проверяем, что formatter создан
            assert formatter is not None, "Formatter должен быть создан"
            
            # Проверяем, что LocalizationService инициализирован
            assert formatter.localization_service is not None, (
                "LocalizationService должен быть инициализирован через DI"
            )
            
            # Проверяем, что использован правильный LocalizationService
            assert formatter.localization_service == mock_loc_service, (
                "Должен использоваться LocalizationService через DI"
            )
    
    def test_create_component_description_keyboard_works(self):
        """
        Проверка: _create_component_description_keyboard() работает корректно.
        
        AC: Keyboard создаётся без ошибок, содержит 4 кнопки.
        """
        # Патчим dependencies.get_localization_service
        with patch('dependencies.get_localization_service') as mock_get_loc:
            from services.common.localization_service import LocalizationService
            mock_loc_service = MagicMock(spec=LocalizationService)
            mock_get_loc.return_value = mock_loc_service
            
            # Импортируем напрямую из модуля
            spec = importlib.util.spec_from_file_location(
                "handlers.dependencies",
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "handlers", "dependencies.py"
                )
            )
            handlers_deps = importlib.util.module_from_spec(spec)
            sys.modules['handlers.dependencies'] = handlers_deps
            spec.loader.exec_module(handlers_deps)
            
            get_product_formatter_service = handlers_deps.get_product_formatter_service
            formatter = get_product_formatter_service()
            
            # Вызываем метод создания keyboard (как в component_handlers.py строка 213)
            component_id = "test_component"
            language = "ru"
            product_id = "test_product"
            
            keyboard = formatter._create_component_description_keyboard(
                component_id,
                language,
                product_id
            )
            
            # Проверяем, что keyboard создан
            assert keyboard is not None, "Keyboard должен быть создан"
            assert isinstance(keyboard, InlineKeyboardMarkup), (
                "Keyboard должен быть экземпляром InlineKeyboardMarkup"
            )
            
            # Проверяем структуру keyboard (4 кнопки для 4 секций)
            assert keyboard.inline_keyboard is not None, "Keyboard должен содержать кнопки"
            assert len(keyboard.inline_keyboard) == 4, (
                "Keyboard должен содержать 4 кнопки (generic, effects, shamanic, warnings)"
            )
            
            # Проверяем callback_data для каждой кнопки
            expected_sections = ["generic", "effects", "shamanic", "warnings"]
            for i, section in enumerate(expected_sections):
                button_row = keyboard.inline_keyboard[i]
                assert len(button_row) == 1, f"Строка {i} должна содержать 1 кнопку"
                button = button_row[0]
                assert isinstance(button, InlineKeyboardButton), f"Кнопка {i} должна быть InlineKeyboardButton"
                expected_callback = f"component_desc:{component_id}:{section}:{language}"
                assert button.callback_data == expected_callback, (
                    f"Callback data для {section} должен быть {expected_callback}, "
                    f"получен {button.callback_data}"
                )
    
    def test_component_handlers_uses_correct_import(self):
        """
        Проверка: component_handlers.py использует правильный импорт get_product_formatter_service.
        
        AC: В component_handlers.py используется импорт из handlers.dependencies, а не прямой ProductFormatterService.
        """
        # Проверяем содержимое файла component_handlers.py
        component_handlers_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "handlers", "catalog", "component_handlers.py"
        )
        
        with open(component_handlers_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем, что используется импорт из handlers.dependencies
        assert "from handlers.dependencies import get_product_formatter_service" in content, (
            "component_handlers.py должен импортировать get_product_formatter_service из handlers.dependencies"
        )
        
        # Проверяем, что используется вызов factory метода
        assert "get_product_formatter_service()" in content, (
            "component_handlers.py должен использовать get_product_formatter_service() вместо прямого создания"
        )
        
        # Проверяем, что НЕ используется прямой импорт ProductFormatterService для создания
        # (может быть импорт для типа, но не для создания экземпляра)
        # Проверяем, что нет строки типа "formatter = ProductFormatterService()"
        assert "formatter = ProductFormatterService()" not in content, (
            "component_handlers.py НЕ должен создавать ProductFormatterService() напрямую"
        )

