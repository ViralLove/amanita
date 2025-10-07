// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IOrganicComponentRegistry
 * @author Amanita Decentralization Team
 * @dev Интерфейс для интеграции с OrganicComponentRegistry
 * @notice Используется в ProductRegistry для валидации компонентов
 */
interface IOrganicComponentRegistry {
    
    // === СТАТУСЫ КОМПОНЕНТОВ ===
    
    enum ComponentStatus {
        ACTIVE,       // Активен и доступен для использования в продуктах
        PENDING,      // Создан, но требует проверки (заготовка для модерации)
        ARCHIVED      // Устарел или неактуален
    }
    
    // === СТРУКТУРЫ ДАННЫХ ===
    
    struct ShareableData {
        string features_cid;           // IPFS CID для features.json
        string component_forms_cid;    // IPFS CID для component_forms.json
        uint256 features_version;      // Версия features словаря
        uint256 forms_version;         // Версия forms словаря
        uint256 last_updated;          // Время последнего обновления
    }
    
    // === ОСНОВНЫЕ ФУНКЦИИ ===
    
    /**
     * @dev Проверить существование компонента
     * @param businessId уникальный текстовый ID
     * @return существует ли компонент
     */
    function validateComponentExists(string memory businessId) external view returns (bool);
    
    /**
     * @dev Получить статус компонента
     * @param businessId уникальный текстовый ID
     * @return статус компонента
     */
    function getComponentStatus(string memory businessId) external view returns (ComponentStatus);
    
    /**
     * @dev Получить корневой CID компонента
     * @param businessId уникальный текстовый ID
     * @return IPFS CID корневого JSON
     */
    function getComponentRootMetadata(string memory businessId) external view returns (string memory);
    
    /**
     * @dev Проверить существование компонента по business_id
     * @param businessId Уникальный текстовый ID компонента.
     * @return bool True, если компонент существует.
     */
    function componentExists(string memory businessId) external view returns (bool);
    
    /**
     * @dev Увеличить счетчик использования компонента
     * @param businessId уникальный текстовый ID
     */
    function incrementUsageCount(string memory businessId) external;
    
    /**
     * @dev Добавить пользователя компонента
     * @param businessId уникальный текстовый ID
     * @param user адрес пользователя
     */
    function addComponentUser(string memory businessId, address user) external;
    
    // === ФУНКЦИИ ДЛЯ SHAREABLE ДАННЫХ ===
    
    /**
     * @dev Получить CID для features
     * @return IPFS CID для features.json
     */
    function getFeaturesCID() external view returns (string memory);
    
    /**
     * @dev Получить CID для component forms
     * @return IPFS CID для component_forms.json
     */
    function getComponentFormsCID() external view returns (string memory);
    
    /**
     * @dev Получить версию features
     * @return версия features словаря
     */
    function getFeaturesVersion() external view returns (uint256);
    
    /**
     * @dev Получить версию component forms
     * @return версия forms словаря
     */
    function getComponentFormsVersion() external view returns (uint256);
    
    /**
     * @dev Получить полные shareable данные
     * @return ShareableData структура с данными
     */
    function getShareableData() external view returns (ShareableData memory);
    
    /**
     * @dev Обновить shareable данные
     * @param featuresCID новый CID для features
     * @param componentFormsCID новый CID для component forms
     * @param featuresVersion новая версия features
     * @param formsVersion новая версия forms
     */
    function updateShareableData(
        string memory featuresCID,
        string memory componentFormsCID,
        uint256 featuresVersion,
        uint256 formsVersion
    ) external;
    
    // === ФУНКЦИИ ДОСТУПА К ДАННЫМ ===
    
    /**
     * @dev Получить общее количество компонентов
     * @return количество созданных компонентов
     */
    function totalComponents() external view returns (uint256);
    
    /**
     * @dev Получить общее количество обновлений
     * @return количество обновлений
     */
    function totalUpdates() external view returns (uint256);
    
    /**
     * @dev Получить счетчик использования компонента
     * @param componentId ID компонента
     * @return количество использований
     */
    function componentUsageCount(uint256 componentId) external view returns (uint256);
    
    /**
     * @dev Получить компоненты создателя
     * @param creator адрес создателя
     * @return массив ID компонентов
     */
    function getComponentsByCreator(address creator) external view returns (uint256[] memory);
    
    /**
     * @dev Получить компоненты пользователя
     * @param user адрес пользователя
     * @return массив ID компонентов
     */
    function getComponentsByUser(address user) external view returns (uint256[] memory);
    
    // === ФУНКЦИИ ДОСТУПА К ИНТЕГРАЦИОННЫМ ПЕРЕМЕННЫМ ===
    
    /**
     * @dev Получить адрес SpiralEngine
     * @return адрес SpiralEngine контракта
     */
    function spiralEngine() external view returns (address);
    
    /**
     * @dev Получить адрес AmanitaInternational
     * @return адрес AmanitaInternational контракта
     */
    function amanitaInternational() external view returns (address);
    
    /**
     * @dev Получить адрес ProductRegistry
     * @return адрес ProductRegistry контракта
     */
    function productRegistry() external view returns (address);
    
    // === СОБЫТИЯ ===
    
    event ComponentCreated(uint256 indexed componentId, string businessId, address indexed creator, string rootMetadataCID, uint256 timestamp);
    event ComponentUpdated(uint256 indexed componentId, address indexed updater, string newRootMetadataCID, uint256 timestamp);
    event ComponentUsageIncremented(uint256 indexed componentId, string businessId, uint256 newUsageCount);
    event ComponentUserAdded(uint256 indexed componentId, string businessId, address indexed user);
    event ShareableDataUpdated(string featuresCID, string componentFormsCID, uint256 indexed featuresVersion, uint256 indexed formsVersion, uint256 indexed timestamp);
}
