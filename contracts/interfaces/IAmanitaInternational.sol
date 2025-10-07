// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

/**
 * @title IAmanitaInternational
 * @author Amanita Decentralization Team
 * @notice Интерфейс для AmanitaInternational контракта
 * @dev Определяет все публичные функции и события для мультиязычных переводов
 */
interface IAmanitaInternational {
    
    // === СТРУКТУРЫ ДАННЫХ ===

    /// @notice Статистика по полям
    struct FieldStatistics {
        uint256 totalSimpleFields;      // Количество простых полей
        uint256 totalComplexClasses;    // Количество классов
        uint256 totalComplexFields;     // Общее количество сложных полей (класс x язык)
    }

    // === СОБЫТИЯ ===

    /// @notice Событие регистрации простого поля
    event SimpleFieldRegistered(
        string indexed fieldKey,
        string cid,
        address indexed updater
    );

    /// @notice Событие регистрации сложного поля
    event ComplexFieldRegistered(
        string indexed className,
        string indexed language,
        string cid,
        address indexed updater
    );

    /// @notice Событие удаления простого поля
    event SimpleFieldRemoved(
        string indexed fieldKey,
        address indexed remover
    );

    /// @notice Событие удаления сложного поля
    event ComplexFieldRemoved(
        string indexed className,
        string indexed language,
        address indexed remover
    );

    /// @notice Событие паузы контракта
    event Paused(address account);

    /// @notice Событие снятия паузы контракта
    event Unpaused(address account);

    // === SIMPLE FIELDS FUNCTIONS ===

    /// @notice Установка CID для простого поля
    function setSimpleFieldCID(
        string memory fieldKey,
        string memory cid
    ) external;

    /// @notice Получение CID простого поля
    function getSimpleFieldCID(
        string memory fieldKey
    ) external view returns (string memory);

    /// @notice Проверка существования простого поля
    function simpleFieldExist(
        string memory fieldKey
    ) external view returns (bool);

    /// @notice Удаление простого поля
    function removeSimpleField(
        string memory fieldKey
    ) external;

    /// @notice Batch установка простых полей
    function batchSetSimpleFields(
        string[] memory fieldKeys,
        string[] memory cids
    ) external;

    /// @notice Получение всех простых полей
    function getAllSimpleFields() external view returns (string[] memory);

    // === COMPLEX FIELDS FUNCTIONS ===

    /// @notice Установка CID для сложного поля
    function setComplexFieldCID(
        string memory className,
        string memory language,
        string memory cid
    ) external;

    /// @notice Получение CID сложного поля
    function getComplexFieldCID(
        string memory className,
        string memory language
    ) external view returns (string memory);

    /// @notice Получение всех языков для класса
    function getComplexFieldLanguages(
        string memory className
    ) external view returns (string[] memory);

    /// @notice Проверка существования сложного поля
    function complexFieldExist(
        string memory className,
        string memory language
    ) external view returns (bool);

    /// @notice Удаление сложного поля
    function removeComplexField(
        string memory className,
        string memory language
    ) external;

    /// @notice Batch установка сложных полей
    function batchSetComplexFields(
        string[] memory classNames,
        string[] memory languages,
        string[] memory cids
    ) external;

    /// @notice Получение всех классов со сложными полями
    function getAllComplexClasses() external view returns (string[] memory);

    // === PAUSE FUNCTIONS ===

    /// @notice Пауза контракта
    function pause() external;

    /// @notice Снятие паузы контракта
    function unpause() external;

    /// @notice Проверка паузы контракта
    function paused() external view returns (bool);

    // === STATISTICS FUNCTIONS ===

    /// @notice Получение статистики по полям
    function getStatistics() external view returns (
        uint256 totalSimpleFields,
        uint256 totalComplexClasses,
        uint256 totalComplexFields
    );

    // === VERSION FUNCTIONS ===

    /// @notice Получение информации о версии
    function getVersionInfo() external pure returns (
        string memory version,
        uint256 logicVersion
    );

    // === ACCESS CONTROL FUNCTIONS ===

    /// @notice Проверка роли у адреса
    function hasRole(
        bytes32 role,
        address account
    ) external view returns (bool);

    /// @notice Выдача роли адресу
    function grantRole(
        bytes32 role,
        address account
    ) external;

    /// @notice Отзыв роли у адреса
    function revokeRole(
        bytes32 role,
        address account
    ) external;

    /// @notice Отказ от роли (сам от себя)
    function renounceRole(
        bytes32 role,
        address account
    ) external;
}
