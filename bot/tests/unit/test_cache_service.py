import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from bot.services.product.cache import ProductCacheService
from bot.model.product import Description, DosageInstruction


@pytest.mark.unit
class TestProductCacheService:
    """Тесты для ProductCacheService с интеграцией IPFS"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.mock_storage = Mock()
        # Мокаем validate_ipfs_cid для поддержки любых CID в тестах
        self.mock_storage.validate_ipfs_cid = Mock(return_value=True)
        self.cache_service = ProductCacheService()
        # ✅ ИЗОЛЯЦИЯ ТЕСТОВ: Очищаем кэши перед каждым тестом
        # ProductCacheService использует singleton паттерн, поэтому состояние сохраняется между тестами
        # Очистка кэшей гарантирует изоляцию тестов
        self.cache_service.invalidate_cache()
        self.cache_service.set_storage_service(self.mock_storage)
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        # ✅ ИЗОЛЯЦИЯ ТЕСТОВ: Очищаем кэши после теста для предотвращения влияния на следующие
        if hasattr(self, 'cache_service'):
            self.cache_service.invalidate_cache()
    
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
            business_id="test-1",
            title="Test Product",
            scientific_name="Test Species",
            generic_description="Test description",
            effects="Test effects",
            shamanic="Test shamanic",
            warnings="Test warnings",
            dosage_instructions=[]
        )
        
        # Используем валидный IPFS CID для теста (Qm + 44 символа base58)
        # Реальный пример: QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG
        valid_ipfs_cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
        
        # Сохраняем в кэш
        self.cache_service.set_cached_item(valid_ipfs_cid, test_description, 'description')
        
        # Получаем из кэша
        result = self.cache_service.get_description_by_cid(valid_ipfs_cid)
        
        assert result == test_description
        # Storage service не должен вызываться для загрузки (только для валидации)
        self.mock_storage.download_json.assert_not_called()
    
    def test_get_description_by_cid_cache_miss(self):
        """Тест получения описания из IPFS при промахе кэша"""
        # Мокаем данные из IPFS
        mock_description_data = {
            "business_id": "test-1",
            "title": "Test Product",
            "scientific_name": "Test Species",
            "generic_description": "Test description",
            "effects": "Test effects",
            "shamanic": "Test shamanic",
            "warnings": "Test warnings",
            "dosage_instructions": []
        }
        
        self.mock_storage.download_json.return_value = mock_description_data
        
        # Используем валидный IPFS CID для теста
        valid_ipfs_cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
        
        # Получаем описание (кэш пустой)
        result = self.cache_service.get_description_by_cid(valid_ipfs_cid)
        
        # Проверяем что storage service был вызван
        self.mock_storage.download_json.assert_called_once_with(valid_ipfs_cid)
        
        # Проверяем результат (проверяем тип по имени класса из-за различий в импортах)
        assert result is not None
        assert type(result).__name__ == "Description"
        assert result.business_id == "test-1"
        assert result.title == "Test Product"
        assert result.generic_description == "Test description"
        
        # Проверяем что результат сохранен в кэше
        cached_result = self.cache_service.get_cached_item(valid_ipfs_cid, 'description')
        assert cached_result == result
    
    def test_get_image_url_by_cid_cache_hit(self):
        """Тест получения URL изображения из кэша"""
        # Используем валидный IPFS CID для теста
        valid_ipfs_cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
        test_url = f"https://gateway.pinata.cloud/ipfs/{valid_ipfs_cid}"
        
        # Сохраняем в кэш
        self.cache_service.set_cached_item(valid_ipfs_cid, test_url, 'image')
        
        # Получаем из кэша
        result = self.cache_service.get_image_url_by_cid(valid_ipfs_cid)
        
        assert result == test_url
        # Storage service не должен вызываться
        self.mock_storage.get_gateway_url.assert_not_called()
    
    def test_get_image_url_by_cid_cache_miss(self):
        """Тест получения URL изображения из IPFS при промахе кэша"""
        # Используем валидный IPFS CID для теста
        valid_ipfs_cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
        test_url = f"https://gateway.pinata.cloud/ipfs/{valid_ipfs_cid}"
        self.mock_storage.get_gateway_url.return_value = test_url
        
        # Получаем URL (кэш пустой)
        result = self.cache_service.get_image_url_by_cid(valid_ipfs_cid)
        
        # Проверяем что storage service был вызван
        self.mock_storage.get_gateway_url.assert_called_once_with(valid_ipfs_cid)
        
        # Проверяем результат
        assert result == test_url
        
        # Проверяем что результат сохранен в кэше
        cached_result = self.cache_service.get_cached_item(valid_ipfs_cid, 'image')
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
        # Используем валидный IPFS CID для теста
        valid_ipfs_cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
        
        # Мокаем некорректные данные
        self.mock_storage.download_json.return_value = "invalid data"
        
        result = self.cache_service.get_description_by_cid(valid_ipfs_cid)
        assert result is None
    
    def test_get_description_by_cid_missing_required_fields(self):
        """Тест обработки данных с отсутствующими обязательными полями"""
        # Используем валидный IPFS CID для теста
        valid_ipfs_cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
        
        # Мокаем данные без обязательных полей
        invalid_data = {
            "title": "Test Product",
            # Отсутствуют business_id, scientific_name, generic_description
        }
        
        self.mock_storage.download_json.return_value = invalid_data
        
        result = self.cache_service.get_description_by_cid(valid_ipfs_cid)
        assert result is None
    
    def test_cache_invalidation(self):
        """Тест инвалидации кэша"""
        # Используем валидные CID для тестов
        valid_ipfs_cid_desc = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
        valid_ipfs_cid_img = "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG"
        
        # Создаем валидные объекты для кэша
        test_description = Description(
            business_id="test-1",
            title="Test Product",
            scientific_name="Test Species",
            generic_description="Test description",
            effects="Test effects",
            shamanic="Test shamanic",
            warnings="Test warnings",
            dosage_instructions=[]
        )
        test_image_url = f"https://gateway.pinata.cloud/ipfs/{valid_ipfs_cid_img}"
        
        # Заполняем кэши
        self.cache_service.set_cached_item(valid_ipfs_cid_desc, test_description, 'description')
        self.cache_service.set_cached_item(valid_ipfs_cid_img, test_image_url, 'image')
        # Используем правильную структуру каталога
        test_catalog = {"version": 1, "products": []}
        self.cache_service.set_cached_item("test3", test_catalog, 'catalog')
        
        # Проверяем что данные есть в кэше
        assert self.cache_service.get_cached_item(valid_ipfs_cid_desc, 'description') == test_description
        assert self.cache_service.get_cached_item(valid_ipfs_cid_img, 'image') == test_image_url
        assert self.cache_service.get_cached_item("test3", 'catalog') == test_catalog
        
        # Инвалидируем только description
        self.cache_service.invalidate_cache('description')
        
        # Проверяем что description очищен, а остальные остались
        assert self.cache_service.get_cached_item(valid_ipfs_cid_desc, 'description') is None
        assert self.cache_service.get_cached_item(valid_ipfs_cid_img, 'image') == test_image_url
        assert self.cache_service.get_cached_item("test3", 'catalog') == test_catalog
        
        # Инвалидируем все кэши
        self.cache_service.invalidate_cache()
        
        # Проверяем что все кэши очищены
        assert self.cache_service.get_cached_item(valid_ipfs_cid_desc, 'description') is None
        assert self.cache_service.get_cached_item(valid_ipfs_cid_img, 'image') is None
        assert self.cache_service.get_cached_item("test3", 'catalog') is None
    
    def test_get_description_by_cid_arweave_cid(self):
        """Тест получения описания с Arweave CID"""
        # Создаем тестовое описание
        test_description = Description(
            business_id="test-arweave",
            title="Test Product Arweave",
            scientific_name="Test Species",
            generic_description="Test description",
            effects="Test effects",
            shamanic="Test shamanic",
            warnings="Test warnings",
            dosage_instructions=[]
        )
        
        # Используем Arweave transaction ID (43 символа base64url)
        arweave_cid = "TestTransactionID123456789012345678901234567890123"
        
        # Сохраняем в кэш
        self.cache_service.set_cached_item(arweave_cid, test_description, 'description')
        
        # Получаем из кэша
        result = self.cache_service.get_description_by_cid(arweave_cid)
        
        assert result == test_description
        # Storage service не должен вызываться
        self.mock_storage.download_json.assert_not_called()
    
    def test_get_image_url_by_cid_arweave_cid(self):
        """Тест получения URL изображения с Arweave CID"""
        # Используем Arweave transaction ID (43 символа base64url)
        arweave_cid = "TestTransactionID123456789012345678901234567890123"
        test_url = f"https://arweave.net/{arweave_cid}"
        
        # Сохраняем в кэш
        self.cache_service.set_cached_item(arweave_cid, test_url, 'image')
        
        # Получаем из кэша
        result = self.cache_service.get_image_url_by_cid(arweave_cid)
        
        assert result == test_url
        # Storage service не должен вызываться
        self.mock_storage.get_gateway_url.assert_not_called()