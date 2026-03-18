// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../IERC5192.sol";

/**
 * @title ISoulIdentity
 * @author Zeya888 (https://zeya888.me)
 * @dev Интерфейс для управления Soulbound Token функциональностью
 * @notice Обеспечивает непередаваемость токенов и систему восстановления доступа
 */
interface ISoulIdentity is IERC5192 {
    // === СОБЫТИЯ SBT ===
    
    /**
     * @dev Событие при обновлении уровня души
     * @param user пользователь, чей уровень обновлен
     * @param oldLevel старый уровень
     * @param newLevel новый уровень
     * @param timestamp время обновления
     */
    event SoulLevelUpdated(address indexed user, uint256 oldLevel, uint256 newLevel, uint256 timestamp);
    
    /**
     * @dev Событие при изменении репутации души
     * @param user пользователь, чья репутация изменена
     * @param change изменение репутации (может быть отрицательным)
     * @param newReputation новая репутация
     * @param timestamp время изменения
     */
    event SoulReputationChanged(address indexed user, int256 change, uint256 newReputation, uint256 timestamp);
    
    /**
     * @dev Событие при связывании идентичности души
     * @param user пользователь, связавший идентичность
     * @param did DID идентификатор
     * @param timestamp время связывания
     */
    event SoulIdentityLinked(address indexed user, string did, uint256 timestamp);
    
    /**
     * @dev Событие при обновлении уровня верификации души
     * @param user пользователь, чей уровень верификации обновлен
     * @param oldLevel старый уровень верификации
     * @param newLevel новый уровень верификации
     * @param timestamp время обновления
     */
    event SoulVerificationLevelUpdated(address indexed user, uint8 oldLevel, uint8 newLevel, uint256 timestamp);
    
    /**
     * @dev Событие при добавлении доверенного лица
     * @param user пользователь, добавивший guardian
     * @param guardian адрес доверенного лица
     * @param timestamp время добавления
     */
    event GuardianAdded(address indexed user, address indexed guardian, uint256 timestamp);
    
    /**
     * @dev Событие при удалении доверенного лица
     * @param user пользователь, удаливший guardian
     * @param guardian адрес доверенного лица
     * @param timestamp время удаления
     */
    event GuardianRemoved(address indexed user, address indexed guardian, uint256 timestamp);
    
    /**
     * @dev Событие при инициации восстановления доступа
     * @param user пользователь, для которого инициируется восстановление
     * @param guardian guardian, инициировавший восстановление
     * @param timestamp время инициации
     */
    event RecoveryInitiated(address indexed user, address indexed guardian, uint256 timestamp);
    
    /**
     * @dev Событие при завершении восстановления доступа
     * @param user пользователь, для которого завершено восстановление
     * @param newKey новый ключ доступа
     * @param timestamp время завершения
     */
    event RecoveryCompleted(address indexed user, address indexed newKey, uint256 timestamp);
    
    /**
     * @dev Событие при создании временного ключа
     * @param user пользователь, создавший временный ключ
     * @param tempKey временный ключ
     * @param expiry срок действия
     * @param timestamp время создания
     */
    event TemporaryKeyCreated(address indexed user, address indexed tempKey, uint256 expiry, uint256 timestamp);
    
    /**
     * @dev Событие при обновлении метаданных SBT
     * @param tokenId идентификатор токена
     * @param sbtType тип SBT
     * @param attributes атрибуты
     * @param timestamp время обновления
     */
    event SBTMetadataUpdated(uint256 indexed tokenId, string sbtType, string attributes, uint256 timestamp);
    
    /**
     * @dev Событие при обновлении версии SBT
     * @param tokenId идентификатор токена
     * @param version новая версия
     * @param timestamp время обновления
     */
    event SBTVersionUpdated(uint256 indexed tokenId, uint256 version, uint256 timestamp);

    // === SBT CORE FUNCTIONS ===
    
    /**
     * @dev SBT токены не могут быть одобрены для делегирования управления
     * @param to адрес, которому пытаются дать одобрение
     * @param tokenId идентификатор токена
     */
    function approve(address to, uint256 tokenId) external;
    
    /**
     * @dev SBT токены не могут быть одобрены для глобального управления
     * @param operator адрес оператора
     * @param approved статус одобрения
     */
    function setApprovalForAll(address operator, bool approved) external;
    
    /**
     * @dev SBT токены не имеют одобренных операторов
     * @param tokenId идентификатор токена
     * @return address(0) всегда, так как SBT не могут быть одобрены
     */
    function getApproved(uint256 tokenId) external view returns (address);
    
    /**
     * @dev SBT токены не имеют глобальных одобрений
     * @param owner владелец токена
     * @param operator оператор
     * @return false всегда, так как SBT не могут быть одобрены
     */
    function isApprovedForAll(address owner, address operator) external view returns (bool);
    
