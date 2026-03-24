// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ISpiralInviteSource {
    function userActivator(address user) external view returns (address);
}

/**
 * @dev Adapter used in tests to expose LoveDo-compatible invite graph methods
 * from real SpiralEngine activation edges.
 */
contract SpiralInviteGraphAdapterMock {
    ISpiralInviteSource public immutable spiral;

    constructor(address spiral_) {
        spiral = ISpiralInviteSource(spiral_);
    }

    function getInviterOf(address user) external view returns (address) {
        return spiral.userActivator(user);
    }

    function invitedBy(address user) external view returns (address) {
        return spiral.userActivator(user);
    }
}

