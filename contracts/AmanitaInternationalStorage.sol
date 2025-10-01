// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title AmanitaInternationalStorage
 * @author Amanita Decentralization Team
 * @dev Персистентное хранилище для мультиязычных переводов
 * @notice Хранит только данные, никакой бизнес-логики
 * 
 * Архитектура:
 * - Этот контракт хранит ТОЛЬКО данные (маппинги CID)
 * - Бизнес-логика находится в Logic контрактах
 * - Proxy делегирует вызовы в Logic, который работает с этим Storage
 * 
 * Наращиваемость:
 * - При необходимости новых данных создается StorageV2
 * - StorageV1.nextStorage указывает на StorageV2
 * - Цепочка может расти бесконечно
 */
contract AmanitaInternationalStorage is AccessControl {
    
    // === РОЛИ ===
    
    /// @notice Роль для Proxy контракта, который может изменять данные
    /// @dev При delegatecall из Proxy в Logic, затем в Storage: msg.sender = Proxy!
    bytes32 public constant PROXY_ROLE = keccak256("PROXY_ROLE");
    
    /// @notice Роль для управления цепочкой Storage контрактов
    bytes32 public constant STORAGE_ADMIN_ROLE = keccak256("STORAGE_ADMIN_ROLE");
    
    // === ВЕРСИОНИРОВАНИЕ STORAGE ===
    
    /// @notice Версия Storage контракта
    uint256 public constant STORAGE_VERSION = 1;
    
    /// @notice Ссылка на следующий Storage в цепочке (для расширения)
    /// @dev address(0) если это последний Storage в цепочке
    address public nextStorage;
    
    /// @notice Массив всех Storage контрактов в цепочке
    /// @dev Используется для итерации по всей цепочке
    address[] public storageChain;
    
    // === ОСНОВНЫЕ ДАННЫЕ (V1) ===
    
    /// @notice Маппинг простых полей: "class.field" → IPFS CID
    /// @dev Один CID содержит переводы для всех языков
    /// @dev Примеры: "product.forms" → "QmXxX..."
    mapping(string => string) public simpleFieldCIDs;
    
    /// @notice Маппинг сложных полей: "class.language" → IPFS CID
    /// @dev Один CID содержит все поля класса на одном языке
    /// @dev Примеры: "Description.ru" → "QmYyY..."
    mapping(string => string) public complexFieldCIDs;
    
    /// @notice Массив всех зарегистрированных простых полей
    string[] private simpleFieldKeys;
    
    /// @notice Маппинг для быстрой проверки существования простого поля
    mapping(string => bool) private simpleFieldExists;
    
    /// @notice Маппинг класса к массиву языков для сложных полей
    mapping(string => string[]) private complexFieldLanguages;
    
    /// @notice Маппинг для быстрой проверки существования сложного поля
    mapping(string => bool) private complexFieldExists;
    
    /// @notice Массив всех зарегистрированных классов со сложными полями
    string[] private complexFieldClasses;
    
    /// @notice Маппинг для проверки существования класса
    mapping(string => bool) private classExists;
    
    // === СОБЫТИЯ ===
    
    /// @notice Событие добавления нового Storage в цепочку
    event NextStorageSet(address indexed nextStorage, uint256 chainLength);
    
    /// @notice Событие предоставления доступа Proxy контракту
    event ProxyContractAuthorized(address indexed proxyContract, address indexed authorizer);
    
    // === КОНСТРУКТОР ===
    
    /**
     * @dev Инициализация Storage контракта
     * @param admin Адрес администратора
     */
    constructor(address admin) {
        require(admin != address(0), "AmanitaInternationalStorage: zero admin address");
        
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(STORAGE_ADMIN_ROLE, admin);
        
        // Добавляем себя в цепочку
        storageChain.push(address(this));
    }
    
    // === УПРАВЛЕНИЕ ЦЕПОЧКОЙ STORAGE ===
    
    /**
     * @notice Установить следующий Storage в цепочке
     * @dev Вызывается когда нужны новые данные (например, для модерации)
     * @param _nextStorage Адрес нового Storage контракта
     */
    function setNextStorage(address _nextStorage) 
        external 
        onlyRole(STORAGE_ADMIN_ROLE) 
    {
        require(_nextStorage != address(0), "AmanitaInternationalStorage: zero address");
        require(nextStorage == address(0), "AmanitaInternationalStorage: next storage already set");
        
        nextStorage = _nextStorage;
        storageChain.push(_nextStorage);
        
        emit NextStorageSet(_nextStorage, storageChain.length);
    }
    
    /**
     * @notice Получить всю цепочку Storage контрактов
     * @return Массив адресов всех Storage контрактов
     */
    function getStorageChain() external view returns (address[] memory) {
        return storageChain;
    }
    
    /**
     * @notice Авторизовать Proxy контракт для работы с данными
     * @dev При delegatecall msg.sender в Storage = Proxy адрес!
     * @param proxyContract Адрес Proxy контракта
     */
    function authorizeProxyContract(address proxyContract) 
        external 
        onlyRole(DEFAULT_ADMIN_ROLE) 
    {
        require(proxyContract != address(0), "AmanitaInternationalStorage: zero proxy address");
        
        _grantRole(PROXY_ROLE, proxyContract);
        
        emit ProxyContractAuthorized(proxyContract, msg.sender);
    }
    
    // === ФУНКЦИИ ДЛЯ ПРОСТЫХ ПОЛЕЙ (только для LOGIC_ROLE) ===
    
    /**
     * @notice Установить CID для простого поля
     * @dev Только Proxy контракт может вызывать (при delegatecall msg.sender = Proxy)
     */
    function setSimpleFieldCID(
        string memory fieldKey,
        string memory cid
    ) external onlyRole(PROXY_ROLE) {
        if (!simpleFieldExists[fieldKey]) {
            simpleFieldKeys.push(fieldKey);
            simpleFieldExists[fieldKey] = true;
        }
        simpleFieldCIDs[fieldKey] = cid;
    }
    
    /**
     * @notice Получить CID для простого поля
     * @dev Публичная функция для чтения
     */
    function getSimpleFieldCID(string memory fieldKey) 
        external 
        view 
        returns (string memory) 
    {
        return simpleFieldCIDs[fieldKey];
    }
    
    /**
     * @notice Удалить простое поле
     * @dev Только Proxy контракт может вызывать (при delegatecall msg.sender = Proxy)
     */
    function removeSimpleField(string memory fieldKey) 
        external 
        onlyRole(PROXY_ROLE) 
    {
        delete simpleFieldCIDs[fieldKey];
        simpleFieldExists[fieldKey] = false;
    }
    
    /**
     * @notice Получить список всех простых полей
     */
    function getAllSimpleFields() external view returns (string[] memory) {
        return simpleFieldKeys;
    }
    
    /**
     * @notice Проверить существование простого поля
     */
    function simpleFieldExist(string memory fieldKey) 
        external 
        view 
        returns (bool) 
    {
        return simpleFieldExists[fieldKey];
    }
    
    // === ФУНКЦИИ ДЛЯ СЛОЖНЫХ ПОЛЕЙ (только для LOGIC_ROLE) ===
    
    /**
     * @notice Установить CID для сложного поля
     * @dev Только Proxy контракт может вызывать (при delegatecall msg.sender = Proxy)
     */
    function setComplexFieldCID(
        string memory className,
        string memory language,
        string memory cid
    ) external onlyRole(PROXY_ROLE) {
        string memory compositeKey = string(abi.encodePacked(className, ".", language));
        
        if (!classExists[className]) {
            complexFieldClasses.push(className);
            classExists[className] = true;
        }
        
        if (!complexFieldExists[compositeKey]) {
            complexFieldLanguages[className].push(language);
            complexFieldExists[compositeKey] = true;
        }
        
        complexFieldCIDs[compositeKey] = cid;
    }
    
    /**
     * @notice Получить CID для сложного поля
     * @dev Публичная функция для чтения
     */
    function getComplexFieldCID(
        string memory className,
        string memory language
    ) external view returns (string memory) {
        string memory compositeKey = string(abi.encodePacked(className, ".", language));
        return complexFieldCIDs[compositeKey];
    }
    
    /**
     * @notice Удалить сложное поле
     * @dev Только Proxy контракт может вызывать (при delegatecall msg.sender = Proxy)
     */
    function removeComplexField(
        string memory className,
        string memory language
    ) external onlyRole(PROXY_ROLE) {
        string memory compositeKey = string(abi.encodePacked(className, ".", language));
        delete complexFieldCIDs[compositeKey];
        complexFieldExists[compositeKey] = false;
    }
    
    /**
     * @notice Получить все языки для класса
     */
    function getComplexFieldLanguages(string memory className) 
        external 
        view 
        returns (string[] memory) 
    {
        return complexFieldLanguages[className];
    }
    
    /**
     * @notice Получить список всех классов
     */
    function getAllComplexClasses() external view returns (string[] memory) {
        return complexFieldClasses;
    }
    
    /**
     * @notice Проверить существование сложного поля
     */
    function complexFieldExist(
        string memory className,
        string memory language
    ) external view returns (bool) {
        string memory compositeKey = string(abi.encodePacked(className, ".", language));
        return complexFieldExists[compositeKey];
    }
    
    /**
     * @notice Получить статистику
     */
    function getStatistics() external view returns (
        uint256 totalSimpleFields,
        uint256 totalComplexClasses
    ) {
        return (simpleFieldKeys.length, complexFieldClasses.length);
    }
    
    /**
     * @notice Получить информацию о версии Storage
     */
    function getStorageVersion() external pure returns (uint256) {
        return STORAGE_VERSION;
    }
}

