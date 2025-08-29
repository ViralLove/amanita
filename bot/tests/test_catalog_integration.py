import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from bot.handlers.catalog import show_catalog

class TestCatalogIntegration:
    
    @pytest.mark.asyncio
    async def test_catalog_uses_storage_service_for_urls(self):
        """Тест что catalog использует storage service для формирования URL"""
        
        # Мокаем все зависимости
        with patch('bot.handlers.catalog.product_registry_service') as mock_registry, \
             patch('bot.handlers.catalog.user_settings') as mock_user_settings, \
             patch('bot.handlers.catalog.Localization') as mock_localization, \
             patch('bot.handlers.catalog.IPFSFactory') as mock_ipfs_factory:
            
            # Настраиваем моки
            mock_user_settings.get_language.return_value = 'ru'
            mock_localization.return_value.t.return_value = 'test'
            
            # Мокаем продукт с изображением
            mock_product = MagicMock()
            mock_product.cover_image_url = "QmTestCID123456789"
            mock_product.id = "test_product"
            mock_registry.get_all_products.return_value = [mock_product]
            
            # Мокаем storage service
            mock_storage = MagicMock()
            mock_storage.get_public_url.return_value = "https://gateway.pinata.cloud/ipfs/QmTestCID123456789"
            mock_ipfs_factory.return_value.get_storage.return_value = mock_storage
            
            # Мокаем callback
            mock_callback = MagicMock()
            mock_callback.data = "menu:catalog"
            mock_callback.from_user.id = 123
            mock_callback.message.answer = AsyncMock()
            mock_callback.message.answer_photo = AsyncMock()
            mock_callback.answer = AsyncMock()
            
            # Мокаем aiohttp session
            with patch('bot.handlers.catalog.aiohttp.ClientSession') as mock_session:
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.read = AsyncMock(return_value=b"fake_image_data")
                mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
                
                # Запускаем функцию
                await show_catalog(mock_callback)
                
                # Проверяем что storage service был вызван для формирования URL
                mock_storage.get_public_url.assert_called_once_with("QmTestCID123456789")
