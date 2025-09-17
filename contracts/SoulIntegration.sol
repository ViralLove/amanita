// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @dev Интерфейс для SpiralEngine - минимальные функции для уведомлений
 */
interface ISpiralEngine {
    function notifySoulCreated(uint256 tokenId, address owner) external;
    function notifySoulRecovered(uint256 tokenId, address oldOwner, address newOwner) external;
}

/**
 * @dev Интерфейс для SoulboundCore - проверка существования токенов
 */
interface ISoulboundCore {
    function ownerOf(uint256 tokenId) external view returns (address);
    function exists(uint256 tokenId) external view returns (bool);
}

/**
 * @title SoulIntegration
 * @author Zeya888 (https://zeya888.me)
 * @dev Интеграционный контракт для уведомления SpiralEngine о событиях SBT
 * @notice Обеспечивает асинхронную обработку событий с graceful degradation
 */
contract SoulIntegration is Ownable {
    
    // === СОБЫТИЯ ===
    
    /**
     * @dev Событие при успешном уведомлении SpiralEngine
     * @param tokenId идентификатор токена
     * @param owner адрес владельца
     * @param eventType тип события ("created" или "recovered")
     */
    event SoulNotified(uint256 indexed tokenId, address indexed owner, string eventType);
    
    /**
     * @dev Событие при обновлении интеграции
     * @param spiralEngine новый адрес SpiralEngine
     * @param soulboundCore новый адрес SoulboundCore
     */
    event IntegrationUpdated(address indexed spiralEngine, address indexed soulboundCore);
    
    /**
     * @dev Событие при ошибке уведомления
     * @param tokenId идентификатор токена
     * @param eventType тип события
     * @param reason причина ошибки
     */
    event NotificationFailed(uint256 indexed tokenId, string eventType, string reason);
    
    // === ХРАНИЛИЩЕ ===
    
    // Адрес контракта SpiralEngine
    ISpiralEngine private _spiralEngine;
    // Адрес контракта SoulboundCore
    ISoulboundCore private _soulboundCore;
    // Включены ли уведомления
    bool private _notificationsEnabled = true;
    
    // === КОНСТРУКТОР ===
    
    constructor(address spiralEngine, address soulboundCore) Ownable(msg.sender) {
        require(spiralEngine != address(0), "SoulIntegration: invalid SpiralEngine address");
        require(soulboundCore != address(0), "SoulIntegration: invalid SoulboundCore address");
        
        _spiralEngine = ISpiralEngine(spiralEngine);
        _soulboundCore = ISoulboundCore(soulboundCore);
        
        emit IntegrationUpdated(spiralEngine, soulboundCore);
    }
    
    // === МОДИФИКАТОРЫ ===
    
    /**
     * @dev Проверяет, что токен существует в SoulboundCore
     */
    modifier tokenExists(uint256 tokenId) {
        require(_soulboundCore.exists(tokenId), "SoulIntegration: token does not exist");
        _;
    }
    
    /**
     * @dev Проверяет, что уведомления включены
     */
    modifier notificationsEnabled() {
        require(_notificationsEnabled, "SoulIntegration: notifications disabled");
        _;
    }
    
    // === ОСНОВНЫЕ ФУНКЦИИ ===
    
    /**
     * @dev Уведомление о создании нового SBT токена
     * @param tokenId идентификатор токена
     * @param owner адрес владельца токена
     */
    function notifySoulCreated(uint256 tokenId, address owner) 
        external 
        tokenExists(tokenId) 
        notificationsEnabled 
    {
        require(owner != address(0), "SoulIntegration: invalid owner address");
        require(_soulboundCore.ownerOf(tokenId) == owner, "SoulIntegration: owner mismatch");
        
        // Попытка уведомления с graceful degradation
        try _spiralEngine.notifySoulCreated(tokenId, owner) {
            emit SoulNotified(tokenId, owner, "created");
        } catch Error(string memory reason) {
            emit NotificationFailed(tokenId, "created", reason);
        } catch (bytes memory) {
            emit NotificationFailed(tokenId, "created", "Unknown error");
        }
    }
    
    /**
     * @dev Уведомление о восстановлении SBT токена
     * @param tokenId идентификатор токена
     * @param oldOwner предыдущий владелец
     * @param newOwner новый владелец
     */
    function notifySoulRecovered(uint256 tokenId, address oldOwner, address newOwner) 
        external 
        tokenExists(tokenId) 
        notificationsEnabled 
    {
        require(oldOwner != address(0), "SoulIntegration: invalid old owner address");
        require(newOwner != address(0), "SoulIntegration: invalid new owner address");
        require(oldOwner != newOwner, "SoulIntegration: owners cannot be the same");
        require(_soulboundCore.ownerOf(tokenId) == newOwner, "SoulIntegration: new owner mismatch");
        
        // Попытка уведомления с graceful degradation
        try _spiralEngine.notifySoulRecovered(tokenId, oldOwner, newOwner) {
            emit SoulNotified(tokenId, newOwner, "recovered");
        } catch Error(string memory reason) {
            emit NotificationFailed(tokenId, "recovered", reason);
        } catch (bytes memory) {
            emit NotificationFailed(tokenId, "recovered", "Unknown error");
        }
    }
    
    // === УПРАВЛЕНИЕ ИНТЕГРАЦИЕЙ ===
    
    /**
     * @dev Установить адрес контракта SpiralEngine (только владелец)
     * @param spiralEngine новый адрес SpiralEngine
     */
    function setSpiralEngine(address spiralEngine) external onlyOwner {
        require(spiralEngine != address(0), "SoulIntegration: invalid SpiralEngine address");
        _spiralEngine = ISpiralEngine(spiralEngine);
        emit IntegrationUpdated(spiralEngine, address(_soulboundCore));
    }
    
    /**
     * @dev Установить адрес контракта SoulboundCore (только владелец)
     * @param soulboundCore новый адрес SoulboundCore
     */
    function setSoulboundCore(address soulboundCore) external onlyOwner {
        require(soulboundCore != address(0), "SoulIntegration: invalid SoulboundCore address");
        _soulboundCore = ISoulboundCore(soulboundCore);
        emit IntegrationUpdated(address(_spiralEngine), soulboundCore);
    }
    
    /**
     * @dev Включить/выключить уведомления (только владелец)
     * @param enabled включены ли уведомления
     */
    function setNotificationsEnabled(bool enabled) external onlyOwner {
        _notificationsEnabled = enabled;
    }
    
    // === VIEW FUNCTIONS ===
    
    /**
     * @dev Получить адрес контракта SpiralEngine
     * @return адрес SpiralEngine
     */
    function getSpiralEngine() external view returns (address) {
        return address(_spiralEngine);
    }
    
    /**
     * @dev Получить адрес контракта SoulboundCore
     * @return адрес SoulboundCore
     */
    function getSoulboundCore() external view returns (address) {
        return address(_soulboundCore);
    }
    
    /**
     * @dev Проверить, включены ли уведомления
     * @return true если уведомления включены
     */
    function areNotificationsEnabled() external view returns (bool) {
        return _notificationsEnabled;
    }
    
    /**
     * @dev Проверить, что интеграция настроена корректно
     * @return true если все адреса установлены
     */
    function isIntegrationValid() external view returns (bool) {
        return address(_spiralEngine) != address(0) && 
               address(_soulboundCore) != address(0) && 
               _notificationsEnabled;
    }
}
