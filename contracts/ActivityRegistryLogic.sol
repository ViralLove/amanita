// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "./interfaces/IActivityRegistry.sol";
import "./interfaces/ISpiralEngine.sol";

/**
 * @title ActivityRegistryLogic
 * @author Zeya888 (https://zeya888.me)
 * @dev UUPS Logic реестра активностей (events/services); состояние хранится в Proxy.
 * @custom:security-contact security@amanita.com
 */
contract ActivityRegistryLogic is
    Initializable,
    UUPSUpgradeable,
    AccessControlUpgradeable,
    PausableUpgradeable,
    ReentrancyGuardUpgradeable,
    IActivityRegistry
{
    // ================================
    // ========== КОНСТАНТЫ ===========
    // ================================

    /// @notice Версия Logic контракта для апгрейдов
    uint256 public constant LOGIC_VERSION = 1;
    /// @notice Роль для обновления контракта (UUPS)
    bytes32 public constant UPGRADER_ROLE = keccak256("UPGRADER_ROLE");
    /// @notice Роль администратора (pause, setSpiralEngine)
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    /// @notice Роль создателя активностей (проверка через SpiralEngine)
    bytes32 public constant ACTIVITY_CREATOR_ROLE = keccak256("ACTIVITY_CREATOR_ROLE");

    // ================================
    // ======== CUSTOM ERRORS =========
    // ================================

    /// @notice Нулевой адрес
    error ZeroAddress();
    /// @notice Неверный адрес SpiralEngine
    error InvalidSpiralEngine();
    /// @notice Пустой metadataCID
    error EmptyCID();
    /// @notice Активность не найдена
    error ActivityNotFound();
    /// @notice Активность не активна (черновик)
    error ActivityNotActive();
    /// @notice Активность уже активна
    error ActivityAlreadyActive();
    /// @notice Не владелец активности
    error NotActivityCreator();
    /// @notice Не активированный создатель (роль/инвайт в SpiralEngine)
    error NotActivatedActivityCreator();

    // ================================
    // ====== STATE VARIABLES =========
    // ================================
    // ⚠️ КРИТИЧНО: Порядок переменных совпадает с планом (solution-architecture 2.4)
    // ⚠️ При delegatecall данные хранятся в Proxy; не менять порядок при апгрейдах

    /// @notice Контракт SpiralEngine для проверки ACTIVITY_CREATOR_ROLE и usedInviteByUser
    ISpiralEngine public spiralEngine;
    /// @notice Хранилище: activityId => Activity
    mapping(uint256 => Activity) private activities;
    /// @notice Индекс: creator => список activityId
    mapping(address => uint256[]) private activitiesByCreator;
    /// @notice Список ID опубликованных активностей (active == true)
    uint256[] private publishedActivityIds;
    /// @notice Счётчик для генерации следующего activityId
    uint256 private _activityIdCounter;

    // ================================
    // ======== STORAGE GAP ===========
    // ================================
    // Резерв слотов для будущих переменных при апгрейдах; при добавлении полей — уменьшать размер gap

    /// @dev Резерв для будущих обновлений (48 слотов)
    uint256[48] private __gap;

    // ================================
    // ======== ИНИЦИАЛИЗАЦИЯ =========
    // ================================

    /**
     * @dev Инициализация Logic контракта (UUPS-совместимый)
     * @param admin Адрес администратора (получает DEFAULT_ADMIN_ROLE, ADMIN_ROLE, UPGRADER_ROLE)
     * @param _spiralEngine Адрес контракта SpiralEngine
     * @notice Вызывается один раз при деплое Proxy через initCalldata
     * @notice Заменяет constructor для upgradeable контрактов
     */
    function initialize(address admin, address _spiralEngine) public initializer {
        if (admin == address(0)) revert ZeroAddress();
        if (_spiralEngine == address(0)) revert InvalidSpiralEngine();
        __AccessControl_init();
        __UUPSUpgradeable_init();
        __Pausable_init();
        __ReentrancyGuard_init();
        spiralEngine = ISpiralEngine(_spiralEngine);
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
    }

    // ================================
    // ===== UUPS UPGRADE PROTECTION ==
    // ================================

    /**
     * @dev Авторизация обновления контракта
     * @param newImplementation Адрес новой Logic-имплементации
     * @notice Только UPGRADER_ROLE может вызывать upgradeToAndCall
     */
    function _authorizeUpgrade(address newImplementation) internal override onlyRole(UPGRADER_ROLE) view {
        if (newImplementation == address(0)) revert ZeroAddress();
    }

    // ================================
    // ======= ФУНКЦИИ ПАУЗЫ ==========
    // ================================

    /**
     * @dev Поставить контракт на паузу (emergency)
     * @notice Доступно только ADMIN_ROLE
     */
    function pause() external onlyRole(ADMIN_ROLE) nonReentrant {
        _pause();
    }

    /**
     * @dev Снять контракт с паузы
     * @notice Доступно только ADMIN_ROLE
     */
    function unpause() external onlyRole(ADMIN_ROLE) nonReentrant {
        _unpause();
    }

    // ================================
    // ======= ADMIN ФУНКЦИИ ==========
    // ================================

    /// @notice Установить адрес SpiralEngine (только ADMIN_ROLE, whenNotPaused)
    function setSpiralEngine(address _spiralEngine) external onlyRole(ADMIN_ROLE) whenNotPaused nonReentrant {
        if (_spiralEngine == address(0)) revert ZeroAddress();
        address oldEngine = address(spiralEngine);
        spiralEngine = ISpiralEngine(_spiralEngine);
        emit SpiralEngineUpdated(oldEngine, _spiralEngine);
    }

    /// @notice Принудительно снять активность с публикации (только ADMIN_ROLE; чужую активность)
    function forceDeactivate(uint256 activityId) external onlyRole(ADMIN_ROLE) whenNotPaused nonReentrant {
        if (activities[activityId].creator == address(0)) revert ActivityNotFound();
        if (!activities[activityId].active) revert ActivityNotActive();
        activities[activityId].active = false;
        _removeFromPublished(activityId);
        emit ActivityDeactivated(activityId, msg.sender);
    }

    // ================================
    // ======== МОДИФИКАТОРЫ ==========
    // ================================

    /// @dev Требует: msg.sender имеет ACTIVITY_CREATOR_ROLE и usedInviteByUser != 0 в SpiralEngine
    modifier onlyActivatedActivityCreator() {
        if (!spiralEngine.hasRole(ACTIVITY_CREATOR_ROLE, msg.sender)) revert NotActivatedActivityCreator();
        if (spiralEngine.usedInviteByUser(msg.sender) == 0) revert NotActivatedActivityCreator();
        _;
    }

    /// @dev Требует: msg.sender == creator активности activityId
    modifier onlyOwnActivity(uint256 activityId) {
        if (activities[activityId].creator != msg.sender) revert NotActivityCreator();
        _;
    }

    // ================================
    // ===== ЖИЗНЕННЫЙ ЦИКЛ ===========
    // ================================

    /**
     * @notice Создать активность (черновик, active = false)
     * @param activity_type Event (0) или Service (1)
     * @param metadataCID CID метаданных (не пустой)
     * @return activityId ID созданной активности
     */
    function createActivity(ActivityType activity_type, string calldata metadataCID)
        external
        whenNotPaused
        nonReentrant
        onlyActivatedActivityCreator
        returns (uint256 activityId)
    {
        if (bytes(metadataCID).length == 0) revert EmptyCID();
        unchecked {
            ++_activityIdCounter;
        }
        activityId = _activityIdCounter;
        activities[activityId] = Activity({
            id: activityId,
            creator: msg.sender,
            activity_type: activity_type,
            metadataCID: metadataCID,
            active: false
        });
        activitiesByCreator[msg.sender].push(activityId);
        emit ActivityCreated(msg.sender, activityId, activity_type, metadataCID, false);
        return activityId;
    }

    /// @notice Получить активность по ID (revert при несуществующем)
    function getActivity(uint256 activityId) external view returns (Activity memory) {
        if (activityId == 0 || activities[activityId].creator == address(0)) revert ActivityNotFound();
        return activities[activityId];
    }

    /// @notice Опубликовать активность (добавить в getPublishedActivityIds)
    function activateActivity(uint256 activityId) external whenNotPaused nonReentrant onlyOwnActivity(activityId) {
        if (activities[activityId].creator == address(0)) revert ActivityNotFound();
        if (activities[activityId].active) revert ActivityAlreadyActive();
        activities[activityId].active = true;
        publishedActivityIds.push(activityId);
        emit ActivityActivated(activityId, msg.sender);
    }

    /// @notice Снять активность с публикации (swap-and-pop в publishedActivityIds)
    function deactivateActivity(uint256 activityId) external whenNotPaused nonReentrant onlyOwnActivity(activityId) {
        if (activities[activityId].creator == address(0)) revert ActivityNotFound();
        if (!activities[activityId].active) revert ActivityNotActive();
        activities[activityId].active = false;
        _removeFromPublished(activityId);
        emit ActivityDeactivated(activityId, msg.sender);
    }

    /// @dev Удаление activityId из publishedActivityIds (swap-and-pop)
    function _removeFromPublished(uint256 activityId) private {
        uint256 len = publishedActivityIds.length;
        for (uint256 i = 0; i < len;) {
            if (publishedActivityIds[i] == activityId) {
                publishedActivityIds[i] = publishedActivityIds[len - 1];
                publishedActivityIds.pop();
                break;
            }
            unchecked {
                ++i;
            }
        }
    }

    // ================================
    // ======== VIEW ФУНКЦИИ ===========
    // ================================

    /// @notice Список ID активностей создателя
    function getActivitiesByCreator(address creator) external view returns (uint256[] memory) {
        return activitiesByCreator[creator];
    }

    /// @notice Список ID опубликованных активностей (active == true)
    function getPublishedActivityIds() external view returns (uint256[] memory) {
        return publishedActivityIds;
    }
}
