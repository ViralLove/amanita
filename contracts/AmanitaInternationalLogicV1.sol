// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./AmanitaInternationalStorage.sol";

/**
 * @title AmanitaInternationalLogicV1
 * @author Amanita Decentralization Team
 * @dev Бизнес-логика для управления мультиязычными переводами
 * @notice Содержит ТОЛЬКО логику, НЕ хранит данные и НЕ проверяет роли
 * 
 * Архитектура:
 * - Logic контракт работает со Storage контрактом
 * - Proxy делегирует вызовы в этот Logic контракт
 * - AccessControl роли проверяются в Proxy через delegatecall контекст
 * - При обновлении меняется только Logic, Storage остается
 * 
 * Версия: 1.0.1
 * - Базовые операции: set/get/remove/batch
 * - Управление простыми и сложными полями
 * - Интеграция со Storage через LOGIC_ROLE
 * - Security: ReentrancyGuard добавлен (v1.0.1)
 */
contract AmanitaInternationalLogicV1 is ReentrancyGuard {
    
    // === ВЕРСИОНИРОВАНИЕ ===
    
    /// @notice Версия Logic контракта
    string public constant VERSION = "1.0.1";
    uint256 public constant LOGIC_VERSION = 1;
    
    // === РОЛИ (для совместимости с Proxy) ===
    
    /// @notice Роль администратора для управления переводами
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    
    // === CUSTOM ERRORS ===
    // Custom errors для экономии gas и улучшения читаемости
    
    /// @notice Ошибка: field key пустой
    error EmptyFieldKey();
    
    /// @notice Ошибка: CID пустой
    error EmptyCID();
    
    /// @notice Ошибка: class name пустой
    error EmptyClassName();
    
    /// @notice Ошибка: language код пустой
    error EmptyLanguage();
    
    /// @notice Ошибка: длины массивов не совпадают
    error ArrayLengthMismatch();
    
    /// @notice Ошибка: поле не существует
    error FieldDoesNotExist();
    
    /// @notice Ошибка: передан нулевой адрес
    error ZeroAddress();
    
    // === ССЫЛКИ НА STORAGE ===
    
    /// @notice Адрес Storage контракта
    /// @dev Immutable - не занимает storage slot, вшит в bytecode
    address public immutable storageContract;
    
    // === СОБЫТИЯ ===
    
    event SimpleFieldRegistered(
        string indexed fieldKey,
        string cid,
        address indexed updater
    );
    
    event ComplexFieldRegistered(
        string indexed className,
        string indexed language,
        string cid,
        address indexed updater
    );
    
    event SimpleFieldRemoved(
        string indexed fieldKey,
        address indexed remover
    );
    
    event ComplexFieldRemoved(
        string indexed className,
        string indexed language,
        address indexed remover
    );
    
    // === КОНСТРУКТОР ===
    
    /**
     * @dev Инициализация Logic контракта
     * @param _storageContract Адрес Storage контракта
     * @notice Admin не нужен - роли проверяются в Proxy через delegatecall
     */
    constructor(address _storageContract) {
        require(_storageContract != address(0), "AmanitaInternationalLogic: zero storage address");
        
        storageContract = _storageContract;
    }
    
    // === VALIDATION HELPERS ===
    // Функции валидации с custom errors (для будущего использования)
    
    /**
     * @dev Проверка ненулевого адреса
     * @param addr адрес для проверки
     */
    function _requireNonZero(address addr) internal pure {
        if (addr == address(0)) revert ZeroAddress();
    }
    
    /**
     * @dev Проверка непустой строки
     * @param str строка для проверки
     */
    function _requireNonEmptyString(string memory str) internal pure {
        if (bytes(str).length == 0) revert EmptyFieldKey();
    }
    
    // === ФУНКЦИИ ДЛЯ ПРОСТЫХ ПОЛЕЙ ===
    
    /**
     * @notice Установить или обновить CID для простого поля
     * @param fieldKey Ключ поля (например, "product.forms")
     * @param cid IPFS CID с переводами для всех языков
     * @dev Роль ADMIN_ROLE проверяется в Proxy через delegatecall
     */
    function setSimpleFieldCID(
        string calldata fieldKey,
        string calldata cid
    ) external nonReentrant {
        require(bytes(fieldKey).length > 0, "AmanitaInternationalLogic: empty field key");
        require(bytes(cid).length > 0, "AmanitaInternationalLogic: empty CID");
        
        AmanitaInternationalStorage(storageContract).setSimpleFieldCID(fieldKey, cid);
        
        emit SimpleFieldRegistered(fieldKey, cid, msg.sender);
    }
    
    /**
     * @notice Получить CID для простого поля
     * @param fieldKey Ключ поля
     * @return CID строка
     */
    function getSimpleFieldCID(
        string calldata fieldKey
    ) external view returns (string memory) {
        return AmanitaInternationalStorage(storageContract).getSimpleFieldCID(fieldKey);
    }
    
    /**
     * @notice Получить список всех простых полей
     * @return Массив ключей полей
     */
    function getAllSimpleFields() external view returns (string[] memory) {
        return AmanitaInternationalStorage(storageContract).getAllSimpleFields();
    }
    
    /**
     * @notice Проверить существование простого поля
     * @param fieldKey Ключ поля
     * @return true если поле зарегистрировано
     */
    function simpleFieldExist(string calldata fieldKey) external view returns (bool) {
        return AmanitaInternationalStorage(storageContract).simpleFieldExist(fieldKey);
    }
    
    /**
     * @notice Удалить простое поле
     * @param fieldKey Ключ поля
     * @dev Роль ADMIN_ROLE проверяется в Proxy через delegatecall
     */
    function removeSimpleField(
        string calldata fieldKey
    ) external nonReentrant {
        require(
            AmanitaInternationalStorage(storageContract).simpleFieldExist(fieldKey),
            "AmanitaInternationalLogic: field does not exist"
        );
        
        AmanitaInternationalStorage(storageContract).removeSimpleField(fieldKey);
        
        emit SimpleFieldRemoved(fieldKey, msg.sender);
    }
    
    // === ФУНКЦИИ ДЛЯ СЛОЖНЫХ ПОЛЕЙ ===
    
    /**
     * @notice Установить или обновить CID для сложного поля
     * @param className Имя класса (например, "Description")
     * @param language Код языка (например, "en")
     * @param cid IPFS CID с переводами
     * @dev Роль ADMIN_ROLE проверяется в Proxy через delegatecall
     */
    function setComplexFieldCID(
        string calldata className,
        string calldata language,
        string calldata cid
    ) external nonReentrant {
        require(bytes(className).length > 0, "AmanitaInternationalLogic: empty class name");
        require(bytes(language).length > 0, "AmanitaInternationalLogic: empty language");
        require(bytes(cid).length > 0, "AmanitaInternationalLogic: empty CID");
        
        AmanitaInternationalStorage(storageContract).setComplexFieldCID(className, language, cid);
        
        emit ComplexFieldRegistered(className, language, cid, msg.sender);
    }
    
    /**
     * @notice Получить CID для сложного поля
     * @param className Имя класса
     * @param language Код языка
     * @return CID строка
     */
    function getComplexFieldCID(
        string calldata className,
        string calldata language
    ) external view returns (string memory) {
        return AmanitaInternationalStorage(storageContract).getComplexFieldCID(className, language);
    }
    
    /**
     * @notice Получить все языки для класса
     * @param className Имя класса
     * @return Массив языковых кодов
     */
    function getComplexFieldLanguages(
        string calldata className
    ) external view returns (string[] memory) {
        return AmanitaInternationalStorage(storageContract).getComplexFieldLanguages(className);
    }
    
    /**
     * @notice Получить список всех классов
     * @return Массив имен классов
     */
    function getAllComplexClasses() external view returns (string[] memory) {
        return AmanitaInternationalStorage(storageContract).getAllComplexClasses();
    }
    
    /**
     * @notice Проверить существование сложного поля
     * @param className Имя класса
     * @param language Код языка
     * @return true если поле зарегистрировано
     */
    function complexFieldExist(
        string calldata className,
        string calldata language
    ) external view returns (bool) {
        return AmanitaInternationalStorage(storageContract).complexFieldExist(className, language);
    }
    
    /**
     * @notice Удалить сложное поле
     * @param className Имя класса
     * @param language Код языка
     * @dev Роль ADMIN_ROLE проверяется в Proxy через delegatecall
     */
    function removeComplexField(
        string calldata className,
        string calldata language
    ) external nonReentrant {
        require(
            AmanitaInternationalStorage(storageContract).complexFieldExist(className, language),
            "AmanitaInternationalLogic: field does not exist"
        );
        
        AmanitaInternationalStorage(storageContract).removeComplexField(className, language);
        
        emit ComplexFieldRemoved(className, language, msg.sender);
    }
    
    // === BATCH ОПЕРАЦИИ ===
    
    /**
     * @notice Batch установка простых полей
     * @param fieldKeys Массив ключей полей
     * @param cids Массив соответствующих CID
     * @dev Роль ADMIN_ROLE проверяется в Proxy через delegatecall
     */
    function batchSetSimpleFields(
        string[] memory fieldKeys,
        string[] memory cids
    ) external nonReentrant {
        require(fieldKeys.length == cids.length, "AmanitaInternationalLogic: arrays length mismatch");
        require(fieldKeys.length > 0, "AmanitaInternationalLogic: empty arrays");
        
        AmanitaInternationalStorage storage_ = AmanitaInternationalStorage(storageContract);
        
        // Газовая оптимизация: unchecked безопасен для инкремента счетчика цикла
        for (uint256 i = 0; i < fieldKeys.length;) {
            require(bytes(fieldKeys[i]).length > 0, "AmanitaInternationalLogic: empty field key");
            require(bytes(cids[i]).length > 0, "AmanitaInternationalLogic: empty CID");
            
            storage_.setSimpleFieldCID(fieldKeys[i], cids[i]);
            
            emit SimpleFieldRegistered(fieldKeys[i], cids[i], msg.sender);
            
            unchecked { ++i; }
        }
    }
    
    /**
     * @notice Batch установка сложных полей
     * @param classNames Массив имен классов
     * @param languages Массив языковых кодов
     * @param cids Массив соответствующих CID
     * @dev Роль ADMIN_ROLE проверяется в Proxy через delegatecall
     */
    function batchSetComplexFields(
        string[] memory classNames,
        string[] memory languages,
        string[] memory cids
    ) external nonReentrant {
        require(
            classNames.length == languages.length && languages.length == cids.length,
            "AmanitaInternationalLogic: arrays length mismatch"
        );
        require(classNames.length > 0, "AmanitaInternationalLogic: empty arrays");
        
        AmanitaInternationalStorage storage_ = AmanitaInternationalStorage(storageContract);
        
        // Газовая оптимизация: unchecked безопасен для инкремента счетчика цикла
        for (uint256 i = 0; i < classNames.length;) {
            require(bytes(classNames[i]).length > 0, "AmanitaInternationalLogic: empty class name");
            require(bytes(languages[i]).length > 0, "AmanitaInternationalLogic: empty language");
            require(bytes(cids[i]).length > 0, "AmanitaInternationalLogic: empty CID");
            
            storage_.setComplexFieldCID(classNames[i], languages[i], cids[i]);
            
            emit ComplexFieldRegistered(classNames[i], languages[i], cids[i], msg.sender);
            
            unchecked { ++i; }
        }
    }
    
    // === УТИЛИТЫ ===
    
    /**
     * @notice Получить общую статистику
     * @return totalSimpleFields Количество простых полей
     * @return totalComplexClasses Количество классов
     */
    function getStatistics() external view returns (
        uint256 totalSimpleFields,
        uint256 totalComplexClasses
    ) {
        return AmanitaInternationalStorage(storageContract).getStatistics();
    }
    
    /**
     * @notice Получить информацию о версии Logic контракта
     * @return version Semantic версия
     * @return logicVersion Числовая версия
     */
    function getVersionInfo() external pure returns (
        string memory version,
        uint256 logicVersion
    ) {
        return (VERSION, LOGIC_VERSION);
    }
    
    /**
     * @notice Получить адрес Storage контракта
     * @return Адрес текущего Storage
     */
    function getStorageAddress() external view returns (address) {
        return storageContract;
    }
}

