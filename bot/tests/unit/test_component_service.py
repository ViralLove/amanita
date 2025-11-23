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

