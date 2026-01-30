// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

/**
 * @title MockSpiralEngine
 * @dev Мок контракт SpiralEngine для тестирования ProductRegistry и ActivityRegistry
 * @notice Простая реализация ISpiralEngine для unit тестов
 */
contract MockSpiralEngine {
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");
    bytes32 public constant ACTIVITY_CREATOR_ROLE = keccak256("ACTIVITY_CREATOR_ROLE");
    
    mapping(address => uint256) public usedInviteByUser;
    mapping(bytes32 => mapping(address => bool)) private _roles;
    
    /**
     * @dev Установить статус активации пользователя (для тестов)
     */
    function setUserActivated(address user, bool activated) external {
        usedInviteByUser[user] = activated ? 1 : 0;
    }
    
    /**
     * @dev Выдать роль пользователю (для тестов)
     */
    function grantRole(bytes32 role, address account) external {
        _roles[role][account] = true;
    }
    
    /**
     * @dev Проверить роль пользователя
     */
    function hasRole(bytes32 role, address account) external view returns (bool) {
        return _roles[role][account];
    }
}

