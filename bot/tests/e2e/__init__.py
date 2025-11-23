"""
E2E (End-to-End) tests for Amanita Bot.

These tests validate full workflows from blockchain to Telegram display.

PREREQUISITES:
- Hardhat node running on localhost:8545
- Contracts deployed (Actions: 1, 777, 555, 9, 444)
- .env configured with MAGIC_REGISTRY_CONTRACT_ADDRESS
- Arweave data available in data/ directory

STRUCTURE:
- harness.py: E2E infrastructure (node management, snapshots, validation helpers)
- conftest.py: Shared fixtures for E2E tests
- test_*.py: Actual E2E test files

USAGE:
    pytest tests/e2e/ -v -m e2e
"""

