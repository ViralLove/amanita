import pytest
import json
from unittest.mock import Mock, patch
from bot.services.product.cache import ProductCacheService
from bot.model.product import Description, DosageInstruction


class TestProductCacheService:
    """Тесты для ProductCacheService с интеграцией IPFS"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.mock_storage = Mock()
        self.cache_service = ProductCacheService()
        self.cache_service.set_storage_service(self.mock_storage)
    
    def test_init_with_storage_service(self):
        """Тест инициализации с переданным storage_service"""
        cache = ProductCacheService()
        cache.set_storage_service(self.mock_storage)
        assert cache._storage_service == self.mock_storage
    
    def test_lazy_storage_service_loading(self):
        """Тест lazy loading storage service"""
        cache = ProductCacheService()  # Без передачи storage_service
        # При первом обращении к storage_service он должен создаться
        storage = cache.storage_service
        assert storage is not None
    
    def test_get_description_by_cid_cache_hit(self):
        """Тест получения описания из кэша"""
        # Создаем тестовое описание
        test_description = Description(
            id="test-1",
            title="Test Product",
            scientific_name="Test Species",
            generic_description="Test description",
            effects="Test effects",
            shamanic="Test shamanic",
            warnings="Test warnings",
            dosage_instructions=[]
        )
        
        # Сохраняем в кэш
        self.cache_service.set_cached_item("test-cid", test_description, 'description')
        
        # Получаем из кэша
        result = self.cache_service.get_description_by_cid("test-cid")
        
        assert result == test_description
        # Storage service не должен вызываться
        self.mock_storage.download_json.assert_not_called()
    
    def test_get_description_by_cid_cache_miss(self):
        """Тест получения описания из IPFS при промахе кэша"""
        # Мокаем данные из IPFS
        mock_description_data = {
            "id": "test-1",
            "title": "Test Product",
            "scientific_name": "Test Species",
            "generic_description": "Test description",
            "effects": "Test effects",
            "shamanic": "Test shamanic",
            "warnings": "Test warnings",
            "dosage_instructions": []
        }
        
        self.mock_storage.download_json.return_value = mock_description_data
        
        # Получаем описание (кэш пустой)
        result = self.cache_service.get_description_by_cid("test-cid")
        
        # Проверяем что storage service был вызван
        self.mock_storage.download_json.assert_called_once_with("test-cid")
        
        # Проверяем результат
        assert isinstance(result, Description)
        assert result.id == "test-1"
        assert result.title == "Test Product"
        assert result.generic_description == "Test description"
        
        # Проверяем что результат сохранен в кэше
        cached_result = self.cache_service.get_cached_item("test-cid", 'description')
        assert cached_result == result
    
    def test_get_image_url_by_cid_cache_hit(self):
        """Тест получения URL изображения из кэша"""
        test_url = "https://gateway.pinata.cloud/ipfs/test-cid"
        
        # Сохраняем в кэш
        self.cache_service.set_cached_item("test-cid", test_url, 'image')
        
        # Получаем из кэша
        result = self.cache_service.get_image_url_by_cid("test-cid")
        
        assert result == test_url
        # Storage service не должен вызываться
        self.mock_storage.get_gateway_url.assert_not_called()
    
    def test_get_image_url_by_cid_cache_miss(self):
        """Тест получения URL изображения из IPFS при промахе кэша"""
        test_url = "https://gateway.pinata.cloud/ipfs/test-cid"
        self.mock_storage.get_gateway_url.return_value = test_url
        
        # Получаем URL (кэш пустой)
        result = self.cache_service.get_image_url_by_cid("test-cid")
        
        # Проверяем что storage service был вызван
        self.mock_storage.get_gateway_url.assert_called_once_with("test-cid")
        
        # Проверяем результат
        assert result == test_url
        
        # Проверяем что результат сохранен в кэше
        cached_result = self.cache_service.get_cached_item("test-cid", 'image')
        assert cached_result == test_url
    
    def test_get_description_by_cid_empty_cid(self):
        """Тест обработки пустого CID"""
        result = self.cache_service.get_description_by_cid("")
        assert result is None
        
        result = self.cache_service.get_description_by_cid(None)
        assert result is None
    
    def test_get_image_url_by_cid_empty_cid(self):
        """Тест обработки пустого CID для изображения"""
        result = self.cache_service.get_image_url_by_cid("")
        assert result is None
        
        result = self.cache_service.get_image_url_by_cid(None)
        assert result is None
    
    def test_get_description_by_cid_invalid_data(self):
        """Тест обработки некорректных данных описания"""
        # Мокаем некорректные данные
        self.mock_storage.download_json.return_value = "invalid data"
        
        result = self.cache_service.get_description_by_cid("test-cid")
        assert result is None
    
    def test_get_description_by_cid_missing_required_fields(self):
        """Тест обработки данных с отсутствующими обязательными полями"""
        # Мокаем данные без обязательных полей
        invalid_data = {
            "title": "Test Product",
            # Отсутствуют id, scientific_name, generic_description
        }
        
        self.mock_storage.download_json.return_value = invalid_data
        
        result = self.cache_service.get_description_by_cid("test-cid")
        assert result is None
    
    def test_cache_invalidation(self):
        """Тест инвалидации кэша"""
        # Заполняем кэши
        self.cache_service.set_cached_item("test1", "value1", 'description')
        self.cache_service.set_cached_item("test2", "value2", 'image')
        self.cache_service.set_cached_item("test3", "value3", 'catalog')
        
        # Проверяем что данные есть в кэше
        assert self.cache_service.get_cached_item("test1", 'description') == "value1"
        assert self.cache_service.get_cached_item("test2", 'image') == "value2"
        assert self.cache_service.get_cached_item("test3", 'catalog') == "value3"
        
        # Инвалидируем только description
        self.cache_service.invalidate_cache('description')
        
        # Проверяем что description очищен, а остальные остались
        assert self.cache_service.get_cached_item("test1", 'description') is None
        assert self.cache_service.get_cached_item("test2", 'image') == "value2"
        assert self.cache_service.get_cached_item("test3", 'catalog') == "value3"
        
        # Инвалидируем все кэши
        self.cache_service.invalidate_cache()
        
        # Проверяем что все кэши очищены
        assert self.cache_service.get_cached_item("test1", 'description') is None
        assert self.cache_service.get_cached_item("test2", 'image') is None
        assert self.cache_service.get_cached_item("test3", 'catalog') is None 