"""
E2E Test Harness for Amanita Bot.

Provides infrastructure management for E2E tests:
- Node lifecycle (connection validation, health checks)
- Snapshot management (EVM state checkpoints)
- Validation helpers (deployment, state, transactions)

Based on: @e2e-test-build.appendix.harness.mdc
"""

import os
import logging
from typing import Optional, Dict, Any
from web3 import Web3
from eth_typing import ChecksumAddress

logger = logging.getLogger(__name__)


class E2EHarness:
    """
    E2E Test Harness for blockchain-based tests.
    
    Strategy: Standalone Node (Background Process)
    - User manually starts: npx hardhat node
    - Tests connect to existing node
    - Snapshots for state isolation
    
    Usage:
        harness = E2EHarness()
        await harness.connect_to_node()
        
        # Take snapshot before test
        snapshot_id = await harness.create_snapshot()
        
        # Run test
        # ...
        
        # Revert to clean state
        await harness.revert_to_snapshot(snapshot_id)
    """
    
    def __init__(
        self,
        rpc_url: Optional[str] = None,
        magic_registry_address: Optional[str] = None
    ):
        """
        Initialize E2E Harness.
        
        Args:
            rpc_url: Web3 provider URL (default: from env or localhost:8545)
            magic_registry_address: MagicRegistry contract address (default: from env)
        """
        self.rpc_url = rpc_url or os.getenv("WEB3_PROVIDER_URI", "http://localhost:8545")
        self.magic_registry_address = magic_registry_address or os.getenv("MAGIC_REGISTRY_CONTRACT_ADDRESS")
        
        self.w3: Optional[Web3] = None
        self.connected: bool = False
        self.snapshots: Dict[str, int] = {}  # name -> snapshot_id mapping
        
        logger.info(f"[E2EHarness] Initialized with RPC: {self.rpc_url}")
    
    async def connect_to_node(self) -> bool:
        """
        Connect to standalone Hardhat node.
        
        Validates:
        - Connection established
        - Node is responsive
        - Chain ID is Hardhat (31337)
        
        Returns:
            bool: True if connected successfully
        
        Raises:
            ConnectionError: If node not running or unreachable
        """
        try:
            logger.info(f"[E2EHarness] Connecting to node: {self.rpc_url}")
            
            # Create Web3 instance
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            
            # Validate connection
            if not self.w3.is_connected():
                raise ConnectionError(
                    f"❌ Failed to connect to node at {self.rpc_url}\n"
                    f"   Is Hardhat node running? Run: npx hardhat node"
                )
            
            # Validate chain ID (Hardhat = 31337)
            chain_id = self.w3.eth.chain_id
            if chain_id != 31337:
                logger.warning(f"⚠️ Chain ID {chain_id} is not Hardhat (31337). Using anyway.")
            
            # Get current block
            block_number = self.w3.eth.block_number
            
            self.connected = True
            logger.info(f"✅ Connected to node")
            logger.info(f"   Chain ID: {chain_id}")
            logger.info(f"   Block: {block_number}")
            logger.info(f"   Accounts: {len(self.w3.eth.accounts)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Node connection failed: {e}")
            raise ConnectionError(f"Node not available at {self.rpc_url}: {e}")
    
    async def validate_prerequisites(self) -> Dict[str, bool]:
        """
        Validate all E2E prerequisites.
        
        Checks:
        - Node connected
        - MagicRegistry deployed
        - Seller address in .env
        - Storage type configured
        
        Returns:
            Dict with validation results
        """
        results = {
            "node_connected": False,
            "magic_registry_deployed": False,
            "seller_configured": False,
            "storage_configured": False
        }
        
        try:
            # Check 1: Node connected
            if not self.connected:
                await self.connect_to_node()
            results["node_connected"] = self.connected
            
            # Check 2: MagicRegistry deployed
            if self.magic_registry_address:
                code = self.w3.eth.get_code(self.magic_registry_address)
                results["magic_registry_deployed"] = len(code) > 0
                
                if not results["magic_registry_deployed"]:
                    logger.error(f"❌ MagicRegistry not deployed at {self.magic_registry_address}")
                    logger.error(f"   Run: DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost")
            else:
                logger.error(f"❌ MAGIC_REGISTRY_CONTRACT_ADDRESS not in .env")
            
            # Check 3: Seller configured
            seller_address = os.getenv("SELLER_ADDRESS")
            results["seller_configured"] = seller_address is not None
            
            if not results["seller_configured"]:
                logger.error(f"❌ SELLER_ADDRESS not in .env")
            
            # Check 4: Storage type
            storage_type = os.getenv("STORAGE_TYPE")
            results["storage_configured"] = storage_type == "arweave"
            
            if not results["storage_configured"]:
                logger.warning(f"⚠️ STORAGE_TYPE={storage_type} (expected: arweave)")
            
            # Summary
            all_ok = all(results.values())
            if all_ok:
                logger.info(f"✅ All prerequisites validated")
            else:
                failed = [k for k, v in results.items() if not v]
                logger.error(f"❌ Prerequisites failed: {failed}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Prerequisites validation failed: {e}")
            return results
    
    async def create_snapshot(self, name: str = "default") -> int:
        """
        Create EVM snapshot for state isolation.
        
        Snapshots allow reverting to clean state between tests,
        avoiding expensive re-deployment.
        
        Args:
            name: Snapshot name for tracking
        
        Returns:
            int: Snapshot ID (for reverting)
        
        Example:
            snapshot_id = await harness.create_snapshot("after-deploy")
            # Run test that modifies state
            await harness.revert_to_snapshot(snapshot_id)
            # State reverted to "after-deploy"
        """
        try:
            if not self.connected:
                raise RuntimeError("Node not connected. Call connect_to_node() first.")
            
            # EVM snapshot RPC call
            snapshot_id = self.w3.provider.make_request("evm_snapshot", [])["result"]
            
            # Convert hex to int
            snapshot_id_int = int(snapshot_id, 16)
            
            # Store with name
            self.snapshots[name] = snapshot_id_int
            
            logger.info(f"📸 Snapshot created: '{name}' (ID: {snapshot_id_int})")
            
            return snapshot_id_int
            
        except Exception as e:
            logger.error(f"❌ Failed to create snapshot '{name}': {e}")
            raise
    
    async def revert_to_snapshot(self, snapshot_id: int) -> bool:
        """
        Revert EVM state to snapshot.
        
        Args:
            snapshot_id: Snapshot ID from create_snapshot()
        
        Returns:
            bool: True if reverted successfully
        """
        try:
            if not self.connected:
                raise RuntimeError("Node not connected")
            
            # EVM revert RPC call
            hex_id = hex(snapshot_id)
            result = self.w3.provider.make_request("evm_revert", [hex_id])
            
            success = result.get("result", False)
            
            if success:
                logger.info(f"⏪ Reverted to snapshot {snapshot_id}")
            else:
                logger.error(f"❌ Failed to revert to snapshot {snapshot_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Revert failed for snapshot {snapshot_id}: {e}")
            return False
    
    async def revert_to_named_snapshot(self, name: str) -> bool:
        """
        Revert to snapshot by name.
        
        Args:
            name: Snapshot name from create_snapshot()
        
        Returns:
            bool: True if reverted successfully
        """
        if name not in self.snapshots:
            logger.error(f"❌ Snapshot '{name}' not found. Available: {list(self.snapshots.keys())}")
            return False
        
        snapshot_id = self.snapshots[name]
        return await self.revert_to_snapshot(snapshot_id)
    
    async def validate_deployment(self, address: str) -> Dict[str, Any]:
        """
        Validate contract deployed on-chain (E2E validation helper).
        
        Checks:
        - Code exists at address
        - Bytecode length > 0
        - Address is valid checksum
        
        Args:
            address: Contract address to validate
        
        Returns:
            Dict with validation results
        """
        try:
            if not self.connected:
                raise RuntimeError("Node not connected")
            
            # Get bytecode
            code = self.w3.eth.get_code(address)
            code_size = len(code)
            
            # Validate
            deployed = code_size > 0
            is_checksum = Web3.is_checksum_address(address)
            
            result = {
                "deployed": deployed,
                "code_size": code_size,
                "address": address,
                "is_checksum": is_checksum
            }
            
            if deployed:
                logger.info(f"✅ Contract deployed at {address} ({code_size} bytes)")
            else:
                logger.error(f"❌ No code at {address}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Deployment validation failed for {address}: {e}")
            return {
                "deployed": False,
                "code_size": 0,
                "address": address,
                "error": str(e)
            }
    
    async def validate_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """
        Validate transaction succeeded on-chain.
        
        Args:
            tx_hash: Transaction hash
        
        Returns:
            Dict with receipt and validation
        """
        try:
            if not self.connected:
                raise RuntimeError("Node not connected")
            
            # Get receipt
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            
            # Validate status
            success = receipt.get("status") == 1
            
            result = {
                "success": success,
                "tx_hash": tx_hash,
                "block_number": receipt.get("blockNumber"),
                "gas_used": receipt.get("gasUsed"),
                "logs": len(receipt.get("logs", []))
            }
            
            if success:
                logger.info(f"✅ Transaction succeeded: {tx_hash}")
            else:
                logger.error(f"❌ Transaction failed: {tx_hash}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Transaction validation failed for {tx_hash}: {e}")
            return {
                "success": False,
                "tx_hash": tx_hash,
                "error": str(e)
            }
    
    async def get_current_state(self) -> Dict[str, Any]:
        """
        Get current node state (for debugging).
        
        Returns:
            Dict with current block, accounts, etc.
        """
        try:
            if not self.connected:
                raise RuntimeError("Node not connected")
            
            state = {
                "block_number": self.w3.eth.block_number,
                "chain_id": self.w3.eth.chain_id,
                "accounts_count": len(self.w3.eth.accounts),
                "snapshots": list(self.snapshots.keys())
            }
            
            logger.debug(f"[E2EHarness] Current state: {state}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Failed to get state: {e}")
            return {}
    
    async def cleanup(self):
        """
        Cleanup harness resources.
        
        Note: For standalone node, this doesn't stop the node.
        Only clears internal state.
        """
        logger.info(f"[E2EHarness] Cleanup (snapshots cleared, node still running)")
        self.snapshots.clear()
        self.connected = False
        self.w3 = None

