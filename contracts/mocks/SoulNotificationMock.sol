// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SoulNotificationMock
 * @dev Mock for SoulIntegration tests: implements notifySoulCreated / notifySoulRecovered
 *      and getters for last notified token/owner and counts.
 */
contract SoulNotificationMock {
    uint256 public lastNotifiedTokenId;
    address public lastNotifiedOwner;
    uint256 public notificationCount;

    uint256 public lastRecoveryTokenId;
    address public lastRecoveryOldOwner;
    address public lastRecoveryNewOwner;
    uint256 public recoveryNotificationCount;

    event SoulCreatedNotification(uint256 indexed tokenId, address indexed owner);
    event SoulRecoveredNotification(uint256 indexed tokenId, address indexed oldOwner, address indexed newOwner);

    function notifySoulCreated(uint256 tokenId, address owner) external {
        lastNotifiedTokenId = tokenId;
        lastNotifiedOwner = owner;
        notificationCount++;
        emit SoulCreatedNotification(tokenId, owner);
    }

    function notifySoulRecovered(uint256 tokenId, address oldOwner, address newOwner) external {
        lastRecoveryTokenId = tokenId;
        lastRecoveryOldOwner = oldOwner;
        lastRecoveryNewOwner = newOwner;
        recoveryNotificationCount++;
        emit SoulRecoveredNotification(tokenId, oldOwner, newOwner);
    }

    function getLastNotifiedTokenId() external view returns (uint256) {
        return lastNotifiedTokenId;
    }

    function getNotificationCount() external view returns (uint256) {
        return notificationCount;
    }

    function getLastRecoveryTokenId() external view returns (uint256) {
        return lastRecoveryTokenId;
    }

    function getRecoveryNotificationCount() external view returns (uint256) {
        return recoveryNotificationCount;
    }
}
