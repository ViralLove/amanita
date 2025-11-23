"""
E2E Infrastructure Validation Tests (Phase 1).

Proof tests to validate E2E infrastructure is working:
1. Node connection
2. Contracts deployed
3. Snapshot isolation

Based on: @e2e-test-build.core.mdc (Phase 1: Infrastructure)
"""

import pytest
import os
import logging
import inspect
from config import MAGIC_REGISTRY_CONTRACT_ADDRESS

logger = logging.getLogger(__name__)


@pytest.mark.e2e
@pytest.mark.requires_node
class TestE2EInfrastructure:
    """
    Phase 1: Infrastructure validation.
    
    GOAL: Validate E2E harness and prerequisites.
    
    Tests:
    1. Node connection and health
    2. Contracts deployed verification
    3. Snapshot isolation (proof test)
    """
    
    @pytest.mark.asyncio
    async def test_proof_1_node_connection(self, e2e_harness):
        """
        PROOF TEST 1: Node connection and health.
        
        VALIDATES:
        - Hardhat node running on :8545
        - Web3 connection established
        - Chain ID is 31337 (Hardhat)
        - Block number > 0
        - Accounts available
        
        CRITICAL: This is the foundation for all E2E tests.
        If this fails, all other E2E tests will fail.
        """
        logger.info("="*60)
        logger.info("PROOF TEST 1: Node Connection")
        logger.info("="*60)
        
        # Validate harness connected
        assert e2e_harness.connected is True, "❌ Harness should be connected"
        assert e2e_harness.w3 is not None, "❌ Web3 instance should exist"
        
        # Validate connection
        assert e2e_harness.w3.is_connected() is True, "❌ Web3 connection failed"
        
        # Validate chain ID (Hardhat = 31337)
        chain_id = e2e_harness.w3.eth.chain_id
        assert chain_id == 31337, f"❌ Expected Hardhat chain (31337), got {chain_id}"
        
        # Validate block number
        block_number = e2e_harness.w3.eth.block_number
        assert block_number >= 0, f"❌ Invalid block number: {block_number}"
        
        # Validate accounts (Hardhat provides 20 accounts)
        accounts = e2e_harness.w3.eth.accounts
        assert len(accounts) >= 2, f"❌ Expected at least 2 accounts, got {len(accounts)}"
        
        logger.info(f"✅ Node connected successfully")
        logger.info(f"   RPC: {e2e_harness.rpc_url}")
        logger.info(f"   Chain ID: {chain_id}")
        logger.info(f"   Block: {block_number}")
        logger.info(f"   Accounts: {len(accounts)}")
        
        print("\n" + "="*60)
        print("✅ PROOF TEST 1 PASSED: Node Connection OK")
        print("="*60)
    
    @pytest.mark.asyncio
    async def test_proof_2_contracts_deployed(self, e2e_harness):
        """
        PROOF TEST 2: Contracts deployed verification.
        
        VALIDATES:
        - MAGIC_REGISTRY_CONTRACT_ADDRESS in .env
        - MagicRegistry deployed (code exists)
        - SELLER_ADDRESS in .env
        - Prerequisites for E2E tests met
        
        CRITICAL: Without deployed contracts, E2E tests cannot run.
        """
        logger.info("="*60)
        logger.info("PROOF TEST 2: Contracts Deployed")
        logger.info("="*60)
        
        # Validate MagicRegistry address
        magic_registry = MAGIC_REGISTRY_CONTRACT_ADDRESS
        assert magic_registry is not None, (
            "❌ MAGIC_REGISTRY_CONTRACT_ADDRESS not in .env\n"
            "   Run: DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost"
        )
        
        logger.info(f"   MagicRegistry: {magic_registry}")
        
        # Validate deployment
        validation = await e2e_harness.validate_deployment(magic_registry)
        
        assert validation["deployed"] is True, (
            f"❌ MagicRegistry not deployed at {magic_registry}\n"
            f"   Code size: {validation['code_size']}\n"
            f"   Run: DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost"
        )
        
        assert validation["code_size"] > 0, f"❌ No bytecode at {magic_registry}"
        
        logger.info(f"✅ MagicRegistry deployed: {validation['code_size']} bytes")
        
        # Validate seller configured
        seller_address = os.getenv("SELLER_ADDRESS")
        assert seller_address is not None, (
            "❌ SELLER_ADDRESS not in .env\n"
            "   Add to .env: SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        )
        
        logger.info(f"✅ Seller configured: {seller_address}")
        
        # Validate storage type
        storage_type = os.getenv("STORAGE_TYPE")
        assert storage_type == "arweave", (
            f"⚠️ STORAGE_TYPE={storage_type} (expected: arweave)\n"
            f"   Set in .env: STORAGE_TYPE=arweave"
        )
        
        logger.info(f"✅ Storage configured: {storage_type}")
        
        print("\n" + "="*60)
        print("✅ PROOF TEST 2 PASSED: Contracts Deployed")
        print(f"   MagicRegistry: {magic_registry}")
        print(f"   Code size: {validation['code_size']} bytes")
        print("="*60)
    
    @pytest.mark.asyncio
    async def test_proof_3_snapshot_isolation(self, e2e_harness):
        """
        PROOF TEST 3: Snapshot isolation works.
        
        VALIDATES:
        - Snapshots can be created
        - State can be reverted
        - Block number increases/decreases as expected
        
        CRITICAL: Snapshots enable test isolation without re-deploying contracts.
        """
        logger.info("="*60)
        logger.info("PROOF TEST 3: Snapshot Isolation")
        logger.info("="*60)
        
        # Get initial block
        initial_block = e2e_harness.w3.eth.block_number
        logger.info(f"   Initial block: {initial_block}")
        
        # Create snapshot
        snapshot_id = await e2e_harness.create_snapshot(name="proof-test-snapshot")
        assert snapshot_id > 0, f"❌ Invalid snapshot ID: {snapshot_id}"
        
        logger.info(f"✅ Snapshot created: {snapshot_id}")
        
        # Mine a block (modify state)
        e2e_harness.w3.provider.make_request("evm_mine", [])
        
        # Verify block increased
        after_mine_block = e2e_harness.w3.eth.block_number
        assert after_mine_block == initial_block + 1, (
            f"❌ Block should increase after mining\n"
            f"   Before: {initial_block}, After: {after_mine_block}"
        )
        
        logger.info(f"✅ Block mined: {initial_block} → {after_mine_block}")
        
        # Revert to snapshot
        reverted = await e2e_harness.revert_to_snapshot(snapshot_id)
        assert reverted is True, "❌ Revert failed"
        
        # Verify block reverted
        reverted_block = e2e_harness.w3.eth.block_number
        assert reverted_block == initial_block, (
            f"❌ Block should revert to initial\n"
            f"   Expected: {initial_block}, Got: {reverted_block}"
        )
        
        logger.info(f"✅ Block reverted: {after_mine_block} → {reverted_block}")
        
        print("\n" + "="*60)
        print("✅ PROOF TEST 3 PASSED: Snapshot Isolation Works")
        print(f"   Snapshot ID: {snapshot_id}")
        print(f"   Block: {initial_block} → {after_mine_block} → {reverted_block}")
        print("="*60)


@pytest.mark.e2e
@pytest.mark.requires_node
class TestE2EServicesHealth:
    """
    Phase 1: Services health validation.
    
    GOAL: Validate real services are properly initialized.
    
    Tests:
    1. BlockchainService health
    2. StorageService health
    3. ComponentService health
    """
    
    @pytest.mark.asyncio
    async def test_blockchain_service_health(self, real_blockchain_service):
        """
        Validate BlockchainService is healthy.
        
        VALIDATES:
        - Web3 connected
        - Can read block number
        - Can get accounts
        """
        logger.info("="*60)
        logger.info("SERVICE HEALTH: BlockchainService")
        logger.info("="*60)
        
        # Connection
        assert real_blockchain_service.web3.is_connected() is True
        
        # Can read block
        block = real_blockchain_service.web3.eth.block_number
        assert block >= 0
        
        # Can get accounts
        accounts = real_blockchain_service.web3.eth.accounts
        assert len(accounts) > 0
        
        logger.info(f"✅ BlockchainService healthy")
        logger.info(f"   Block: {block}")
        logger.info(f"   Accounts: {len(accounts)}")
        
        print("\n✅ BlockchainService: HEALTHY")
    
    @pytest.mark.asyncio
    async def test_storage_service_health(self, real_storage_service):
        """
        Validate StorageService is healthy.
        
        VALIDATES:
        - Correct type (ArWeaveUploader)
        - Can download real CID
        """
        logger.info("="*60)
        logger.info("SERVICE HEALTH: StorageService")
        logger.info("="*60)
        
        from services.core.storage.ar_weave import ArWeaveUploader
        
        # Correct type
        assert isinstance(real_storage_service, ArWeaveUploader), (
            f"❌ Expected ArWeaveUploader, got {type(real_storage_service)}"
        )
        
        # Can download (use known CID)
        test_cid = "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4"  # amanita_muscaria.ru
        
        result = real_storage_service.download_json(test_cid)

        if inspect.isawaitable(result):
            data = await result
        else:
            data = result
        
        assert data is not None, f"❌ Failed to download {test_cid}"
        assert isinstance(data, dict), f"❌ Expected dict, got {type(data)}"
        assert "generic_description" in data, "❌ Invalid ComponentDescription structure"
        
        logger.info(f"✅ StorageService healthy")
        logger.info(f"   Type: ArWeaveUploader")
        logger.info(f"   Test download: OK ({len(str(data))} bytes)")
        
        print("\n✅ StorageService: HEALTHY")
    
    @pytest.mark.asyncio
    async def test_component_service_health(self, real_component_service):
        """
        Validate ComponentService is healthy.
        
        VALIDATES:
        - Dependencies injected
        - Cache initialized
        - Can fetch component
        """
        logger.info("="*60)
        logger.info("SERVICE HEALTH: ComponentService")
        logger.info("="*60)
        
        # Dependencies
        assert real_component_service.blockchain_service is not None
        assert real_component_service.storage_service is not None
        
        # Cache initialized
        assert hasattr(real_component_service, '_cache')
        
        # Can fetch component (real blockchain call)
        component = real_component_service.get_component_full("amanita_muscaria")
        
        assert component is not None, "❌ Failed to fetch amanita_muscaria"
        assert component.component_id == "amanita_muscaria"
        assert component.active is True
        
        logger.info(f"✅ ComponentService healthy")
        logger.info(f"   Component fetched: {component.component_id}")
        logger.info(f"   Scientific title: {component.scientific_title}")
        
        print("\n✅ ComponentService: HEALTHY")

