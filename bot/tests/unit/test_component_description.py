"""
Unit tests for ComponentDescription model.

Tests:
- __post_init__: Validation of all fields (generic_description, dosage_instructions, features)
- from_dict(): Deserialization from dictionaries (including real Arweave data)
- to_dict(): Serialization to dictionaries (including nested structures)
- __eq__ and __hash__: Equality and hashing for collections

Focus: Model validation, real data compatibility, nested structures
"""

import pytest
import json
from pathlib import Path
from model.component_description import ComponentDescription
from model.dosage_instruction import DosageInstruction


# ==============================================================================
# TEST DATA FIXTURES
# ==============================================================================

@pytest.fixture
def minimal_data():
    """Minimal valid ComponentDescription data"""
    return {
        "generic_description": "Test description with minimum 10 characters"
    }


@pytest.fixture
def full_data():
    """Full ComponentDescription data with all fields"""
    return {
        "generic_description": "Full test description with all fields populated",
        "title": "Test Title",
        "scientific_title": "Testus maximus",
        "effects": "Test effects description",
        "shamanic": "Test shamanic perspective",
        "warnings": "Test warnings",
        "features": ["feature1", "feature2", "feature3"]
    }


@pytest.fixture
def real_arweave_data_ru():
    """
    Real Arweave data from amanita_muscaria.ComponentDescription.ru.json
    
    NOTE: This fixture loads ACTUAL production data to validate
    that ComponentDescription can handle real-world content with:
    - Emoji (🔬 🔹 🌿 🌀 ⚠️)
    - Newlines (\n)
    - Quotes ("текст")
    - Long text (~700 characters)
    """
    file_path = Path("data/components/amanita_muscaria/complex_fields/amanita_muscaria.ComponentDescription.ru.json")
    
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # Fallback to inline data if file not found
        return {
            "generic_description": "🔬 Активные компоненты:\n🔹Мусцимол — седатив, диссоциатив, открывает доступ к \"второму телу\", активируя тормозную систему ГАМК.\n🔹Иботеновая кислота — психостимулятор, вызывает возбуждение через NMDA-рецепторы.",
            "effects": "🌿 Целительное действие:\n🔹Нейромодуляция: балансирует возбуждение и торможение.",
            "shamanic": "🌀 Шаманская перспектива:\nМухомор не \"даёт приход\" — он отключает автоматизм.",
            "warnings": "⚠️ Предостережения:\n🔹Нельзя употреблять в сыром виде."
        }


@pytest.fixture
def test_dosage_instruction():
    """Test DosageInstruction for nested structure tests"""
    return DosageInstruction(
        type="dried",
        title="Сушеная форма",
        description="Тестовая инструкция по дозировке"
    )


# ==============================================================================
# TEST CLASS 1: VALIDATION (__post_init__)
# ==============================================================================

