// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

/**
 * @title AmanitaInternationalProxy
 * @notice UUPS Proxy для AmanitaInternational контракта
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
 * 
 * @custom:security-contact security@amanita.com
 */
contract AmanitaInternationalProxy is ERC1967Proxy {
    /**
     * @notice Конструктор прокси контракта
     * @param implementation Адрес Logic контракта
     * @param initData Данные для инициализации через initialize()
     * 
     * @dev initData должна содержать закодированный вызов initialize(admin)
     * Пример: abi.encodeWithSignature("initialize(address)", adminAddress)
     */
    constructor(
        address implementation,
        bytes memory initData
    ) ERC1967Proxy(implementation, initData) {}
}

