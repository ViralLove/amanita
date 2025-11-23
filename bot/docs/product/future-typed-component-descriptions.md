# Future Architecture: Typed Component Descriptions

**Version:** 1.0  
**Date:** 2025-01-XX  
**Status:** Future Planning  
**Method:** @analysis.mdc

---

## 📋 Executive Summary

This document outlines the architecture for implementing **typed component descriptions** where different component categories (mushrooms, plants, minerals, essential oils, vitamins, additives) can have specialized description schemas while maintaining a common base structure.

### Key Decisions

- ✅ **Category Storage:** Enum-based categories stored in IPFS metadata
- ✅ **Schema Architecture:** Base schema + category-specific extensions
- ✅ **Blockchain Integration:** Category → schema mapping in smart contract
- ✅ **Python Implementation:** Class inheritance pattern

### Motivation

The current `ComponentDescription` schema is optimized for mushrooms and plants:
- `generic_description`, `effects`, `shamanic`, `warnings`, `dosage_instructions`, `features`

However, future categories require different fields:
- **Minerals**: chemical composition, crystal structure, trace elements
- **Essential Oils**: extraction method, botanical source, aroma profile
- **Vitamins**: vitamin type, daily value, bioavailability
- **Additives**: purpose, concentration, safety profile

This architecture enables **type-safe, category-specific descriptions** while maintaining a unified interface.

---

## 🏗️ Architecture Overview

### 1. Component Categories

**Smart Contract Enum:**

```solidity
// contracts/OrganicComponentRegistryLogic.sol

enum ComponentCategory {
    MUSHROOM,        // 0 - Fungi (Amanita, Lions Mane, Cordyceps, etc.)
    PLANT,           // 1 - Plants (Blue Lotus, Passionflower, Nettle, etc.)
    MINERAL,         // 2 - Minerals and crystals
    ESSENTIAL_OIL,   // 3 - Essential oils and extracts
    VITAMIN,         // 4 - Vitamins and supplements
    ADDITIVE,        // 5 - Additives and compounds
    UNKNOWN          // 6 - Default/uncategorized
}
```

**Category Values in Metadata:**

```json
{
  "biounit_id": "amanita_muscaria",
  "category": "mushroom",  // Lowercase string matching enum
  "scientific_title": "Amanita muscaria"
}
```

**Valid Category Strings:**
- `"mushroom"`, `"plant"`, `"mineral"`, `"essential_oil"`, `"vitamin"`, `"additive"`

---

### 2. Description Schema Architecture

**Principle:** Base schema + category-specific extensions

#### 2.1 Base Schema (All Categories)

```json
{
  "schema_version": "1.0",
  "base": {
    "generic_description": "string (required)",
    "warnings": "string (optional)",
    "safety_profile": "string (optional)",
    "contraindications": "string (optional)"
  }
}
```

**Rationale:**
- All components need a generic description
- Safety information (warnings, contraindications) is universal
- Base fields ensure consistent UI display

#### 2.2 Category-Specific Extensions

**Mushroom Description:**
```json
{
  "schema_version": "1.0",
  "base": {
    "generic_description": "...",
    "warnings": "..."
  },
  "category_specific": {
    "mushroom": {
      "effects": "string (optional)",
      "shamanic": "string (optional)",
      "taxonomy": {
        "kingdom": "fungi",
        "phylum": "basidiomycota",
        "class": "agaricomycetes",
        "order": "agaricales",
        "family": "amanitaceae",
        "genus": "Amanita",
        "species": "muscaria"
      },
      "active_compounds": ["muscimol", "ibotenic_acid"],
      "traditional_use": "string (optional)"
    }
  }
}
```

**Plant Description:**
```json
{
  "schema_version": "1.0",
  "base": {
    "generic_description": "...",
    "warnings": "..."
  },
  "category_specific": {
    "plant": {
      "effects": "string (optional)",
      "botanical_family": "nymphaeaceae",
      "parts_used": ["flowers", "leaves", "rhizomes"],
      "active_compounds": ["nuciferine", "aporphine"],
      "traditional_use": "string (optional)",
      "cultivation": "string (optional)"
    }
  }
}
```

