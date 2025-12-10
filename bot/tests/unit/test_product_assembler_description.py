"""
Unit tests for ProductAssembler ComponentDescription enrichment.

Tests:
- _enrich_components(): ComponentDescription fetch for all products (unified method)

Focus: Async logic, graceful degradation, error handling, language parameter
"""

import pytest
from unittest.mock import Mock, AsyncMock
from services.product.assembler import ProductAssembler
from model.organic_component import OrganicComponent
from model.component_description import ComponentDescription


class MockComponentService:
    """
    Enhanced mock ComponentService for testing ComponentDescription fetch.
    
    Supports both sync (get_component_full) and async (get_component_description) methods.
    """
    
    def __init__(self):
        self.components = {}  # For get_component_full
        self.descriptions = {}  # For get_component_description
    
    def get_component_full(self, component_id):
        """Mock get_component_full (sync)"""
        return self.components.get(component_id)
    
    async def get_component_description(self, component_id, language="ru"):
        """Mock get_component_description (async)"""
        key = f"{component_id}:{language}"
        return self.descriptions.get(key)


@pytest.mark.unit
class TestProductAssemblerDescriptionSingle:
    """Test ComponentDescription fetch for products with single component"""
    
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
        
        # Add test description (Russian)
        test_description_ru = ComponentDescription(
            generic_description="Мухомор красный - древний шаманский гриб для медитации и духовного роста.",
            effects="Усиление осознанности, глубокая релаксация, улучшение сна.",
            shamanic="Традиционно используется шаманами для путешествий и видений.",
            warnings="Не употреблять в сыром виде. Требуется микродозинг."
        )
        service.descriptions["amanita_muscaria:ru"] = test_description_ru
        
        # Add test description (English)
        test_description_en = ComponentDescription(
            generic_description="Fly agaric - ancient shamanic mushroom for meditation and spiritual growth.",
            effects="Enhanced awareness, deep relaxation, improved sleep.",
            shamanic="Traditionally used by shamans for journeys and visions.",
            warnings="Do not consume raw. Microdosing required."
        )
        service.descriptions["amanita_muscaria:en"] = test_description_en
        
        return service
    
    @pytest.fixture
    def assembler(self, mock_component_service):
        """Create ProductAssembler with enhanced mock ComponentService"""
        return ProductAssembler(component_service=mock_component_service)
    
    # ==================================================================================
    # ТЕСТЫ: SINGLE PRODUCT - SUCCESS CASES
    # ==================================================================================
    
    @pytest.mark.asyncio
    async def test_enrich_components_with_description_success(self, assembler):
        """
        Test successful ComponentDescription fetch for product with single component.
        
        GIVEN: Product metadata with single component + component with description
        WHEN: _enrich_components() called with language
        THEN: Component dict includes 'description' field with all sections
        """
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
        
        # Check organic_components added
        assert "organic_components" in enriched
        assert len(enriched["organic_components"]) == 1
        
        # Check component structure
        component = enriched["organic_components"][0]
        assert component["component_id"] == "amanita_muscaria"
        
        # ✅ CRITICAL: Check description added
        assert "description" in component, "ComponentDescription должен быть добавлен"
        
        desc = component["description"]
        assert isinstance(desc, dict), "Description должен быть словарем (from to_dict())"
        
        # Validate description structure
        assert "generic_description" in desc
        assert "effects" in desc
        assert "shamanic" in desc
        assert "warnings" in desc
        
        # Validate content (Russian)
        assert "Мухомор" in desc["generic_description"]
        assert "релаксация" in desc["effects"]
        assert "шаманами" in desc["shamanic"]
        assert "микродозинг" in desc["warnings"]
    
    @pytest.mark.asyncio
    async def test_enrich_components_preserves_component_data_with_description(self, assembler):
        """
        Test that component data is preserved when description added.
        
        GIVEN: Product with single component and description
        WHEN: _enrich_components() called with language
        THEN: Original component data preserved + description added
        """
        metadata = {
            "business_id": "test_product",
            "organic_components": [
                {
                    "component_id": "amanita_muscaria",
                    "proportion": "50g"
                }
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        component = enriched["organic_components"][0]
        
        # Check original data preserved
        assert component["component_id"] == "amanita_muscaria"
        assert component["proportion"] == "50g"
        assert component["scientific_title"] == "Amanita muscaria"
        assert "forms" in component
        assert "features" in component
        
        # Check description added
        assert "description" in component
    
    # ==================================================================================
    # ТЕСТЫ: SINGLE PRODUCT - GRACEFUL DEGRADATION
    # ==================================================================================
    
    @pytest.mark.asyncio
    async def test_enrich_components_description_not_found(self, assembler):
        """
        Test graceful degradation when ComponentDescription not found.
        
        GIVEN: Component exists, but no description for requested language
        WHEN: _enrich_components() called with language
        THEN: Product still enriched, description gracefully skipped (no error)
        """
        # Setup: component exists, but remove description
        assembler.component_service.descriptions.clear()
        
        metadata = {
            "business_id": "test_product",
            "organic_components": [
                {
                    "component_id": "amanita_muscaria",
                    "proportion": "100g"
                }
            ]
        }
        
        # Should NOT raise exception
        enriched = await assembler._enrich_components(metadata, "ru")
        
        # Component enriched successfully
        assert "organic_components" in enriched
        component = enriched["organic_components"][0]
        
        # Component data present
        assert component["component_id"] == "amanita_muscaria"
        assert component["scientific_title"] == "Amanita muscaria"
        
        # ✅ CRITICAL: Description gracefully skipped (not added, but no error)
        assert "description" not in component, "Description должен быть пропущен при отсутствии"
    
    @pytest.mark.asyncio
    async def test_enrich_components_description_fetch_error(self, assembler):
        """
        Test graceful degradation when description fetch raises exception.
        
        GIVEN: get_component_description raises exception
        WHEN: _enrich_components() called with language
        THEN: Product still enriched, description gracefully skipped
        """
        # Setup: make get_component_description raise exception
        async def raise_error(component_id, language):
            raise Exception("Arweave timeout")
        
        assembler.component_service.get_component_description = raise_error
        
        metadata = {
            "business_id": "test_product",
            "organic_components": [
                {
                    "component_id": "amanita_muscaria",
                    "proportion": "100g"
                }
            ]
        }
        
        # Should NOT propagate exception
        enriched = await assembler._enrich_components(metadata, "ru")
        
        # Product enriched successfully
        assert "organic_components" in enriched
        component = enriched["organic_components"][0]
        
        # Component data present, description skipped
        assert component["component_id"] == "amanita_muscaria"
        assert "description" not in component


@pytest.mark.unit
class TestProductAssemblerDescriptionMulti:
    """Test ComponentDescription fetch for products with multiple components"""
    
    @pytest.fixture
    def mock_component_service(self):
        """Create mock ComponentService with multiple components and descriptions"""
        service = MockComponentService()
        
        # Add test components
        service.components["amanita_muscaria"] = OrganicComponent(
            component_id="amanita_muscaria",
            scientific_title="Amanita muscaria",
            forms=["dried"],
            features={"common": ["stress_relief"]}
        )
        
        service.components["lions_mane"] = OrganicComponent(
            component_id="lions_mane",
            scientific_title="Hericium erinaceus",
            forms=["dried"],
            features={"common": ["cognitive_support"]}
        )
        
        service.components["passionflower"] = OrganicComponent(
            component_id="passionflower",
            scientific_title="Passiflora incarnata",
            forms=["dried"],
            features={"common": ["relaxation"]}
        )
        
        # Add descriptions
        service.descriptions["amanita_muscaria:ru"] = ComponentDescription(
            generic_description="Мухомор красный для медитации."
        )
        
        service.descriptions["lions_mane:ru"] = ComponentDescription(
            generic_description="Ежовик гребенчатый для когнитивных функций."
        )
        
        service.descriptions["passionflower:ru"] = ComponentDescription(
            generic_description="Пассифлора для расслабления и сна."
        )
        
        return service
    
    @pytest.fixture
    def assembler(self, mock_component_service):
        """Create ProductAssembler with enhanced mock ComponentService"""
        return ProductAssembler(component_service=mock_component_service)
    
    # ==================================================================================
    # ТЕСТЫ: MULTI PRODUCT - SUCCESS CASES
    # ==================================================================================
    
    @pytest.mark.asyncio
    async def test_enrich_components_with_descriptions_all_found(self, assembler):
        """
        Test successful ComponentDescription fetch for all components in product.
        
        GIVEN: Product with 2 components, both have descriptions
        WHEN: _enrich_components() called with language
        THEN: Both components include 'description' field
        """
        metadata = {
            "business_id": "blend_product",
            "title": "Relaxation Blend",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "lions_mane", "proportion": "30g"}
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        # Check both components enriched
        assert len(enriched["organic_components"]) == 2
        
        # ✅ CRITICAL: Check first component has description
        comp1 = enriched["organic_components"][0]
        assert "description" in comp1
        assert "Мухомор" in comp1["description"]["generic_description"]
        
        # ✅ CRITICAL: Check second component has description
        comp2 = enriched["organic_components"][1]
        assert "description" in comp2
        assert "Ежовик" in comp2["description"]["generic_description"]
    
    @pytest.mark.asyncio
    async def test_enrich_components_with_descriptions_three_components(self, assembler):
        """
        Test ComponentDescription fetch for 3-component product.
        
        GIVEN: Product with 3 components
        WHEN: _enrich_components() called with language
        THEN: All 3 components include descriptions
        """
        metadata = {
            "business_id": "triple_blend",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "40g"},
                {"component_id": "lions_mane", "proportion": "30g"},
                {"component_id": "passionflower", "proportion": "30g"}
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        # Check all 3 components have descriptions
        assert len(enriched["organic_components"]) == 3
        
        for i, comp in enumerate(enriched["organic_components"]):
            assert "description" in comp, f"Компонент {i} должен иметь description"
            assert "generic_description" in comp["description"]
            assert len(comp["description"]["generic_description"]) > 10
    
    # ==================================================================================
    # ТЕСТЫ: MULTI PRODUCT - GRACEFUL DEGRADATION
    # ==================================================================================
    
    @pytest.mark.asyncio
    async def test_enrich_components_partial_descriptions(self, assembler):
        """
        Test partial success when some descriptions not found.
        
        GIVEN: Product with 2 components, only 1 has description
        WHEN: _enrich_components() called with language
        THEN: Component with description enriched, other gracefully skipped
        """
        # Remove description for lions_mane
        assembler.component_service.descriptions.pop("lions_mane:ru", None)
        
        metadata = {
            "business_id": "partial_blend",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "lions_mane", "proportion": "50g"}
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        # Check both components enriched
        assert len(enriched["organic_components"]) == 2
        
        # First component: description present
        comp1 = enriched["organic_components"][0]
        assert "description" in comp1
        
        # Second component: description gracefully skipped
        comp2 = enriched["organic_components"][1]
        assert "description" not in comp2, "Description должен быть пропущен при отсутствии"
        
        # But component data still present
        assert comp2["component_id"] == "lions_mane"
        assert comp2["scientific_title"] == "Hericium erinaceus"
    
    @pytest.mark.asyncio
    async def test_enrich_components_all_descriptions_not_found(self, assembler):
        """
        Test when NO descriptions available for any component.
        
        GIVEN: Product with multiple components, no descriptions available
        WHEN: _enrich_components() called with language
        THEN: Product still enriched, all descriptions gracefully skipped
        """
        # Clear all descriptions
        assembler.component_service.descriptions.clear()
        
        metadata = {
            "business_id": "no_desc_blend",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "lions_mane", "proportion": "50g"}
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        # Both components enriched without descriptions
        assert len(enriched["organic_components"]) == 2
        
        for comp in enriched["organic_components"]:
            assert "description" not in comp
            assert "component_id" in comp
            assert "scientific_title" in comp
    
    @pytest.mark.asyncio
    async def test_enrich_components_description_fetch_errors(self, assembler):
        """
        Test graceful degradation when description fetch raises exceptions.
        
        GIVEN: get_component_description raises exception for all components
        WHEN: _enrich_components() called with language
        THEN: Product still enriched, descriptions gracefully skipped
        """
        # Make get_component_description raise exception
        async def raise_error(component_id, language):
            raise Exception(f"Arweave timeout for {component_id}")
        
        assembler.component_service.get_component_description = raise_error
        
        metadata = {
            "business_id": "error_blend",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "lions_mane", "proportion": "50g"}
            ]
        }
        
        # Should NOT propagate exception
        enriched = await assembler._enrich_components(metadata, "ru")
        
        # Product enriched successfully
        assert len(enriched["organic_components"]) == 2
        
        # Descriptions gracefully skipped for all
        for comp in enriched["organic_components"]:
            assert "description" not in comp
            assert "component_id" in comp