    /**
     * @dev Проверяет, заблокирован ли токен (всегда true для SBT)
     * @param tokenId идентификатор токена для проверки
     * @return true всегда, так как все токены являются SBT
     */
    function locked(uint256 tokenId) external view returns (bool);

    // === RECOVERY SYSTEM FUNCTIONS ===
    
    /**
     * @dev Добавить доверенное лицо для восстановления доступа
     * @param guardian адрес доверенного лица
     */
    function addTrustedGuardian(address guardian) external;
    
    /**
     * @dev Удалить доверенное лицо
     * @param guardian адрес доверенного лица
     */
    function removeTrustedGuardian(address guardian) external;
    
    /**
     * @dev Получить список доверенных лиц пользователя
     * @param user адрес пользователя
     * @return массив адресов доверенных лиц
     */
    function getTrustedGuardians(address user) external view returns (address[] memory);
    
    /**
     * @dev Проверить, является ли адрес доверенным лицом
     * @param user адрес пользователя
     * @param guardian адрес для проверки
     * @return true если адрес является доверенным лицом
     */
    function isTrustedGuardian(address user, address guardian) external view returns (bool);
    
    /**
     * @dev Инициировать процесс восстановления доступа
     * @param user адрес пользователя, для которого инициируется восстановление
     */
    function initiateRecovery(address user) external;
    
    /**
     * @dev Завершить процесс восстановления доступа
     * @param user адрес пользователя
     * @param newKey новый ключ доступа
     */
    function completeRecovery(address user, address newKey) external;
    
    /**
     * @dev Проверить, идет ли процесс восстановления
     * @param user адрес пользователя
     * @return true если процесс восстановления активен
     */
    function isRecoveryInProgress(address user) external view returns (bool);
    
    /**
     * @dev Создать временный ключ доступа
     * @param tempKey адрес временного ключа
     * @param duration продолжительность действия в секундах
     */
    function createTemporaryKey(address tempKey, uint256 duration) external;
    
    /**
     * @dev Получить временный ключ пользователя
     * @param user адрес пользователя
     * @return адрес временного ключа
     */
    function getTemporaryKey(address user) external view returns (address);
    
    /**
     * @dev Проверить, действителен ли временный ключ
     * @param tempKey адрес временного ключа
     * @return true если ключ действителен
     */
    function isTemporaryKeyValid(address tempKey) external view returns (bool);

    // === SBT METADATA FUNCTIONS ===
    
    /**
     * @dev Получить расширенные метаданные SBT
     * @param tokenId идентификатор токена
     * @return tokenSbtType тип SBT
     * @return version версия SBT
     * @return attributes дополнительные атрибуты
     * @return isLocked заблокирован ли токен
     */
    function getSBTMetadata(uint256 tokenId) external view returns (
        string memory tokenSbtType,
        uint256 version,
        string memory attributes,
        bool isLocked
    );
    
    /**
     * @dev Обновить метаданные SBT (только владелец)
     * @param tokenId идентификатор токена
     * @param newSbtType новый тип SBT
     * @param newAttributes новые атрибуты
     */
    function updateSBTMetadata(uint256 tokenId, string memory newSbtType, string memory newAttributes) external;
    
    /**
     * @dev Обновить версию SBT (только админ)
     * @param tokenId идентификатор токена
     * @param newVersion новая версия
     */
    function updateSBTVersion(uint256 tokenId, uint256 newVersion) external;
    
    /**
     * @dev Получить версию SBT токена
     * @param tokenId идентификатор токена
     * @return версия SBT
     */
    function getSBTVersion(uint256 tokenId) external view returns (uint256);
    
    /**
     * @dev Проверить, является ли токен SBT
     * @param tokenId идентификатор токена
     * @return true если токен является SBT
     */
    function isSBT(uint256 tokenId) external view returns (bool);
    
    /**
     * @dev Получить тип SBT токена
     * @param tokenId идентификатор токена
     * @return тип SBT
     */
    function getSBTType(uint256 tokenId) external view returns (string memory);
    
    /**
     * @dev Получить атрибуты SBT токена
     * @param tokenId идентификатор токена
     * @return атрибуты SBT
     */
    function getSBTAttributes(uint256 tokenId) external view returns (string memory);

    // === SOUL СТАТУСЫ ===
    
    /**
     * @dev Получить уровень души пользователя
     * @param user адрес пользователя
     * @return уровень души
     */
    function getSoulLevel(address user) external view returns (uint256);
    
    /**
     * @dev Получить репутацию души пользователя
     * @param user адрес пользователя
     * @return репутация души
     */
    function getSoulReputation(address user) external view returns (uint256);
    
    /**
     * @dev Получить идентичность души пользователя
     * @param user адрес пользователя
     * @return DID идентификатор
     */
    function getSoulIdentity(address user) external view returns (string memory);
    