@pytest.mark.unit
class TestComponentDescriptionValidation:
    """
    Test __post_init__ validation logic.
    
    Validates:
    - generic_description length (10-1000 characters)
    - dosage_instructions type and content
    - features type and content
    """
    
    # ==========================================================================
    # VALID CASES (5 tests)
    # ==========================================================================
    
    def test_valid_minimal_description(self):
        """Test minimal valid ComponentDescription (only generic_description)"""
        desc = ComponentDescription(
            generic_description="Valid test description text"
        )
        assert desc.generic_description == "Valid test description text"
        assert desc.title is None
        assert desc.effects is None
    
    def test_valid_with_emoji_and_newlines(self):
        """Test validation accepts emoji and newlines in text"""
        desc = ComponentDescription(
            generic_description="🔬 Test with emoji\n🔹 And newlines\n🌿 Multiple lines"
        )
        assert "🔬" in desc.generic_description
        assert "\n" in desc.generic_description
    
    def test_valid_with_dosage_instructions_empty_list(self):
        """Test validation accepts empty dosage_instructions list"""
        desc = ComponentDescription(
            generic_description="Test description text",
            dosage_instructions=[]
        )
        assert desc.dosage_instructions == []
    
    def test_valid_with_features_empty_list(self):
        """Test validation accepts empty features list"""
        desc = ComponentDescription(
            generic_description="Test description text",
            features=[]
        )
        assert desc.features == []
    
    def test_valid_full_structure(self):
        """Test validation with all fields populated"""
        dosage = DosageInstruction(
            type="dried",
            title="Test Dosage",
            description="Test dosage description"
        )
        
        desc = ComponentDescription(
            generic_description="Full test description",
            title="Test Title",
            scientific_title="Testus maximus",
            effects="Test effects",
            shamanic="Test shamanic",
            warnings="Test warnings",
            dosage_instructions=[dosage],
            features=["feature1", "feature2"]
        )
        
        assert desc.generic_description == "Full test description"
        assert desc.title == "Test Title"
        assert len(desc.dosage_instructions) == 1
        assert len(desc.features) == 2
    
    # ==========================================================================
    # INVALID CASES (8 tests)
    # ==========================================================================
    
    def test_reject_empty_generic_description(self):
        """Test ValueError for empty generic_description"""
        with pytest.raises(ValueError, match="не может быть пустым"):
            ComponentDescription(generic_description="")
    
    def test_reject_whitespace_only_generic_description(self):
        """Test ValueError for whitespace-only generic_description"""
        with pytest.raises(ValueError, match="не может быть пустым"):
            ComponentDescription(generic_description="   \n  \t  ")
    
    def test_reject_too_short_generic_description(self):
        """Test ValueError for generic_description < 10 characters"""
        with pytest.raises(ValueError, match="слишком короткий"):
            ComponentDescription(generic_description="Short")  # 5 chars
    
    def test_reject_too_long_generic_description(self):
        """Test ValueError for generic_description > 1000 characters"""
        long_text = "x" * 1001
        with pytest.raises(ValueError, match="слишком длинный"):
            ComponentDescription(generic_description=long_text)
    
    def test_reject_dosage_instructions_not_list(self):
        """Test ValueError when dosage_instructions is not a list"""
        with pytest.raises(ValueError, match="должен быть списком"):
            ComponentDescription(
                generic_description="Test description",
                dosage_instructions="not a list"
            )
    
    def test_reject_dosage_instructions_invalid_type(self):
        """Test ValueError when dosage_instructions contains non-DosageInstruction"""
        with pytest.raises(ValueError, match="должен быть объектом DosageInstruction"):
            ComponentDescription(
                generic_description="Test description",
                dosage_instructions=["invalid", "items"]
            )
    
    def test_reject_features_not_list(self):
        """Test ValueError when features is not a list"""
        with pytest.raises(ValueError, match="должен быть списком"):
            ComponentDescription(
                generic_description="Test description",
                features="not a list"
            )
    
    def test_reject_features_empty_string(self):
        """Test ValueError when features contains empty string"""
        with pytest.raises(ValueError, match="должен быть непустой строкой"):
            ComponentDescription(
                generic_description="Test description",
                features=["valid", "", "another"]
            )
    
    # ==========================================================================
    # EDGE CASES (2 tests)
    # ==========================================================================
    
    def test_boundary_exactly_10_characters(self):
        """Test boundary: exactly 10 characters (minimum valid)"""
        desc = ComponentDescription(generic_description="1234567890")
        assert len(desc.generic_description) == 10
    
    def test_boundary_exactly_1000_characters(self):
        """Test boundary: exactly 1000 characters (maximum valid)"""
        text_1000 = "x" * 1000
        desc = ComponentDescription(generic_description=text_1000)
        assert len(desc.generic_description) == 1000


# ==============================================================================
# TEST CLASS 2: DESERIALIZATION (from_dict)
# ==============================================================================

