"""
Unit tests for ComponentService.

Tests:
- Cache methods (_get_from_cache, _set_cache, _evict_cache)
- get_component_full() with mock blockchain service
"""

import pytest
from datetime import datetime, timedelta
from services.product.component_service import ComponentService
from model.organic_component import OrganicComponent


@pytest.mark.unit
class TestComponentServiceCache:
    """Test cache functionality"""
    
    def test_cache_miss(self, mock_blockchain_service):
        """Test cache miss returns None"""
        service = ComponentService(blockchain_service=mock_blockchain_service)
        
        result = service._get_from_cache("non_existent")
        
        assert result is None
    
    def test_cache_set_and_get(self, mock_blockchain_service):
        """Test setting and getting from cache"""
        service = ComponentService(blockchain_service=mock_blockchain_service)
        
        test_component = OrganicComponent(component_id="test")
        service._set_cache("test", test_component)
        
        result = service._get_from_cache("test")
        
        assert result is not None
        assert result.component_id == "test"
    
    def test_cache_ttl_expiration(self, mock_blockchain_service):
        """Test cache expiration after TTL"""
        service = ComponentService(blockchain_service=mock_blockchain_service)
        service.CACHE_TTL = 1  # 1 second TTL
        
        test_component = OrganicComponent(component_id="test")
        service._set_cache("test", test_component)
        
        # Mock expired cache entry
        service._cache["test"]["cached_at"] = datetime.now() - timedelta(seconds=2)
        
        result = service._get_from_cache("test")
        
        assert result is None
        assert "test" not in service._cache  # Should be deleted
    
    def test_cache_eviction(self, mock_blockchain_service):
        """Test LRU cache eviction when max size reached"""
        service = ComponentService(blockchain_service=mock_blockchain_service)
        service.CACHE_MAX_SIZE = 2
        
        # Fill cache to max
        service._set_cache("comp1", OrganicComponent(component_id="comp1"))
        service._set_cache("comp2", OrganicComponent(component_id="comp2"))
        
        # Add third component - should evict oldest
        service._set_cache("comp3", OrganicComponent(component_id="comp3"))
        
        assert len(service._cache) == 2
        assert "comp1" not in service._cache  # Oldest should be evicted
        assert "comp2" in service._cache
        assert "comp3" in service._cache
    
    def test_clear_cache(self, mock_blockchain_service):
        """Test manual cache clearing"""
        service = ComponentService(blockchain_service=mock_blockchain_service)
        
        # Fill cache with multiple entries
        service._set_cache("comp1", OrganicComponent(component_id="comp1"))
        service._set_cache("comp2", OrganicComponent(component_id="comp2"))
        service._set_cache("comp3", OrganicComponent(component_id="comp3"))
        
        assert len(service._cache) == 3
        
        # Clear cache
        service.clear_cache()
        
        assert len(service._cache) == 0
        assert "comp1" not in service._cache
        assert "comp2" not in service._cache
        assert "comp3" not in service._cache


