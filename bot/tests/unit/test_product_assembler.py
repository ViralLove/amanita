"""
Unit tests for ProductAssembler.

Tests:
- _enrich_components(): ComponentService integration (unified method)
"""

import pytest
from unittest.mock import Mock
from services.product.assembler import ProductAssembler
from model.organic_component import OrganicComponent


class MockComponentService:
    """Mock ComponentService для тестов ProductAssembler"""
    
    def __init__(self):
        self.components = {}
    
    def get_component_full(self, component_id):
        """Mock get_component_full"""
        return self.components.get(component_id)


@pytest.mark.unit
class TestProductAssemblerEnrichComponents:
    """Test _enrich_components() method (unified for all products)"""
    
    @pytest.fixture
    def mock_component_service(self):
        """Create mock ComponentService with test data"""
        service = MockComponentService()
        
        # Add test component
        test_component = OrganicComponent(
            component_id="amanita_muscaria",
            scientific_title="Amanita muscaria",
            forms=["dried", "powder"],
            features={"common": ["stress_relief", "meditation"]}
        )
        service.components["amanita_muscaria"] = test_component
        
        return service
    
    @pytest.fixture
    def assembler(self, mock_component_service):
        """Create ProductAssembler with mock ComponentService"""
        return ProductAssembler(component_service=mock_component_service)
    
    @pytest.mark.asyncio
    async def test_enrich_components_single_component_success(self, assembler):
        """Test successful enrichment of product with single component"""
        metadata = {
            "business_id": "test_product",
            "title": "Test Product",
            "organic_components": [
                {
                    "component_id": "amanita_muscaria",
                    "proportion": "100g"
                }
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        # Check organic_components enriched
        assert "organic_components" in enriched
        assert isinstance(enriched["organic_components"], list)
        assert len(enriched["organic_components"]) == 1
        
        # Check component data
        component = enriched["organic_components"][0]
        assert component["component_id"] == "amanita_muscaria"
        assert component["proportion"] == "100g"
        assert component["scientific_title"] == "Amanita muscaria"
        assert "forms" in component
        assert "features" in component
    
    @pytest.mark.asyncio
    async def test_enrich_components_missing_proportion(self, assembler):
        """Test ValueError when proportion missing"""
        metadata = {
            "business_id": "test_product",
            "organic_components": [
                {
                    "component_id": "amanita_muscaria"
                    # No proportion
                }
            ]
        }
        
        with pytest.raises(ValueError, match="Отсутствует proportion|Missing proportion"):
            await assembler._enrich_components(metadata, "ru")
    
    @pytest.mark.asyncio
    async def test_enrich_components_component_not_found(self, assembler):
        """Test ValueError when component not found in registry"""
        metadata = {
            "business_id": "test_product",
            "organic_components": [
                {
                    "component_id": "non_existent_component",
                    "proportion": "50g"
                }
            ]
        }
        
        with pytest.raises(ValueError, match="не найден|not found"):
            await assembler._enrich_components(metadata, "ru")
    
    @pytest.mark.asyncio
    async def test_enrich_components_preserves_metadata(self, assembler):
        """Test that original metadata is preserved"""
        metadata = {
            "business_id": "test_product",
            "title": "Test Product",
            "categories": ["mushrooms"],
            "extra_field": "extra_value",
            "organic_components": [
                {
                    "component_id": "amanita_muscaria",
                    "proportion": "100g"
                }
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        # Check original fields preserved
        assert enriched["business_id"] == "test_product"
        assert enriched["title"] == "Test Product"
        assert enriched["categories"] == ["mushrooms"]
        assert enriched["extra_field"] == "extra_value"
        
        # Check components enriched
        assert len(enriched["organic_components"]) == 1


@pytest.mark.unit
class TestProductAssemblerEnrichComponentsMulti:
    """Test _enrich_components() method with multiple components"""
    
    @pytest.fixture
    def mock_component_service(self):
        """Create mock ComponentService with multiple test components"""
        service = MockComponentService()
        
        # Add test components
        service.components["amanita_muscaria"] = OrganicComponent(
            component_id="amanita_muscaria",
            scientific_title="Amanita muscaria",
            forms=["dried", "powder"],
            features={"common": ["stress_relief", "meditation"]}
        )
        
        service.components["lions_mane"] = OrganicComponent(
            component_id="lions_mane",
            scientific_title="Hericium erinaceus",
            forms=["dried", "extract"],
            features={"common": ["cognitive_support", "nerve_health"]}
        )
        
        service.components["passionflower"] = OrganicComponent(
            component_id="passionflower",
            scientific_title="Passiflora incarnata",
            forms=["dried", "tincture"],
            features={"common": ["relaxation", "sleep_support"]}
        )
        
        return service
    
    @pytest.fixture
    def assembler(self, mock_component_service):
        """Create ProductAssembler with mock ComponentService"""
        return ProductAssembler(component_service=mock_component_service)
    
    @pytest.mark.asyncio
    async def test_enrich_components_multi_success(self, assembler):
        """Test successful enrichment of product with multiple components"""
        metadata = {
            "business_id": "blend_product",
            "title": "Relaxation Blend",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "lions_mane", "proportion": "30g"}
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        # Check organic_components enriched
        assert "organic_components" in enriched
        assert isinstance(enriched["organic_components"], list)
        assert len(enriched["organic_components"]) == 2
        
        # Check first component
        comp1 = enriched["organic_components"][0]
        assert comp1["component_id"] == "amanita_muscaria"
        assert comp1["proportion"] == "50g"
        assert comp1["scientific_title"] == "Amanita muscaria"
        assert "forms" in comp1
        assert "features" in comp1
        
        # Check second component
        comp2 = enriched["organic_components"][1]
        assert comp2["component_id"] == "lions_mane"
        assert comp2["proportion"] == "30g"
        assert comp2["scientific_title"] == "Hericium erinaceus"
    
    @pytest.mark.asyncio
    async def test_enrich_components_three_components(self, assembler):
        """Test enrichment with three components"""
        metadata = {
            "business_id": "triple_blend",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "40g"},
                {"component_id": "lions_mane", "proportion": "30g"},
                {"component_id": "passionflower", "proportion": "30g"}
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        assert len(enriched["organic_components"]) == 3
        assert enriched["organic_components"][0]["component_id"] == "amanita_muscaria"
        assert enriched["organic_components"][1]["component_id"] == "lions_mane"
        assert enriched["organic_components"][2]["component_id"] == "passionflower"
    
    @pytest.mark.asyncio
    async def test_enrich_components_not_found(self, assembler):
        """Test ValueError when component not found in registry"""
        metadata = {
            "business_id": "invalid_blend",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "non_existent", "proportion": "50g"}
            ]
        }
        
        with pytest.raises(ValueError, match="не найден|not found"):
            await assembler._enrich_components(metadata, "ru")
    
    @pytest.mark.asyncio
    async def test_enrich_components_missing_component_id(self, assembler):
        """Test ValueError when component_id missing"""
        metadata = {
            "business_id": "invalid_blend",
            "organic_components": [
                {"proportion": "100g"}  # No component_id
            ]
        }
        
        with pytest.raises(ValueError, match="Отсутствует component_id|Missing component_id"):
            await assembler._enrich_components(metadata, "ru")
    
    @pytest.mark.asyncio
    async def test_enrich_components_missing_proportion(self, assembler):
        """Test ValueError when proportion missing"""
        metadata = {
            "business_id": "invalid_blend",
            "organic_components": [
                {"component_id": "amanita_muscaria"}  # No proportion
            ]
        }
        
        with pytest.raises(ValueError, match="Отсутствует proportion|Missing proportion"):
            await assembler._enrich_components(metadata, "ru")
    
    @pytest.mark.asyncio
    async def test_enrich_components_empty_array(self, assembler):
        """Test ValueError when organic_components is empty"""
        metadata = {
            "business_id": "invalid_product",
            "organic_components": []  # Empty array
        }
        
        with pytest.raises(ValueError, match="не может быть пустым|cannot be empty"):
            await assembler._enrich_components(metadata, "ru")
    
    @pytest.mark.asyncio
    async def test_enrich_components_missing_organic_components(self, assembler):
        """Test ValueError when organic_components missing"""
        metadata = {
            "business_id": "invalid_product"
            # No organic_components
        }
        
        with pytest.raises(ValueError, match="Отсутствует обязательное поле|Missing required field"):
            await assembler._enrich_components(metadata, "ru")
    
    @pytest.mark.asyncio
    async def test_enrich_components_preserves_metadata(self, assembler):
        """Test that original metadata is preserved"""
        metadata = {
            "business_id": "blend_product",
            "title": "Test Blend",
            "categories": ["mushrooms", "blends"],
            "extra_field": "extra_value",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "lions_mane", "proportion": "50g"}
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        # Check original fields preserved
        assert enriched["business_id"] == "blend_product"
        assert enriched["title"] == "Test Blend"
        assert enriched["categories"] == ["mushrooms", "blends"]
        assert enriched["extra_field"] == "extra_value"
        
        # Check components enriched
        assert len(enriched["organic_components"]) == 2


@pytest.mark.unit
class TestProductAssemblerExtractBlockchainData:
    """Test _extract_blockchain_data() method with new structure (5 elements)"""
    
    @pytest.fixture
    def assembler(self):
        """Create ProductAssembler with mock ComponentService"""
        mock_component_service = MockComponentService()
        return ProductAssembler(component_service=mock_component_service)
    
    def test_extract_blockchain_data_success(self, assembler):
        """Test successful extraction with new structure (5 elements)"""
        blockchain_data = (
            123,                              # [0] id
            "0x1234567890abcdef",            # [1] seller
            ["amanita_muscaria", "lions_mane"],  # [2] componentIds
            "QmMetadataCID123",              # [3] metadataCID
            True                              # [4] active
        )
        
        result = assembler._extract_blockchain_data(blockchain_data)
        
        assert result is not None
        product_id, seller, component_ids, ipfs_cid, is_active = result
        
        assert product_id == 123
        assert seller == "0x1234567890abcdef"
        assert component_ids == ["amanita_muscaria", "lions_mane"]
        assert ipfs_cid == "QmMetadataCID123"
        assert is_active is True
    
    def test_extract_blockchain_data_single_component(self, assembler):
        """Test extraction with single component in componentIds"""
        blockchain_data = (
            456,
            "0xabcdef1234567890",
            ["blue_lotus"],  # Single component
            "QmSingleCID",
            False
        )
        
        result = assembler._extract_blockchain_data(blockchain_data)
        
        assert result is not None
        product_id, seller, component_ids, ipfs_cid, is_active = result
        
        assert component_ids == ["blue_lotus"]
        assert is_active is False
    
    def test_extract_blockchain_data_empty_component_ids(self, assembler):
        """Test extraction with empty componentIds list"""
        blockchain_data = (
            789,
            "0x9876543210fedcba",
            [],  # Empty list
            "QmEmptyCID",
            True
        )
        
        result = assembler._extract_blockchain_data(blockchain_data)
        
        assert result is not None
        _, _, component_ids, _, _ = result
        assert component_ids == []
    
    def test_extract_blockchain_data_insufficient_elements(self, assembler):
        """Test that insufficient elements returns None"""
        blockchain_data = (123, "0x123", "QmCID")  # Only 3 elements
        
        result = assembler._extract_blockchain_data(blockchain_data)
        
        assert result is None
    
    def test_extract_blockchain_data_invalid_component_ids_type(self, assembler):
        """Test that non-list componentIds returns None"""
        blockchain_data = (
            123,
            "0x123",
            "not_a_list",  # Should be a list
            "QmCID",
            True
        )
        
        result = assembler._extract_blockchain_data(blockchain_data)
        
        assert result is None


@pytest.mark.unit
class TestProductAssemblerValidateComponentIds:
    """Test _validate_component_ids_match() method"""
    
    @pytest.fixture
    def assembler(self):
        """Create ProductAssembler with mock ComponentService"""
        mock_component_service = MockComponentService()
        return ProductAssembler(component_service=mock_component_service)
    
    def test_validate_component_ids_match_success(self, assembler):
        """Test successful validation when componentIds match"""
        component_ids = ["amanita_muscaria", "lions_mane"]
        metadata = {
            "business_id": "test_product",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "lions_mane", "proportion": "50g"}
            ]
        }
        
        result = assembler._validate_component_ids_match(component_ids, metadata)
        
        assert result is True
    
    def test_validate_component_ids_match_different_order(self, assembler):
        """Test validation when order differs but sets match"""
        component_ids = ["lions_mane", "amanita_muscaria"]  # Different order
        metadata = {
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "lions_mane", "proportion": "50g"}
            ]
        }
        
        result = assembler._validate_component_ids_match(component_ids, metadata)
        
        assert result is True  # Order doesn't matter
    
    def test_validate_component_ids_match_mismatch(self, assembler):
        """Test validation fails when componentIds don't match"""
        component_ids = ["amanita_muscaria", "lions_mane"]
        metadata = {
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "blue_lotus", "proportion": "50g"}  # Different
            ]
        }
        
        result = assembler._validate_component_ids_match(component_ids, metadata)
        
        assert result is False
    
    def test_validate_component_ids_match_missing_in_metadata(self, assembler):
        """Test validation fails when metadata has fewer components"""
        component_ids = ["amanita_muscaria", "lions_mane", "blue_lotus"]
        metadata = {
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"}
            ]
        }
        
        result = assembler._validate_component_ids_match(component_ids, metadata)
        
        assert result is False
    
    def test_validate_component_ids_match_extra_in_metadata(self, assembler):
        """Test validation fails when metadata has extra components"""
        component_ids = ["amanita_muscaria"]
        metadata = {
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "lions_mane", "proportion": "50g"}  # Extra
            ]
        }
        
        result = assembler._validate_component_ids_match(component_ids, metadata)
        
        assert result is False
    
    def test_validate_component_ids_match_missing_organic_components(self, assembler):
        """Test validation fails when organic_components missing"""
        component_ids = ["amanita_muscaria"]
        metadata = {
            "business_id": "test_product"
            # No organic_components
        }
        
        result = assembler._validate_component_ids_match(component_ids, metadata)
        
        assert result is False
    
    def test_validate_component_ids_match_empty_arrays(self, assembler):
        """Test validation with empty arrays"""
        component_ids = []
        metadata = {
            "organic_components": []
        }
        
        result = assembler._validate_component_ids_match(component_ids, metadata)
        
        assert result is True  # Both empty, so they match
