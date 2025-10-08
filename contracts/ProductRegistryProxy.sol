// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

/**
 * @title ProductRegistryProxy
 * @author Zeya888 (https://zeya888.me)
 * @notice UUPS Proxy для ProductRegistry контракта
 * @dev Наследует ERC1967Proxy от OpenZeppelin
 * 
 * Архитектура:
 * - Proxy хранит данные и делегирует вызовы Logic контракту
 * - Logic содержит бизнес-логику и может быть обновлён
 * - Обновление через _authorizeUpgrade() в Logic
 * 
 * Ключевые особенности:
 * - ✅ ERC1967 совместимость
 * - ✅ UUPS паттерн (upgrade логика в Logic)
 * - ✅ Минимальный Proxy (только конструктор)
 * - ✅ Стандарт OpenZeppelin v5
 * - ✅ Поддержка управления каталогом продуктов
 * 
 * Deployment:
 * 1. Deploy ProductRegistryLogic implementation
 * 2. Encode initialize(admin, spiralEngine) calldata
 * 3. Deploy ProductRegistryProxy(logic, initCalldata)
 * 4. All calls go through Proxy → delegatecall → Logic
 * 
 * State Storage:
 * - Все state variables физически хранятся в Proxy
 * - Logic контракт содержит только код (не хранит данные)
 * - delegatecall выполняет код Logic в контексте Proxy
 * 
 * @custom:security-contact security@amanita.com
 */
contract ProductRegistryProxy is ERC1967Proxy {
    /**
     * @notice Конструктор прокси контракта
     * @param implementation Адрес Logic контракта (ProductRegistryLogic)
     * @param initData Данные для инициализации через initialize()
     * 
     * @dev initData должна содержать закодированный вызов initialize(admin, spiralEngine)
     * Пример: abi.encodeWithSignature("initialize(address,address)", adminAddress, spiralEngineAddress)
     * 
     * При деплое автоматически вызывается initialize через delegatecall.
     * После инициализации Proxy готов к использованию.
     * 
     * Важно:
     * - implementation НЕ ДОЛЖЕН быть нулевым адресом
     * - initData ДОЛЖНА быть валидной для initialize функции
     * - initialize может быть вызван только ОДИН РАЗ (защита через initializer)
     */
    constructor(
        address implementation,
        bytes memory initData
    ) ERC1967Proxy(implementation, initData) {}
}

