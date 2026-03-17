// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title LoveAmanitaRegistryMock
 * @dev Mock for LoveDoPostNFT: hasSellerRole. For tests, returns true for any address.
 */
contract LoveAmanitaRegistryMock {
    function hasSellerRole(address) external pure returns (bool) {
        return true;
    }
}
