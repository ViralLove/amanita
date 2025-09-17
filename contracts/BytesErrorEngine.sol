// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BytesErrorEngine
 * @dev Mock контракт, который бросает ошибки без строки для тестирования unknown errors
 */
contract BytesErrorEngine {
    function notifySoulCreated(uint256, address) external pure {
        assembly {
            revert(0, 0)
        }
    }
    
    function notifySoulRecovered(uint256, address, address) external pure {
        assembly {
            revert(0, 0)
        }
    }
}
