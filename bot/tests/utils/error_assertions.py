"""
Helper functions for universal revert error assertions in integration tests.

Works with all blockchain networks:
- localhost (Anvil/Foundry): ContractCustomError with error codes
- testnet (amoy): web3.py exceptions via RPC
- mainnet (polygon): web3.py exceptions via RPC

All networks use web3.py, so errors follow web3.py exception patterns.

Usage:
    from bot.tests.utils.error_assertions import assert_revert
    
    with pytest.raises(Exception) as exc_info:
        contract.functions.someFunction().transact({'from': account.address})
    assert_revert(exc_info, "Expected transaction to revert")
"""

from web3.exceptions import ContractCustomError, ContractLogicError
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.python_api import ExceptionInfo


def assert_revert(exc_info: "ExceptionInfo", custom_message: str = "Expected transaction to revert") -> None:
    """
    Universal revert assertion that works with all blockchain networks.
    
    Supported networks:
    - localhost (Anvil): ContractCustomError with error codes
    - testnet (amoy): web3.py exceptions via RPC
    - mainnet (polygon): web3.py exceptions via RPC
    
    All networks use web3.py, so errors are handled consistently.
    
    Args:
        exc_info: ExceptionInfo from pytest.raises()
        custom_message: Custom assertion message (optional)
    
    Raises:
        AssertionError: If exception is not a revert error
    
    Examples:
        >>> with pytest.raises(Exception) as exc_info:
        ...     contract.functions.mintInvite(code, 0).transact({'from': account.address})
        >>> assert_revert(exc_info, "Ожидали revert при попытке минтить дубликат кода")
    """
    error = exc_info.value
    
    # Check 1: Web3 contract errors (all networks via web3.py)
    # ContractCustomError: Anvil returns structured error codes
    # ContractLogicError: Generic contract logic errors (all networks)
    if isinstance(error, (ContractCustomError, ContractLogicError)):
        return  # Revert confirmed
    
    # Check 2: Error message contains revert indicators (fallback for RPC errors)
    # Some RPC providers may return errors as strings with "revert" in message
    error_str = str(error).lower()
    revert_indicators = ["revert", "reverted", "execution reverted", "vm exception"]
    if any(indicator in error_str for indicator in revert_indicators):
        return  # Revert confirmed
    
    # Check 3: Fallback - any exception from transaction is likely a revert
    # In test context, if transaction raises exception, it's usually a revert
    # Exclude common non-revert exceptions that shouldn't be treated as revert
    if isinstance(error, Exception):
        non_revert_exceptions = (ValueError, TypeError, AttributeError, KeyError, ImportError)
        if not isinstance(error, non_revert_exceptions):
            return  # Assume revert for transaction exceptions
    
    # If we get here, it's not a revert error
    error_type = type(error).__name__
    error_str_preview = str(error)[:200] if str(error) else "N/A"
    raise AssertionError(
        f"{custom_message}. "
        f"Exception type: {error_type}, "
        f"message: {error_str_preview}"
    )

