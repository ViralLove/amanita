// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title ProductRegistryMock
 * @author Zeya888 (https://zeya888.me)
 * @dev Мок контракта ProductRegistry для тестирования OrganicComponentRegistry.
 * @notice Реализует минимальный функционал для интеграции с OrganicComponentRegistry.
 */
contract ProductRegistryMock is AccessControl {
    
    // === РОЛИ ===
    
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");
    
    // === ДАННЫЕ ===
    
    mapping(string => uint256) public componentUsageCount;
    mapping(string => address[]) public componentUsers;
    
    // === ИНТЕГРАЦИЯ ===
    
    address public organicComponentRegistry;
    
    // === СОБЫТИЯ ===
    
    event ComponentUsed(string indexed businessId, address indexed user);
    event ComponentUsageIncremented(string indexed businessId, uint256 newCount);
    
    // === КОНСТРУКТОР ===
    
    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }
    
    // === ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ ===
    
    /**
     * @dev Использовать компонент в продукте (для тестов)
     * @param businessId ID компонента
     * @param user Адрес пользователя
     */
    function useComponent(string memory businessId, address user) external onlyRole(SELLER_ROLE) {
        componentUsageCount[businessId]++;
        componentUsers[businessId].push(user);
        
        emit ComponentUsed(businessId, user);
        emit ComponentUsageIncremented(businessId, componentUsageCount[businessId]);
        
        // Уведомляем OrganicComponentRegistry о использовании
        if (organicComponentRegistry != address(0)) {
            // Вызываем функцию увеличения счетчика использования
            (bool success, ) = organicComponentRegistry.call(
                abi.encodeWithSignature("incrementUsageCount(string)", businessId)
            );
            require(success, "ProductRegistryMock: failed to notify OrganicComponentRegistry");
            
            // Вызываем функцию добавления пользователя
            (success, ) = organicComponentRegistry.call(
                abi.encodeWithSignature("addComponentUser(string,address)", businessId, user)
            );
            require(success, "ProductRegistryMock: failed to add component user");
        }
    }
    
    /**
     * @dev Получить количество использований компонента
     * @param businessId ID компонента
     * @return uint256 Количество использований
     */
    function getComponentUsageCount(string memory businessId) external view returns (uint256) {
        return componentUsageCount[businessId];
    }
    
    /**
     * @dev Получить пользователей компонента
     * @param businessId ID компонента
     * @return address[] Массив адресов пользователей
     */
    function getComponentUsers(string memory businessId) external view returns (address[] memory) {
        return componentUsers[businessId];
    }
    
    // === ФУНКЦИИ ДЛЯ НАСТРОЙКИ ТЕСТОВ ===
    
    /**
     * @dev Установить адрес OrganicComponentRegistry
     * @param _registry Адрес контракта OrganicComponentRegistry
     */
    function setOrganicComponentRegistry(address _registry) external onlyRole(DEFAULT_ADMIN_ROLE) {
        organicComponentRegistry = _registry;
    }
    
    /**
     * @dev Установить роль селлера (только для тестов)
     * @param user Адрес пользователя
     */
    function setSellerRole(address user) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _grantRole(SELLER_ROLE, user);
    }
    
    /**
     * @dev Установить счетчик использования компонента (только для тестов)
     * @param businessId ID компонента
     * @param count Количество использований
     */
    function setComponentUsageCount(string memory businessId, uint256 count) external onlyRole(DEFAULT_ADMIN_ROLE) {
        componentUsageCount[businessId] = count;
    }
}
