// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./SoulboundCore.sol";

/**
 * @title SoulRecovery
 * @author Zeya888 (https://zeya888.me)
 * @dev Система восстановления доступа к SoulboundCore токенам через guardian'ов
 * @notice Упрощенная система с одним guardian на пользователя
 */
contract SoulRecovery {
    
    // === СОБЫТИЯ ===
    
    /**
     * @dev Событие установки guardian'а
     * @param tokenId идентификатор токена
     * @param owner владелец токена
     * @param guardian адрес guardian'а
     */
    event GuardianSet(uint256 indexed tokenId, address indexed owner, address indexed guardian);
    
    /**
     * @dev Событие инициации восстановления
     * @param tokenId идентификатор токена
     * @param oldOwner старый владелец
     * @param newOwner новый владелец
     * @param guardian guardian, инициировавший восстановление
     */
    event RecoveryInitiated(uint256 indexed tokenId, address indexed oldOwner, address indexed newOwner, address guardian);
    
    /**
     * @dev Событие завершения восстановления
     * @param tokenId идентификатор токена
     * @param newOwner новый владелец
     */
    event RecoveryCompleted(uint256 indexed tokenId, address indexed newOwner);
    
    /**
     * @dev Событие отмены восстановления
     * @param tokenId идентификатор токена
     * @param owner владелец токена
     */
    event RecoveryCancelled(uint256 indexed tokenId, address indexed owner);
    
    // === СТРУКТУРЫ ДАННЫХ ===
    
    /**
     * @dev Информация о guardian'е для токена
     */
    struct GuardianInfo {
        address guardian;           // Адрес guardian'а
        uint256 setTimestamp;      // Время установки guardian'а
        bool isActive;             // Активен ли guardian
    }
    
    /**
     * @dev Информация о процессе восстановления
     */
    struct RecoveryInfo {
        address newOwner;          // Новый владелец
        address guardian;          // Guardian, инициировавший восстановление
        uint256 initiatedAt;       // Время инициации
        bool isActive;             // Активен ли процесс восстановления
    }
    
    // === ХРАНИЛИЩЕ ===
    
    // Ссылка на основной SoulboundCore контракт
    SoulboundCore public immutable soulboundCore;
    // Мост SoulIdentity — может вызывать *For методы от имени владельца/guardian (SBT-REC-1)
    address public soulIdentity;
    address private _owner;
    
    // Mapping от tokenId к информации о guardian'е
    mapping(uint256 => GuardianInfo) private _guardians;
    
    // Mapping от tokenId к информации о восстановлении
    mapping(uint256 => RecoveryInfo) private _recoveries;
    
    // Время задержки для восстановления (24 часа)
    uint256 public constant RECOVERY_DELAY = 24 hours;
    
    // Минимальное время после установки guardian'а перед возможностью восстановления (7 дней)
    uint256 public constant GUARDIAN_DELAY = 7 days;
    
    // === МОДИФИКАТОРЫ ===
    
    /**
     * @dev Проверяет, что токен существует в SoulboundCore
     */
    modifier tokenExists(uint256 tokenId) {
        require(soulboundCore.exists(tokenId), "SoulRecovery: token does not exist");
        _;
    }
    
    /**
     * @dev Проверяет, что вызывающий является владельцем токена
     */
    modifier onlyTokenOwner(uint256 tokenId) {
        require(
            soulboundCore.ownerOf(tokenId) == msg.sender,
            "SoulRecovery: not token owner"
        );
        _;
    }
    
    /**
     * @dev Проверяет, что вызывающий является guardian'ом токена
     */
    modifier onlyGuardian(uint256 tokenId) {
        require(
            _guardians[tokenId].guardian == msg.sender && _guardians[tokenId].isActive,
            "SoulRecovery: not authorized guardian"
        );
        _;
    }
    
    // === КОНСТРУКТОР ===
    
    constructor(address _soulboundCore) {
        require(_soulboundCore != address(0), "SoulRecovery: invalid address");
        soulboundCore = SoulboundCore(_soulboundCore);
        _owner = msg.sender;
    }
    
    /**
     * @dev Установить адрес SoulIdentity для вызовов через мост (SBT-REC-1)
     */
    function setSoulIdentity(address _soulIdentity) external {
        require(msg.sender == _owner, "SoulRecovery: not owner");
        soulIdentity = _soulIdentity;
    }
    
    // === ОСНОВНЫЕ ФУНКЦИИ ===
    
    /**
     * @dev Установка guardian'а для токена
     * @param tokenId идентификатор токена
     * @param guardian адрес guardian'а
     */
    function setGuardian(uint256 tokenId, address guardian) 
        external 
        tokenExists(tokenId) 
        onlyTokenOwner(tokenId) 
    {
        require(guardian != address(0), "SoulRecovery: invalid guardian address");
        require(guardian != msg.sender, "SoulRecovery: cannot be self guardian");
        require(guardian != soulboundCore.ownerOf(tokenId), "SoulRecovery: guardian cannot be owner");
        
        _guardians[tokenId] = GuardianInfo({
            guardian: guardian,
            setTimestamp: block.timestamp,
            isActive: true
        });
        
        emit GuardianSet(tokenId, msg.sender, guardian);
    }
    
    /**
     * @dev Удаление guardian'а
     * @param tokenId идентификатор токена
     */
    function removeGuardian(uint256 tokenId) 
        external 
        tokenExists(tokenId) 
        onlyTokenOwner(tokenId) 
    {
        require(_guardians[tokenId].isActive, "SoulRecovery: no active guardian");
        
        delete _guardians[tokenId];
        
        emit GuardianSet(tokenId, msg.sender, address(0));
    }
    
    /**
     * @dev Установка guardian'а при вызове через SoulIdentity (SBT-REC-1)
     * @param tokenId идентификатор токена
     * @param guardian адрес guardian'а
     * @param owner владелец токена (должен совпадать с ownerOf(tokenId))
     */
    function setGuardianFor(uint256 tokenId, address guardian, address owner)
        external
        tokenExists(tokenId)
    {
        require(msg.sender == soulIdentity, "SoulRecovery: only SoulIdentity");
        require(soulboundCore.ownerOf(tokenId) == owner, "SoulRecovery: not token owner");
        require(guardian != address(0), "SoulRecovery: invalid guardian address");
        require(guardian != owner, "SoulRecovery: cannot be self guardian");
        require(guardian != soulboundCore.ownerOf(tokenId), "SoulRecovery: guardian cannot be owner");
        
        _guardians[tokenId] = GuardianInfo({
            guardian: guardian,
            setTimestamp: block.timestamp,
            isActive: true
        });
        
        emit GuardianSet(tokenId, owner, guardian);
    }
    
    /**
     * @dev Удаление guardian'а при вызове через SoulIdentity (SBT-REC-1)
     */
    function removeGuardianFor(uint256 tokenId, address owner)
        external
        tokenExists(tokenId)
    {
        require(msg.sender == soulIdentity, "SoulRecovery: only SoulIdentity");
        require(soulboundCore.ownerOf(tokenId) == owner, "SoulRecovery: not token owner");
        require(_guardians[tokenId].isActive, "SoulRecovery: no active guardian");
        
        delete _guardians[tokenId];
        
        emit GuardianSet(tokenId, owner, address(0));
    }
    
    /**
     * @dev Инициация процесса восстановления
     * @param tokenId идентификатор токена
     * @param newOwner новый владелец токена
     */
    function initiateRecovery(uint256 tokenId, address newOwner) 
        external 
        tokenExists(tokenId) 
        onlyGuardian(tokenId) 
    {
        require(newOwner != address(0), "SoulRecovery: invalid new owner");
        require(newOwner != soulboundCore.ownerOf(tokenId), "SoulRecovery: same owner");
        require(!_recoveries[tokenId].isActive, "SoulRecovery: recovery already active");
        
        // Проверяем, что guardian был установлен достаточно давно
        require(
            block.timestamp >= _guardians[tokenId].setTimestamp + GUARDIAN_DELAY,
            "SoulRecovery: guardian delay not passed"
        );
        
        _recoveries[tokenId] = RecoveryInfo({
            newOwner: newOwner,
            guardian: msg.sender,
            initiatedAt: block.timestamp,
            isActive: true
        });
        
        emit RecoveryInitiated(tokenId, soulboundCore.ownerOf(tokenId), newOwner, msg.sender);
    }
    
    /**
     * @dev Инициация восстановления при вызове через SoulIdentity (SBT-REC-1)
     */
    function initiateRecoveryFor(uint256 tokenId, address newOwner, address guardian)
        external
        tokenExists(tokenId)
    {
        require(msg.sender == soulIdentity, "SoulRecovery: only SoulIdentity");
        require(_guardians[tokenId].guardian == guardian && _guardians[tokenId].isActive, "SoulRecovery: not authorized guardian");
        require(newOwner != address(0), "SoulRecovery: invalid new owner");
        require(newOwner != soulboundCore.ownerOf(tokenId), "SoulRecovery: same owner");
        require(!_recoveries[tokenId].isActive, "SoulRecovery: recovery already active");
        require(
            block.timestamp >= _guardians[tokenId].setTimestamp + GUARDIAN_DELAY,
            "SoulRecovery: guardian delay not passed"
        );
        
        _recoveries[tokenId] = RecoveryInfo({
            newOwner: newOwner,
            guardian: guardian,
            initiatedAt: block.timestamp,
            isActive: true
        });
        
        emit RecoveryInitiated(tokenId, soulboundCore.ownerOf(tokenId), newOwner, guardian);
    }
    
    /**
     * @dev Подтверждение восстановления при вызове через SoulIdentity (SBT-REC-1)
     */
    function confirmRecoveryFor(uint256 tokenId, address guardian)
        external
        tokenExists(tokenId)
    {
        require(msg.sender == soulIdentity, "SoulRecovery: only SoulIdentity");
        RecoveryInfo storage recovery = _recoveries[tokenId];
        require(recovery.isActive, "SoulRecovery: no active recovery");
        require(recovery.guardian == guardian, "SoulRecovery: not recovery guardian");
        require(
            block.timestamp >= recovery.initiatedAt + RECOVERY_DELAY,
            "SoulRecovery: recovery delay not passed"
        );
        
        address newOwner = recovery.newOwner;
        soulboundCore.executeRecovery(tokenId, newOwner);
        delete _recoveries[tokenId];
        
        emit RecoveryCompleted(tokenId, newOwner);
    }
    
    /**
     * @dev Подтверждение восстановления (после задержки)
     * @param tokenId идентификатор токена
     */
    function confirmRecovery(uint256 tokenId) 
        external 
        tokenExists(tokenId) 
        onlyGuardian(tokenId) 
    {
        RecoveryInfo storage recovery = _recoveries[tokenId];
        require(recovery.isActive, "SoulRecovery: no active recovery");
        require(recovery.guardian == msg.sender, "SoulRecovery: not recovery guardian");
        require(
            block.timestamp >= recovery.initiatedAt + RECOVERY_DELAY,
            "SoulRecovery: recovery delay not passed"
        );
        
        // Сохраняем данные для восстановления
        address newOwner = recovery.newOwner;
        
        // Выполняем фактическое восстановление через SoulboundCore
        soulboundCore.executeRecovery(tokenId, newOwner);
        
        // Очищаем процесс восстановления ПОСЛЕ успешного восстановления
        delete _recoveries[tokenId];
        
        emit RecoveryCompleted(tokenId, newOwner);
    }
    
    /**
     * @dev Отмена процесса восстановления (владельцем токена)
     * @param tokenId идентификатор токена
     */
    function cancelRecovery(uint256 tokenId) 
        external 
        tokenExists(tokenId) 
        onlyTokenOwner(tokenId) 
    {
        require(_recoveries[tokenId].isActive, "SoulRecovery: no active recovery");
        
        delete _recoveries[tokenId];
        
        emit RecoveryCancelled(tokenId, msg.sender);
    }
    
    // === VIEW FUNCTIONS ===
    
    /**
     * @dev Получить информацию о guardian'е
     * @param tokenId идентификатор токена
     * @return GuardianInfo структура с информацией о guardian'е
     */
    function getGuardianInfo(uint256 tokenId) external view tokenExists(tokenId) returns (GuardianInfo memory) {
        return _guardians[tokenId];
    }
    
    /**
     * @dev Получить адрес guardian'а
     * @param tokenId идентификатор токена
     * @return адрес guardian'а или address(0) если не установлен
     */
    function getGuardian(uint256 tokenId) external view returns (address) {
        return _guardians[tokenId].isActive ? _guardians[tokenId].guardian : address(0);
    }
    
    /**
     * @dev Проверить, есть ли активный guardian
     * @param tokenId идентификатор токена
     * @return true если есть активный guardian
     */
    function hasActiveGuardian(uint256 tokenId) external view returns (bool) {
        return _guardians[tokenId].isActive;
    }
    
    /**
     * @dev Получить информацию о процессе восстановления
     * @param tokenId идентификатор токена
     * @return RecoveryInfo структура с информацией о восстановлении
     */
    function getRecoveryInfo(uint256 tokenId) external view tokenExists(tokenId) returns (RecoveryInfo memory) {
        return _recoveries[tokenId];
    }
    
    /**
     * @dev Проверить, активен ли процесс восстановления
     * @param tokenId идентификатор токена
     * @return true если процесс восстановления активен
     */
    function isRecoveryActive(uint256 tokenId) external view returns (bool) {
        return _recoveries[tokenId].isActive;
    }
    
    /**
     * @dev Проверить, можно ли подтвердить восстановление
     * @param tokenId идентификатор токена
     * @return true если восстановление можно подтвердить
     */
    function canConfirmRecovery(uint256 tokenId) external view returns (bool) {
        RecoveryInfo memory recovery = _recoveries[tokenId];
        return recovery.isActive && 
               block.timestamp >= recovery.initiatedAt + RECOVERY_DELAY;
    }
    
    /**
     * @dev Получить время до возможности подтверждения восстановления
     * @param tokenId идентификатор токена
     * @return секунды до возможности подтверждения (0 если уже можно)
     */
    function getRecoveryTimeLeft(uint256 tokenId) external view returns (uint256) {
        RecoveryInfo memory recovery = _recoveries[tokenId];
        if (!recovery.isActive) {
            return 0;
        }
        
        uint256 confirmTime = recovery.initiatedAt + RECOVERY_DELAY;
        if (block.timestamp >= confirmTime) {
            return 0;
        }
        
        return confirmTime - block.timestamp;
    }
}
