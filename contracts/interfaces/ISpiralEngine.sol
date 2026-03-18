// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

/**
 * @title ISpiralEngine
 * @author Zeya888 (https://zeya888.me)
 * @dev Интерфейс контракта управления спиральной иерархией
 * @notice Инвайты — только лог (inviteId); uint256 в API = inviteId (id записи инвайта). Сигнатуры сохранены для обратной совместимости.
 */
interface ISpiralEngine {
    // === СТРУКТУРЫ ДАННЫХ ===
    
    /**
     * @dev Структура информации об инвайте
     * @notice tokenId в структуре = inviteId (id записи инвайта)
     */
    struct InviteInfo {
        string inviteCode;
        uint256 tokenId;            // inviteId, совместимость API
        bool isUsed;
        address activatedBy;
        uint256 activationTime;
        uint256 expiry;
    }
    
    struct SellerDiagnostics {
        bool isActivated;
        uint256 usedInviteTokenId;  // inviteId использованного инвайта
        bool hasSellerRole;         // Наличие роли SELLER_ROLE
        bool hasActivatorRole;      // Наличие роли ACTIVATOR_ROLE
        InviteInfo[] userInvites;   // Массив инвайтов пользователя
        uint256 totalInvitesMinted; // Общее количество заминченных инвайтов
    }
    
    // === КОНСТАНТЫ (как view функции) ===
    
    /**
     * @dev Получить роль продавца
     * @return bytes32 идентификатор роли SELLER_ROLE
     */
    function SELLER_ROLE() external view returns (bytes32);
    
    /**
     * @dev Получить роль активатора
     * @return bytes32 идентификатор роли ACTIVATOR_ROLE
     */
    function ACTIVATOR_ROLE() external view returns (bytes32);
    
    /**
     * @dev Проверить наличие роли у пользователя (из AccessControl)
     * @param role идентификатор роли
     * @param account адрес для проверки
     * @return true если пользователь имеет роль
     * @notice Этот метод нужен для интеграции с OrganicComponentRegistry
     */
    function hasRole(bytes32 role, address account) external view returns (bool);
    
    // === СОБЫТИЯ ===
    
    /**
     * @dev Событие создания новой записи инвайта (inviteId = id записи, не NFT)
     */
    event InviteMinted(
        address indexed minter,
        uint256 indexed tokenId,    // inviteId
        string inviteCode,
        uint256 expiry
    );
    
    /**
     * @dev Событие использования инвайта
     * @param tokenId inviteId использованного инвайта
     */
    event InviteUsed(
        address indexed user,
        uint256 indexed tokenId,
        string inviteCode
    );
    
    /**
     * @dev Событие активации пользователя
     * @param user адрес активированного пользователя
     * @param activator адрес активатора
     * @param timestamp время активации
     */
    event UserActivated(
        address indexed user,
        address indexed activator,
        uint256 timestamp
    );
    
    /**
     * @dev Событие назначения роли продавца
     * @param user адрес пользователя, получившего роль
     * @param nominator адрес номинатора
     * @param timestamp время назначения
     */
    event SellerRoleGranted(
        address indexed user,
        address indexed nominator,
        uint256 timestamp
    );
    
    /**
     * @dev Событие приостановки пользователя
     * @param user адрес приостановленного пользователя
     * @param until до какого времени приостановлен
     * @param reason причина приостановки
     */
    event UserSuspended(
        address indexed user,
        uint256 until,
        string reason
    );
    
    /**
     * @dev Событие обновления адреса SoulIdentity контракта
     * @param oldSoulIdentity предыдущий адрес
     * @param newSoulIdentity новый адрес
     */
    event SoulIdentityUpdated(
        address indexed oldSoulIdentity,
        address indexed newSoulIdentity
    );
    
    // === ОСНОВНЫЕ ФУНКЦИИ УПРАВЛЕНИЯ ИНВАЙТАМИ ===
    
    /**
     * @dev Создание новой записи инвайта (inviteId, без ERC721)
     * @return tokenId inviteId созданной записи (совместимость API)
     */
    function mintInvite(
        string memory inviteCode,
        uint256 expiry
    ) external returns (uint256 tokenId);
    
