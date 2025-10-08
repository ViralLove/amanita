// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AmanitaInternationalMock
 * @author Amanita Decentralization Team
 * @dev Mock контракт для тестирования интеграции с AmanitaInternational
 */
contract AmanitaInternationalMock {
    // Простой мок без сложной логики
    function isActive() external pure returns (bool) {
        return true;
    }
    
    function getVersion() external pure returns (string memory) {
        return "1.0.0";
    }
}
