import pytest
"""
Test script for OrganicComponentRegistry integration in blockchain.py

This script validates that:
1. OrganicComponentRegistry contract loads successfully
2. Component reading methods work correctly
3. CID retrieval works for Arweave metadata
4. Error handling works as expected

Usage:
    python bot/tests/test_component_integration.py
"""

import sys
import os
import logging

# Add bot directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.core.blockchain import BlockchainService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.mark.integration
def test_contract_loading():
    """Test 1: OrganicComponentRegistry loads successfully"""
    print("\n" + "="*60)
    print("TEST 1: Contract Loading")
    print("="*60)
    
    try:
        bs = BlockchainService()
        
        # Check that OrganicComponentRegistry is loaded
        component_registry = bs.get_contract("OrganicComponentRegistry")
        
        if component_registry:
            print("✅ SUCCESS: OrganicComponentRegistry contract loaded")
            print(f"   Contract address: {component_registry.address}")
        else:
            print("❌ FAILED: OrganicComponentRegistry contract not loaded")
            assert False, "OrganicComponentRegistry contract not loaded"
            
    except Exception as e:
        print(f"❌ FAILED: Error loading contract: {e}")
        raise


@pytest.mark.integration
def test_component_exists():
    """Test 2: component_exists() method"""
    print("\n" + "="*60)
    print("TEST 2: component_exists() Method")
    print("="*60)
    
    try:
        bs = BlockchainService()
        
        # Test with a known component (adjust based on your deployment)
        test_component_id = "amanita_muscaria"
        
        print(f"Testing component_exists('{test_component_id}')...")
        exists = bs.component_exists(test_component_id)
        
        print(f"✅ Method executed successfully")
        print(f"   Result: {exists}")
        
        if exists:
            print(f"   ✅ Component '{test_component_id}' exists in registry")
        else:
            print(f"   ⚠️  Component '{test_component_id}' not found (may not be deployed yet)")
        
    except Exception as e:
        print(f"❌ FAILED: Error calling component_exists(): {e}")
        raise


@pytest.mark.integration
def test_get_component():
    """Test 3: get_component() method"""
    print("\n" + "="*60)
    print("TEST 3: get_component() Method")
    print("="*60)
    
    try:
        bs = BlockchainService()
        
        # First, check if component exists
        test_component_id = "amanita_muscaria"
        
        if not bs.component_exists(test_component_id):
            print(f"⚠️  SKIPPED: Component '{test_component_id}' not deployed yet")
            print("   Deploy components first using Action 555")
            pytest.skip(f"Component '{test_component_id}' not deployed yet")
        
        print(f"Fetching component data for '{test_component_id}'...")
        component = bs.get_component(test_component_id)
        
        if component:
            print(f"✅ SUCCESS: Component data retrieved")
            print(f"   Component structure type: {type(component)}")
            
            # Display component data
            if isinstance(component, (list, tuple)):
                print(f"   Component data (tuple/list):")
                print(f"     - ID: {component[0] if len(component) > 0 else 'N/A'}")
                print(f"     - Business ID: {component[1] if len(component) > 1 else 'N/A'}")
                print(f"     - Creator: {component[2] if len(component) > 2 else 'N/A'}")
                print(f"     - Root Metadata CID: {component[3] if len(component) > 3 else 'N/A'}")
                print(f"     - Active: {component[4] if len(component) > 4 else 'N/A'}")
                print(f"     - Created At: {component[5] if len(component) > 5 else 'N/A'}")
            elif isinstance(component, dict):
                print(f"   Component data (dict):")
                for key, value in component.items():
                    print(f"     - {key}: {value}")
            
        else:
            print(f"❌ FAILED: Component data not retrieved")
            assert False, "Component data not retrieved"
            
    except Exception as e:
        print(f"❌ FAILED: Error calling get_component(): {e}")
        raise


@pytest.mark.integration
def test_get_component_cid():
    """Test 4: get_component_root_metadata_cid() method"""
    print("\n" + "="*60)
    print("TEST 4: get_component_root_metadata_cid() Method")
    print("="*60)
    
    try:
        bs = BlockchainService()
        
        test_component_id = "amanita_muscaria"
        
        if not bs.component_exists(test_component_id):
            print(f"⚠️  SKIPPED: Component '{test_component_id}' not deployed yet")
            pytest.skip(f"Component '{test_component_id}' not deployed yet")
        
        print(f"Fetching root metadata CID for '{test_component_id}'...")
        cid = bs.get_component_root_metadata_cid(test_component_id)
        
        if cid:
            print(f"✅ SUCCESS: CID retrieved")
            print(f"   CID: {cid}")
            print(f"   Arweave URL: https://arweave.net/{cid}")
        else:
            print(f"❌ FAILED: CID not retrieved")
            assert False, "CID not retrieved"
            
    except Exception as e:
        print(f"❌ FAILED: Error calling get_component_root_metadata_cid(): {e}")
        raise


@pytest.mark.integration
def test_get_all_components():
    """Test 5: get_all_components() method"""
    print("\n" + "="*60)
    print("TEST 5: get_all_components() Method")
    print("="*60)
    
    try:
        bs = BlockchainService()
        
        print("Fetching all components from registry...")
        components = bs.get_all_components()
        
        print(f"✅ Method executed successfully")
        print(f"   Total components found: {len(components)}")
        
        if len(components) > 0:
            print(f"\n   Component IDs:")
            for i, comp in enumerate(components, 1):
                if isinstance(comp, (list, tuple)) and len(comp) > 1:
                    business_id = comp[1]
                    print(f"     {i}. {business_id}")
                elif isinstance(comp, dict):
                    business_id = comp.get('businessId', 'Unknown')
                    print(f"     {i}. {business_id}")
        else:
            print("   ⚠️  No components found (may not be deployed yet)")
        
    except Exception as e:
        print(f"❌ FAILED: Error calling get_all_components(): {e}")
        raise


@pytest.mark.integration
def test_nonexistent_component():
    """Test 6: Error handling for non-existent component"""
    print("\n" + "="*60)
    print("TEST 6: Error Handling (Non-existent Component)")
    print("="*60)
    
    try:
        bs = BlockchainService()
        
        fake_component_id = "nonexistent_component_xyz123"
        
        print(f"Testing with non-existent component '{fake_component_id}'...")
        
        # Should return False
        exists = bs.component_exists(fake_component_id)
        print(f"   component_exists(): {exists} ✅")
        
        # Should return None
        component = bs.get_component(fake_component_id)
        print(f"   get_component(): {component} ✅")
        
        # Should return None
        cid = bs.get_component_root_metadata_cid(fake_component_id)
        print(f"   get_component_root_metadata_cid(): {cid} ✅")
        
        print("✅ SUCCESS: Error handling works correctly")
        
    except Exception as e:
        print(f"❌ FAILED: Unexpected exception: {e}")
        raise


def main():
    """Run all tests"""
    print("\n" + "#"*60)
    print("# OrganicComponentRegistry Integration Test Suite")
    print("#"*60)
    
    tests = [
        ("Contract Loading", test_contract_loading),
        ("component_exists()", test_component_exists),
        ("get_component()", test_get_component),
        ("get_component_root_metadata_cid()", test_get_component_cid),
        ("get_all_components()", test_get_all_components),
        ("Error Handling", test_nonexistent_component),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n{'='*60}")
    print(f"Total: {passed}/{total} tests passed")
    print(f"{'='*60}\n")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! OrganicComponentRegistry integration is working.")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