**Mineral Description:**
```json
{
  "schema_version": "1.0",
  "base": {
    "generic_description": "...",
    "warnings": "..."
  },
  "category_specific": {
    "mineral": {
      "chemical_formula": "MgSO₄",
      "crystal_system": "orthorhombic",
      "hardness": 2.5,
      "trace_elements": ["magnesium", "sulfur", "oxygen"],
      "bioavailability": "high",
      "absorption_factors": ["vitamin_d", "calcium"],
      "deficiency_symptoms": "string (optional)"
    }
  }
}
```

**Essential Oil Description:**
```json
{
  "schema_version": "1.0",
  "base": {
    "generic_description": "...",
    "warnings": "..."
  },
  "category_specific": {
    "essential_oil": {
      "extraction_method": "steam_distillation",
      "botanical_source": "lavandula angustifolia",
      "aroma_profile": "floral, herbaceous, sweet",
      "volatility": "top",
      "main_constituents": ["linalool", "linalyl_acetate"],
      "therapeutic_properties": ["calming", "antibacterial", "analgesic"],
      "blending_notes": "string (optional)"
    }
  }
}
```

**Vitamin Description:**
```json
{
  "schema_version": "1.0",
  "base": {
    "generic_description": "...",
    "warnings": "..."
  },
  "category_specific": {
    "vitamin": {
      "vitamin_type": "vitamin_d3",
      "daily_value_percentage": 100,
      "bioavailability": "high",
      "synergistic_compounds": ["vitamin_k2", "magnesium"],
      "deficiency_symptoms": "string (optional)",
      "optimal_timing": "with_fat_meal",
      "storage_requirements": "cool_dry_place"
    }
  }
}
```

**Additive Description:**
```json
{
  "schema_version": "1.0",
  "base": {
    "generic_description": "...",
    "warnings": "..."
  },
  "category_specific": {
    "additive": {
      "purpose": "bioavailability_enhancer",
      "concentration": "5mg",
      "safety_profile": "GRAS",
      "interactions": ["may_increase_absorption"],
      "effect_mechanism": "string (optional)",
      "recommended_ratio": "string (optional)"
    }
  }
}
```

---

### 3. Blockchain Integration

#### 3.1 Category → Schema Mapping

**Smart Contract:**

```solidity
// contracts/OrganicComponentRegistryLogic.sol

/// @notice Schema registry: category → schema_id
mapping(string => string) public categorySchemas;

/// @notice Set schema for a category
function setCategorySchema(string calldata category, string calldata schemaId) 
    external 
    onlyRole(ADMIN_ROLE) 
{
    require(bytes(category).length > 0, "Category cannot be empty");
    require(bytes(schemaId).length > 0, "Schema ID cannot be empty");
    categorySchemas[category] = schemaId;
    emit CategorySchemaSet(category, schemaId);
}

/// @notice Get schema ID for a category
function getCategorySchema(string calldata category) 
    external 
    view 
    returns (string memory) 
{
    return categorySchemas[category];
}
```

**Schema IDs:**
```
"mushroom" → "component.v1.mushroom"
"plant" → "component.v1.plant"
"mineral" → "component.v1.mineral"
"essential_oil" → "component.v1.essential_oil"
"vitamin" → "component.v1.vitamin"
"additive" → "component.v1.additive"
```

**Rationale:**
- Centralized schema registry ensures consistency
- Admin-controlled schema updates enable evolution
- Schema versioning (`v1`, `v2`, etc.) supports migration

#### 3.2 IPFS Storage

**Description JSON stored in IPFS via `complexFieldCIDs`:**
```
complexFieldCIDs["ComponentDescription.{language}"] → CID → IPFS JSON
```

**Note:** For per-component descriptions, we use simple fields:
```
simpleFieldCIDs["component.{biounit_id}.*.{language}"] → CID → IPFS JSON
```

The category-specific schema is determined by the component's `category` field in metadata, not by the CID key.

---

### 4. Python Implementation

#### 4.1 Base Class

**File:** `bot/model/component_description.py`

```python
from typing import Dict, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class BaseComponentDescription(ABC):
    """
    Base class for all component descriptions.
    
    Attributes:
        generic_description (str): General description (REQUIRED)
        warnings (Optional[str]): Safety warnings
        safety_profile (Optional[str]): Safety profile
        contraindications (Optional[str]): Contraindications
    """
    generic_description: str
    warnings: Optional[str] = None
    safety_profile: Optional[str] = None
    contraindications: Optional[str] = None
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseComponentDescription":
        """Create description from dictionary based on schema."""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert description to dictionary."""
        pass
    
    def get_category(self) -> str:
        """Return category identifier."""
        return self.__class__.__name__.replace("Description", "").lower()
```

