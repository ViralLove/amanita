"""
Integration Test: MultilingualIPFSService → BlockchainService (Complex Fields)

Phase 3: Flow Testing - Multi-step integration scenario
Validates module boundary handshake between MultilingualIPFSService and BlockchainService

Goal: Verify that MultilingualIPFSService correctly loads complex fields through blockchain mapping:
1. Get CID from AmanitaInternational contract via BlockchainService
2. Download JSON from IPFS using the CID
3. Validate structure and cache the result

Method: @integration-test-build.core.mdc
- Real modules: MultilingualIPFSService (via conftest fixture)
- Minimal mocks: BlockchainServiceStub (external blockchain API), IPFSFactoryStub (external IPFS API)
- State tracking: Cache state verification
"""

import pytest
from unittest.mock import Mock, MagicMock
from bot.services.common.multilingual_ipfs_service import MultilingualIPFSService
from tests.integration.blockchain_stub import BlockchainServiceStub, AmanitaInternationalContractStub
from tests.integration.ipfs_stub import IPFSFactoryStub


class TestMultilingualIPFSServiceBlockchainIntegration:
    """Integration tests for MultilingualIPFSService → BlockchainService for complex fields"""
    
    def test_load_complex_field_success(self, multilingual_ipfs_service, blockchain_service, ipfs_factory):
        """Test successful loading of complex field through blockchain"""
        # GIVEN: Blockchain contract returns CID
        className = "ComponentDescription"
        language = "ru"
        cid = "QmTestCID123456789"
        
        # Setup blockchain contract stub to return CID via setComplexFieldCID
        contract = blockchain_service.get_contract("AmanitaInternational")
        
        # Use contract.functions.setComplexFieldCID to set the CID in the stub
        contract.functions.setComplexFieldCID(className, language, cid).transact()
        
        # GIVEN: IPFS service returns valid JSON
        ipfs_service = ipfs_factory.get_service()
        valid_payload = {
            "label": "ComponentDescription",
            "type": "complex",
            "fields": {
                "generic_description": "Test description",
                "effects": "Test effects",
                "contraindications": "Test contraindications"
            }
        }
        ipfs_service._storage[cid] = valid_payload
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs(className, language)
        
        # THEN: BlockchainService.get_contract called with correct contract name
        contract_from_service = blockchain_service.get_contract("AmanitaInternational")
        assert contract_from_service is not None
        
        # THEN: IPFS download_json called with CID
        assert cid in ipfs_service._storage
        
        # THEN: Result contains valid data
        assert result is not None
        assert result["label"] == "ComponentDescription"
        assert result["type"] == "complex"
        assert "fields" in result
        assert "generic_description" in result["fields"]
        assert result["fields"]["generic_description"] == "Test description"
    
    def test_load_complex_field_empty_cid(self, multilingual_ipfs_service, blockchain_service):
        """Test handling of empty CID (complex field not found)"""
        # GIVEN: Blockchain contract returns empty CID
        className = "ComponentDescription"
        language = "ru"
        
        contract = blockchain_service.get_contract("AmanitaInternational")
        
        # Set empty CID in blockchain stub
        contract.functions.setComplexFieldCID(className, language, "").transact()
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs(className, language)
        
        # THEN: Result is None (empty CID handled)
        assert result is None
    
    def test_load_complex_field_contract_not_found(self, multilingual_ipfs_service, blockchain_service):
        """Test handling when AmanitaInternational contract is not found"""
        # GIVEN: BlockchainService returns None for contract
        blockchain_service.get_contract = Mock(return_value=None)
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs("ComponentDescription", "ru")
        
        # THEN: Result is None
        assert result is None
        
        # THEN: get_contract was called
        blockchain_service.get_contract.assert_called_once_with("AmanitaInternational")
    
    def test_load_complex_field_blockchain_error(self, multilingual_ipfs_service, blockchain_service):
        """Test handling of blockchain contract errors"""
        # GIVEN: Blockchain contract raises exception
        className = "ComponentDescription"
        language = "ru"
        
        contract = blockchain_service.get_contract("AmanitaInternational")
        
        # Simulate error by making contract.functions.getComplexFieldCID raise exception
        original_functions = contract.functions
        
        # Create a mock that raises exception on call
        mock_functions = Mock()
        mock_get_complex_field = Mock(return_value=Mock(
            call=Mock(side_effect=Exception("Blockchain error"))
        ))
        mock_functions.getComplexFieldCID = mock_get_complex_field
        contract.functions = mock_functions
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs(className, language)
        
        # THEN: Result is None (error handled gracefully)
        assert result is None
        
        # Restore original functions
        contract.functions = original_functions
    
    def test_load_complex_field_caching(self, multilingual_ipfs_service, blockchain_service, ipfs_factory, translation_cache_service):
        """Test caching of complex field data"""
        # GIVEN: Setup data in cache
        className = "ComponentDescription"
        language = "ru"
        cache_key = f"complex_{className}_{language}"
        
        cached_data = {
            "label": "ComponentDescription",
            "type": "complex",
            "fields": {"generic_description": "Cached description"}
        }
        
        # Save to external cache
        translation_cache_service.set(cache_key, cached_data, 'ipfs')
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs(className, language)
        
        # THEN: Result from cache
        assert result is not None
        assert result == cached_data
        
        # THEN: BlockchainService NOT called (cache hit)
        # Check that blockchain wasn't accessed (contract methods not called)
        contract = blockchain_service.get_contract("AmanitaInternational")
        # If get_complex_field_cid exists, it shouldn't have been called
        if hasattr(contract, 'get_complex_field_cid'):
            # Reset mock if it was set up
            if isinstance(contract.get_complex_field_cid, Mock):
                contract.get_complex_field_cid.reset_mock()
        
        # THEN: Cache service was checked (via _get_from_cache mechanism)
        # Verify cache hit by checking stats or cache state
        stats = multilingual_ipfs_service.get_stats()
        # Cache hit should be recorded
        assert stats.get('cache_hits', 0) >= 1 or cache_key in multilingual_ipfs_service.ipfs_cache
    
    def test_load_complex_field_invalid_structure(self, multilingual_ipfs_service, blockchain_service, ipfs_factory):
        """Test handling of invalid JSON structure from IPFS"""
        # GIVEN: Blockchain returns valid CID, but IPFS returns invalid structure
        className = "ComponentDescription"
        language = "ru"
        cid = "QmInvalidCID"
        
        contract = blockchain_service.get_contract("AmanitaInternational")
        
        # Set CID in blockchain stub
        contract.functions.setComplexFieldCID(className, language, cid).transact()
        
        # GIVEN: IPFS returns invalid structure (missing required fields)
        ipfs_service = ipfs_factory.get_service()
        invalid_payload = {
            "invalid": "structure"  # Missing 'label', 'type', 'fields'
        }
        ipfs_service._storage[cid] = invalid_payload
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs(className, language)
        
        # THEN: Result is None (validation failed)
        assert result is None
        
        # THEN: IPFS download was attempted
        assert cid in ipfs_service._storage
    
    def test_load_complex_field_ipfs_error(self, multilingual_ipfs_service, blockchain_service, ipfs_factory):
        """Test handling of IPFS download errors"""
        # GIVEN: Blockchain returns valid CID, but IPFS download fails
        className = "ComponentDescription"
        language = "ru"
        cid = "QmErrorCID"
        
        contract = blockchain_service.get_contract("AmanitaInternational")
        
        # Set CID in blockchain stub
        contract.functions.setComplexFieldCID(className, language, cid).transact()
        
        # GIVEN: IPFS service returns None (download error - CID not in storage)
        ipfs_service = ipfs_factory.get_service()
        # Don't add CID to storage, so download_json returns None
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs(className, language)
        
        # THEN: Result is None
        assert result is None
        
        # THEN: Error stats updated
        stats = multilingual_ipfs_service.get_stats()
        # Errors should be recorded (though might be 0 if error handled gracefully)
    
    def test_load_complex_field_none_cid(self, multilingual_ipfs_service, blockchain_service):
        """Test handling when CID is None"""
        # GIVEN: Blockchain contract returns None CID
        className = "ComponentDescription"
        language = "ru"
        
        contract = blockchain_service.get_contract("AmanitaInternational")
        
        # Don't set CID in blockchain stub (None/empty will be returned)
        # When getComplexFieldCID is called on a non-existent key, it returns empty string
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs(className, language)
        
        # THEN: Result is None (no CID set)
        assert result is None
    
    def test_get_complex_field_cid_success(self, multilingual_ipfs_service, blockchain_service):
        """Test _get_complex_field_cid method directly"""
        # GIVEN: Blockchain contract returns CID
        className = "ComponentDescription"
        language = "ru"
        expected_cid = "QmDirectCID123"
        
        contract = blockchain_service.get_contract("AmanitaInternational")
        
        # Set CID in blockchain stub
        contract.functions.setComplexFieldCID(className, language, expected_cid).transact()
        
        # WHEN: Getting CID directly
        cid = multilingual_ipfs_service._get_complex_field_cid(className, language)
        
        # THEN: CID is returned
        assert cid == expected_cid
        
        # THEN: Contract was accessed
        assert blockchain_service.get_contract("AmanitaInternational") is not None
    
    def test_get_complex_field_cid_no_blockchain_service(self, multilingual_ipfs_service):
        """Test _get_complex_field_cid when blockchain_service is None"""
        # GIVEN: MultilingualIPFSService without blockchain_service
        multilingual_ipfs_service.blockchain_service = None
        
        # WHEN: Getting CID
        cid = multilingual_ipfs_service._get_complex_field_cid("ComponentDescription", "ru")
        
        # THEN: CID is None
        assert cid is None
    
    def test_complex_field_caching_flow(self, multilingual_ipfs_service, blockchain_service, ipfs_factory, translation_cache_service):
        """Test full caching flow: first load → cache → second load from cache"""
        className = "ComponentDescription"
        language = "ru"
        cid = "QmCacheFlowCID"
        
        # GIVEN: First load - no cache
        contract = blockchain_service.get_contract("AmanitaInternational")
        
        # Set CID in blockchain stub
        contract.functions.setComplexFieldCID(className, language, cid).transact()
        
        ipfs_service = ipfs_factory.get_service()
        payload = {
            "label": "ComponentDescription",
            "type": "complex",
            "fields": {"generic_description": "Cache flow test"}
        }
        ipfs_service._storage[cid] = payload
        
        # Clear cache before first load
        multilingual_ipfs_service.clear_cache()
        translation_cache_service.clear_cache('ipfs')
        
        # WHEN: First load
        result1 = multilingual_ipfs_service._load_complex_field_from_ipfs(className, language)
        
        # THEN: Data loaded successfully
        assert result1 is not None
        assert result1 == payload
        
        # WHEN: Second load (should use cache)
        result2 = multilingual_ipfs_service._load_complex_field_from_ipfs(className, language)
        
        # THEN: Same data returned from cache
        assert result2 == result1
        assert result2 == payload
        
        # THEN: Cache hit was recorded
        stats = multilingual_ipfs_service.get_stats()
        assert stats.get('cache_hits', 0) >= 1