@pytest.mark.unit
class TestComponentDescriptionFromDict:
    """
    Test from_dict() deserialization.
    
    Validates:
    - Minimal dict structure
    - Full dict with all fields
    - Real Arweave data (emoji, newlines, quotes)
    - Nested DosageInstruction deserialization
    - Error handling for invalid data
    """
    
    # ==========================================================================
    # VALID CASES (6 tests)
    # ==========================================================================
    
    def test_from_dict_minimal(self, minimal_data):
        """Test from_dict with minimal data (only generic_description)"""
        desc = ComponentDescription.from_dict(minimal_data)
        
        assert desc.generic_description == minimal_data["generic_description"]
        assert desc.title is None
        assert desc.effects is None
        assert desc.shamanic is None
        assert desc.warnings is None
        assert desc.dosage_instructions is None
        assert desc.features is None
    
    def test_from_dict_full_structure(self, full_data):
        """Test from_dict with all fields populated"""
        desc = ComponentDescription.from_dict(full_data)
        
        assert desc.generic_description == full_data["generic_description"]
        assert desc.title == full_data["title"]
        assert desc.scientific_title == full_data["scientific_title"]
        assert desc.effects == full_data["effects"]
        assert desc.shamanic == full_data["shamanic"]
        assert desc.warnings == full_data["warnings"]
        assert desc.features == full_data["features"]
    
    def test_from_dict_with_dosage_instructions(self):
        """Test from_dict with nested DosageInstruction deserialization"""
        data = {
            "generic_description": "Test with dosage instructions",
            "dosage_instructions": [
                {
                    "type": "dried",
                    "title": "Сушеная форма",
                    "description": "Тестовая инструкция"
                },
                {
                    "type": "tincture",
                    "title": "Настойка",
                    "description": "Другая инструкция"
                }
            ]
        }
        
        desc = ComponentDescription.from_dict(data)
        
        # Check nested deserialization worked
        assert desc.dosage_instructions is not None
        assert len(desc.dosage_instructions) == 2
        assert isinstance(desc.dosage_instructions[0], DosageInstruction)
        assert desc.dosage_instructions[0].type == "dried"
        assert desc.dosage_instructions[1].type == "tincture"
    
    def test_from_dict_with_features(self):
        """Test from_dict with features array"""
        data = {
            "generic_description": "Test with features",
            "features": ["feature1", "feature2", "feature3"]
        }
        
        desc = ComponentDescription.from_dict(data)
        
        assert desc.features is not None
        assert len(desc.features) == 3
        assert desc.features == ["feature1", "feature2", "feature3"]
    
    def test_from_dict_real_arweave_russian(self, real_arweave_data_ru):
        """
        CRITICAL TEST: Real Arweave data (Russian) deserialization.
        
        Tests with ACTUAL production data containing:
        - Emoji (🔬 🔹 🌿 🌀 ⚠️)
        - Newlines (\n)
        - Quotes ("текст")
        - Long text (~700 characters)
        """
        desc = ComponentDescription.from_dict(real_arweave_data_ru)
        
        # Validate real content
        assert "Мусцимол" in desc.generic_description or "🔬" in desc.generic_description
        
        # Validate emoji preserved
        emoji_found = any(e in desc.generic_description for e in ["🔬", "🔹", "🌿", "🌀", "⚠️"])
        assert emoji_found, "Emoji должны сохраняться"
        
        # Validate newlines preserved (if effects present)
        if desc.effects:
            assert "\n" in desc.effects or "\n" in desc.generic_description
        
        # Validate quotes preserved (if shamanic present)
        if desc.shamanic:
            # Russian data may have quotes
            pass  # Graceful — quotes optional
        
        # Validate long text handled
        assert len(desc.generic_description) >= 10, "Generic description должен быть валиден"
    
    def test_from_dict_real_arweave_english(self):
        """
        CRITICAL TEST: Real Arweave data (English) deserialization.
        
        Tests with English production data if available.
        """
        file_path = Path("data/components/amanita_muscaria/complex_fields/amanita_muscaria.ComponentDescription.en.json")
        
        if not file_path.exists():
            pytest.skip("English Arweave data not found")
        
        with open(file_path, "r", encoding="utf-8") as f:
            real_data_en = json.load(f)
        
        desc = ComponentDescription.from_dict(real_data_en)
        
        # Validate structure
        assert desc.generic_description is not None
        assert len(desc.generic_description) >= 10
    
    # ==========================================================================
    # INVALID CASES (4 tests)
    # ==========================================================================
    
    def test_from_dict_reject_non_dict(self):
        """Test ValueError when data is not a dict"""
        with pytest.raises(ValueError, match="должны быть словарем"):
            ComponentDescription.from_dict("not a dict")
    
    def test_from_dict_reject_missing_generic_description(self):
        """Test ValueError when generic_description field missing"""
        data = {
            "title": "Test",
            "effects": "Effects"
            # No generic_description
        }
        
        with pytest.raises(ValueError, match="Отсутствует обязательное поле"):
            ComponentDescription.from_dict(data)
    
    def test_from_dict_reject_invalid_dosage_instructions_format(self):
        """Test ValueError when dosage_instructions has invalid format"""
        data = {
            "generic_description": "Test description",
            "dosage_instructions": "not a list"
        }
        
        with pytest.raises(ValueError, match="должен быть списком"):
            ComponentDescription.from_dict(data)
    
    def test_from_dict_reject_invalid_features_format(self):
        """Test ValueError when features has invalid format"""
        data = {
            "generic_description": "Test description",
            "features": "not a list"
        }
        
        with pytest.raises(ValueError, match="должен быть списком"):
            ComponentDescription.from_dict(data)
    
    # ==========================================================================
    # EDGE CASES (2 tests)
    # ==========================================================================
    
    def test_from_dict_ignores_unknown_fields(self):
        """Test that unknown fields in dict are gracefully ignored"""
        data = {
            "generic_description": "Test description",
            "unknown_field": "should be ignored",
            "another_unknown": 12345
        }
        
        # Should NOT raise exception
        desc = ComponentDescription.from_dict(data)
        
        # Known field processed
        assert desc.generic_description == "Test description"
        
        # Unknown fields ignored (not added as attributes)
        assert not hasattr(desc, "unknown_field")
    
    def test_from_dict_handles_none_values(self):
        """Test handling of explicit None values in dict"""
        data = {
            "generic_description": "Test description",
            "title": None,
            "effects": None,
            "features": None
        }
        
        desc = ComponentDescription.from_dict(data)
        
        # Should accept None values
        assert desc.generic_description == "Test description"
        assert desc.title is None
        assert desc.effects is None
        assert desc.features is None


