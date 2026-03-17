// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

/**
 * @title IActivityRegistry
 * @author Zeya888 (https://zeya888.me)
 * @notice Интерфейс контракта реестра активностей (events/services)
 * @dev Определяет публичный API для ActivityRegistry: создание, активация/деактивация,
 *      получение активностей и списков. Интеграция с SpiralEngine для проверки ACTIVATOR_ROLE и usedInviteByUser.
 * @custom:security-contact security@amanita.com
 */
interface IActivityRegistry {

    // ================================
    // ========== ТИПЫ ================
    // ================================

    /**
     * @notice Тип активности (газовая оптимизация вместо string)
     */
    enum ActivityType {
        Event,   // 0
        Service  // 1
    }

    // ================================
    // ========== СТРУКТУРЫ ===========
    // ================================

    /**
     * @notice Структура активности
     * @param id Уникальный идентификатор активности
     * @param creator Адрес создателя (владельца)
     * @param activity_type Тип: Event или Service
     * @param metadataCID Arweave/IPFS CID метаданных (полный JSON off-chain)
     * @param active false = черновик (не в поиске), true = опубликовано
     */
    struct Activity {
        uint256 id;
        address creator;
        ActivityType activity_type;
        string metadataCID;
        bool active;
    }

    // ================================
    // =========== СОБЫТИЯ ============
    // ================================

    /**
     * @notice Событие создания активности
     * @param creator Адрес создателя (indexed)
     * @param activityId ID созданной активности (indexed)
     * @param activity_type Тип активности
     * @param metadataCID CID метаданных
     * @param active Изначально false (черновик)
     */
    event ActivityCreated(
        address indexed creator,
        uint256 indexed activityId,
        ActivityType activity_type,
        string metadataCID,
        bool active
    );

    /**
     * @notice Событие публикации активности
     * @param activityId ID активности (indexed)
     * @param initiator Адрес инициатора (indexed)
     */
    event ActivityActivated(
        uint256 indexed activityId,
        address indexed initiator
    );

    /**
     * @notice Событие снятия активности с публикации
     * @param activityId ID активности (indexed)
     * @param initiator Адрес инициатора (indexed)
     */
    event ActivityDeactivated(
        uint256 indexed activityId,
        address indexed initiator
    );

    /**
     * @notice Событие обновления адреса SpiralEngine
     * @param oldSpiralEngine Предыдущий адрес (indexed)
     * @param newSpiralEngine Новый адрес (indexed)
     */
    event SpiralEngineUpdated(
        address indexed oldSpiralEngine,
        address indexed newSpiralEngine
    );

    // ================================
    // ===== ЖИЗНЕННЫЙ ЦИКЛ ===========
    // ================================

    /**
     * @notice Создать активность (черновик)
     * @param activity_type Тип: Event или Service
     * @param metadataCID CID метаданных (не пустой)
     * @return activityId ID созданной активности
     */
    function createActivity(
        ActivityType activity_type,
        string calldata metadataCID
    ) external returns (uint256 activityId);

    /**
     * @notice Опубликовать активность (добавить в поиск)
     * @param activityId ID активности (должна принадлежать msg.sender и быть неактивной)
     */
    function activateActivity(uint256 activityId) external;

    /**
     * @notice Снять активность с публикации
     * @param activityId ID активности (должна принадлежать msg.sender и быть активной)
     */
    function deactivateActivity(uint256 activityId) external;

    // ================================
    // ========== VIEW ================
    // ================================

    /**
     * @notice Получить активность по ID
     * @param activityId ID активности
     * @return Активность (revert при несуществующем id)
     */
    function getActivity(uint256 activityId) external view returns (Activity memory);

    /**
     * @notice Получить список ID активностей создателя
     * @param creator Адрес создателя
     * @return Массив activityId
     */
    function getActivitiesByCreator(address creator) external view returns (uint256[] memory);

    /**
     * @notice Получить список ID опубликованных активностей (active == true)
     * @return Массив activityId
     */
    function getPublishedActivityIds() external view returns (uint256[] memory);

    // ================================
    // ========== АДМИН ===============
    // ================================

    /**
     * @notice Приостановить контракт (только ADMIN_ROLE)
     */
    function pause() external;

    /**
     * @notice Снять приостановку (только ADMIN_ROLE)
     */
    function unpause() external;

    /**
     * @notice Установить адрес SpiralEngine (только ADMIN_ROLE, whenNotPaused)
     * @param _spiralEngine Адрес контракта SpiralEngine
     */
    function setSpiralEngine(address _spiralEngine) external;

    /**
     * @notice Принудительно снять активность с публикации (только ADMIN_ROLE; чужую активность)
     * @param activityId ID активности
     */
    function forceDeactivate(uint256 activityId) external;
}
