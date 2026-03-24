// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ISpiralRolesSource {
    function hasRole(bytes32 role, address account) external view returns (bool);
}

/**
 * @dev Adapter used in tests to expose LoveDo-compatible seller registry check
 * using real SpiralEngine SELLER_ROLE.
 */
contract SpiralSellerRegistryAdapterMock {
    ISpiralRolesSource public immutable spiral;
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");

    constructor(address spiral_) {
        spiral = ISpiralRolesSource(spiral_);
    }

    function hasSellerRole(address user) external view returns (bool) {
        return spiral.hasRole(SELLER_ROLE, user);
    }
}

