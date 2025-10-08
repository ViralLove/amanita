// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

/**
 * @title SpiralEngineProxy
 * @author Zeya888 (https://zeya888.me)
 * @notice UUPS Proxy для SpiralEngine контракта
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
 * - ✅ Поддержка ERC721 через delegatecall
 * 
 * Deployment:
 * 1. Deploy SpiralEngineLogic implementation
 * 2. Encode initialize(admin) calldata
 * 3. Deploy SpiralEngineProxy(logic, initCalldata)
 * 4. All calls go through Proxy → delegatecall → Logic
 * 
 * @custom:security-contact security@amanita.com
 */
contract SpiralEngineProxy is ERC1967Proxy {
    /**
     * @notice Конструктор прокси контракта
     * @param implementation Адрес Logic контракта (SpiralEngineLogic)
     * @param initData Данные для инициализации через initialize()
     * 
     * @dev initData должна содержать закодированный вызов initialize(admin)
     * Пример: abi.encodeWithSignature("initialize(address)", adminAddress)
     * 
     * При деплое автоматически вызывается initialize через delegatecall.
     * После инициализации Proxy готов к использованию.
     */
    constructor(
        address implementation,
        bytes memory initData
    ) ERC1967Proxy(implementation, initData) {}
}