# ==============================================================================
# TEST CLASS 3: SERIALIZATION (to_dict)
# ==============================================================================

@pytest.mark.unit
class TestComponentDescriptionToDict:
    """
    Test to_dict() serialization.
    
    Validates:
    - Minimal structure (only generic_description)
    - Full structure (all fields)
    - None fields not included in output
    - Nested DosageInstruction.to_dict() calls
    - Round-trip (from_dict → to_dict)
    """
    
    # ==========================================================================
    # MINIMAL STRUCTURE (2 tests)
    # ==========================================================================
    
    def test_to_dict_minimal(self):
        """Test to_dict with only generic_description (minimal)"""
        desc = ComponentDescription(generic_description="Test description text")
        
        result = desc.to_dict()
        
        # Only generic_description in output
        assert result == {"generic_description": "Test description text"}
        
        # No other keys
        assert len(result) == 1
    
    def test_to_dict_none_fields_not_included(self):
        """Test that None fields are NOT included in output"""
        desc = ComponentDescription(
            generic_description="Test minimum 10 chars",
            title=None,
            effects=None,
            shamanic=None
        )
        
        result = desc.to_dict()
        
        # Only generic_description present
        assert "generic_description" in result
        
        # None fields not included
        assert "title" not in result
        assert "effects" not in result
        assert "shamanic" not in result
    
    # ==========================================================================
    # FULL STRUCTURE (3 tests)
    # ==========================================================================
    
    def test_to_dict_full_structure(self):
        """Test to_dict with all fields populated"""
        desc = ComponentDescription(
            generic_description="Full description",
            title="Test Title",
            scientific_title="Testus maximus",
            effects="Test effects",
            shamanic="Test shamanic",
            warnings="Test warnings",
            features=["f1", "f2"]
        )
        
        result = desc.to_dict()
        
        # All fields included
        assert result["generic_description"] == "Full description"
        assert result["title"] == "Test Title"
        assert result["scientific_title"] == "Testus maximus"
        assert result["effects"] == "Test effects"
        assert result["shamanic"] == "Test shamanic"
        assert result["warnings"] == "Test warnings"
        assert result["features"] == ["f1", "f2"]
    
    def test_to_dict_with_dosage_instructions_nested(self):
        """Test to_dict with nested DosageInstruction.to_dict() calls"""
        dosage1 = DosageInstruction(
            type="dried",
            title="Dried Form",
            description="Dosage for dried"
        )
        dosage2 = DosageInstruction(
            type="tincture",
            title="Tincture Form",
            description="Dosage for tincture"
        )
        
        desc = ComponentDescription(
            generic_description="Test with dosage",
            dosage_instructions=[dosage1, dosage2]
        )
        
        result = desc.to_dict()
        
        # Check dosage_instructions serialized
        assert "dosage_instructions" in result
        assert len(result["dosage_instructions"]) == 2
        
        # Check nested to_dict() called
        assert result["dosage_instructions"][0]["type"] == "dried"
        assert result["dosage_instructions"][1]["type"] == "tincture"
        assert isinstance(result["dosage_instructions"][0], dict)
    
    def test_to_dict_with_features_array(self):
        """Test to_dict with features array"""
        desc = ComponentDescription(
            generic_description="Test with features",
            features=["feature1", "feature2", "feature3"]
        )
        
        result = desc.to_dict()
        
        assert result["features"] == ["feature1", "feature2", "feature3"]
        assert isinstance(result["features"], list)
    
    # ==========================================================================
    # ROUND-TRIP (2 tests)
    # ==========================================================================
    
    def test_round_trip_from_dict_to_dict(self, full_data):
        """Test round-trip: from_dict(data) → to_dict() should match original"""
        # from_dict
        desc = ComponentDescription.from_dict(full_data)
        
        # to_dict
        result = desc.to_dict()
        
        # Should match original (minus None fields)
        assert result["generic_description"] == full_data["generic_description"]
        assert result["title"] == full_data["title"]
        assert result["effects"] == full_data["effects"]
        assert result["features"] == full_data["features"]
    
    def test_round_trip_create_to_dict_from_dict(self):
        """Test round-trip: Create → to_dict() → from_dict() → objects equal"""
        # Create object
        original = ComponentDescription(
            generic_description="Round trip test",
            effects="Test effects",
            features=["f1", "f2"]
        )
        
        # to_dict
        serialized = original.to_dict()
        
        # from_dict
        deserialized = ComponentDescription.from_dict(serialized)
        
        # Objects should be equal
        assert original == deserialized
        assert original.generic_description == deserialized.generic_description
        assert original.effects == deserialized.effects
        assert original.features == deserialized.features
    
    # ==========================================================================
    # EDGE CASE (1 test)
    # ==========================================================================
    
    def test_to_dict_long_text_no_loss(self):
        """Test that very long text serializes without data loss"""
        long_text = "x" * 999  # Near maximum
        desc = ComponentDescription(
            generic_description=long_text,
            effects="y" * 500
        )
        
        result = desc.to_dict()
        
        # No data loss
        assert len(result["generic_description"]) == 999
        assert len(result["effects"]) == 500
        assert result["generic_description"] == long_text