    /**
     * @dev Создание нескольких записей инвайтов (batch)
     * @return tokenIds массив inviteId (совместимость API)
     */
    function mintInviteBatch(
        string[] calldata inviteCodes,
        uint256[] calldata expiries
    ) external returns (uint256[] memory tokenIds);
    
    /**
     * @dev Активация пользователя с помощью инвайта
     * @param inviteCode код инвайта
     * @param user адрес пользователя для активации
     * @param newInviteCodes новые инвайты для пользователя (ровно 12)
     * @param expiry срок действия новых инвайтов
     */
    function activateUser(
        string memory inviteCode,
        address user,
        string[] memory newInviteCodes,
        uint256 expiry
    ) external;
    
    /**
     * @dev Назначение роли продавца
     * @param user адрес пользователя
     */
    function grantSellerRole(address user) external;
    
    /**
     * @dev Приостановка пользователя
     * @param user адрес пользователя
     * @param duration продолжительность приостановки в секундах
     * @param reason причина приостановки
     */
    function suspendUser(
        address user,
        uint256 duration,
        string memory reason
    ) external;
    
    // === VIEW ФУНКЦИИ - ДАННЫЕ ИНВАЙТОВ ===
    
    /**
     * @dev Получить inviteId по коду инвайта (совместимость: возвращаемый тип uint256 = inviteId)
     */
    function inviteCodeToTokenId(string memory inviteCode) external view returns (uint256);
    
    function inviteCodeExists(string memory inviteCode) external view returns (bool);
    
    /**
     * @dev Получить код инвайта по inviteId (параметр tokenId = inviteId для совместимости API)
     */
    function tokenIdToInviteCode(uint256 tokenId) external view returns (string memory);
    
    /**
     * @dev Проверить использован ли инвайт (tokenId = inviteId)
     */
    function isInviteUsed(uint256 tokenId) external view returns (bool);
    
    /**
     * @dev Получить использованный инвайт пользователя (возврат: inviteId + 1 offset)
     */
    function usedInviteByUser(address user) external view returns (uint256);
    
    /** @dev Срок действия инвайта (tokenId = inviteId) */
    function inviteExpiry(uint256 tokenId) external view returns (uint256);
    
    /** @dev Дата создания инвайта (tokenId = inviteId) */
    function inviteCreatedAt(uint256 tokenId) external view returns (uint256);
    
    /** @dev Создатель записи инвайта (tokenId = inviteId) */
    function inviteMinter(uint256 tokenId) external view returns (address);
    
    /** @dev Первый владелец записи инвайта (tokenId = inviteId) */
    function inviteFirstOwner(uint256 tokenId) external view returns (address);
    
    /**
     * @dev Получить общее количество использованных инвайтов
     * @return count количество использованных инвайтов
     */
    function totalInvitesUsed() external view returns (uint256);
    
    /**
     * @dev Получить общее количество выпущенных инвайтов
     * @return count количество выпущенных инвайтов
     */
    function totalInvitesMinted() external view returns (uint256);
    
    // inviteTransferHistory объявлен как public mapping - автоматический getter с другой сигнатурой
    // activatedUsers объявлен как public array - автоматический getter по индексу
    
    /**
     * @dev Получить количество инвайтов пользователя
     * @param user адрес пользователя
     * @return count количество инвайтов
     */
    function userInviteCount(address user) external view returns (uint256);
    
    // === VIEW ФУНКЦИИ - ОТСЛЕЖИВАНИЕ ОТВЕТСТВЕННОСТИ ===
    
    /**
     * @dev Получить активатора пользователя
     * @param user адрес пользователя
     * @return activator адрес активатора
     */
    function userActivator(address user) external view returns (address);
    
    /**
     * @dev Получить номинатора селлера
     * @param user адрес пользователя
     * @return nominator адрес номинатора
     */
    function sellerNominator(address user) external view returns (address);
    
    // activatedBy и nominatedSellers объявлены как public mappings - автоматические getters по индексу
    
    // === VIEW ФУНКЦИИ - СИСТЕМА САНКЦИЙ ===
    
    /**
     * @dev Получить количество нарушений пользователя
     * @param user адрес пользователя
     * @return count количество нарушений
     */
    function violationCount(address user) external view returns (uint256);
    