#### 4.2 Category-Specific Classes

**File:** `bot/model/component_description.py`

```python
@dataclass
class MushroomDescription(BaseComponentDescription):
    """Description schema for mushroom components."""
    effects: Optional[str] = None
    shamanic: Optional[str] = None
    taxonomy: Optional[Dict[str, str]] = None
    active_compounds: Optional[List[str]] = None
    traditional_use: Optional[str] = None
    dosage_instructions: Optional[List[DosageInstruction]] = None
    features: Optional[List[str]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MushroomDescription":
        """Create MushroomDescription from dictionary."""
        base_data = data.get("base", {})
        mushroom_data = data.get("category_specific", {}).get("mushroom", {})
        
        return cls(
            generic_description=base_data["generic_description"],
            warnings=base_data.get("warnings"),
            safety_profile=base_data.get("safety_profile"),
            contraindications=base_data.get("contraindications"),
            effects=mushroom_data.get("effects"),
            shamanic=mushroom_data.get("shamanic"),
            taxonomy=mushroom_data.get("taxonomy"),
            active_compounds=mushroom_data.get("active_compounds"),
            traditional_use=mushroom_data.get("traditional_use"),
            dosage_instructions=mushroom_data.get("dosage_instructions"),
            features=mushroom_data.get("features")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with base + category_specific structure."""
        return {
            "schema_version": "1.0",
            "base": {
                "generic_description": self.generic_description,
                "warnings": self.warnings,
                "safety_profile": self.safety_profile,
                "contraindications": self.contraindications
            },
            "category_specific": {
                "mushroom": {
                    "effects": self.effects,
                    "shamanic": self.shamanic,
                    "taxonomy": self.taxonomy,
                    "active_compounds": self.active_compounds,
                    "traditional_use": self.traditional_use,
                    "dosage_instructions": [d.to_dict() for d in self.dosage_instructions] if self.dosage_instructions else None,
                    "features": self.features
                }
            }
        }

@dataclass
class PlantDescription(BaseComponentDescription):
    """Description schema for plant components."""
    effects: Optional[str] = None
    botanical_family: Optional[str] = None
    parts_used: Optional[List[str]] = None
    active_compounds: Optional[List[str]] = None
    traditional_use: Optional[str] = None
    cultivation: Optional[str] = None
    dosage_instructions: Optional[List[DosageInstruction]] = None
    features: Optional[List[str]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlantDescription":
        """Create PlantDescription from dictionary."""
        base_data = data.get("base", {})
        plant_data = data.get("category_specific", {}).get("plant", {})
        
        return cls(
            generic_description=base_data["generic_description"],
            warnings=base_data.get("warnings"),
            safety_profile=base_data.get("safety_profile"),
            contraindications=base_data.get("contraindications"),
            effects=plant_data.get("effects"),
            botanical_family=plant_data.get("botanical_family"),
            parts_used=plant_data.get("parts_used"),
            active_compounds=plant_data.get("active_compounds"),
            traditional_use=plant_data.get("traditional_use"),
            cultivation=plant_data.get("cultivation"),
            dosage_instructions=plant_data.get("dosage_instructions"),
            features=plant_data.get("features")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with base + category_specific structure."""
        return {
            "schema_version": "1.0",
            "base": {
                "generic_description": self.generic_description,
                "warnings": self.warnings,
                "safety_profile": self.safety_profile,
                "contraindications": self.contraindications
            },
            "category_specific": {
                "plant": {
                    "effects": self.effects,
                    "botanical_family": self.botanical_family,
                    "parts_used": self.parts_used,
                    "active_compounds": self.active_compounds,
                    "traditional_use": self.traditional_use,
                    "cultivation": self.cultivation,
                    "dosage_instructions": [d.to_dict() for d in self.dosage_instructions] if self.dosage_instructions else None,
                    "features": self.features
                }
            }
        }

@dataclass
class MineralDescription(BaseComponentDescription):
    """Description schema for mineral components."""
    chemical_formula: Optional[str] = None
    crystal_system: Optional[str] = None
    hardness: Optional[float] = None
    trace_elements: Optional[List[str]] = None
    bioavailability: Optional[str] = None
    absorption_factors: Optional[List[str]] = None
    deficiency_symptoms: Optional[str] = None
    
    # ... from_dict and to_dict methods similar to above
```