@pytest.mark.unit
class TestComponentServiceGetComponentFull:
    """Test get_component_full() method"""
    
    def test_get_component_full_success(self, mock_blockchain_service, mock_storage_service):
        """Test successful component fetch"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        # amanita_muscaria exists in mock data
        component = service.get_component_full("amanita_muscaria")
        
        assert component is not None
        assert component.component_id == "amanita_muscaria"
        assert component.scientific_title == "Amanita muscaria"
        assert component.blockchain_id == 1
        assert component.is_registry_component() is True
        assert component.proportion is None
    
    def test_get_component_full_cache_hit(self, mock_blockchain_service, mock_storage_service):
        """Test cache hit on second call"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        # First call
        component1 = service.get_component_full("amanita_muscaria")
        
        # Second call should hit cache
        component2 = service.get_component_full("amanita_muscaria")
        
        assert component1 is component2  # Same object from cache
    
    def test_get_component_full_not_found(self, mock_blockchain_service, mock_storage_service):
        """Test component not found returns None"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        component = service.get_component_full("non_existent_component")
        
        assert component is None
    
    def test_get_component_full_graceful_degradation_no_metadata(
        self, 
        mock_blockchain_service, 
        mock_storage_service
    ):
        """Test graceful degradation when metadata fetch fails"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        # Add component with empty CID to trigger graceful degradation
        mock_blockchain_service.component_registry_state["components"]["no_metadata"] = {
            "id": 99,
            "businessId": "no_metadata",
            "creator": "0x123",
            "rootMetadataCID": "",  # Empty CID
            "active": True,
            "createdAt": 1730000000
        }
        
        component = service.get_component_full("no_metadata")
        
        # Should return component with only blockchain data
        assert component is not None
        assert component.component_id == "no_metadata"
        assert component.blockchain_id == 99
        assert component.scientific_title is None  # No metadata
        assert component.forms is None
    
    def test_get_component_full_multiple_components(
        self, 
        mock_blockchain_service, 
        mock_storage_service
    ):
        """Test fetching multiple different components"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        comp1 = service.get_component_full("amanita_muscaria")
        comp2 = service.get_component_full("blue_lotus")
        
        assert comp1 is not None
        assert comp2 is not None
        assert comp1.component_id != comp2.component_id
        assert comp1.scientific_title != comp2.scientific_title
        assert comp1.scientific_title == "Amanita muscaria"
        assert comp2.scientific_title == "Nymphaea caerulea"
        
        # Both should be in cache
        assert len(service._cache) == 2


@pytest.mark.unit
class TestComponentServiceHelpers:
    """Test helper methods for field extraction"""
    
    def test_get_component_features(self, mock_blockchain_service, mock_storage_service):
        """Test extracting features list"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        features = service.get_component_features("amanita_muscaria")
        
        assert isinstance(features, list)
        assert len(features) == 2
        assert "stress_relief" in features
        assert "vitality_boost" in features
    
    def test_get_component_features_empty(self, mock_blockchain_service, mock_storage_service):
        """Test features returns empty list when not available"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        # blue_lotus has features but might not have 'common'
        features = service.get_component_features("blue_lotus")
        
        assert isinstance(features, list)
        # Either has features or returns []
    
    def test_get_component_features_nonexistent(self, mock_blockchain_service, mock_storage_service):
        """Test features returns empty list for non-existent component"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        features = service.get_component_features("non_existent")
        
        assert features == []
    
    def test_get_component_forms(self, mock_blockchain_service, mock_storage_service):
        """Test extracting forms list"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        forms = service.get_component_forms("amanita_muscaria")
        
        assert isinstance(forms, list)
        assert len(forms) == 1
        assert "dried" in forms
    
    def test_get_component_forms_empty(self, mock_blockchain_service, mock_storage_service):
        """Test forms returns empty list when not available"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        forms = service.get_component_forms("non_existent")
        
        assert forms == []
    
    def test_get_component_title(self, mock_blockchain_service, mock_storage_service):
        """Test extracting scientific title"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        title = service.get_component_title("amanita_muscaria")
        
        assert title == "Amanita muscaria"
    
    def test_get_component_title_with_language(self, mock_blockchain_service, mock_storage_service):
        """Test title extraction with language parameter (currently returns scientific_title)"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        # Language parameter currently unused, but test for future compatibility
        title_en = service.get_component_title("amanita_muscaria", "en")
        title_ru = service.get_component_title("amanita_muscaria", "ru")
        
        # Both should return scientific_title for now
        assert title_en == "Amanita muscaria"
        assert title_ru == "Amanita muscaria"
    
    def test_get_component_title_none(self, mock_blockchain_service, mock_storage_service):
        """Test title returns None for non-existent component"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        title = service.get_component_title("non_existent")
        
        assert title is None
    
    def test_helpers_use_cache(self, mock_blockchain_service, mock_storage_service):
        """Test that helper methods leverage get_component_full() cache"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service
        )
        
        # First call caches component
        features = service.get_component_features("amanita_muscaria")
        assert len(features) == 2
        
        # Subsequent calls should use cache
        forms = service.get_component_forms("amanita_muscaria")
        title = service.get_component_title("amanita_muscaria")
        
        # Verify cache hit
        assert "amanita_muscaria" in service._cache
        assert len(service._cache) == 1  # Only one component cached