    /**
     * @dev Получить до какого времени заблокирован пользователь
     * @param user адрес пользователя
     * @return until timestamp окончания блокировки
     */
    function suspensionUntil(address user) external view returns (uint256);
    
    /**
     * @dev Получить количество нарушений активированных пользователей
     * @param activator адрес активатора
     * @return count количество нарушений
     */
    function activationViolations(address activator) external view returns (uint256);
    
    /**
     * @dev Получить количество нарушений назначенных селлеров
     * @param nominator адрес номинатора
     * @return count количество нарушений
     */
    function nominationViolations(address nominator) external view returns (uint256);
    
    // === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
    
    /**
     * @dev Получить размер круга активатора
     * @param activator адрес активатора
     * @return size размер круга
     */
    function getCircleSize(address activator) external view returns (uint256);
    
    /**
     * @dev Получить членов круга активатора
     * @param activator адрес активатора
     * @return members массив адресов членов круга
     */
    function getCircleMembers(address activator) external view returns (address[] memory);
    
    /**
     * @dev Проверить, является ли инвайт от активатора (tokenId = inviteId)
     */
    function isInviteFromActivator(uint256 tokenId, address activator) external view returns (bool);
    
    // === УПРАВЛЕНИЕ SOUL IDENTITY ===
    
    /**
     * @dev Установить адрес контракта SoulIdentity
     * @param _soulIdentity адрес контракта SoulIdentity
     */
    function setSoulIdentity(address _soulIdentity) external;
    
    // soulIdentity() не нужен - public state variable автоматически создаёт getter
    
    // === ДЕЛЕГИРОВАНИЕ К SOUL IDENTITY ===
    
    /**
     * @dev Получить уровень души пользователя
     * @param user адрес пользователя
     * @return level уровень души
     */
    function getSoulLevel(address user) external view returns (uint256);
    
    /**
     * @dev Получить репутацию души пользователя
     * @param user адрес пользователя
     * @return reputation репутация души
     */
    function getSoulReputation(address user) external view returns (uint256);
    
    /**
     * @dev Получить идентичность души пользователя
     * @param user адрес пользователя
     * @return identity DID идентификатор
     */
    function getSoulIdentity(address user) external view returns (string memory);
    
    /**
     * @dev Получить уровень верификации души пользователя
     * @param user адрес пользователя
     * @return verificationLevel уровень верификации
     */
    function getSoulVerificationLevel(address user) external view returns (uint8);
    
    /**
     * @dev Получить полный профиль души пользователя
     * @param user адрес пользователя
     * @return level уровень души
     * @return reputation репутация души
     * @return identity идентичность души
     * @return verificationLevel уровень верификации
     * @return guardians список доверенных лиц
     */
    function getSoulProfile(address user) external view returns (
        uint256 level,
        uint256 reputation,
        string memory identity,
        uint8 verificationLevel,
        address[] memory guardians
    );
    
    // === ДИАГНОСТИЧЕСКИЕ ФУНКЦИИ ===
    
    /**
     * @dev Получить полную диагностику состояния селлера
     * @param seller адрес селлера для диагностики
     * @return diagnostics диагностическая информация о состоянии селлера
     */
    function getSellerDiagnostics(address seller) external view returns (SellerDiagnostics memory);
    
    /**
     * @dev Получить инвайты пользователя (только владелец или админ). Возвращает массив inviteId.
     */
    function getUserInvites(address user) external view returns (uint256[] memory);
    
    /**
     * @dev Получить количество инвайтов пользователя (публичный доступ)
     * @param user адрес пользователя
     * @return count количество инвайтов
     */
    function getUserInviteCount(address user) external view returns (uint256);
    
    /**
     * @dev Получить публичную информацию о селлере (без приватных данных)
     * @param seller адрес селлера
     * @return isActivated статус активации пользователя
     * @return hasSellerRole наличие роли SELLER_ROLE
     * @return hasActivatorRole наличие роли ACTIVATOR_ROLE
     * @return inviteCount количество инвайтов пользователя
     * @return userTotalInvites общее количество заминченных инвайтов пользователем
     */
    function getSellerPublicInfo(address seller) external view returns (
        bool isActivated,
        bool hasSellerRole,
        bool hasActivatorRole,
        uint256 inviteCount,
        uint256 userTotalInvites
    );
}
