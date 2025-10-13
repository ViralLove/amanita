// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "./interfaces/ISpiralEngine.sol";

/**
 * @title AmanitaInternationalLogic
 * @author Amanita Decentralization Team
 * @dev Полная UUPS имплементация для AmanitaInternational
 * @notice Содержит ВСЕ state variables, роли, паузу и бизнес-логику
 * @notice Версия: 2.0.0 - UUPS Standard (миграция от 3-contract архитектуры)
 * 
 * Архитектура:
 * - Все state variables объявлены в Logic
 * - При delegatecall state физически хранится в Proxy
 * - Прямой доступ к переменным (без StorageSlot)
 * - Роли и пауза управляются через Logic
 * - Апгрейды через _authorizeUpgrade (UPGRADER_ROLE)
 * 
 * Миграция от 3-contract к UUPS:
 * - Storage + Logic + Proxy → Logic + Proxy
 * - Все маппинги из Storage консолидированы здесь
 * - ReentrancyGuard добавлен (M1)
 * - Custom errors добавлены (M1)
 * - Gas optimizations применены (M1)
 * 
 * @custom:security-contact security@amanita.com
 */
contract AmanitaInternationalLogic is 
    Initializable, 
    UUPSUpgradeable, 
    AccessControlUpgradeable,
    PausableUpgradeable,
    ReentrancyGuardUpgradeable
{
    // === КОНСТАНТЫ ===

    /// @notice Версия Logic контракта
    string public constant VERSION = "2.0.0";
    
    /// @notice Версия Logic для апгрейдов
    uint256 public constant LOGIC_VERSION = 2;

    // === РОЛИ ===

    /// @notice Роль для обновления контракта
    bytes32 public constant UPGRADER_ROLE = keccak256("UPGRADER_ROLE");
    
    /// @notice Роль администратора для управления переводами
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    
    /// @notice Роль продавца для управления переводами своих компонентов
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");

    // === CUSTOM ERRORS ===
    // Custom errors для экономии gas и улучшения читаемости (M1)

    /// @notice Ошибка: пустой ключ поля
    error EmptyFieldKey();

    /// @notice Ошибка: пустой CID
    error EmptyCID();

    /// @notice Ошибка: пустое имя класса
    error EmptyClassName();

    /// @notice Ошибка: пустой язык
    error EmptyLanguage();

    /// @notice Ошибка: несоответствие длины массивов
    error ArrayLengthMismatch();

    /// @notice Ошибка: поле не существует
    error FieldDoesNotExist();

    /// @notice Ошибка: нулевой адрес
    error ZeroAddress();
    
    /// @notice Ошибка: несанкционированный доступ к полю
    /// @param caller Адрес вызывающего
    /// @param fieldKey Ключ поля
    error UnauthorizedFieldAccess(address caller, string fieldKey);

    // === STATE VARIABLES ===
    // Консолидация из AmanitaInternationalStorage

    /// @notice Маппинг простых полей: "fieldKey" → IPFS CID
    /// @dev Один CID содержит переводы для всех языков
    /// @dev Примеры: "product.forms" → "QmXxX..."
    mapping(string => string) public simpleFieldCIDs;
    
    /// @notice Маппинг сложных полей: "className.language" → IPFS CID
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
    
    /// @notice Маппинг владельцев простых полей: "fieldKey" → owner address
    /// @dev Владелец может обновлять свои поля, admin может обновлять любые
    mapping(string => address) public simpleFieldOwner;
    
    /// @notice Маппинг владельцев сложных полей: "className.language" → owner address
    /// @dev Владелец может обновлять свои поля, admin может обновлять любые
    mapping(string => address) public complexFieldOwner;
    
    /// @notice Маппинг глобальных полей: "fieldKey" → isGlobal
    /// @dev Глобальные поля (features, forms) могут изменять только admin
    mapping(string => bool) public isGlobalField;
    
    /// @notice Адрес контракта SpiralEngine для проверки SELLER_ROLE
    /// @dev SpiralEngine = Single Source of Truth для управления ролями sellers
    /// @dev AmanitaInternational делегирует проверку SELLER_ROLE этому контракту
    /// @dev Обновлено в версии 2.1.0 для интеграции с SpiralEngine
    ISpiralEngine public spiralEngine;

    // === STORAGE GAP ===
    // Резерв для будущих переменных в апгрейдах
    // Уменьшено с 50 до 46 из-за добавления:
    // - 3 mappings (ownership: simpleFieldOwner, complexFieldOwner, isGlobalField)
    // - 1 interface reference (spiralEngine)
    uint256[46] private __gap;

    // === СОБЫТИЯ ===

    /// @notice Событие регистрации простого поля
    /// @param fieldKey Ключ поля
    /// @param cid IPFS CID с переводами
    /// @param updater Адрес обновившего
    event SimpleFieldRegistered(
        string indexed fieldKey,
        string cid,
        address indexed updater
    );

    /// @notice Событие регистрации сложного поля
    /// @param className Имя класса
    /// @param language Язык перевода
    /// @param cid IPFS CID с переводами
    /// @param updater Адрес обновившего
    event ComplexFieldRegistered(
        string indexed className,
        string indexed language,
        string cid,
        address indexed updater
    );
    
    /// @notice Событие установки глобального поля
    /// @param fieldKey Ключ поля
    /// @param isGlobal true если поле глобальное
    /// @param admin Адрес администратора
    event GlobalFieldSet(
        string indexed fieldKey,
        bool isGlobal,
        address indexed admin
    );
    
    /// @notice Событие обновления адреса SpiralEngine
    /// @param oldSpiralEngine Старый адрес контракта SpiralEngine
    /// @param newSpiralEngine Новый адрес контракта SpiralEngine
    /// @param admin Адрес администратора, выполнившего обновление
    event SpiralEngineUpdated(
        address indexed oldSpiralEngine,
        address indexed newSpiralEngine,
        address indexed admin
    );

    /// @notice Событие удаления простого поля
    /// @param fieldKey Ключ поля
    /// @param remover Адрес удалившего
    event SimpleFieldRemoved(
        string indexed fieldKey,
        address indexed remover
    );

    /// @notice Событие удаления сложного поля
    /// @param className Имя класса
    /// @param language Язык перевода
    /// @param remover Адрес удалившего
    event ComplexFieldRemoved(
        string indexed className,
        string indexed language,
        address indexed remover
    );

    // === МОДИФИКАТОРЫ ===

    /// @notice Проверка что поле существует
    modifier fieldExists(string calldata fieldKey) {
        if (!simpleFieldExists[fieldKey]) revert FieldDoesNotExist();
        _;
    }

    /// @notice Проверка что сложное поле существует
    modifier complexExists(string calldata className, string calldata language) {
        string memory key = string(abi.encodePacked(className, ".", language));
        if (!complexFieldExists[key]) revert FieldDoesNotExist();
        _;
    }

    // === ИНИЦИАЛИЗАЦИЯ ===

    /// @notice Инициализация контракта с ролями и интеграцией SpiralEngine
    /// @param admin Адрес администратора
    /// @param _spiralEngine Адрес контракта SpiralEngine для проверки SELLER_ROLE
    /// @dev Заменяет constructor для upgradeable контрактов
    /// @dev SpiralEngine = Single Source of Truth для управления ролями sellers
    function initialize(address admin, address _spiralEngine) public initializer {
        // Проверка входных параметров
        if (admin == address(0)) revert ZeroAddress();
        if (_spiralEngine == address(0)) revert ZeroAddress();

        // Инициализация модулей OpenZeppelin
        __AccessControl_init();
        __UUPSUpgradeable_init();
        __Pausable_init();
        __ReentrancyGuard_init();

        // Настройка ролей
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        
        // Интеграция с SpiralEngine
        spiralEngine = ISpiralEngine(_spiralEngine);
    }

    // === UUPS UPGRADE ===

    /// @notice Авторизация апгрейда контракта
    /// @param newImplementation Адрес новой имплементации
    /// @dev Только UPGRADER_ROLE может обновлять контракт
    function _authorizeUpgrade(
        address newImplementation
    ) internal view override onlyRole(UPGRADER_ROLE) {
        // Дополнительные проверки можно добавить здесь
        require(newImplementation != address(0), "Invalid implementation");
    }

    // === PAUSE FUNCTIONS ===

    /// @notice Пауза контракта
    /// @dev Только ADMIN_ROLE может ставить на паузу
    function pause() external onlyRole(ADMIN_ROLE) nonReentrant {
        _pause();
    }

    /// @notice Снятие паузы контракта
    /// @dev Только ADMIN_ROLE может снимать с паузы
    function unpause() external onlyRole(ADMIN_ROLE) nonReentrant {
        _unpause();
    }
    
    // === HELPER FUNCTIONS ===
    
    /**
     * @notice Проверяет, имеет ли account SELLER_ROLE
     * @dev Проверяет роль в ДВУХ местах для гибкости:
     *      1. Локально в этом контракте (для обратной совместимости или manual grants)
     *      2. В контракте SpiralEngine (основной источник истины)
     * 
     * Архитектурный принцип:
     * - SpiralEngine = Single Source of Truth для управления sellers
     * - AmanitaInternational делегирует проверку SELLER_ROLE
     * - Обратная совместимость с локальными ролями сохранена
     * 
     * @param account Адрес для проверки
     * @return bool true если account имеет SELLER_ROLE в любом из контрактов
     * 
     * @custom:security try-catch для устойчивости к ошибкам SpiralEngine
     * @custom:gas-optimization Проверка локальной роли первой (дешевле)
     */
    function _hasSellerRole(address account) internal view returns (bool) {
        // Проверка 1: Локальная роль (для обратной совместимости или manual grants)
        if (hasRole(SELLER_ROLE, account)) {
            return true;
        }
        
        // Проверка 2: Роль в SpiralEngine (основной источник истины)
        if (address(spiralEngine) != address(0)) {
            try spiralEngine.hasRole(spiralEngine.SELLER_ROLE(), account) returns (bool hasSpiralRole) {
                return hasSpiralRole;
            } catch {
                // Если SpiralEngine недоступен или возникла ошибка, возвращаем false
                // Это безопасное поведение: в случае проблем доступ запрещается
                return false;
            }
        }
        
        return false;
    }

    // === SIMPLE FIELDS FUNCTIONS ===

    /// @notice Установка CID для простого поля
    /// @param fieldKey Ключ поля (например: "product.forms")
    /// @param cid IPFS CID с мультиязычными переводами
    /// @dev Права доступа:
    ///      - ADMIN_ROLE: может устанавливать любые поля
    ///      - SELLER_ROLE: может создавать новые поля (становится owner)
    ///      - Owner поля: может обновлять свои поля
    ///      - Глобальные поля (isGlobalField=true): только ADMIN_ROLE
    /// @dev Gas optimization: calldata вместо memory (M1)
    function setSimpleFieldCID(
        string calldata fieldKey,
        string calldata cid
    ) external whenNotPaused nonReentrant {
        // Валидация входных данных
        if (bytes(fieldKey).length == 0) revert EmptyFieldKey();
        if (bytes(cid).length == 0) revert EmptyCID();
        
        address owner = simpleFieldOwner[fieldKey];
        bool isGlobal = isGlobalField[fieldKey];
        
        // Проверка прав доступа
        if (owner == address(0)) {
            // НОВОЕ ПОЛЕ - может создать ADMIN или SELLER
            // ✅ Интеграция с SpiralEngine: _hasSellerRole() проверяет роль в SpiralEngine
            if (!hasRole(ADMIN_ROLE, msg.sender) && !_hasSellerRole(msg.sender)) {
                revert UnauthorizedFieldAccess(msg.sender, fieldKey);
            }
            
            // Запоминаем владельца
            simpleFieldOwner[fieldKey] = msg.sender;
            simpleFieldExists[fieldKey] = true;
            simpleFieldKeys.push(fieldKey);
            
        } else {
            // СУЩЕСТВУЮЩЕЕ ПОЛЕ
            
            // Глобальные поля - только ADMIN
            if (isGlobal) {
                if (!hasRole(ADMIN_ROLE, msg.sender)) {
                    revert UnauthorizedFieldAccess(msg.sender, fieldKey);
                }
            } else {
                // Обычные поля - owner или ADMIN
                if (owner != msg.sender && !hasRole(ADMIN_ROLE, msg.sender)) {
                    revert UnauthorizedFieldAccess(msg.sender, fieldKey);
                }
            }
        }

        // Сохраняем CID
        simpleFieldCIDs[fieldKey] = cid;

        emit SimpleFieldRegistered(fieldKey, cid, msg.sender);
    }

    /// @notice Получение CID простого поля
    /// @param fieldKey Ключ поля
    /// @return IPFS CID
    /// @dev Gas optimization: calldata вместо memory (M1)
    function getSimpleFieldCID(
        string calldata fieldKey
    ) external view returns (string memory) {
        return simpleFieldCIDs[fieldKey];
    }

    /// @notice Проверка существования простого поля
    /// @param fieldKey Ключ поля
    /// @return true если поле существует
    /// @dev Gas optimization: calldata вместо memory (M1)
    function simpleFieldExist(
        string calldata fieldKey
    ) external view returns (bool) {
        return simpleFieldExists[fieldKey];
    }

    /// @notice Удаление простого поля
    /// @param fieldKey Ключ поля
    /// @dev Только ADMIN_ROLE может удалять поля
    /// @dev Gas optimization: calldata вместо memory (M1)
    function removeSimpleField(
        string calldata fieldKey
    ) external onlyRole(ADMIN_ROLE) whenNotPaused nonReentrant fieldExists(fieldKey) {
        // Удаляем маркер существования
        simpleFieldExists[fieldKey] = false;
        
        // Удаляем CID
        delete simpleFieldCIDs[fieldKey];

        // Примечание: не удаляем из массива simpleFieldKeys для экономии gas
        // Массив используется только для итерации, пустые элементы можно пропускать

        emit SimpleFieldRemoved(fieldKey, msg.sender);
    }

    /// @notice Batch установка простых полей
    /// @param fieldKeys Массив ключей полей
    /// @param cids Массив соответствующих CID
    /// @dev Только ADMIN_ROLE может устанавливать переводы
    /// @dev Gas optimization: unchecked для инкремента (M1)
    function batchSetSimpleFields(
        string[] memory fieldKeys,
        string[] memory cids
    ) external onlyRole(ADMIN_ROLE) whenNotPaused nonReentrant {
        // Валидация длины массивов
        if (fieldKeys.length != cids.length) revert ArrayLengthMismatch();
        if (fieldKeys.length == 0) revert EmptyFieldKey();

        // Gas optimization: unchecked безопасен для инкремента счетчика цикла (M1)
        for (uint256 i = 0; i < fieldKeys.length;) {
            // Валидация каждого элемента
            if (bytes(fieldKeys[i]).length == 0) revert EmptyFieldKey();
            if (bytes(cids[i]).length == 0) revert EmptyCID();

            // Если поле новое - добавляем в массив
            if (!simpleFieldExists[fieldKeys[i]]) {
                simpleFieldKeys.push(fieldKeys[i]);
                simpleFieldExists[fieldKeys[i]] = true;
            }

            // Сохраняем CID
            simpleFieldCIDs[fieldKeys[i]] = cids[i];

            emit SimpleFieldRegistered(fieldKeys[i], cids[i], msg.sender);

            unchecked { ++i; }
        }
    }

    /// @notice Получение всех простых полей
    /// @return Массив всех зарегистрированных ключей полей
    function getAllSimpleFields() external view returns (string[] memory) {
        return simpleFieldKeys;
    }

    // === COMPLEX FIELDS FUNCTIONS ===

    /// @notice Установка CID для сложного поля
    /// @param className Имя класса (например: "Description")
    /// @param language Код языка (например: "ru")
    /// @param cid IPFS CID с переводами этого класса на этом языке
    /// @dev Права доступа:
    ///      - ADMIN_ROLE: может устанавливать любые поля
    ///      - SELLER_ROLE: может создавать новые поля (становится owner)
    ///      - Owner поля: может обновлять свои поля
    ///      - Глобальные поля (isGlobalField=true): только ADMIN_ROLE
    /// @dev Gas optimization: calldata вместо memory (M1)
    function setComplexFieldCID(
        string calldata className,
        string calldata language,
        string calldata cid
    ) external whenNotPaused nonReentrant {
        // Валидация входных данных
        if (bytes(className).length == 0) revert EmptyClassName();
        if (bytes(language).length == 0) revert EmptyLanguage();
        if (bytes(cid).length == 0) revert EmptyCID();

        // Создаем составной ключ
        string memory key = string(abi.encodePacked(className, ".", language));
        
        address owner = complexFieldOwner[key];
        bool isGlobal = isGlobalField[key];
        
        // Проверка прав доступа
        if (owner == address(0)) {
            // НОВОЕ ПОЛЕ - может создать ADMIN или SELLER
            // ✅ Интеграция с SpiralEngine: _hasSellerRole() проверяет роль в SpiralEngine
            if (!hasRole(ADMIN_ROLE, msg.sender) && !_hasSellerRole(msg.sender)) {
                revert UnauthorizedFieldAccess(msg.sender, key);
            }
            
            // Запоминаем владельца
            complexFieldOwner[key] = msg.sender;
            
            // Если класс новый - добавляем в массив
            if (!classExists[className]) {
                complexFieldClasses.push(className);
                classExists[className] = true;
            }
            
            // Если это новый язык для этого класса - добавляем
            if (!complexFieldExists[key]) {
                complexFieldLanguages[className].push(language);
                complexFieldExists[key] = true;
            }
            
        } else {
            // СУЩЕСТВУЮЩЕЕ ПОЛЕ
            
            // Глобальные поля - только ADMIN
            if (isGlobal) {
                if (!hasRole(ADMIN_ROLE, msg.sender)) {
                    revert UnauthorizedFieldAccess(msg.sender, key);
                }
            } else {
                // Обычные поля - owner или ADMIN
                if (owner != msg.sender && !hasRole(ADMIN_ROLE, msg.sender)) {
                    revert UnauthorizedFieldAccess(msg.sender, key);
                }
            }
        }

        // Сохраняем CID
        complexFieldCIDs[key] = cid;

        emit ComplexFieldRegistered(className, language, cid, msg.sender);
    }

    /// @notice Получение CID сложного поля
    /// @param className Имя класса
    /// @param language Код языка
    /// @return IPFS CID
    /// @dev Gas optimization: calldata вместо memory (M1)
    function getComplexFieldCID(
        string calldata className,
        string calldata language
    ) external view returns (string memory) {
        string memory key = string(abi.encodePacked(className, ".", language));
        return complexFieldCIDs[key];
    }

    /// @notice Получение всех языков для класса
    /// @param className Имя класса
    /// @return Массив кодов языков
    /// @dev Gas optimization: calldata вместо memory (M1)
    function getComplexFieldLanguages(
        string calldata className
    ) external view returns (string[] memory) {
        return complexFieldLanguages[className];
    }

    /// @notice Проверка существования сложного поля
    /// @param className Имя класса
    /// @param language Код языка
    /// @return true если поле существует
    /// @dev Gas optimization: calldata вместо memory (M1)
    function complexFieldExist(
        string calldata className,
        string calldata language
    ) external view returns (bool) {
        string memory key = string(abi.encodePacked(className, ".", language));
        return complexFieldExists[key];
    }

    /// @notice Удаление сложного поля
    /// @param className Имя класса
    /// @param language Код языка
    /// @dev Только ADMIN_ROLE может удалять поля
    /// @dev Gas optimization: calldata вместо memory (M1)
    function removeComplexField(
        string calldata className,
        string calldata language
    ) external onlyRole(ADMIN_ROLE) whenNotPaused nonReentrant complexExists(className, language) {
        // Создаем составной ключ
        string memory key = string(abi.encodePacked(className, ".", language));

        // Удаляем маркер существования
        complexFieldExists[key] = false;
        
        // Удаляем CID
        delete complexFieldCIDs[key];

        // Примечание: не удаляем из массивов для экономии gas

        emit ComplexFieldRemoved(className, language, msg.sender);
    }

    /// @notice Batch установка сложных полей
    /// @param classNames Массив имен классов
    /// @param languages Массив языков
    /// @param cids Массив соответствующих CID
    /// @dev Только ADMIN_ROLE может устанавливать переводы
    /// @dev Gas optimization: unchecked для инкремента (M1)
    function batchSetComplexFields(
        string[] memory classNames,
        string[] memory languages,
        string[] memory cids
    ) external onlyRole(ADMIN_ROLE) whenNotPaused nonReentrant {
        // Валидация длины массивов
        if (classNames.length != languages.length || languages.length != cids.length) {
            revert ArrayLengthMismatch();
        }
        if (classNames.length == 0) revert EmptyClassName();

        // Gas optimization: unchecked безопасен для инкремента счетчика цикла (M1)
        for (uint256 i = 0; i < classNames.length;) {
            // Валидация каждого элемента
            if (bytes(classNames[i]).length == 0) revert EmptyClassName();
            if (bytes(languages[i]).length == 0) revert EmptyLanguage();
            if (bytes(cids[i]).length == 0) revert EmptyCID();

            // Создаем составной ключ
            string memory key = string(abi.encodePacked(classNames[i], ".", languages[i]));

            // Если класс новый - добавляем в массив
            if (!classExists[classNames[i]]) {
                complexFieldClasses.push(classNames[i]);
                classExists[classNames[i]] = true;
            }

            // Если это новый язык для этого класса - добавляем
            if (!complexFieldExists[key]) {
                complexFieldLanguages[classNames[i]].push(languages[i]);
                complexFieldExists[key] = true;
            }

            // Сохраняем CID
            complexFieldCIDs[key] = cids[i];

            emit ComplexFieldRegistered(classNames[i], languages[i], cids[i], msg.sender);

            unchecked { ++i; }
        }
    }

    /// @notice Получение всех классов со сложными полями
    /// @return Массив всех зарегистрированных классов
    function getAllComplexClasses() external view returns (string[] memory) {
        return complexFieldClasses;
    }
    
    // === OWNERSHIP & GLOBAL FIELDS FUNCTIONS ===
    
    /// @notice Пометить поле как глобальное (только ADMIN может изменять)
    /// @param fieldKey Ключ поля (для simple) или "className.language" (для complex)
    /// @param isGlobal true если поле глобальное
    /// @dev Только ADMIN_ROLE может помечать поля как глобальные
    /// @dev Примеры глобальных полей: "features", "component_forms"
    function setGlobalField(
        string calldata fieldKey,
        bool isGlobal
    ) external onlyRole(ADMIN_ROLE) whenNotPaused {
        if (bytes(fieldKey).length == 0) revert EmptyFieldKey();
        
        isGlobalField[fieldKey] = isGlobal;
        
        emit GlobalFieldSet(fieldKey, isGlobal, msg.sender);
    }
    
    /// @notice Получение владельца простого поля
    /// @param fieldKey Ключ поля
    /// @return Адрес владельца (address(0) если поле не существует)
    function getSimpleFieldOwner(
        string calldata fieldKey
    ) external view returns (address) {
        return simpleFieldOwner[fieldKey];
    }
    
    /// @notice Получение владельца сложного поля
    /// @param className Имя класса
    /// @param language Код языка
    /// @return Адрес владельца (address(0) если поле не существует)
    function getComplexFieldOwner(
        string calldata className,
        string calldata language
    ) external view returns (address) {
        string memory key = string(abi.encodePacked(className, ".", language));
        return complexFieldOwner[key];
    }
    
    /// @notice Проверка является ли поле глобальным
    /// @param fieldKey Ключ поля
    /// @return true если поле глобальное
    function isFieldGlobal(
        string calldata fieldKey
    ) external view returns (bool) {
        return isGlobalField[fieldKey];
    }
    
    /**
     * @notice Обновляет адрес контракта SpiralEngine
     * @param _spiralEngine Новый адрес контракта SpiralEngine
     * @dev Только ADMIN_ROLE может вызвать эту функцию
     * @dev Используется для обновления интеграции или миграции SpiralEngine
     * 
     * Примеры использования:
     * - Обновление SpiralEngine при апгрейде
     * - Миграция на новую версию SpiralEngine
     * - Экстренное изменение интеграции
     */
    function setSpiralEngine(address _spiralEngine) external onlyRole(ADMIN_ROLE) {
        if (_spiralEngine == address(0)) revert ZeroAddress();
        
        address oldSpiralEngine = address(spiralEngine);
        spiralEngine = ISpiralEngine(_spiralEngine);
        
        emit SpiralEngineUpdated(oldSpiralEngine, _spiralEngine, msg.sender);
    }

    // === STATISTICS FUNCTIONS ===

    /// @notice Получение статистики по полям
    /// @return totalSimpleFields Количество простых полей
    /// @return totalComplexClasses Количество классов
    /// @return totalComplexFields Общее количество сложных полей (класс x язык)
    function getStatistics() external view returns (
        uint256 totalSimpleFields,
        uint256 totalComplexClasses,
        uint256 totalComplexFields
    ) {
        totalSimpleFields = simpleFieldKeys.length;
        totalComplexClasses = complexFieldClasses.length;
        
        // Подсчет общего количества сложных полей
        for (uint256 i = 0; i < complexFieldClasses.length; i++) {
            totalComplexFields += complexFieldLanguages[complexFieldClasses[i]].length;
        }
    }

    // === VERSION FUNCTIONS ===

    /// @notice Получение информации о версии
    /// @return version Строковая версия контракта
    /// @return logicVersion Числовая версия для апгрейдов
    function getVersionInfo() external pure returns (
        string memory version,
        uint256 logicVersion
    ) {
        return (VERSION, LOGIC_VERSION);
    }
}