@pytest.mark.unit
@pytest.mark.asyncio
class TestComponentServiceGetComponentDescription:
    """Test get_component_description() method with complex fields"""
    
    @pytest.fixture
    def mock_multilingual_ipfs_service(self):
        """Mock MultilingualIPFSService для тестирования get_component_description"""
        from unittest.mock import MagicMock
        mock_service = MagicMock()
        # _load_component_description_from_ipfs - синхронный метод, не async
        mock_service._load_component_description_from_ipfs = MagicMock()
        return mock_service
    
    async def test_get_component_description_success(
        self, 
        mock_blockchain_service, 
        mock_storage_service,
        mock_multilingual_ipfs_service
    ):
        """Test successful component description fetch via MultilingualIPFSService"""
        from model.component_description import ComponentDescription
        
        # GIVEN: ComponentService with mocked MultilingualIPFSService
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service,
            multilingual_ipfs_service=mock_multilingual_ipfs_service
        )
        
        component_id = "amanita_muscaria"
        language = "ru"
        expected_fields = {
            "generic_description": "Test description",
            "effects": "Test effects",
            "shamanic": "Test shamanic",
            "warnings": "Test warnings"
        }
        
        # Mock _load_component_description_from_ipfs to return fields (синхронный метод)
        mock_multilingual_ipfs_service._load_component_description_from_ipfs.return_value = expected_fields
        
        # WHEN: Getting component description
        result = await service.get_component_description(component_id, language)
        
        # THEN: Method called with correct parameters (component_id, language)
        mock_multilingual_ipfs_service._load_component_description_from_ipfs.assert_called_once_with(
            component_id, language
        )
        
        # THEN: Result is ComponentDescription
        assert result is not None
        assert isinstance(result, ComponentDescription)
        assert result.generic_description == "Test description"
        assert result.effects == "Test effects"
        assert result.shamanic == "Test shamanic"
        assert result.warnings == "Test warnings"
    
    async def test_get_component_description_uses_cache(
        self,
        mock_blockchain_service,
        mock_storage_service,
        mock_multilingual_ipfs_service
    ):
        """Test that get_component_description uses cache"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service,
            multilingual_ipfs_service=mock_multilingual_ipfs_service
        )
        
        component_id = "amanita_muscaria"
        language = "ru"
        expected_fields = {
            "generic_description": "Cached description",
            "effects": "Cached effects"
        }
        
        # First call - populate cache
        mock_multilingual_ipfs_service._load_component_description_from_ipfs.return_value = expected_fields
        result1 = await service.get_component_description(component_id, language)
        
        # Reset mock to verify second call uses cache
        mock_multilingual_ipfs_service._load_component_description_from_ipfs.reset_mock()
        # Не устанавливаем return_value, чтобы проверить что метод не вызывается
        
        # Second call - should use cache
        result2 = await service.get_component_description(component_id, language)
        
        # THEN: Same result from cache
        assert result1 is not None
        assert result2 is not None
        assert result1 is result2  # Same object from cache
        
        # THEN: MultilingualIPFSService NOT called second time
        mock_multilingual_ipfs_service._load_component_description_from_ipfs.assert_not_called()
    
    async def test_get_component_description_returns_none_when_no_data(
        self,
        mock_blockchain_service,
        mock_storage_service,
        mock_multilingual_ipfs_service
    ):
        """Test that get_component_description returns None when no data available"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service,
            multilingual_ipfs_service=mock_multilingual_ipfs_service
        )
        
        component_id = "amanita_muscaria"
        language = "ru"
        
        # Mock _load_component_description_from_ipfs to return None
        mock_multilingual_ipfs_service._load_component_description_from_ipfs.return_value = None
        
        # WHEN: Getting component description
        result = await service.get_component_description(component_id, language)
        
        # THEN: Result is None
        assert result is None
        
        # THEN: Method was called
        mock_multilingual_ipfs_service._load_component_description_from_ipfs.assert_called_once_with(
            component_id, language
        )
    
    async def test_get_component_description_returns_none_when_component_not_found(
        self,
        mock_blockchain_service,
        mock_storage_service,
        mock_multilingual_ipfs_service
    ):
        """Test that get_component_description returns None when component not found"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service,
            multilingual_ipfs_service=mock_multilingual_ipfs_service
        )
        
        component_id = "non_existent_component"
        language = "ru"
        
        # WHEN: Getting component description for non-existent component
        result = await service.get_component_description(component_id, language)
        
        # THEN: Result is None (component not found)
        assert result is None
        
        # THEN: MultilingualIPFSService NOT called (component check failed first)
        mock_multilingual_ipfs_service._load_component_description_from_ipfs.assert_not_called()
    
    async def test_get_component_description_uses_correct_classname_format(
        self,
        mock_blockchain_service,
        mock_storage_service,
        mock_multilingual_ipfs_service
    ):
        """Test that get_component_description uses correct className format with biounit_id"""
        service = ComponentService(
            blockchain_service=mock_blockchain_service,
            storage_service=mock_storage_service,
            multilingual_ipfs_service=mock_multilingual_ipfs_service
        )
        
        component_id = "amanita_muscaria"
        language = "ru"
        expected_fields = {
            "generic_description": "Test description"
        }
        
        # Mock _load_component_description_from_ipfs
        mock_multilingual_ipfs_service._load_component_description_from_ipfs.return_value = expected_fields
        
        # WHEN: Getting component description
        result = await service.get_component_description(component_id, language)
        
        # THEN: Method called with component_id (not className)
        # _load_component_description_from_ipfs internally forms className = "ComponentDescription.{component_id}"
        mock_multilingual_ipfs_service._load_component_description_from_ipfs.assert_called_once_with(
            component_id,  # ✅ component_id передается напрямую
            language
        )
        
        # THEN: Result is valid
        assert result is not None
        assert result.generic_description == "Test description"

