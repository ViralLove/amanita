// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title SpiralEngineMock
 * @author Zeya888 (https://zeya888.me)
 * @dev Мок контракта SpiralEngine для тестирования OrganicComponentRegistry.
 * @notice Реализует минимальный функционал для проверки прав пользователей.
 */
contract SpiralEngineMock is AccessControl {
    
    // === РОЛИ ===
    
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");
    bytes32 public constant ACTIVATOR_ROLE = keccak256("ACTIVATOR_ROLE");
    
    // === ДАННЫЕ ===
    
    mapping(address => uint256) public usedInviteByUser;
    mapping(address => bool) public userActivated;
    
    // === СОБЫТИЯ ===
    
    event UserActivated(address indexed user, uint256 inviteId);
    event SellerRoleGranted(address indexed user, address indexed nominator);
    
    // === КОНСТРУКТОР ===
    
    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }
    
    // === ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ ===
    
    /**
     * @dev Активировать пользователя (для тестов)
     * @param user Адрес пользователя
     * @param inviteId ID инвайта
     */
    function activateUser(address user, uint256 inviteId) external onlyRole(ACTIVATOR_ROLE) {
        usedInviteByUser[user] = inviteId;
        userActivated[user] = true;
        emit UserActivated(user, inviteId);
    }
    
    /**
     * @dev Выдать роль селлера (для тестов)
     * @param user Адрес пользователя
     */
    function grantSellerRole(address user) external onlyRole(ACTIVATOR_ROLE) {
        require(userActivated[user], "SpiralEngineMock: user not activated");
        _grantRole(SELLER_ROLE, user);
        emit SellerRoleGranted(user, msg.sender);
    }
    
    /**
     * @dev Проверить активацию пользователя
     * @param user Адрес пользователя
     * @return bool True, если пользователь активирован
     */
    function isUserActivated(address user) external view returns (bool) {
        return userActivated[user];
    }
    
    /**
     * @dev Получить ID использованного инвайта
     * @param user Адрес пользователя
     * @return uint256 ID инвайта
     */
    function getUsedInviteByUser(address user) external view returns (uint256) {
        return usedInviteByUser[user];
    }
    
    // === ФУНКЦИИ ДЛЯ НАСТРОЙКИ ТЕСТОВ ===
    
    /**
     * @dev Установить активацию пользователя (только для тестов)
     * @param user Адрес пользователя
     * @param inviteId ID инвайта
     */
    function setUserActivation(address user, uint256 inviteId) external onlyRole(DEFAULT_ADMIN_ROLE) {
        usedInviteByUser[user] = inviteId;
        userActivated[user] = true;
    }
    
    /**
     * @dev Установить роль селлера (только для тестов)
     * @param user Адрес пользователя
     */
    function setSellerRole(address user) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _grantRole(SELLER_ROLE, user);
    }
}