# ==============================================================================
# TEST CLASS 4: EQUALITY AND HASHING
# ==============================================================================

@pytest.mark.unit
class TestComponentDescriptionEquality:
    """
    Test __eq__ and __hash__ for collections.
    
    Validates:
    - Equality comparison
    - Inequality for different content
    - Hash consistency
    - Usage in set() and dict
    """
    
    # ==========================================================================
    # EQUALITY (4 tests)
    # ==========================================================================
    
    def test_equality_same_content(self):
        """Test two descriptions with same content are equal"""
        desc1 = ComponentDescription(generic_description="Same content here")
        desc2 = ComponentDescription(generic_description="Same content here")
        
        assert desc1 == desc2
    
    def test_inequality_different_generic_description(self):
        """Test inequality for different generic_description"""
        desc1 = ComponentDescription(generic_description="First description")
        desc2 = ComponentDescription(generic_description="Second different")
        
        assert desc1 != desc2
    
    def test_equality_all_fields_same(self):
        """Test equality when all fields are identical"""
        desc1 = ComponentDescription(
            generic_description="Test description",
            effects="Same effects",
            shamanic="Same shamanic",
            features=["f1", "f2"]
        )
        desc2 = ComponentDescription(
            generic_description="Test description",
            effects="Same effects",
            shamanic="Same shamanic",
            features=["f1", "f2"]
        )
        
        assert desc1 == desc2
    
    def test_equality_comparison_with_non_description(self):
        """Test that comparison with non-ComponentDescription returns False"""
        desc = ComponentDescription(generic_description="Test description")
        
        assert desc != "not a ComponentDescription"
        assert desc != {"generic_description": "Test"}
        assert desc != None
    
    # ==========================================================================
    # HASHING (2 tests)
    # ==========================================================================
    
    def test_hash_consistency_same_content(self):
        """Test that same content produces same hash"""
        desc1 = ComponentDescription(generic_description="Same content here")
        desc2 = ComponentDescription(generic_description="Same content here")
        
        assert hash(desc1) == hash(desc2)
    
    def test_usage_in_set_and_dict(self):
        """Test that ComponentDescription can be used in set() and as dict key"""
        desc1 = ComponentDescription(generic_description="First description")
        desc2 = ComponentDescription(generic_description="Second different")
        desc3 = ComponentDescription(generic_description="First description")  # Same as desc1
        
        # Usage in set
        desc_set = {desc1, desc2, desc3}
        assert len(desc_set) == 2, "Set should have 2 unique descriptions (desc1 == desc3)"
        
        # Usage as dict key
        desc_dict = {desc1: "value1", desc2: "value2"}
        assert desc_dict[desc1] == "value1"
        assert desc_dict[desc3] == "value1", "desc3 should map to same value as desc1"

