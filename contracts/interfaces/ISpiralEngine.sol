// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

/**
 * @title ISpiralEngine
 * @author Zeya888 (https://zeya888.me)
 * @dev Интерфейс контракта управления спиральной иерархией
 * @notice Определяет публичный API для SpiralEngine контракта
 */
interface ISpiralEngine {
    // === СТРУКТУРЫ ДАННЫХ ===
    
    /**
     * @dev Структура информации об инвайте
     */
    struct InviteInfo {
        string inviteCode;           // Код инвайта
        uint256 tokenId;            // ID токена инвайта
        bool isUsed;                // Статус использования
        address activatedBy;        // Адрес активатора (если инвайт использован)
        uint256 activationTime;     // Время активации
        uint256 expiry;             // Срок действия
    }
    
    /**
     * @dev Структура полной диагностики состояния селлера
     */
    struct SellerDiagnostics {
        bool isActivated;           // Статус активации пользователя
        uint256 usedInviteTokenId;  // ID использованного инвайта
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
     * @dev Событие минтинга нового инвайта
     * @param minter адрес создателя инвайта
     * @param tokenId ID созданного NFT токена
     * @param inviteCode уникальный код инвайта
     * @param expiry срок действия (0 = бессрочный)
     */
    event InviteMinted(
        address indexed minter,
        uint256 indexed tokenId,
        string inviteCode,
        uint256 expiry
    );
    
    /**
     * @dev Событие использования инвайта
     * @param user адрес пользователя, использовавшего инвайт
     * @param tokenId ID использованного инвайта
     * @param inviteCode код инвайта
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
     * @dev Минт нового инвайта
     * @param inviteCode уникальный код инвайта
     * @param expiry срок действия (0 = бессрочный)
     * @return tokenId идентификатор созданного NFT
     */
    function mintInvite(
        string memory inviteCode,
        uint256 expiry
    ) external returns (uint256 tokenId);
    
    /**
     * @dev Минт нескольких инвайтов в одной транзакции (batch)
     * @param inviteCodes массив уникальных кодов инвайтов
     * @param expiries массив сроков действия (0 = бессрочный) для каждого инвайта
     * @return tokenIds массив идентификаторов созданных NFT
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
     * @dev Получить tokenId по коду инвайта
     * @param inviteCode код инвайта
     * @return tokenId идентификатор токена
     */
    function inviteCodeToTokenId(string memory inviteCode) external view returns (uint256);
    
    /**
     * @dev Проверить существование инвайт кода
     * @param inviteCode код инвайта
     * @return exists существует ли код
     */
    function inviteCodeExists(string memory inviteCode) external view returns (bool);
    
    /**
     * @dev Получить код инвайта по tokenId
     * @param tokenId идентификатор токена
     * @return inviteCode код инвайта
     */
    function tokenIdToInviteCode(uint256 tokenId) external view returns (string memory);
    
    /**
     * @dev Проверить использован ли инвайт
     * @param tokenId идентификатор токена
     * @return isUsed использован ли инвайт
     */
    function isInviteUsed(uint256 tokenId) external view returns (bool);
    
    /**
     * @dev Получить использованный инвайт пользователя
     * @param user адрес пользователя
     * @return tokenId идентификатор использованного инвайта (+1 offset)
     */
    function usedInviteByUser(address user) external view returns (uint256);
    
    /**
     * @dev Получить срок действия инвайта
     * @param tokenId идентификатор токена
     * @return expiry timestamp срока действия (0 = бессрочный)
     */
    function inviteExpiry(uint256 tokenId) external view returns (uint256);
    
    /**
     * @dev Получить дату создания инвайта
     * @param tokenId идентификатор токена
     * @return createdAt timestamp создания
     */
    function inviteCreatedAt(uint256 tokenId) external view returns (uint256);
    
    /**
     * @dev Получить создателя инвайта
     * @param tokenId идентификатор токена
     * @return minter адрес создателя
     */
    function inviteMinter(uint256 tokenId) external view returns (address);
    
    /**
     * @dev Получить первого владельца инвайта
     * @param tokenId идентификатор токена
     * @return firstOwner адрес первого владельца
     */
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
     * @dev Проверить, является ли инвайт от активатора
     * @param tokenId идентификатор токена
     * @param activator адрес активатора
     * @return isFrom true если инвайт от активатора
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
     * @dev Получить инвайты пользователя (только владелец или админ)
     * @param user адрес пользователя
     * @return invites массив ID токенов инвайтов пользователя
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
