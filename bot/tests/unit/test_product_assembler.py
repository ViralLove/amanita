"""
Unit tests for ProductAssembler.

Tests:
- _detect_product_format(): SINGLE/MULTI detection
- _enrich_single_component(): ComponentService integration
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
class TestProductAssemblerDetectFormat:
    """Test _detect_product_format() method"""
    
    @pytest.fixture
    def assembler(self):
        """Create ProductAssembler with mock ComponentService"""
        mock_component_service = MockComponentService()
        return ProductAssembler(component_service=mock_component_service)
    
    def test_detect_single_format(self, assembler):
        """Test detection of SINGLE format (component_id at root)"""
        metadata = {
            "business_id": "product_001",
            "title": "Amanita Muscaria",
            "component_id": "amanita_muscaria",
            "proportion": "100g",
            "categories": ["mushrooms"],
            "forms": ["dried"],
            "species": ["Amanita muscaria"]
        }
        
        format_type = assembler._detect_product_format(metadata)
        
        assert format_type == ProductAssembler.FORMAT_SINGLE
    
    def test_detect_single_format_empty_component_id(self, assembler):
        """Test that empty component_id raises ValueError"""
        metadata = {
            "business_id": "product_001",
            "component_id": "",  # Empty string
            "categories": ["mushrooms"]
        }
        
        with pytest.raises(ValueError, match="Неподдерживаемый формат"):
            assembler._detect_product_format(metadata)
    
    def test_detect_multi_format(self, assembler):
        """Test detection of NEW_MULTI format (organic_components array)"""
        metadata = {
            "business_id": "product_002",
            "title": "Blend Product",
            "organic_components": [
                {
                    "component_id": "amanita_muscaria",
                    "proportion": "50g"
                },
                {
                    "component_id": "psilocybe_cubensis",
                    "proportion": "30g"
                }
            ],
            "categories": ["mushrooms", "blends"],
            "forms": ["dried"],
            "species": ["Amanita muscaria", "Psilocybe cubensis"]
        }
        
        format_type = assembler._detect_product_format(metadata)
        
        assert format_type == ProductAssembler.FORMAT_MULTI
    
    def test_detect_multi_format_single_component(self, assembler):
        """Test NEW_MULTI format with single component in array"""
        metadata = {
            "business_id": "product_003",
            "title": "Single Component in Array",
            "organic_components": [
                {
                    "component_id": "blue_lotus",
                    "proportion": "100g"
                }
            ],
            "categories": ["flowers"],
            "forms": ["dried"]
        }
        
        format_type = assembler._detect_product_format(metadata)
        
        assert format_type == ProductAssembler.FORMAT_MULTI
    
    def test_reject_empty_organic_components_array(self, assembler):
        """Test that empty organic_components array raises ValueError"""
        metadata = {
            "business_id": "product_006",
            "title": "Empty Components",
            "organic_components": [],  # Empty array
            "categories": ["mushrooms"]
        }
        
        with pytest.raises(ValueError, match="Пустой массив organic_components|Empty organic_components"):
            assembler._detect_product_format(metadata)
    
    def test_reject_organic_components_without_component_id(self, assembler):
        """Test that organic_components without component_id raises ValueError"""
        metadata = {
            "business_id": "product_007",
            "title": "Missing Component ID",
            "organic_components": [
                {
                    "proportion": "100g"  # No component_id!
                }
            ],
            "categories": ["mushrooms"]
        }
        
        with pytest.raises(ValueError, match="не содержат component_id|does not contain component_id"):
            assembler._detect_product_format(metadata)
    
    def test_reject_unknown_format_no_component_id_no_organic_components(self, assembler):
        """Test that metadata without component_id or organic_components raises ValueError"""
        metadata = {
            "business_id": "product_008",
            "title": "Unknown Format",
            "categories": ["mushrooms"]
            # No component_id, no organic_components
        }
        
        with pytest.raises(ValueError, match="Неподдерживаемый формат|Unsupported product format"):
            assembler._detect_product_format(metadata)
    
    def test_reject_unknown_format_only_business_id(self, assembler):
        """Test that minimal metadata raises ValueError"""
        metadata = {
            "business_id": "product_009"
            # Minimal metadata, no component info
        }
        
        with pytest.raises(ValueError, match="Неподдерживаемый формат|Unsupported product format"):
            assembler._detect_product_format(metadata)
    
    def test_detect_single_with_additional_fields(self, assembler):
        """Test NEW_SINGLE format with many additional fields"""
        metadata = {
            "business_id": "product_010",
            "title": "Rich Metadata Product",
            "component_id": "amanita_muscaria",
            "proportion": "100g",
            "categories": ["mushrooms"],
            "forms": ["dried", "powder"],
            "species": ["Amanita muscaria"],
            "cover_image_url": "QmImage123",
            "description": "Some description",
            "price": 100,
            "currency": "USD"
        }
        
        format_type = assembler._detect_product_format(metadata)
        
        assert format_type == ProductAssembler.FORMAT_SINGLE
    
    def test_detect_multi_with_additional_fields(self, assembler):
        """Test NEW_MULTI format with many additional fields"""
        metadata = {
            "business_id": "product_011",
            "title": "Rich Multi-Component Product",
            "organic_components": [
                {
                    "component_id": "amanita_muscaria",
                    "proportion": "50g",
                    "extraction_method": "dried"
                },
                {
                    "component_id": "psilocybe_cubensis",
                    "proportion": "30g",
                    "purity": "99%"
                }
            ],
            "categories": ["mushrooms", "blends"],
            "forms": ["dried"],
            "species": ["Amanita muscaria", "Psilocybe cubensis"],
            "cover_image_url": "QmBlendImage"
        }
        
        format_type = assembler._detect_product_format(metadata)
        
        assert format_type == ProductAssembler.FORMAT_MULTI
    
    def test_reject_component_id_not_string(self, assembler):
        """Test that non-string component_id raises ValueError"""
        metadata = {
            "business_id": "product_012",
            "component_id": 12345,  # Not a string
            "categories": ["mushrooms"]
        }
        
        with pytest.raises(ValueError, match="Неподдерживаемый формат|Unsupported product format"):
            assembler._detect_product_format(metadata)
    
    def test_reject_organic_components_not_list(self, assembler):
        """Test that organic_components not being a list raises ValueError"""
        metadata = {
            "business_id": "product_013",
            "organic_components": "not_a_list",  # Should be a list
            "categories": ["mushrooms"]
        }
        
        with pytest.raises(ValueError, match="Неподдерживаемый формат|Unsupported product format"):
            assembler._detect_product_format(metadata)

@pytest.mark.unit
class TestProductAssemblerEnrichSingle:
    """Test _enrich_single_component() method"""
    
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
    async def test_enrich_single_component_success(self, assembler):
        """Test successful enrichment of SINGLE product"""
        metadata = {
            "business_id": "test_product",
            "component_id": "amanita_muscaria",
            "proportion": "100g",
            "title": "Test Product"
        }
        
        enriched = await assembler._enrich_single_component(metadata)
        
        # Check organic_components added
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
    async def test_enrich_single_component_default_proportion(self, assembler):
        """Test enrichment with default proportion"""
        metadata = {
            "business_id": "test_product",
            "component_id": "amanita_muscaria",
            "title": "Test Product"
            # No proportion → should default to "100g"
        }
        
        enriched = await assembler._enrich_single_component(metadata)
        
        component = enriched["organic_components"][0]
        assert component["proportion"] == "100g"
    
    @pytest.mark.asyncio
    async def test_enrich_single_component_not_found(self, assembler):
        """Test ValueError when component not found in registry"""
        metadata = {
            "business_id": "test_product",
            "component_id": "non_existent_component",
            "proportion": "50g"
        }
        
        with pytest.raises(ValueError, match="не найден|not found"):
            await assembler._enrich_single_component(metadata)
    
    @pytest.mark.asyncio
    async def test_enrich_single_component_preserves_metadata(self, assembler):
        """Test that original metadata is preserved"""
        metadata = {
            "business_id": "test_product",
            "component_id": "amanita_muscaria",
            "proportion": "100g",
            "title": "Test Product",
            "categories": ["mushrooms"],
            "extra_field": "extra_value"
        }
        
        enriched = await assembler._enrich_single_component(metadata)
        
        # Check original fields preserved
        assert enriched["business_id"] == "test_product"
        assert enriched["title"] == "Test Product"
        assert enriched["categories"] == ["mushrooms"]
        assert enriched["extra_field"] == "extra_value"
        
        # Check new field added
        assert "organic_components" in enriched


@pytest.mark.unit
class TestProductAssemblerEnrichMulti:
    """Test _enrich_multi_component() method"""
    
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
    async def test_enrich_multi_component_success(self, assembler):
        """Test successful enrichment of MULTI product"""
        metadata = {
            "business_id": "blend_product",
            "title": "Relaxation Blend",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "lions_mane", "proportion": "30g"}
            ]
        }
        
        enriched = await assembler._enrich_multi_component(metadata)
        
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
    async def test_enrich_multi_component_three_components(self, assembler):
        """Test enrichment with three components"""
        metadata = {
            "business_id": "triple_blend",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "40g"},
                {"component_id": "lions_mane", "proportion": "30g"},
                {"component_id": "passionflower", "proportion": "30g"}
            ]
        }
        
        enriched = await assembler._enrich_multi_component(metadata)
        
        assert len(enriched["organic_components"]) == 3
        assert enriched["organic_components"][0]["component_id"] == "amanita_muscaria"
        assert enriched["organic_components"][1]["component_id"] == "lions_mane"
        assert enriched["organic_components"][2]["component_id"] == "passionflower"
    
    @pytest.mark.asyncio
    async def test_enrich_multi_component_not_found(self, assembler):
        """Test ValueError when component not found in registry"""
        metadata = {
            "business_id": "invalid_blend",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "non_existent", "proportion": "50g"}
            ]
        }
        
        with pytest.raises(ValueError, match="не найден|not found"):
            await assembler._enrich_multi_component(metadata)
    
    @pytest.mark.asyncio
    async def test_enrich_multi_component_missing_component_id(self, assembler):
        """Test ValueError when component_id missing"""
        metadata = {
            "business_id": "invalid_blend",
            "organic_components": [
                {"proportion": "100g"}  # No component_id
            ]
        }
        
        with pytest.raises(ValueError, match="Отсутствует component_id|Missing component_id"):
            await assembler._enrich_multi_component(metadata)
    
    @pytest.mark.asyncio
    async def test_enrich_multi_component_missing_proportion(self, assembler):
        """Test ValueError when proportion missing"""
        metadata = {
            "business_id": "invalid_blend",
            "organic_components": [
                {"component_id": "amanita_muscaria"}  # No proportion
            ]
        }
        
        with pytest.raises(ValueError, match="Отсутствует proportion|Missing proportion"):
            await assembler._enrich_multi_component(metadata)
    
    @pytest.mark.asyncio
    async def test_enrich_multi_component_preserves_metadata(self, assembler):
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
        
        enriched = await assembler._enrich_multi_component(metadata)
        
        # Check original fields preserved
        assert enriched["business_id"] == "blend_product"
        assert enriched["title"] == "Test Blend"
        assert enriched["categories"] == ["mushrooms", "blends"]
        assert enriched["extra_field"] == "extra_value"
        
        # Check components enriched
        assert len(enriched["organic_components"]) == 2
