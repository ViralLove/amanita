// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "./interfaces/ISpiralEngine.sol";
import "./interfaces/IAmanitaInternational.sol";
import "./interfaces/IProductRegistry.sol";
import "./interfaces/IOrganicComponentRegistry.sol";

/**
 * @title OrganicComponentRegistryLogic
 * @author Zeya888 (https://zeya888.me)
 * @dev Полная UUPS имплементация для OrganicComponentRegistry
 * @notice Содержит ВСЕ state variables, роли, паузу и бизнес-логику
 * @notice Версия: 3.0.0 - Стандартный UUPS паттерн
 * 
 * Архитектура:
 * - Все state variables объявлены в Logic
 * - При delegatecall state физически хранится в Proxy
 * - Прямой доступ к переменным (без StorageSlot)
 * - Роли и пауза управляются через Logic
 * - Апгрейды через _authorizeUpgrade (UPGRADER_ROLE)
 */
contract OrganicComponentRegistryLogic is 
    Initializable, 
    UUPSUpgradeable, 
    AccessControlUpgradeable,
    PausableUpgradeable,
    IOrganicComponentRegistry 
{
    // === КОНСТАНТЫ ===

    /// @notice Версия Logic контракта
    uint256 public constant LOGIC_VERSION = 2;

    /// @notice Максимальная длина business_id
    uint256 public constant MAX_BUSINESS_ID_LENGTH = 64;

    /// @notice Максимальная длина IPFS CID
    uint256 public constant MAX_CID_LENGTH = 64;

    /// @notice Максимальное количество компонентов на одного пользователя
    uint256 public constant MAX_COMPONENTS_PER_USER = 100;

    // === РОЛИ ===

    /// @notice Роль для обновления контракта
    bytes32 public constant UPGRADER_ROLE = keccak256("UPGRADER_ROLE");
    
    /// @notice Роль для управления переводами и shareable данными
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    
    /// @notice Роль для создания и редактирования компонентов
    bytes32 public constant CONTRIBUTOR_ROLE = keccak256("CONTRIBUTOR_ROLE");

    // === СТАТУСЫ КОМПОНЕНТОВ ===
    // ComponentStatus определен в IOrganicComponentRegistry

    // === СТРУКТУРЫ ДАННЫХ ===
    // Все структуры объявлены в Logic, физически хранятся в Proxy через delegatecall

    /// @notice Структура компонента
    struct Component {
        uint256 blockchain_id;
        address creator;
        uint256 created_at;
        uint256 last_updated;
        ComponentStatus status;
        bool is_shared;
    }


    /// @notice Предложение обновления компонента
    struct ComponentUpdate {
        uint256 component_id;
        address proposer;
        string new_root_metadata_cid;
        string change_description;
        uint256 proposed_at;
        bool is_approved;
        address approved_by;
        uint256 approved_at;
    }

    /// @notice Валидатор обновления компонента
    struct ComponentValidator {
        address validator;
        uint256 component_id;
        bool has_validated;
        uint256 validated_at;
        string validation_comment;
    }

    // === ДАННЫЕ ===
    // В UUPS архитектуре все state variables объявлены в Logic
    // При delegatecall данные физически хранятся в Proxy
    // Прямой доступ к переменным (без StorageSlot)
    
    mapping(uint256 => Component) public components;
    mapping(uint256 => string) public componentBusinessIds;
    mapping(uint256 => string) public componentRootMetadataCIDs;
    mapping(string => uint256) public businessIdToComponentId;
    mapping(address => uint256[]) public componentsByCreator;
    mapping(address => uint256[]) public componentsByUser;
    IOrganicComponentRegistry.ShareableData public shareableData;
    mapping(uint256 => ComponentUpdate[]) public componentUpdates;
    mapping(uint256 => ComponentValidator[]) public componentValidators;
    mapping(uint256 => uint256) public requiredValidations;
    mapping(uint256 => uint256) public componentUpdateCount;
    uint256 public totalComponents;
    uint256 public totalUpdates;
    mapping(uint256 => uint256) public componentUsageCount;
    
    // === ИНТЕГРАЦИЯ С ЭКОСИСТЕМОЙ ===
    // Интеграционные переменные с прямым доступом (не StorageSlot)
    
    address public spiralEngine;
    address public amanitaInternational;
    address public productRegistry;


    // === СОБЫТИЯ ===
    // События определены в IOrganicComponentRegistry интерфейсе

    event ComponentUpdateProposed(
        uint256 indexed componentId,
        address indexed proposer,
        string newRootMetadataCID,
        string changeDescription,
        uint256 timestamp
    );

    event ComponentUpdateValidated(
        uint256 indexed componentId,
        uint256 indexed updateId,
        address indexed validator,
        bool approved,
        string comment,
        uint256 timestamp
    );


    // === ИНИЦИАЛИЗАЦИЯ ===

    /**
     * @dev Инициализация Logic контракта (UUPS-совместимый)
     * @param admin Адрес администратора, получающего все роли
     * @notice Инициализация должна происходить через Proxy при деплое
     */
    function initialize(address admin) public initializer {
        require(admin != address(0), "OrganicComponentRegistryLogic: invalid admin");
        
        __AccessControl_init();
        __UUPSUpgradeable_init();
        __Pausable_init();
        
        // Выдаем роли админу
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
        _grantRole(CONTRIBUTOR_ROLE, admin);
    }

    // === ДОСТУП К ДАННЫМ ===
    // Public переменные автоматически создают getter функции
    // Solidity автоматически генерирует getter для public переменных
    // Для массивов нужны отдельные getter функции
    
    /**
     * @dev Получить все компоненты создателя
     * @param creator адрес создателя
     * @return массив ID компонентов
     */
    function getComponentsByCreator(address creator) external view returns (uint256[] memory) {
        return componentsByCreator[creator];
    }
    
    /**
     * @dev Получить все компоненты пользователя
     * @param user адрес пользователя
     * @return массив ID компонентов
     */
    function getComponentsByUser(address user) external view returns (uint256[] memory) {
        return componentsByUser[user];
    }

    /**
     * @dev Авторизация обновления контракта
     * @param newImplementation адрес новой реализации
     */
    function _authorizeUpgrade(address newImplementation) internal override onlyRole(UPGRADER_ROLE) {
        // Дополнительные проверки можно добавить здесь
    }

    // === ФУНКЦИИ ПАУЗЫ ===

    /**
     * @dev Поставить контракт на паузу
     * @notice Доступно только ADMIN_ROLE
     */
    function pause() external onlyRole(ADMIN_ROLE) {
        _pause();
    }

    /**
     * @dev Снять контракт с паузы
     * @notice Доступно только ADMIN_ROLE
     */
    function unpause() external onlyRole(ADMIN_ROLE) {
        _unpause();
    }

    // === МОДИФИКАТОРЫ ===

    /// @notice Модификатор: только активированные пользователи
    modifier onlyActivatedUser() {
        require(spiralEngine != address(0), "OrganicComponentRegistryLogic: SpiralEngine not set");
        
        address realUser = _msgSender();
        require(realUser != address(0), "OrganicComponentRegistryLogic: realUser is zero address");
        
        // Проверяем активацию через SpiralEngine
        ISpiralEngine spiralEngineContract = ISpiralEngine(spiralEngine);
        uint256 usedInvite = spiralEngineContract.usedInviteByUser(realUser);
        require(usedInvite > 0, "OrganicComponentRegistryLogic: user not activated");
        _;
    }

    /// @notice Модификатор: только селлеры
    modifier onlySeller() {
        require(spiralEngine != address(0), "OrganicComponentRegistryLogic: SpiralEngine not set");
        
        address realUser = _msgSender();
        ISpiralEngine spiralEngineContract = ISpiralEngine(spiralEngine);
        require(spiralEngineContract.hasRole(spiralEngineContract.SELLER_ROLE(), realUser), "OrganicComponentRegistryLogic: not a seller");
        _;
    }

    /// @notice Модификатор: только создатель компонента
    modifier onlyComponentCreator(uint256 componentId) {
        require(componentId > 0 && componentId <= totalComponents, "OrganicComponentRegistryLogic: component not found");
        // В UUPS архитектуре msg.sender - это Proxy, нужно получить реального пользователя
        address realUser = _msgSender();
        require(components[componentId].creator == realUser, "OrganicComponentRegistryLogic: not component creator");
        _;
    }

    /// @notice Модификатор: валидация business_id
    modifier validBusinessId(string memory businessId) {
        require(bytes(businessId).length > 0, "OrganicComponentRegistryLogic: business ID cannot be empty");
        require(bytes(businessId).length <= MAX_BUSINESS_ID_LENGTH, "OrganicComponentRegistryLogic: business ID too long");
        _;
    }

    /// @notice Модификатор: валидация IPFS CID
    modifier validCID(string memory cid) {
        require(bytes(cid).length > 0, "OrganicComponentRegistryLogic: CID cannot be empty");
        require(bytes(cid).length <= MAX_CID_LENGTH, "OrganicComponentRegistryLogic: CID too long");
        _;
    }

    // === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

    /**
     * @dev Проверить существование компонента по business_id
     * @param businessId уникальный текстовый ID
     * @return существует ли компонент
     */
    function _componentExists(string memory businessId) internal view returns (bool) {
        // При delegatecall Logic работает с данными Proxy как с собственными
        return businessIdToComponentId[businessId] > 0;
    }

    /**
     * @dev Получить количество компонентов создателя
     * @param creator адрес создателя
     * @return количество компонентов
     */
    function getCreatorComponentCount(address creator) internal view returns (uint256) {
        // При delegatecall Logic работает с данными Proxy как с собственными
        return componentsByCreator[creator].length;
    }

    // === ФУНКЦИИ УПРАВЛЕНИЯ КОМПОНЕНТАМИ ===

    /**
     * @dev Создать новый компонент
     * @param businessId Уникальный текстовый ID компонента (например, "amanita_muscaria").
     * @param rootMetadataCID IPFS CID корневого JSON, содержащего всю информацию о компоненте.
     * @return componentId Уникальный ID созданного компонента в блокчейне.
     */
    function createComponent(
        string memory businessId,
        string memory rootMetadataCID
    ) external whenNotPaused onlyActivatedUser onlySeller validBusinessId(businessId) validCID(rootMetadataCID) returns (uint256 componentId) {

        // Проверяем уникальность business_id
        require(!_componentExists(businessId), "OrganicComponentRegistryLogic: component with this business ID already exists");

        // Получаем реального пользователя
        address realUser = _msgSender();
        
        // Проверяем лимит компонентов на пользователя
        require(getCreatorComponentCount(realUser) < MAX_COMPONENTS_PER_USER, "OrganicComponentRegistryLogic: component limit exceeded");

        componentId = ++totalComponents;

        // Сохраняем данные напрямую (при delegatecall это данные Proxy)
        components[componentId] = Component({
            blockchain_id: componentId,
            creator: realUser,
            created_at: block.timestamp,
            last_updated: block.timestamp,
            status: IOrganicComponentRegistry.ComponentStatus.ACTIVE,
            is_shared: true
        });
        
        componentBusinessIds[componentId] = businessId;
        componentRootMetadataCIDs[componentId] = rootMetadataCID;
        businessIdToComponentId[businessId] = componentId;
        componentsByCreator[realUser].push(componentId);

        emit ComponentCreated(componentId, businessId, realUser, rootMetadataCID, block.timestamp);
    }

    /**
     * @dev Обновить root_metadata_cid компонента
     * @param componentId Уникальный ID компонента в блокчейне.
     * @param newRootMetadataCID Новый IPFS CID корневого JSON.
     */
    function updateComponent(
        uint256 componentId,
        string memory newRootMetadataCID
    ) external whenNotPaused onlyComponentCreator(componentId) validCID(newRootMetadataCID) {
        require(componentId > 0 && componentId <= totalComponents, "OrganicComponentRegistryLogic: component not found");

        // Обновляем данные напрямую
        componentRootMetadataCIDs[componentId] = newRootMetadataCID;
        components[componentId].last_updated = block.timestamp;

        address realUser = _msgSender();
        emit ComponentUpdated(componentId, realUser, newRootMetadataCID, block.timestamp);
    }

    /**
     * @dev Получить компонент по blockchain_id
     * @param componentId Уникальный ID компонента в блокчейне.
     * @return Component Структура компонента.
     */
    function getComponent(uint256 componentId) external view returns (Component memory) {
        require(componentId > 0 && componentId <= totalComponents, "OrganicComponentRegistryLogic: component not found");
        return components[componentId];
    }

    /**
     * @dev Получить компонент по business_id
     * @param businessId Уникальный текстовый ID компонента.
     * @return Component Структура компонента.
     */
    function getComponentByBusinessId(string memory businessId) external view returns (Component memory) {
        uint256 componentId = businessIdToComponentId[businessId];
        require(componentId > 0, "OrganicComponentRegistryLogic: component not found");
        return components[componentId];
    }

    /**
     * @dev Проверить существование компонента по business_id
     * @param businessId Уникальный текстовый ID компонента.
     * @return bool True, если компонент существует.
     */
    function componentExists(string memory businessId) external view returns (bool) {
        return businessIdToComponentId[businessId] > 0;
    }

    /**
     * @dev Проверить существование компонента по business_id
     * @param businessId Уникальный текстовый ID компонента.
     * @return bool True, если компонент существует.
     */
    function validateComponentExists(string memory businessId) external view returns (bool) {
        return _componentExists(businessId);
    }

    /**
     * @dev Получить статус компонента по business_id
     * @param businessId Уникальный текстовый ID компонента.
     * @return ComponentStatus Статус компонента.
     */
    function getComponentStatus(string memory businessId) external view returns (IOrganicComponentRegistry.ComponentStatus) {
        uint256 componentId = businessIdToComponentId[businessId];
        require(componentId > 0, "OrganicComponentRegistryLogic: component not found");
        return IOrganicComponentRegistry.ComponentStatus(uint8(components[componentId].status));
    }

    /**
     * @dev Получить корневой CID метаданных компонента по business_id
     * @return cid IPFS CID корневого JSON.
     */
    function getComponentRootMetadata(string memory businessId) external view returns (string memory cid) {
        uint256 componentId = businessIdToComponentId[businessId];
        require(componentId > 0, "OrganicComponentRegistryLogic: component not found");
        return componentRootMetadataCIDs[componentId];
    }
    
    /**
     * @dev Получить CID для features
     * @return IPFS CID для features.json
     */
    function getFeaturesCID() external view returns (string memory) {
        return shareableData.features_cid;
    }
    
    /**
     * @dev Получить CID для component forms
     * @return IPFS CID для component_forms.json
     */
    function getComponentFormsCID() external view returns (string memory) {
        return shareableData.component_forms_cid;
    }
    
    /**
     * @dev Получить версию features
     * @return версия features словаря
     */
    function getFeaturesVersion() external view returns (uint256) {
        return shareableData.features_version;
    }
    
    /**
     * @dev Получить версию component forms
     * @return версия forms словаря
     */
    function getComponentFormsVersion() external view returns (uint256) {
        return shareableData.forms_version;
    }

    // === ФУНКЦИИ ДЛЯ ИНТЕГРАЦИИ ===

    /**
     * @dev Установить адрес SpiralEngine в Proxy storage
     * @param _spiralEngine Адрес контракта SpiralEngine
     */
    function setSpiralEngine(address _spiralEngine) external onlyRole(ADMIN_ROLE) {
        require(_spiralEngine != address(0), "OrganicComponentRegistryLogic: invalid address");
        spiralEngine = _spiralEngine;
    }

    /**
     * @dev Установить адрес AmanitaInternational
     * @param _amanitaInternational Адрес контракта AmanitaInternational
     */
    function setAmanitaInternational(address _amanitaInternational) external onlyRole(ADMIN_ROLE) {
        require(_amanitaInternational != address(0), "OrganicComponentRegistryLogic: invalid address");
        amanitaInternational = _amanitaInternational;
    }

    /**
     * @dev Установить адрес ProductRegistry
     * @param _productRegistry Адрес контракта ProductRegistry
     */
    function setProductRegistry(address _productRegistry) external onlyRole(ADMIN_ROLE) {
        require(_productRegistry != address(0), "OrganicComponentRegistryLogic: invalid address");
        productRegistry = _productRegistry;
    }

    // === ЗАГЛУШКИ ДЛЯ СОВМЕСТИМОСТИ ===
    // TODO: Реализовать полную функциональность в следующих итерациях

    function updateShareableData(
        string memory featuresCID,
        string memory componentFormsCID,
        uint256 featuresVersion,
        uint256 formsVersion
    ) external onlyRole(ADMIN_ROLE) validCID(featuresCID) validCID(componentFormsCID) {
        IOrganicComponentRegistry.ShareableData storage data = shareableData;
        data.features_cid = featuresCID;
        data.component_forms_cid = componentFormsCID;
        data.features_version = featuresVersion;
        data.forms_version = formsVersion;
        data.last_updated = block.timestamp;
        
        emit ShareableDataUpdated(featuresCID, componentFormsCID, featuresVersion, formsVersion, block.timestamp);
    }

    function getShareableData() external view returns (IOrganicComponentRegistry.ShareableData memory) {
        IOrganicComponentRegistry.ShareableData storage data = shareableData;
        return IOrganicComponentRegistry.ShareableData({
            features_cid: data.features_cid,
            component_forms_cid: data.component_forms_cid,
            features_version: data.features_version,
            forms_version: data.forms_version,
            last_updated: data.last_updated
        });
    }

    function proposeComponentUpdate(
        uint256 /* componentId */,
        string memory /* newRootMetadataCID */,
        string memory /* changeDescription */
    ) external view onlyActivatedUser validCID("") {
        // TODO: Реализовать предложение обновления
        revert("OrganicComponentRegistryLogic: proposeComponentUpdate not implemented yet");
    }

    function validateComponentUpdate(
        uint256 /* componentId */,
        uint256 /* updateId */,
        bool /* approved */,
        string memory /* comment */
    ) external view onlyActivatedUser {
        // TODO: Реализовать валидацию обновления
        revert("OrganicComponentRegistryLogic: validateComponentUpdate not implemented yet");
    }

    function incrementUsageCount(string memory businessId) external {
        uint256 componentId = businessIdToComponentId[businessId];
        require(componentId > 0, "OrganicComponentRegistryLogic: component not found");
        
        componentUsageCount[componentId]++;
        emit ComponentUsageIncremented(componentId, businessId, componentUsageCount[componentId]);
    }

    function addComponentUser(string memory businessId, address user) external {
        uint256 componentId = businessIdToComponentId[businessId];
        require(componentId > 0, "OrganicComponentRegistryLogic: component not found");
        require(user != address(0), "OrganicComponentRegistryLogic: invalid user address");
        
        // Проверяем, что пользователь еще не добавлен
        uint256[] memory userComponents = componentsByUser[user];
        bool alreadyAdded = false;
        for (uint256 i = 0; i < userComponents.length; i++) {
            if (userComponents[i] == componentId) {
                alreadyAdded = true;
                break;
            }
        }
        
        require(!alreadyAdded, "OrganicComponentRegistryLogic: user already added to component");
        
        // Добавляем компонент в массив пользователя
        componentsByUser[user].push(componentId);
        emit ComponentUserAdded(componentId, businessId, user);
    }

    // === ФУНКЦИИ ДЛЯ COMPONENT UPDATE (ЗАГЛУШКИ) ===
    
    function getComponentUpdate(uint256 /* componentId */, uint256 /* updateId */) external pure returns (ComponentUpdate memory) {
        revert("OrganicComponentRegistryLogic: getComponentUpdate not implemented yet");
    }
    
    function getComponentUpdateCount(uint256 /* componentId */) external pure returns (uint256) {
        revert("OrganicComponentRegistryLogic: getComponentUpdateCount not implemented yet");
    }
    
    function getComponentValidator(uint256 /* componentId */, uint256 /* validatorIndex */) external pure returns (ComponentValidator memory) {
        revert("OrganicComponentRegistryLogic: getComponentValidator not implemented yet");
    }
    
    function getComponentValidatorCount(uint256 /* componentId */) external pure returns (uint256) {
        revert("OrganicComponentRegistryLogic: getComponentValidatorCount not implemented yet");
    }
    
    function hasUserValidatedComponent(uint256 /* componentId */, address /* validator */) external pure returns (bool) {
        revert("OrganicComponentRegistryLogic: hasUserValidatedComponent not implemented yet");
    }
    
}
