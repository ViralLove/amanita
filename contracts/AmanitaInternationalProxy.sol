// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title AmanitaInternationalProxy
 * @author Amanita Decentralization Team
 * @dev Чистый Proxy контракт для делегирования вызовов в Logic контракт
 * @notice Фиксированный адрес - точка входа для всех операций с переводами
 * 
 * Архитектура:
 * - Этот контракт НИКОГДА не меняется после деплоя
 * - Адрес Proxy - это публичный адрес, который используют все сервисы
 * - Все вызовы делегируются в текущий Logic контракт через delegatecall
 * - Logic контракт может обновляться, Proxy остается неизменным
 * 
 * Принцип работы:
 * 1. Пользователь вызывает функцию на Proxy
 * 2. Proxy делегирует вызов в currentLogic через delegatecall
 * 3. Logic работает с Storage контрактом
 * 4. Результат возвращается пользователю через Proxy
 */
contract AmanitaInternationalProxy is AccessControl {
    
    // === РОЛИ ===
    
    /// @notice Роль для управления обновлениями Logic контракта
    bytes32 public constant UPGRADER_ROLE = keccak256("UPGRADER_ROLE");
    
    /// @notice Роль администратора для управления переводами (делегируется в Logic)
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    
    // === СОСТОЯНИЕ PROXY ===
    // КРИТИЧНО: Этот storage layout ДОЛЖЕН совпадать с Logic для delegatecall!
    
    /// @notice Адрес Storage контракта (SLOT 0 после AccessControl slots)
    /// @dev ВАЖНО: Эта переменная должна быть первой для совпадения с Logic storage layout
    address public storageContract;
    
    // === PROXY СПЕЦИФИЧНЫЕ ПЕРЕМЕННЫЕ ===
    // Эти переменные НЕ используются в Logic через delegatecall
    
    /// @notice Адрес текущего Logic контракта
    /// @dev Может обновляться через upgradeLogic()
    address public currentLogic;
    
    /// @notice История всех Logic контрактов
    /// @dev Используется для аудита и отслеживания обновлений
    address[] public logicHistory;
    
    /// @notice Timestamp последнего обновления
    uint256 public lastUpgradeTime;
    
    /// @notice Флаг паузы контракта (emergency stop)
    bool public paused;
    
    // === СОБЫТИЯ ===
    
    /// @notice Событие обновления Logic контракта
    event LogicUpgraded(
        address indexed oldLogic,
        address indexed newLogic,
        address indexed upgrader,
        uint256 timestamp
    );
    
    /// @notice Событие экстренной остановки
    event EmergencyPaused(address indexed admin, uint256 timestamp);
    
    /// @notice Событие возобновления работы
    event EmergencyUnpaused(address indexed admin, uint256 timestamp);
    
    // === КОНСТРУКТОР ===
    
    /**
     * @dev Инициализация Proxy с начальным Logic контрактом
     * @param admin Адрес администратора
     * @param initialLogic Адрес начального Logic контракта
     * @param _storageContract Адрес Storage контракта
     */
    constructor(
        address admin,
        address initialLogic,
        address _storageContract
    ) {
        require(admin != address(0), "AmanitaInternationalProxy: zero admin address");
        require(initialLogic != address(0), "AmanitaInternationalProxy: zero logic address");
        require(_storageContract != address(0), "AmanitaInternationalProxy: zero storage address");
        
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin); // Для делегирования в Logic
        
        currentLogic = initialLogic;
        storageContract = _storageContract;
        
        logicHistory.push(initialLogic);
        lastUpgradeTime = block.timestamp;
        paused = false;
    }
    
    // === УПРАВЛЕНИЕ ОБНОВЛЕНИЯМИ ===
    
    /**
     * @notice Обновить Logic контракт
     * @dev Только UPGRADER_ROLE может обновлять
     * @param newLogic Адрес нового Logic контракта
     */
    function upgradeLogic(address newLogic) 
        external 
        onlyRole(UPGRADER_ROLE) 
    {
        require(newLogic != address(0), "AmanitaInternationalProxy: zero logic address");
        require(newLogic != currentLogic, "AmanitaInternationalProxy: same logic address");
        require(!paused, "AmanitaInternationalProxy: contract paused");
        
        address oldLogic = currentLogic;
        currentLogic = newLogic;
        
        logicHistory.push(newLogic);
        lastUpgradeTime = block.timestamp;
        
        emit LogicUpgraded(oldLogic, newLogic, msg.sender, block.timestamp);
    }
    
    /**
     * @notice Откатиться к предыдущему Logic контракту
     * @dev Emergency функция для быстрого отката
     */
    function rollbackToPreviousLogic() 
        external 
        onlyRole(DEFAULT_ADMIN_ROLE) 
    {
        require(logicHistory.length > 1, "AmanitaInternationalProxy: no previous logic");
        
        address oldLogic = currentLogic;
        address previousLogic = logicHistory[logicHistory.length - 2];
        
        currentLogic = previousLogic;
        lastUpgradeTime = block.timestamp;
        
        emit LogicUpgraded(oldLogic, previousLogic, msg.sender, block.timestamp);
    }
    
    // === EMERGENCY CONTROLS ===
    
    /**
     * @notice Экстренная остановка контракта
     * @dev Блокирует все вызовы через fallback
     */
    function emergencyPause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(!paused, "AmanitaInternationalProxy: already paused");
        paused = true;
        emit EmergencyPaused(msg.sender, block.timestamp);
    }
    
    /**
     * @notice Возобновление работы контракта
     */
    function emergencyUnpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(paused, "AmanitaInternationalProxy: not paused");
        paused = false;
        emit EmergencyUnpaused(msg.sender, block.timestamp);
    }
    
    // === УТИЛИТЫ ===
    
    /**
     * @notice Получить историю всех Logic контрактов
     * @return Массив адресов Logic контрактов в хронологическом порядке
     */
    function getLogicHistory() external view returns (address[] memory) {
        return logicHistory;
    }
    
    /**
     * @notice Получить количество обновлений
     * @return Количество раз когда Logic был обновлен
     */
    function getUpgradeCount() external view returns (uint256) {
        return logicHistory.length - 1;
    }
    
    /**
     * @notice Получить информацию о текущем состоянии Proxy
     * @return logic Адрес текущего Logic
     * @return storage_ Адрес Storage
     * @return upgradeCount Количество обновлений
     * @return isPaused Статус паузы
     */
    function getProxyInfo() external view returns (
        address logic,
        address storage_,
        uint256 upgradeCount,
        bool isPaused
    ) {
        return (
            currentLogic,
            storageContract,
            logicHistory.length - 1,
            paused
        );
    }
    
    // === FALLBACK (ДЕЛЕГИРОВАНИЕ) ===
    
    /**
     * @dev Fallback функция для делегирования всех вызовов в Logic
     * @notice Использует delegatecall для сохранения контекста (msg.sender, storage)
     * @notice ВАЖНО: При delegatecall роли проверяются в Proxy, но выполняются в Logic контексте
     */
    fallback() external payable {
        require(!paused, "AmanitaInternationalProxy: contract paused");
        
        // Проверяем роль ADMIN_ROLE для мутирующих операций
        // Читающие функции доступны всем
        bytes4 sig = bytes4(msg.data);
        
        // Сигнатуры мутирующих функций
        bytes4 SET_SIMPLE_SIG = bytes4(keccak256("setSimpleFieldCID(string,string)"));
        bytes4 SET_COMPLEX_SIG = bytes4(keccak256("setComplexFieldCID(string,string,string)"));
        bytes4 REMOVE_SIMPLE_SIG = bytes4(keccak256("removeSimpleField(string)"));
        bytes4 REMOVE_COMPLEX_SIG = bytes4(keccak256("removeComplexField(string,string)"));
        bytes4 BATCH_SIMPLE_SIG = bytes4(keccak256("batchSetSimpleFields(string[],string[])"));
        bytes4 BATCH_COMPLEX_SIG = bytes4(keccak256("batchSetComplexFields(string[],string[],string[])"));
        
        // Если это мутирующая операция - проверяем роль
        if (sig == SET_SIMPLE_SIG || sig == SET_COMPLEX_SIG || 
            sig == REMOVE_SIMPLE_SIG || sig == REMOVE_COMPLEX_SIG ||
            sig == BATCH_SIMPLE_SIG || sig == BATCH_COMPLEX_SIG) {
            require(hasRole(ADMIN_ROLE, msg.sender), "AmanitaInternationalProxy: caller is not admin");
        }
        
        address logic = currentLogic;
        require(logic != address(0), "AmanitaInternationalProxy: no logic contract");
        
        assembly {
            // Копируем calldata в память
            calldatacopy(0, 0, calldatasize())
            
            // Делегируем вызов в Logic контракт
            let result := delegatecall(gas(), logic, 0, calldatasize(), 0, 0)
            
            // Копируем результат обратно
            returndatacopy(0, 0, returndatasize())
            
            // Возвращаем результат или revert
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
    
    /**
     * @dev Receive функция для принятия ETH
     */
    receive() external payable {
        revert("AmanitaInternationalProxy: direct ETH transfers not allowed");
    }
}