    /**
     * @dev Получить уровень верификации души пользователя
     * @param user адрес пользователя
     * @return уровень верификации (0-5)
     */
    function getSoulVerificationLevel(address user) external view returns (uint8);
    
    /**
     * @dev Получить полный профиль души пользователя
     * @param user адрес пользователя
     * @return level уровень души
     * @return reputation репутация души
     * @return identity идентичность души (DID)
     * @return verificationLevel уровень верификации
     * @return guardians список доверенных лиц
     * @return displayName отображаемое имя (Passport MVP)
     * @return handle community-prefixed handle, напр. @spiral:handle (Passport MVP)
     */
    function getSoulProfile(address user) external view returns (
        uint256 level,
        uint256 reputation,
        string memory identity,
        uint8 verificationLevel,
        address[] memory guardians,
        string memory displayName,
        string memory handle
    );

    /**
     * @dev Получить displayName пользователя (Passport MVP)
     */
    function getDisplayName(address user) external view returns (string memory);

    /**
     * @dev Получить handle пользователя, формат @communityId:handle (Passport MVP)
     */
    function getHandle(address user) external view returns (string memory);

    /**
     * @dev Установить/обновить displayName (только владелец души). Макс. 64 байт.
     */
    function setDisplayName(string calldata displayName) external;

    /**
     * @dev Установить/обновить handle, формат @communityId:localHandle (только владелец души). Макс. 32 байт.
     */
    function setHandle(string calldata handle) external;

    // === EXTERNAL IDENTITY MANAGEMENT ===
    
    /**
     * @dev Структура для внешних идентичностей
     */
    struct ExternalIdentity {
        string identityType;    // "did:spiral", "did:polygon", "did:ethr"
        string identityValue;   // фактическое значение DID
        bool verified;          // статус верификации
        uint256 createdAt;      // время создания
        address verifiedBy;     // кто верифицировал (0x0 для legacy)
    }
    
    /**
     * @dev Событие при связывании внешней идентичности
     * @param user пользователь, связавший идентичность
     * @param identityType тип идентичности
     * @param identityValue значение идентичности
     * @param verified статус верификации
     * @param timestamp время связывания
     */
    event ExternalIdentityLinked(
        address indexed user,
        string identityType,
        string identityValue,
        bool verified,
        uint256 timestamp
    );
    
    /**
     * @dev Связать внешнюю идентичность с адресом
     * @param user адрес пользователя
     * @param identityType тип идентичности ("did:spiral", "did:polygon")
     * @param identityValue значение идентичности
     * @param verified статус верификации
     */
    function linkExternalIdentity(
        address user,
        string memory identityType,
        string memory identityValue,
        bool verified
    ) external;
    
    /**
     * @dev Получить основную идентичность пользователя
     * @param user адрес пользователя
     * @return identity структура основной идентичности
     */
    function getPrimaryIdentity(address user) 
        external view returns (ExternalIdentity memory identity);
    
    /**
     * @dev Получить все идентичности пользователя
     * @param user адрес пользователя
     * @return identities массив всех идентичностей
     */
    function getAllIdentities(address user) 
        external view returns (ExternalIdentity[] memory identities);
    
    /**
     * @dev Проверить наличие идентичности определенного типа
     * @param user адрес пользователя
     * @param identityType тип идентичности
     * @return hasIdentity есть ли идентичность данного типа
     */
    function hasIdentityType(address user, string memory identityType) 
        external view returns (bool hasIdentity);

    // === ОБНОВЛЕНИЕ SOUL СТАТУСА ===
    
    /**
     * @dev Обновить уровень души пользователя
     * @param user адрес пользователя
     * @param newLevel новый уровень души
     */
    function updateSoulLevel(address user, uint256 newLevel) external;
    
    /**
     * @dev Изменить репутацию души пользователя
     * @param user адрес пользователя
     * @param change изменение репутации (может быть отрицательным)
     */
    function updateSoulReputation(address user, int256 change) external;
    
    /**
     * @dev Связать идентичность души с DID (DEPRECATED - используйте linkExternalIdentity)
     * @param did DID идентификатор
     */
    function linkSoulIdentity(string memory did) external;
    
    /**
     * @dev Отвязать идентичность души
     */
    function unlinkSoulIdentity() external;
    
    /**
     * @dev Обновить уровень верификации души
     * @param user адрес пользователя
     * @param level новый уровень верификации (0-5)
     */
    function updateSoulVerificationLevel(address user, uint8 level) external;
    
    /**
     * @dev Проверить, связана ли идентичность души
     * @param user адрес пользователя
     * @return true если идентичность связана
     */
    function hasSoulIdentityLinked(address user) external view returns (bool);
    
    /**
     * @dev Получить адрес по DID идентичности
     * @param did DID идентификатор
     * @return адрес пользователя
     */
    function getAddressBySoulIdentity(string memory did) external view returns (address);
}