@pytest.mark.unit
class TestProductAssemblerDescriptionEdgeCases:
    """Test edge cases for ComponentDescription enrichment"""
    
    @pytest.fixture
    def mock_component_service(self):
        """Create mock ComponentService"""
        service = MockComponentService()
        
        service.components["test_component"] = OrganicComponent(
            component_id="test_component",
            scientific_title="Test Component",
            forms=["dried"],
            features={"common": ["test"]}
        )
        
        return service
    
    @pytest.fixture
    def assembler(self, mock_component_service):
        """Create ProductAssembler"""
        return ProductAssembler(component_service=mock_component_service)
    
    @pytest.mark.asyncio
    async def test_description_none_returned(self, assembler):
        """
        Test when get_component_description returns None (valid case).
        
        GIVEN: get_component_description returns None (not found)
        WHEN: _enrich_components() called with language
        THEN: Description gracefully skipped, no error
        """
        # get_component_description returns None by default (not in descriptions dict)
        metadata = {
            "business_id": "test",
            "organic_components": [
                {
                    "component_id": "test_component",
                    "proportion": "100g"
                }
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        component = enriched["organic_components"][0]
        assert "description" not in component
        assert component["component_id"] == "test_component"
    
    @pytest.mark.asyncio
    async def test_description_empty_dict_returned(self, assembler):
        """
        Test handling of empty description (edge case).
        
        GIVEN: get_component_description returns empty-ish description
        WHEN: _enrich_components() called with language
        THEN: Description added (even if minimal)
        """
        # Add minimal description
        assembler.component_service.descriptions["test_component:ru"] = ComponentDescription(
            generic_description="Minimal description only."
        )
        
        metadata = {
            "business_id": "test",
            "organic_components": [
                {
                    "component_id": "test_component",
                    "proportion": "100g"
                }
            ]
        }
        
        enriched = await assembler._enrich_components(metadata, "ru")
        
        component = enriched["organic_components"][0]
        
        # Description added (even if minimal)
        assert "description" in component
        assert component["description"]["generic_description"] == "Minimal description only."
        
        # Optional fields None or missing (graceful)
        assert component["description"].get("effects") is None or "effects" not in component["description"]