#### 4.3 Description Factory

**File:** `bot/model/component_description.py`

```python
from typing import Union, Type

ComponentDescription = Union[
    MushroomDescription,
    PlantDescription,
    MineralDescription,
    EssentialOilDescription,
    VitaminDescription,
    AdditiveDescription
]

class ComponentDescriptionFactory:
    """Factory for creating category-specific descriptions."""
    
    _category_map: Dict[str, Type[BaseComponentDescription]] = {
        "mushroom": MushroomDescription,
        "plant": PlantDescription,
        "mineral": MineralDescription,
        "essential_oil": EssentialOilDescription,
        "vitamin": VitaminDescription,
        "additive": AdditiveDescription
    }
    
    @classmethod
    def create(cls, category: str, data: Dict[str, Any]) -> BaseComponentDescription:
        """
        Create description instance based on category.
        
        Args:
            category: Component category ("mushroom", "plant", etc.)
            data: Description data dictionary
            
        Returns:
            BaseComponentDescription: Category-specific description instance
            
        Raises:
            ValueError: If category is unknown or data is invalid
        """
        description_class = cls._category_map.get(category.lower())
        if not description_class:
            raise ValueError(f"Unknown category: {category}")
        
        return description_class.from_dict(data)
    
    @classmethod
    def get_schema_id(cls, category: str) -> str:
        """Get schema ID for category."""
        return f"component.v1.{category.lower()}"
```

---

### 5. Service Layer Updates

#### 5.1 ComponentService Integration

**File:** `bot/services/product/component_service.py`

```python
async def get_component_description(
    self,
    component_id: str,
    language: str = "en"
) -> Optional[BaseComponentDescription]:
    """
    Get component description with category-specific schema.
    
    Args:
        component_id: Component biounit_id
        language: Language code
        
    Returns:
        BaseComponentDescription: Category-specific description or None
    """
    # 1. Get component metadata to determine category
    component = await self.get_component_full(component_id)
    if not component:
        return None
    
    category = component.category or "mushroom"  # Default for MVP
    
    # 2. Get description data via LocalizationService
    localization_service = get_localization_service(lang=language)
    fields_to_fetch = self._get_fields_for_category(category)
    
    description_data = {}
    for field in fields_to_fetch:
        key = f'component.{component_id}.{field}'
        value = localization_service.t(key, default='')
        if value and value != key:
            description_data[field] = value
    
    # 3. Create category-specific description
    try:
        description = ComponentDescriptionFactory.create(
            category=category,
            data=description_data
        )
        return description
    except ValueError as e:
        logger.error(f"Failed to create description for {component_id}: {e}")
        return None

def _get_fields_for_category(self, category: str) -> List[str]:
    """Get fields to fetch based on category."""
    base_fields = ['generic_description', 'warnings']
    
    category_fields = {
        "mushroom": ['effects', 'shamanic', 'taxonomy', 'active_compounds'],
        "plant": ['effects', 'botanical_family', 'parts_used', 'active_compounds'],
        "mineral": ['chemical_formula', 'crystal_system', 'hardness', 'trace_elements'],
        "essential_oil": ['extraction_method', 'botanical_source', 'aroma_profile'],
        "vitamin": ['vitamin_type', 'daily_value_percentage', 'bioavailability'],
        "additive": ['purpose', 'concentration', 'safety_profile']
    }
    
    return base_fields + category_fields.get(category.lower(), [])
```

---

### 6. Validation

#### 6.1 Schema Validation

**File:** `bot/validation/component_description_validator.py` (new)

