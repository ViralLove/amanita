// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

/**
 * @title OrganicComponentRegistryProxy
 * @author Amanita Decentralization Team
 * @dev Стандартный ERC1967 Proxy контракт для UUPS архитектуры
 * @notice Делегирует все вызовы в Logic контракт через delegatecall
 * @notice Версия: 3.0.0 - Полностью стандартный UUPS паттерн
 * 
 * Архитектура:
 * - Proxy = простая обертка над ERC1967Proxy (только делегирование)
 * - Logic = полная UUPS имплементация с state, ролями, паузой
 * - Все state variables находятся в Logic (физически в Proxy через delegatecall)
 * - Апгрейды выполняются через Logic функцию upgradeTo()
 * 
 * Deployment:
 * 1. Deploy Logic implementation
 * 2. Encode initialize(admin) calldata
 * 3. Deploy Proxy(logic, initCalldata)
 * 4. All calls go through Proxy → delegatecall → Logic
 */
contract OrganicComponentRegistryProxy is ERC1967Proxy {
    /**
     * @dev Конструктор proxy контракта
     * @param implementation Адрес Logic контракта (имплементации)
     * @param initData Закодированные данные для вызова initialize() в Logic
     * @notice При деплое автоматически вызывается initialize через delegatecall
     */
    constructor(address implementation, bytes memory initData)
        ERC1967Proxy(implementation, initData)
    {}
}
