// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BytesErrorEngine
 * @dev Mock that reverts without a reason string (revert(0,0)) for SoulIntegration error-handling tests.
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
