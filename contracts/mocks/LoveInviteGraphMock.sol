// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title LoveInviteGraphMock
 * @dev Mock for LoveDoPostNFT and LoveEmissionEngine tests: getInviterOf + invitedBy.
 */
contract LoveInviteGraphMock {
    mapping(address => address) private _inviterOf;

    function setInviter(address user, address inviter) external {
        _inviterOf[user] = inviter;
    }

    function getInviterOf(address user) external view returns (address) {
        return _inviterOf[user];
    }

    function invitedBy(address user) external view returns (address) {
        return _inviterOf[user];
    }
}
