// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FaultySpiralEngine
 * @dev Mock контракт, который всегда бросает ошибки для тестирования error handling
 */
contract FaultySpiralEngine {
    function notifySoulCreated(uint256, address) external pure {
        revert("FaultySpiralEngine: intentional error");
    }
    
    function notifySoulRecovered(uint256, address, address) external pure {
        revert("FaultySpiralEngine: intentional recovery error");
    }
}
