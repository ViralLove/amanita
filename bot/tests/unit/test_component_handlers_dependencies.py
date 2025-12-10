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


@pytest.mark.unit
class TestComponentHandlersDependencies:
    """Tests for component_handlers.py dependency injection"""
    
    def test_get_product_formatter_service_creates_formatter_with_localization_service(
        self,
        mock_localization_service  # ← Используем фикстуру (следует паттерну mock_blockchain_service)
    ):
        """
        Проверка: get_product_formatter_service() создаёт formatter с LocalizationService.
        
        AC: formatter.localization_service не равен None.
        
        Изоляция: Использует mock_localization_service для изоляции от реальных зависимостей.
        """
        # ВАЖНО: Мокируем BlockchainService на уровне модуля ДО всех импортов
        # Это предотвращает создание реального BlockchainService → Web3
        # при выполнении exec_module (который может импортировать модули, создающие BlockchainService)
        # Также мокируем ServiceFactory и dependencies.get_localization_service
        with patch('services.core.blockchain.BlockchainService', new=Mock(), create=True) as mock_blockchain_class, \
             patch('services.service_factory.ServiceFactory') as mock_service_factory_class, \
             patch('dependencies.get_localization_service', return_value=mock_localization_service) as mock_get_loc, \
             patch('services.product.registry_singleton.product_registry_service', new=Mock(), create=True):
            
            # Создаем мок ServiceFactory, который возвращает mock_localization_service
            mock_factory_instance = Mock()
            mock_factory_instance.create_localization_service = Mock(return_value=mock_localization_service)
            mock_service_factory_class.return_value = mock_factory_instance
            
            # Импортируем factory метод напрямую из модуля
            # Используем importlib для прямого импорта, минуя handlers.__init__
            # (который может импортировать catalog_handlers → ProductRegistryService → BlockchainService)
            spec = importlib.util.spec_from_file_location(
                "handlers.dependencies",
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "handlers", "dependencies.py"
                )
            )
            handlers_deps = importlib.util.module_from_spec(spec)
            sys.modules['handlers.dependencies'] = handlers_deps
            
            # Выполняем exec_module - dependencies.get_localization_service уже замокирован
            spec.loader.exec_module(handlers_deps)
            
            get_product_formatter_service = handlers_deps.get_product_formatter_service
            
            # Создаём formatter через factory
            # Внутри get_product_formatter_service() будет вызван
            # dependencies.get_localization_service(), который мы замокировали
            formatter = get_product_formatter_service()
            
            # Проверки структуры
            assert formatter is not None, "Formatter должен быть создан"
            assert formatter.localization_service is not None, (
                "LocalizationService должен быть инициализирован через DI"
            )
            assert formatter.localization_service == mock_localization_service, (
                "Должен использоваться LocalizationService через DI"
            )
            
            # ✅ P0 FIX: Проверка реального вызова get_localization_service()
            mock_get_loc.assert_called_once(), (
                "get_localization_service() должен быть вызван через DI"
            )
            
            # ✅ P0 FIX: Проверка реального использования localization_service
            assert formatter.localization_service.t('test.key') == 'Mock Translation', (
                "localization_service должен реально использоваться в formatter"
            )
    
    def test_create_component_description_keyboard_works(
        self,
        mock_localization_service  # ← Используем фикстуру (следует паттерну mock_blockchain_service)
    ):
        """
        Проверка: _create_component_description_keyboard() работает корректно.
        
        AC: Keyboard создаётся без ошибок, содержит 4 кнопки.
        
        Изоляция: Использует mock_localization_service для изоляции от реальных зависимостей.
        """
        # ВАЖНО: Мокируем BlockchainService на уровне модуля ДО всех импортов
        # Это предотвращает создание реального BlockchainService → Web3
        # при выполнении exec_module (который может импортировать модули, создающие BlockchainService)
        # Также мокируем ServiceFactory и dependencies.get_localization_service
        with patch('services.core.blockchain.BlockchainService', new=Mock(), create=True) as mock_blockchain_class, \
             patch('services.service_factory.ServiceFactory') as mock_service_factory_class, \
             patch('dependencies.get_localization_service', return_value=mock_localization_service), \
             patch('services.product.registry_singleton.product_registry_service', new=Mock(), create=True):
            
            # Создаем мок ServiceFactory, который возвращает mock_localization_service
            mock_factory_instance = Mock()
            mock_factory_instance.create_localization_service = Mock(return_value=mock_localization_service)
            mock_service_factory_class.return_value = mock_factory_instance
            
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

