// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MockSpiralEngine
 * @dev Mock контракт для тестирования интеграции SoulIntegration
 */
contract MockSpiralEngine {
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
    
    function getNotificationCount() external view returns (uint256) {
        return notificationCount;
    }
    
    function getRecoveryNotificationCount() external view returns (uint256) {
        return recoveryNotificationCount;
    }
    
    function getLastNotifiedTokenId() external view returns (uint256) {
        return lastNotifiedTokenId;
    }
    
    function getLastNotifiedOwner() external view returns (address) {
        return lastNotifiedOwner;
    }
    
    function getLastRecoveryTokenId() external view returns (uint256) {
        return lastRecoveryTokenId;
    }
    
    function getLastRecoveryOldOwner() external view returns (address) {
        return lastRecoveryOldOwner;
    }
    
    function getLastRecoveryNewOwner() external view returns (address) {
        return lastRecoveryNewOwner;
    }
}
