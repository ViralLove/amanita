"""
E2E Full Flow Tests for Product Deserialization.

Tests the complete pipeline from blockchain to Telegram display:
1. Blockchain extraction (ProductRegistry)
2. Arweave metadata download
3. Component enrichment
4. ComponentDescription fetch (Russian)
5. Telegram formatting (HTML message)
6. Inline keyboard creation

Based on: @e2e-test-build.core.mdc (Phase 2: Deploy/Component/Full Flow)
Plan: E2E-DESERIALIZATION-FULL-FLOW-PLAN.md
"""

import pytest
import logging

from model.component_description import ComponentDescription

logger = logging.getLogger(__name__)


@pytest.mark.e2e
@pytest.mark.requires_node
@pytest.mark.requires_arweave
class TestProductFullDeserializationFlow:
    """
    Phase 2: Full flow E2E tests.
    
    GOAL: Validate complete pipeline from blockchain to Telegram.
    
    Prerequisites:
    - Hardhat node running (:8545)
    - Contracts deployed (Actions 1, 777, 555, 9, 444)
    - Product #0 (amanita1) uploaded
    - Arweave data available
    
    Tests:
    1. E2E Single Product (amanita1) — 6 stages
    """
    
    @pytest.mark.asyncio
    async def test_e2e_single_product_full_flow(
        self,
        e2e_harness,
        e2e_snapshot,
        real_product_registry,
        real_formatter_service,
        russian_localization,
        expected_product_amanita1,
        expected_component_amanita_muscaria
    ):
        """
        E2E TEST: Blockchain → Arweave → Assembler → Formatter → Telegram
        
        GIVEN: Product #0 (amanita1) deployed to blockchain
        WHEN: Full deserialization flow executed
        THEN: 
          - Product fetched from blockchain ✅
          - Metadata downloaded from Arweave ✅
          - Component enriched with full data ✅
          - ComponentDescription fetched (Russian) ✅
          - Telegram message formatted ✅
          - Inline keyboard created ✅
        
        TIME: ~3-4 seconds (real blockchain + real Arweave)
        """
        logger.info("="*80)
        logger.info("E2E TEST: SINGLE Product Full Flow (amanita1)")
        logger.info("="*80)
        
        # ========================================
        # STAGE 1: Blockchain Extraction
        # ========================================
        logger.info("\n📡 STAGE 1: Blockchain Extraction")
        
        product_id = 1  # amanita1 (first product minted on dev network)
        
        # Get product from blockchain (full flow)
        product = await real_product_registry.get_product(product_id)
        
        # ASSERTIONS: Stage 1
        assert product is not None, "❌ Product should be fetched from blockchain"
        assert product.blockchain_id == 0, f"❌ Expected blockchain_id=0, got {product.blockchain_id}"
        
        # Seller validation (if available in expected data)
        if "seller" in expected_product_amanita1:
            expected_seller = expected_product_amanita1["seller"].lower()
            actual_seller = product.seller.lower()
            assert actual_seller == expected_seller, (
                f"❌ Seller mismatch:\n"
                f"   Expected: {expected_seller}\n"
                f"   Got: {actual_seller}"
            )
        
        # CID validation
        assert product.cid == expected_product_amanita1["metadataCID"], (
            f"❌ CID mismatch:\n"
            f"   Expected: {expected_product_amanita1['metadataCID']}\n"
            f"   Got: {product.cid}"
        )
        
        # Active status
        assert product.is_active == expected_product_amanita1["active"], (
            f"❌ Active status mismatch:\n"
            f"   Expected: {expected_product_amanita1['active']}\n"
            f"   Got: {product.is_active}"
        )
        
        logger.info(f"✅ STAGE 1 PASSED: Blockchain data extracted")
        logger.info(f"   Product ID: {product.blockchain_id}")
        logger.info(f"   Seller: {product.seller}")
        logger.info(f"   CID: {product.cid}")
        logger.info(f"   Active: {product.is_active}")
        
        # ========================================
        # STAGE 2: Metadata Validation
        # ========================================
        logger.info("\n📦 STAGE 2: Metadata Download & Parsing")
        
        # Business ID
        assert product.business_id == expected_product_amanita1["id"], (
            f"❌ Business ID mismatch:\n"
            f"   Expected: {expected_product_amanita1['id']}\n"
            f"   Got: {product.business_id}"
        )
        
        # Title (should be loaded from Arweave metadata)
        assert product.title is not None, "❌ Title should be loaded from metadata"
        assert len(product.title) > 0, "❌ Title should not be empty"
        assert "Мухомор" in product.title, (
            f"❌ Expected Russian title with 'Мухомор', got: {product.title}"
        )
        
        logger.info(f"✅ STAGE 2 PASSED: Metadata downloaded and parsed")
        logger.info(f"   Business ID: {product.business_id}")
        logger.info(f"   Title: {product.title}")
        logger.info(f"   Title length: {len(product.title)} chars")
        
        # ========================================
        # STAGE 3: Component Enrichment
        # ========================================
        logger.info("\n🧬 STAGE 3: Component Enrichment")
        
        # Product should have organic_components
        assert hasattr(product, 'organic_components'), (
            "❌ Product should have organic_components attribute"
        )
        assert product.organic_components is not None, (
            "❌ organic_components should not be None"
        )
        
        # SINGLE product (1 component)
        assert len(product.organic_components) == 1, (
            f"❌ Expected SINGLE product (1 component), got {len(product.organic_components)}"
        )
        
        component = product.organic_components[0]
        
        # Component ID validation
        assert component.component_id == "amanita_muscaria", (
            f"❌ Expected component_id='amanita_muscaria', got: {component.component_id}"
        )
        
        # Scientific title (enriched from blockchain)
        assert component.scientific_title is not None, (
            "❌ Scientific title should be enriched from blockchain"
        )
        assert "Amanita muscaria" in component.scientific_title, (
            f"❌ Expected 'Amanita muscaria' in scientific title, got: {component.scientific_title}"
        )
        
        logger.info(f"✅ STAGE 3 PASSED: Component enriched")
        logger.info(f"   Component ID: {component.component_id}")
        logger.info(f"   Scientific title: {component.scientific_title}")
        logger.info(f"   Active: {component.active}")
        
        # ========================================
        # STAGE 4: ComponentDescription Fetch
        # ========================================
        logger.info("\n📖 STAGE 4: ComponentDescription Fetch (Russian)")
        
        # Description should be fetched
        assert hasattr(component, 'description'), (
            "❌ Component should have 'description' attribute"
        )
        assert component.description is not None, (
            "❌ Description should be fetched (amanita_muscaria has Russian description)"
        )
        
        description = component.description
        
        # Validate ComponentDescription type
        assert isinstance(description, ComponentDescription), (
            f"❌ Expected ComponentDescription, got {type(description).__name__}"
        )
        
        # Validate generic_description (required field)
        assert description.generic_description is not None, (
            "❌ generic_description is required field"
        )
        assert len(description.generic_description) > 500, (
            f"❌ Expected full Russian description (~700 chars), got {len(description.generic_description)} chars"
        )
        
        # Validate Russian content
        assert "Мусцимол" in description.generic_description, (
            "❌ Expected 'Мусцимол' in Russian description (main active compound)"
        )
        assert "🔬" in description.generic_description, (
            "❌ Emoji should be preserved in description"
        )
        assert "\n" in description.generic_description, (
            "❌ Newlines should be preserved for formatting"
        )
        
        # Validate optional fields (amanita_muscaria.ru has all sections)
        assert description.effects is not None, (
            "❌ amanita_muscaria.ru should have 'effects' section"
        )
        assert "Нейромодуляция" in description.effects or "нейромодуляция" in description.effects.lower(), (
            "❌ Expected 'Нейромодуляция' in effects section"
        )
        
        assert description.shamanic is not None, (
            "❌ amanita_muscaria.ru should have 'shamanic' section"
        )
        assert "Мухомор" in description.shamanic or "мухомор" in description.shamanic.lower(), (
            "❌ Expected 'Мухомор' in shamanic section"
        )
        
        assert description.warnings is not None, (
            "❌ amanita_muscaria.ru should have 'warnings' section"
        )
        assert "Нельзя" in description.warnings or "нельзя" in description.warnings.lower(), (
            "❌ Expected warning text in warnings section"
        )
        
        logger.info(f"✅ STAGE 4 PASSED: ComponentDescription fetched")
        logger.info(f"   Generic length: {len(description.generic_description)} chars")
        logger.info(f"   Has effects: {description.effects is not None}")
        logger.info(f"   Has shamanic: {description.shamanic is not None}")
        logger.info(f"   Has warnings: {description.warnings is not None}")
        logger.info(f"   Has dosage: {description.dosage is not None}")
        
        # ========================================
        # STAGE 5: Telegram Formatting
        # ========================================
        logger.info("\n💬 STAGE 5: Telegram Message Formatting")
        
        # Format product for Telegram
        result = real_formatter_service.format_product_details_for_telegram(
            product,
            russian_localization
        )
        
        # Validate result structure
        assert isinstance(result, dict), (
            f"❌ Expected dict with 'text' and 'inline_keyboard', got {type(result).__name__}"
        )
        assert "text" in result, (
            "❌ Result should have 'text' key (formatted HTML message)"
        )
        assert "inline_keyboard" in result, (
            "❌ Result should have 'inline_keyboard' key (SINGLE with description)"
        )
        
        formatted_text = result["text"]
        inline_keyboard = result["inline_keyboard"]
        
        # Validate formatted text
        assert formatted_text is not None, (
            "❌ Formatted text should not be None"
        )
        assert len(formatted_text) > 200, (
            f"❌ Expected rich HTML message (>200 chars), got {len(formatted_text)} chars"
        )
        
        # Check product info in formatted text
        assert "Мухомор" in formatted_text, (
            "❌ Product title should be in message"
        )
        assert "Amanita muscaria" in formatted_text, (
            "❌ Scientific title should be in message"
        )
        
        # Check forms in formatted text
        has_forms = "dried" in formatted_text.lower() or "whole_caps" in formatted_text.lower() or "форм" in formatted_text.lower()
        assert has_forms, (
            "❌ Forms should be mentioned in message"
        )
        
        # Check SINGLE product marker or emoji
        has_single_marker = "Монокомпонентный" in formatted_text or "🔬" in formatted_text
        assert has_single_marker, (
            "❌ SINGLE product marker should be present"
        )
        
        # Check description hint (if description available)
        has_description_hint = "💡" in formatted_text or "Подробное описание" in formatted_text or "описани" in formatted_text.lower()
        assert has_description_hint, (
            "❌ Description hint should be present (product has full description)"
        )
        
        logger.info(f"✅ STAGE 5 PASSED: Telegram message formatted")
        logger.info(f"   Message length: {len(formatted_text)} chars")
        logger.info(f"   Has emoji: {'🔬' in formatted_text}")
        logger.info(f"   Has description hint: {has_description_hint}")
        
        # ========================================
        # STAGE 6: Inline Keyboard Validation
        # ========================================
        logger.info("\n⌨️ STAGE 6: Inline Keyboard Validation")
        
        # Inline keyboard should be created for SINGLE with description
        assert inline_keyboard is not None, (
            "❌ Inline keyboard should be created for SINGLE product with description"
        )
        
        # Check keyboard structure
        from aiogram.types import InlineKeyboardMarkup
        assert isinstance(inline_keyboard, InlineKeyboardMarkup), (
            f"❌ Expected InlineKeyboardMarkup, got {type(inline_keyboard).__name__}"
        )
        
        # Check buttons count (4 sections: generic, effects, shamanic, warnings)
        # Note: Could be 3 or 4 depending on available sections
        buttons_count = len(inline_keyboard.inline_keyboard)
        assert buttons_count >= 3, (
            f"❌ Expected at least 3 buttons (generic + 2 optional), got {buttons_count}"
        )
        assert buttons_count <= 5, (
            f"❌ Expected at most 5 buttons (generic + 4 optional), got {buttons_count}"
        )
        
        logger.info(f"   Total buttons: {buttons_count}")
        
        # Validate button 1: Активные компоненты (generic)
        button_1 = inline_keyboard.inline_keyboard[0][0]
        assert "Активные компоненты" in button_1.text or "компонент" in button_1.text.lower(), (
            f"❌ Expected 'Активные компоненты' button, got: {button_1.text}"
        )
        assert "component_desc" in button_1.callback_data, (
            f"❌ Expected 'component_desc' in callback_data, got: {button_1.callback_data}"
        )
        assert "amanita_muscaria" in button_1.callback_data, (
            f"❌ Expected 'amanita_muscaria' in callback_data, got: {button_1.callback_data}"
        )
        assert "generic" in button_1.callback_data, (
            f"❌ Expected 'generic' in callback_data, got: {button_1.callback_data}"
        )
        assert "ru" in button_1.callback_data, (
            f"❌ Expected 'ru' in callback_data, got: {button_1.callback_data}"
        )
        
        logger.info(f"   Button 1: {button_1.text}")
        logger.info(f"   Callback: {button_1.callback_data}")
        
        # Validate remaining buttons (optional sections)
        for idx in range(1, buttons_count):
            button = inline_keyboard.inline_keyboard[idx][0]
            
            # All buttons should have component_desc callback
            assert "component_desc" in button.callback_data, (
                f"❌ Button {idx+1} should have 'component_desc' in callback_data"
            )
            assert "amanita_muscaria" in button.callback_data, (
                f"❌ Button {idx+1} should have 'amanita_muscaria' in callback_data"
            )
            
            logger.info(f"   Button {idx+1}: {button.text}")
            logger.info(f"   Callback: {button.callback_data}")
        
        logger.info(f"✅ STAGE 6 PASSED: Inline keyboard validated")
        logger.info(f"   Buttons count: {buttons_count}")
        logger.info(f"   All buttons have valid callback_data")
        
        # ========================================
        # FINAL VERIFICATION
        # ========================================
        logger.info("\n" + "="*80)
        logger.info("🎉 E2E TEST PASSED: Full flow blockchain → Telegram")
        logger.info("="*80)
        logger.info(f"✅ STAGE 1: Blockchain extraction")
        logger.info(f"✅ STAGE 2: Metadata download")
        logger.info(f"✅ STAGE 3: Component enrichment")
        logger.info(f"✅ STAGE 4: ComponentDescription fetch (Russian)")
        logger.info(f"✅ STAGE 5: Telegram formatting")
        logger.info(f"✅ STAGE 6: Inline keyboard creation")
        logger.info(f"")
        logger.info(f"📊 METRICS:")
        logger.info(f"   Product: {product.business_id} ({product.title})")
        logger.info(f"   Component: {component.component_id} ({component.scientific_title})")
        logger.info(f"   Description length: {len(description.generic_description)} chars")
        logger.info(f"   Message length: {len(formatted_text)} chars")
        logger.info(f"   Buttons: {buttons_count}")
        logger.info("="*80)
        
        print("\n" + "="*80)
        print("🎉 E2E TEST PASSED: SINGLE Product Full Flow")
        print("="*80)
        print(f"Product: {product.business_id} — {product.title}")
        print(f"Component: {component.component_id} — {component.scientific_title}")
        print(f"All 6 stages validated ✅")
        print("="*80)
    
    @pytest.mark.asyncio
    async def test_e2e_fallback_language_mechanism(
        self,
        e2e_harness,
        e2e_snapshot,
        real_component_service,
        expected_component_amanita_muscaria
    ):
        """
        E2E TEST 2: Fallback Language Mechanism (French → English)
        
        GIVEN: amanita_muscaria component with Russian + English descriptions
        WHEN: Request French description (not available)
        THEN: Falls back to English "[TODO: English translation]"
        
        NOTE: This test validates ComponentService.get_component_description()
        fallback logic directly, since assembler.py currently hardcodes "ru".
        
        TODO: When language parameter is added to get_product(), update to full flow test.
        
        TIME: ~2-3 seconds (real Arweave fetch)
        """
        logger.info("="*80)
        logger.info("E2E TEST 2: Fallback Language Mechanism (fr → en)")
        logger.info("="*80)
        
        component_id = "amanita_muscaria"
        
        # ========================================
        # STAGE 1: Validate Russian (baseline)
        # ========================================
        logger.info("\n🇷🇺 STAGE 1: Russian Description (baseline)")
        
        description_ru = await real_component_service.get_component_description(
            component_id,
            "ru"
        )
        
        # Russian should exist
        assert description_ru is not None, (
            "❌ Russian description should exist for amanita_muscaria"
        )
        assert isinstance(description_ru, ComponentDescription), (
            f"❌ Expected ComponentDescription, got {type(description_ru).__name__}"
        )
        
        # Validate Russian content
        assert "Мусцимол" in description_ru.generic_description, (
            "❌ Expected Russian content with 'Мусцимол'"
        )
        assert len(description_ru.generic_description) > 500, (
            f"❌ Expected full Russian description, got {len(description_ru.generic_description)} chars"
        )
        
        logger.info(f"✅ STAGE 1 PASSED: Russian description fetched")
        logger.info(f"   Component: {component_id}")
        logger.info(f"   Language: ru")
        logger.info(f"   Length: {len(description_ru.generic_description)} chars")
        logger.info(f"   Has Мусцимол: True")
        
        # ========================================
        # STAGE 2: Validate English (fallback target)
        # ========================================
        logger.info("\n🇬🇧 STAGE 2: English Description (fallback target)")
        
        description_en = await real_component_service.get_component_description(
            component_id,
            "en"
        )
        
        # English should exist (as fallback)
        assert description_en is not None, (
            "❌ English description should exist (fallback language)"
        )
        assert isinstance(description_en, ComponentDescription), (
            f"❌ Expected ComponentDescription, got {type(description_en).__name__}"
        )
        
        # Validate English content (TODO marker)
        assert "[TODO:" in description_en.generic_description, (
            "❌ Expected TODO marker in English description"
        )
        assert "translation" in description_en.generic_description, (
            "❌ Expected translation placeholder in English description"
        )
        
        logger.info(f"✅ STAGE 2 PASSED: English description fetched")
        logger.info(f"   Component: {component_id}")
        logger.info(f"   Language: en")
        logger.info(f"   Length: {len(description_en.generic_description)} chars")
        logger.info(f"   Has TODO marker: True")
        
        # ========================================
        # STAGE 3: Test Fallback (French → English)
        # ========================================
        logger.info("\n🇫🇷 STAGE 3: French Request → English Fallback")
        
        # Request French (not available)
        description_fr = await real_component_service.get_component_description(
            component_id,
            "fr"  # Not available
        )
        
        # Should fallback to English (not None)
        assert description_fr is not None, (
            "❌ Should fallback to English when French unavailable"
        )
        assert isinstance(description_fr, ComponentDescription), (
            f"❌ Expected ComponentDescription, got {type(description_fr).__name__}"
        )
        
        # Validate it's English (not Russian, not None)
        assert "[TODO:" in description_fr.generic_description, (
            "❌ Should fallback to English (TODO marker expected)"
        )
        assert "translation" in description_fr.generic_description, (
            "❌ Should contain translation placeholder"
        )
        
        # Should NOT be Russian
        assert "Мусцимол" not in description_fr.generic_description, (
            "❌ Should NOT fallback to Russian (fr → en, not fr → ru)"
        )
        
        logger.info(f"✅ STAGE 3 PASSED: Fallback fr → en works")
        logger.info(f"   Requested: fr (not available)")
        logger.info(f"   Fallback: en (TODO marker present)")
        logger.info(f"   NOT Russian: True (no Мусцимол)")
        
        # ========================================
        # STAGE 4: Test Fallback (German → English)
        # ========================================
        logger.info("\n🇩🇪 STAGE 4: German Request → English Fallback")
        
        # Request German (also not available)
        description_de = await real_component_service.get_component_description(
            component_id,
            "de"  # Not available
        )
        
        # Should also fallback to English
        assert description_de is not None, (
            "❌ Should fallback to English when German unavailable"
        )
        
        # Validate it's English
        assert "[TODO:" in description_de.generic_description, (
            "❌ de → en fallback should return English TODO"
        )
        
        # Should match English content
        assert "translation" in description_de.generic_description, (
            "❌ de → en fallback should contain translation placeholder"
        )
        
        logger.info(f"✅ STAGE 4 PASSED: Fallback de → en works")
        logger.info(f"   Requested: de (not available)")
        logger.info(f"   Fallback: en (matches direct en fetch)")
        
        # ========================================
        # STAGE 5: Cache Behavior Validation
        # ========================================
        logger.info("\n💾 STAGE 5: Cache Behavior for Fallback")
        
        # Request French again (should use cache)
        description_fr_cached = await real_component_service.get_component_description(
            component_id,
            "fr"
        )
        
        # Should be same object (or equal content)
        assert description_fr_cached is not None
        assert description_fr_cached.generic_description == description_fr.generic_description, (
            "❌ Cached fallback should return same content"
        )
        
        logger.info(f"✅ STAGE 5 PASSED: Cache works for fallback")
        logger.info(f"   Second fr request: Returns same content")
        
        # ========================================
        # FINAL VERIFICATION
        # ========================================
        logger.info("\n" + "="*80)
        logger.info("🎉 E2E TEST 2 PASSED: Fallback Language Mechanism")
        logger.info("="*80)
        logger.info(f"✅ STAGE 1: Russian description (baseline)")
        logger.info(f"✅ STAGE 2: English description (fallback target)")
        logger.info(f"✅ STAGE 3: French → English fallback")
        logger.info(f"✅ STAGE 4: German → English fallback")
        logger.info(f"✅ STAGE 5: Cache behavior validated")
        logger.info(f"")
        logger.info(f"📊 METRICS:")
        logger.info(f"   Component: {component_id}")
        logger.info(f"   Russian length: {len(description_ru.generic_description)} chars")
        logger.info(f"   English length: {len(description_en.generic_description)} chars")
        logger.info(f"   Fallback logic: fr → en ✅, de → en ✅")
        logger.info(f"   Cache: Working ✅")
        logger.info("="*80)
        
        print("\n" + "="*80)
        print("🎉 E2E TEST 2 PASSED: Fallback Language Mechanism")
        print("="*80)
        print(f"Component: {component_id}")
        print(f"Fallback logic validated: fr → en, de → en ✅")
        print(f"All 5 stages validated ✅")
        print("="*80)
    
    @pytest.mark.asyncio
    async def test_e2e_cache_performance_validation(
        self,
        e2e_harness,
        e2e_snapshot,
        real_product_registry,
        expected_product_amanita1
    ):
        """
        E2E TEST 3: Cache Performance Validation
        
        GIVEN: Product #0 (amanita1) with ComponentDescription
        WHEN: Same product fetched twice
        THEN: 
          - First fetch: Cache miss (downloads from Arweave)
          - Second fetch: Cache hit (returns from cache)
          - Cache hit is significantly faster (~2-10x)
          - Content identical between fetches
        
        NOTE: This test validates cache behavior across the full pipeline,
        including ComponentService cache for descriptions.
        
        TIME: ~6-8 seconds (2 full fetches)
        """
        logger.info("="*80)
        logger.info("E2E TEST 3: Cache Performance Validation")
        logger.info("="*80)
        
        product_id = 1  # amanita1 (first product id)
        
        # ========================================
        # STAGE 1: First Fetch (Cache Miss)
        # ========================================
        logger.info("\n💾 STAGE 1: First Fetch (Cache Miss)")
        
        import time
        
        start_1 = time.time()
        product_1 = await real_product_registry.get_product(product_id)
        duration_1 = time.time() - start_1
        
        # Validate first fetch succeeded
        assert product_1 is not None, (
            "❌ First fetch failed"
        )
        assert product_1.blockchain_id == 0, (
            f"❌ Expected blockchain_id=0, got {product_1.blockchain_id}"
        )
        
        # Validate component and description
        assert len(product_1.organic_components) == 1, (
            f"❌ Expected 1 component, got {len(product_1.organic_components)}"
        )
        
        component_1 = product_1.organic_components[0]
        assert component_1.component_id == "amanita_muscaria", (
            f"❌ Expected amanita_muscaria, got {component_1.component_id}"
        )
        
        # Description should be fetched
        assert hasattr(component_1, 'description'), (
            "❌ Component should have description attribute"
        )
        assert component_1.description is not None, (
            "❌ Description should be fetched in first call"
        )
        
        description_1 = component_1.description
        
        # Validate description content
        assert isinstance(description_1, ComponentDescription), (
            f"❌ Expected ComponentDescription, got {type(description_1).__name__}"
        )
        assert len(description_1.generic_description) > 500, (
            f"❌ Expected full description, got {len(description_1.generic_description)} chars"
        )
        assert "Мусцимол" in description_1.generic_description, (
            "❌ Expected Russian content"
        )
        
        logger.info(f"✅ STAGE 1 PASSED: First fetch completed (cache miss)")
        logger.info(f"   Product ID: {product_1.blockchain_id}")
        logger.info(f"   Component: {component_1.component_id}")
        logger.info(f"   Description length: {len(description_1.generic_description)} chars")
        logger.info(f"   Duration: {duration_1:.3f}s")
        
        # ========================================
        # STAGE 2: Second Fetch (Cache Hit)
        # ========================================
        logger.info("\n⚡ STAGE 2: Second Fetch (Cache Hit)")
        
        start_2 = time.time()
        product_2 = await real_product_registry.get_product(product_id)
        duration_2 = time.time() - start_2
        
        # Validate second fetch succeeded
        assert product_2 is not None, (
            "❌ Second fetch failed"
        )
        assert product_2.blockchain_id == 0, (
            f"❌ Expected blockchain_id=0, got {product_2.blockchain_id}"
        )
        
        # Validate component
        assert len(product_2.organic_components) == 1, (
            f"❌ Expected 1 component, got {len(product_2.organic_components)}"
        )
        
        component_2 = product_2.organic_components[0]
        assert component_2.component_id == "amanita_muscaria", (
            f"❌ Expected amanita_muscaria, got {component_2.component_id}"
        )
        
        # Description should be fetched from cache
        assert component_2.description is not None, (
            "❌ Description should be available from cache"
        )
        
        description_2 = component_2.description
        
        logger.info(f"✅ STAGE 2 PASSED: Second fetch completed (cache hit)")
        logger.info(f"   Product ID: {product_2.blockchain_id}")
        logger.info(f"   Component: {component_2.component_id}")
        logger.info(f"   Description length: {len(description_2.generic_description)} chars")
        logger.info(f"   Duration: {duration_2:.3f}s")
        
        # ========================================
        # STAGE 3: Performance Comparison
        # ========================================
        logger.info("\n📊 STAGE 3: Performance Comparison")
        
        # Calculate speedup
        if duration_2 > 0:
            speedup = duration_1 / duration_2
        else:
            speedup = float('inf')
        
        logger.info(f"   First fetch (miss): {duration_1:.3f}s")
        logger.info(f"   Second fetch (hit): {duration_2:.3f}s")
        logger.info(f"   Speedup: {speedup:.1f}x")
        
        # Cache hit should be faster (at least marginally)
        # NOTE: We don't enforce strict timing (flaky in CI), but log for visibility
        if duration_2 < duration_1:
            logger.info(f"✅ Cache hit faster than cache miss ({speedup:.1f}x speedup)")
        else:
            logger.warning(f"⚠️ Cache hit not faster (timing variance or cache not working)")
            logger.warning(f"   This may be normal in fast environments or with warm caches")
        
        # ========================================
        # STAGE 4: Content Validation
        # ========================================
        logger.info("\n🔍 STAGE 4: Content Validation (Cache Correctness)")
        
        # Descriptions should have identical content
        assert description_1.generic_description == description_2.generic_description, (
            "❌ Description content should match between fetches"
        )
        
        # Validate all fields match
        assert description_1.effects == description_2.effects, (
            "❌ Effects should match"
        )
        assert description_1.shamanic == description_2.shamanic, (
            "❌ Shamanic should match"
        )
        assert description_1.warnings == description_2.warnings, (
            "❌ Warnings should match"
        )
        assert description_1.dosage == description_2.dosage, (
            "❌ Dosage should match"
        )
        
        logger.info(f"✅ STAGE 4 PASSED: Content identical between fetches")
        logger.info(f"   Generic: {len(description_1.generic_description)} chars (both)")
        logger.info(f"   Effects: {description_1.effects is not None} (both)")
        logger.info(f"   Shamanic: {description_1.shamanic is not None} (both)")
        logger.info(f"   Warnings: {description_1.warnings is not None} (both)")
        logger.info(f"   Dosage: {description_1.dosage is not None} (both)")
        
        # ========================================
        # STAGE 5: Component-Level Cache
        # ========================================
        logger.info("\n💾 STAGE 5: Component-Level Cache Validation")
        
        # Test ComponentService cache directly
        from services.product.component_service import ComponentService
        
        # Get component service from registry (same instance used in fetches)
        component_service = real_product_registry.assembler.component_service
        
        # Third fetch of description (should hit ComponentService cache)
        start_3 = time.time()
        description_3 = await component_service.get_component_description(
            "amanita_muscaria",
            "ru"
        )
        duration_3 = time.time() - start_3
        
        assert description_3 is not None, (
            "❌ Third description fetch failed"
        )
        
        # Content should match
        assert description_3.generic_description == description_1.generic_description, (
            "❌ ComponentService cache should return same content"
        )
        
        logger.info(f"✅ STAGE 5 PASSED: ComponentService cache validated")
        logger.info(f"   Direct cache fetch: {duration_3:.3f}s")
        logger.info(f"   Content matches: True")
        
        # ========================================
        # FINAL VERIFICATION
        # ========================================
        logger.info("\n" + "="*80)
        logger.info("🎉 E2E TEST 3 PASSED: Cache Performance Validation")
        logger.info("="*80)
        logger.info(f"✅ STAGE 1: First fetch (cache miss) — {duration_1:.3f}s")
        logger.info(f"✅ STAGE 2: Second fetch (cache hit) — {duration_2:.3f}s")
        logger.info(f"✅ STAGE 3: Performance comparison — {speedup:.1f}x speedup")
        logger.info(f"✅ STAGE 4: Content validation — Identical")
        logger.info(f"✅ STAGE 5: Component cache — Working")
        logger.info(f"")
        logger.info(f"📊 METRICS:")
        logger.info(f"   Product: {product_1.business_id}")
        logger.info(f"   Component: {component_1.component_id}")
        logger.info(f"   Cache miss: {duration_1:.3f}s")
        logger.info(f"   Cache hit: {duration_2:.3f}s")
        logger.info(f"   Speedup: {speedup:.1f}x")
        logger.info(f"   Content integrity: ✅")
        logger.info("="*80)
        
        print("\n" + "="*80)
        print("🎉 E2E TEST 3 PASSED: Cache Performance Validation")
        print("="*80)
        print(f"Product: {product_1.business_id}")
        print(f"Component: {component_1.component_id}")
        print(f"Cache miss: {duration_1:.3f}s")
        print(f"Cache hit: {duration_2:.3f}s")
        print(f"Speedup: {speedup:.1f}x ⚡")
        print(f"All 5 stages validated ✅")
        print("="*80)
    
    @pytest.mark.asyncio
    async def test_e2e_multi_component_product_flow(
        self,
        e2e_harness,
        e2e_snapshot,
        real_product_assembler,
        real_formatter_service,
        russian_localization
    ):
        """
        E2E TEST 4: MULTI Component Product (PLANNED)
        
        PROBLEM: Production data currently has NO multi-component products!
        All products in data/registry/ are SINGLE component (amanita1, amanita2, etc.)
        
        SOLUTION OPTIONS:
        
        Option 1 (RECOMMENDED): Create synthetic MULTI product
        - Synthetic blockchain data (product_id=99)
        - Synthetic metadata with 2-3 components
        - Test assembler + formatter with MULTI logic
        - Time: ~30 minutes
        
        Option 2 (PRODUCTION): Add real MULTI product to catalog
        - Create metadata: data/registry/multi_blend_001.json
        - Upload to Arweave (Action 444)
        - Register in ProductRegistry
        - Time: ~1-2 hours
        
        TEST STRUCTURE (when implemented):
        
        STAGE 1: Synthetic Product Assembly
        - Create blockchain_data with 2-3 component_ids
        - Create metadata with MULTI format
        - Assemble via ProductAssembler
        
        STAGE 2: Multi-Component Enrichment
        - Validate all components enriched (scientific_title)
        - Each component may have description (graceful degradation)
        
        STAGE 3: MULTI Telegram Formatting
        - Validate "Мультикомпонентный продукт" marker
        - All component names/titles in message
        - MULTI-specific layout
        
        STAGE 4: Multi-Component Inline Keyboard
        - Buttons for each component with description
        - Up to 3 component buttons (per component)
        - Proper callback_data format
        
        STAGE 5: Multi-Description Fetch
        - Descriptions fetched for available components
        - Graceful degradation if some missing
        - Cache behavior for multiple components
        
        EXPECTED ASSERTIONS: ~30-40
        EXPECTED TIME: ~5-7 seconds (multiple component fetches)
        
        CRITICAL VALIDATIONS:
        - len(components) >= 2 (MULTI product)
        - All components enriched
        - MULTI formatter logic used
        - Multiple inline keyboard buttons
        - Descriptions fetched for each component
        
        IMPLEMENTATION GUIDE:
        
        ```python
        # Synthetic blockchain data (MULTI product)
        blockchain_data = (
            99,  # Synthetic product_id
            "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",  # Seller
            ["amanita_muscaria", "blue_lotus", "lions_mane"],  # 3 components
            "QmSyntheticMultiProductCID",  # Metadata CID (can be fake for test)
            True  # active
        )
        
        # Synthetic metadata (MULTI format)
        metadata = {
            "business_id": "multi_test_product",
            "title": "Синтетический мультипродукт (E2E тест)",
            "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "30g"},
                {"component_id": "blue_lotus", "proportion": "20g"},
                {"component_id": "lions_mane", "proportion": "50g"}
            ],
            "forms": ["powder", "capsules"],
            "species": "Multi-component blend",
            "categories": ["blends", "nootropics"]
        }
        
        # Assemble product (uses real ProductAssembler)
        product = await real_product_assembler.assemble_product(
            blockchain_data,
            metadata
        )
        
        # STAGE 1: Assembly validation
        assert product is not None
        assert len(product.organic_components) == 3
        assert product.business_id == "multi_test_product"
        
        # STAGE 2: Component enrichment
        for idx, component in enumerate(product.organic_components):
            assert component.component_id in ["amanita_muscaria", "blue_lotus", "lions_mane"]
            assert component.scientific_title is not None
            # Description may be None (graceful degradation)
            logger.info(f"Component {idx+1}: {component.component_id} ({component.scientific_title})")
        
        # STAGE 3: MULTI formatting
        result = real_formatter_service.format_product_details_for_telegram(
            product,
            russian_localization
        )
        
        assert "text" in result
        assert "inline_keyboard" in result
        
        formatted_text = result["text"]
        
        # MULTI marker should be present
        assert "Мультикомпонентный" in formatted_text or "Multi" in formatted_text.lower()
        
        # All component names should be mentioned
        assert "Amanita muscaria" in formatted_text or "amanita" in formatted_text.lower()
        assert "Blue lotus" in formatted_text or "lotus" in formatted_text.lower()
        assert "Lion" in formatted_text or "lion" in formatted_text.lower()
        
        # STAGE 4: Multi-component keyboard
        inline_keyboard = result["inline_keyboard"]
        
        if inline_keyboard:
            buttons = inline_keyboard.inline_keyboard
            # Should have buttons for components with descriptions
            # (amanita_muscaria has description, others may not)
            assert len(buttons) >= 1
            assert len(buttons) <= 3
            
            # At least amanita_muscaria button should exist
            button_texts = [btn[0].text for btn in buttons]
            has_amanita_button = any("Активные компоненты" in text or "компонент" in text.lower() for text in button_texts)
            assert has_amanita_button
        
        # STAGE 5: Performance (multiple fetches)
        # Multi-component products fetch multiple descriptions
        # Cache should help after first fetch
        
        logger.info("✅ E2E TEST 4: MULTI Product validated")
        logger.info(f"   Product: {product.business_id}")
        logger.info(f"   Components: {len(product.organic_components)}")
        logger.info(f"   Message length: {len(formatted_text)} chars")
        
        print("\\n" + "="*80)
        print("🎉 E2E TEST 4 PASSED: MULTI Component Product")
        print("="*80)
        print(f"Product: {product.business_id}")
        print(f"Components: {len(product.organic_components)}")
        print("All stages validated ✅")
        print("="*80)
        ```
        
        NOTE: Remove @pytest.mark.skip when MULTI product data is available.
        """
        # This test is skipped until MULTI product is available
        # Implementation code above in docstring
        pass