```python
from jsonschema import validate, ValidationError

class ComponentDescriptionValidator:
    """Validator for category-specific description schemas."""
    
    SCHEMAS = {
        "mushroom": {
            "type": "object",
            "properties": {
                "schema_version": {"type": "string"},
                "base": {
                    "type": "object",
                    "required": ["generic_description"],
                    "properties": {
                        "generic_description": {"type": "string", "minLength": 10},
                        "warnings": {"type": "string"},
                        "safety_profile": {"type": "string"},
                        "contraindications": {"type": "string"}
                    }
                },
                "category_specific": {
                    "type": "object",
                    "properties": {
                        "mushroom": {
                            "type": "object",
                            "properties": {
                                "effects": {"type": "string"},
                                "shamanic": {"type": "string"},
                                "taxonomy": {"type": "object"},
                                "active_compounds": {"type": "array", "items": {"type": "string"}},
                                "traditional_use": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "required": ["schema_version", "base"]
        },
        # ... schemas for other categories
    }
    
    @classmethod
    def validate(cls, category: str, data: Dict[str, Any]) -> ValidationResult:
        """Validate description data against category schema."""
        schema = cls.SCHEMAS.get(category.lower())
        if not schema:
            return ValidationResult(
                valid=False,
                errors=[f"Unknown category: {category}"]
            )
        
        try:
            validate(instance=data, schema=schema)
            return ValidationResult(valid=True, errors=[])
        except ValidationError as e:
            return ValidationResult(valid=False, errors=[str(e)])
```

---

### 7. Migration Path

#### 7.1 Existing Components

**Strategy:** Backward compatibility not required (MVP launch)

**Migration steps:**
1. Add `category` field to all existing component metadata
2. Migrate existing `ComponentDescription` data to new schema format
3. Update all components to use category-specific classes

**Migration script:** `bot/scripts/migrate_to_typed_descriptions.py`

```python
async def migrate_component(component_id: str):
    """Migrate component to typed description schema."""
    # 1. Determine category from scientific_title or manual mapping
    component = await get_component(component_id)
    category = detect_category(component)
    
    # 2. Get existing description
    old_description = component.description
    
    # 3. Convert to new schema
    new_description_data = convert_to_new_schema(
        old_description,
        category
    )
    
    # 4. Update component metadata with category
    component.category = category
    
    # 5. Upload new description to IPFS
    # 6. Update blockchain CID mapping
```

---

### 8. Future Categories

#### 8.1 Natural Medicine Focus

All future categories must align with the mission: **providing safe, effective alternatives to big pharma** that prevent cyclical dependency on medications.

**Potential categories:**
- **Herbs** (extended from "plant"): Traditional herbal medicine
- **Probiotics**: Beneficial microorganisms
- **Enzymes**: Digestive and metabolic enzymes
- **Adaptogens**: Stress-response modifiers
- **Nootropics**: Cognitive enhancers (natural)
- **Phytonutrients**: Plant-derived nutrients

**Requirements:**
- Must have scientific backing
- Must emphasize safety and prevention
- Must avoid dependency cycles
- Must promote holistic health

---

## 🚀 Implementation Plan

### Phase 1: Foundation (Current MVP)
- ✅ Add `category` field to metadata (see JIRA task)
- ✅ Document architecture
- ✅ Prepare schema definitions

### Phase 2: Schema Implementation
- Implement base + category-specific schema structure
- Create category-specific Python classes
- Add validation logic

### Phase 3: Service Integration
- Update `ComponentService` to use factory pattern
- Integrate category detection
- Update localization service to handle category fields

### Phase 4: Blockchain Integration
- Add category → schema mapping to contract
- Update contract functions
- Deploy schema registry

### Phase 5: Migration
- Migrate existing components to typed descriptions
- Update all component metadata
- Validate all descriptions

---

## 📊 Benefits

1. **Type Safety:** Category-specific fields prevent errors
2. **Scalability:** Easy to add new categories with their own schemas
3. **Flexibility:** Base schema ensures common fields across all categories
4. **Validation:** Schema validation catches errors early
5. **UI Integration:** Category-specific UI can display relevant fields
6. **Future-Proof:** Architecture supports expansion to new natural medicine categories

---

## 🔗 Related Documents

- `bot/docs/jira/add-component-category-field.md` - JIRA task for category field
- `bot/docs/product/product-structure.md` - Product structure documentation
- `bot/docs/analysis/temp-complex-fields-current-implementation-analysis.md` - Current implementation analysis

---

**Status:** ✅ Architecture Designed  
**Next Steps:** Implement category field (see JIRA task)  
**Target Implementation:** Post-MVP launch

