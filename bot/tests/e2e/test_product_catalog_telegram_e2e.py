"""
E2E Tests for Product Catalog via Telegram Bot Handler.

Tests the complete catalog loading flow through Telegram handler:
1. Telegram CallbackQuery handling
2. Catalog loading via CatalogHandler
3. Language support (ru, en)
4. Integration with ProductRegistryService

Based on: @temp-test-fixes-architecture.md (Section 3.5)
"""

import pytest
import logging
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Any

logger = logging.getLogger(__name__)


@pytest.mark.e2e
class TestProductCatalogTelegramE2E:
    """
    E2E tests for product catalog via Telegram bot handler.
    
    GOAL: Validate complete catalog loading pipeline from Telegram handler to UI.
    
    Prerequisites:
    - E2E_USE_STUBS=true (uses stub services for fast execution)
    - Local profile with caching enabled
    - Test data from fixtures/products.json
    
    Tests:
    1. Catalog loads via Telegram handler (Russian)
    2. Catalog loads via Telegram handler (English)
    """
    
    @pytest.fixture
    def mock_callback_query(self):
        """Создает мок CallbackQuery для Telegram handler"""
        callback = Mock()
        callback.data = "menu:catalog"
        callback.from_user = Mock()
        callback.from_user.id = 12345
        callback.from_user.language_code = "ru"
        callback.message = Mock()
        callback.message.message_id = 100
        callback.message.chat = Mock()
        callback.message.chat.id = 12345
        callback.message.answer = AsyncMock(return_value=Mock())
        callback.message.edit_text = AsyncMock(return_value=Mock())
        callback.message.delete = AsyncMock(return_value=True)
        callback.answer = AsyncMock(return_value=True)
        return callback
    
    @pytest.fixture
    def mock_catalog_service(self):
        """Создает мок CatalogService"""
        service = Mock()
        service.get_catalog_with_progress = AsyncMock(return_value=[])
        service.send_catalog_to_user = AsyncMock(return_value=None)
        return service
    
    @pytest.fixture
    def mock_product_registry_service(self):
        """Создает мок ProductRegistryService"""
        service = Mock()
        service.get_all_products = AsyncMock(return_value=[])
        return service
    
    @pytest.fixture
    def mock_localization(self, language="ru"):
        """Создает мок локализации для указанного языка"""
        loc = Mock()
        loc.language = language
        loc.t = lambda key, **kwargs: f"Localized[{language}]: {key}"
        return loc
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_catalog_loads_via_telegram_handler_ru(
        self,
        mock_callback_query,
        mock_catalog_service,
        mock_product_registry_service,
        e2e_local_profile,
        caplog
    ):
        """
        E2E TEST: Catalog loads via Telegram handler (Russian)
        
        Проверяет загрузку каталога через Telegram handler на русском языке.
        """
        logger.info("="*80)
        logger.info("E2E TEST: Catalog loads via Telegram handler (Russian)")
        logger.info("="*80)
        
        # Импорт EnvironmentValidator для проверки окружения
        from bot.tests.fixtures.env_validator import EnvironmentValidator
        
        # Проверка окружения
        is_valid, error_message = EnvironmentValidator.validate_e2e_environment()
        if not is_valid:
            pytest.skip(f"⚠️ {error_message}")
        
        use_stubs = EnvironmentValidator.should_use_stubs()
        if use_stubs:
            logger.info("✅ E2E_USE_STUBS=true: stub режим активирован")
        else:
            node_available, node_message = EnvironmentValidator.validate_hardhat_node()
            if not node_available:
                pytest.skip(f"⚠️ Hardhat node недоступен: {node_message}. Установите E2E_USE_STUBS=true для stub режима.")
        
        # Настраиваем мок для локализации (русский язык)
        mock_callback_query.from_user.language_code = "ru"
        
        # Настраиваем мок CatalogService для возврата тестовых продуктов
        test_products = [
            Mock(business_id="test_product_1", title="Test Product 1"),
            Mock(business_id="test_product_2", title="Test Product 2"),
        ]
        mock_catalog_service.get_catalog_with_progress = AsyncMock(return_value=test_products)
        
        # Мокируем зависимости
        mock_user_settings = Mock()
        mock_user_settings.get_language = Mock(return_value="ru")
        
        with patch('bot.handlers.catalog.catalog_handlers.get_catalog_service', return_value=mock_catalog_service), \
             patch('bot.handlers.catalog.catalog_handlers.product_registry_service', mock_product_registry_service), \
             patch('bot.handlers.catalog.mixins.localization.get_user_settings', return_value=mock_user_settings), \
             patch('bot.handlers.catalog.mixins.localization.Localization') as mock_localization_class:
            
            # Настраиваем мок Localization
            mock_loc = Mock()
            mock_loc.language = "ru"
            mock_loc.t = lambda key, **kwargs: f"Localized[ru]: {key}"
            mock_localization_class.return_value = mock_loc
            
            # Импортируем handler
            from bot.handlers.catalog.catalog_handlers import CatalogHandler
            
            # Создаем экземпляр handler
            handler = CatalogHandler()
            
            # Вызываем handle_show_catalog
            await handler.handle_show_catalog(mock_callback_query)
            
            # Проверяем, что get_catalog_with_progress был вызван с правильным языком
            mock_catalog_service.get_catalog_with_progress.assert_called_once_with("ru")
            
            # Проверяем, что send_catalog_to_user был вызван
            assert mock_catalog_service.send_catalog_to_user.called, "send_catalog_to_user должен быть вызван"
            
            logger.info("✅ Тест пройден: каталог загружен через Telegram handler (ru)")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_catalog_loads_via_telegram_handler_en(
        self,
        mock_callback_query,
        mock_catalog_service,
        mock_product_registry_service,
        e2e_local_profile,
        caplog
    ):
        """
        E2E TEST: Catalog loads via Telegram handler (English)
        
        Проверяет загрузку каталога через Telegram handler на английском языке.
        """
        logger.info("="*80)
        logger.info("E2E TEST: Catalog loads via Telegram handler (English)")
        logger.info("="*80)
        
        # Импорт EnvironmentValidator для проверки окружения
        from bot.tests.fixtures.env_validator import EnvironmentValidator
        
        # Проверка окружения
        is_valid, error_message = EnvironmentValidator.validate_e2e_environment()
        if not is_valid:
            pytest.skip(f"⚠️ {error_message}")
        
        use_stubs = EnvironmentValidator.should_use_stubs()
        if use_stubs:
            logger.info("✅ E2E_USE_STUBS=true: stub режим активирован")
        else:
            node_available, node_message = EnvironmentValidator.validate_hardhat_node()
            if not node_available:
                pytest.skip(f"⚠️ Hardhat node недоступен: {node_message}. Установите E2E_USE_STUBS=true для stub режима.")
        
        # Настраиваем мок для локализации (английский язык)
        mock_callback_query.from_user.language_code = "en"
        
        # Настраиваем мок CatalogService для возврата тестовых продуктов
        test_products = [
            Mock(business_id="test_product_1", title="Test Product 1"),
            Mock(business_id="test_product_2", title="Test Product 2"),
        ]
        mock_catalog_service.get_catalog_with_progress = AsyncMock(return_value=test_products)
        
        # Мокируем зависимости
        mock_user_settings = Mock()
        mock_user_settings.get_language = Mock(return_value="en")
        
        with patch('bot.handlers.catalog.catalog_handlers.get_catalog_service', return_value=mock_catalog_service), \
             patch('bot.handlers.catalog.catalog_handlers.product_registry_service', mock_product_registry_service), \
             patch('bot.handlers.catalog.mixins.localization.get_user_settings', return_value=mock_user_settings), \
             patch('bot.handlers.catalog.mixins.localization.Localization') as mock_localization_class:
            
            # Настраиваем мок Localization
            mock_loc = Mock()
            mock_loc.language = "en"
            mock_loc.t = lambda key, **kwargs: f"Localized[en]: {key}"
            mock_localization_class.return_value = mock_loc
            
            # Импортируем handler
            from bot.handlers.catalog.catalog_handlers import CatalogHandler
            
            # Создаем экземпляр handler
            handler = CatalogHandler()
            
            # Вызываем handle_show_catalog
            await handler.handle_show_catalog(mock_callback_query)
            
            # Проверяем, что get_catalog_with_progress был вызван с правильным языком
            mock_catalog_service.get_catalog_with_progress.assert_called_once_with("en")
            
            # Проверяем, что send_catalog_to_user был вызван
            assert mock_catalog_service.send_catalog_to_user.called, "send_catalog_to_user должен быть вызван"
            
            logger.info("✅ Тест пройден: каталог загружен через Telegram handler (en)")

