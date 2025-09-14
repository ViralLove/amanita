// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./interfaces/ISoulIdentity.sol";

/**
 * @title SoulIdentity
 * @author Zeya888 (https://zeya888.me)
 * @dev Контракт для управления Soulbound Token функциональностью и Soul статусами
 * @notice Обеспечивает непередаваемость токенов, систему восстановления доступа и управление "душой" пользователя
 * @notice Управляет статусом, репутацией и идентичностью пользователей в спиральной системе
 */
contract SoulIdentity is ERC721, AccessControl, ISoulIdentity {
    // === РОЛИ ===
    bytes32 public constant SOUL_MANAGER_ROLE = keccak256("SOUL_MANAGER_ROLE");
    bytes32 public constant SOUL_VERIFIER_ROLE = keccak256("SOUL_VERIFIER_ROLE");
    
    // === СОСТОЯНИЕ SOUL ===
    
    // Уровни души пользователей
    mapping(address => uint256) public soulLevel;
    
    // Репутация души пользователей
    mapping(address => uint256) public soulReputation;
    
    // DID идентичности пользователей
    mapping(address => string) public soulIdentity;
    
    // Обратное отображение DID -> адрес
    mapping(string => address) public addressBySoulIdentity;
    
    // Уровни верификации души (0-5)
    mapping(address => uint8) public soulVerificationLevel;
    
    // === СИСТЕМА ВОССТАНОВЛЕНИЯ ===
    
    // Доверенные лица для восстановления
    mapping(address => mapping(address => bool)) public trustedGuardians;
    mapping(address => address[]) public userGuardians;
    
    // Активные процессы восстановления
    mapping(address => bool) public recoveryInProgress;
    mapping(address => address) public recoveryInitiator;
    
    // Временные ключи доступа
    mapping(address => address) public temporaryKeys;
    mapping(address => uint256) public temporaryKeyExpiry;
    
    // === SBT МЕТАДАННЫЕ ===
    
    // Версии SBT токенов
    mapping(uint256 => uint256) public sbtVersion;
    
    // Типы SBT токенов
    mapping(uint256 => string) public sbtType;
    
    // Атрибуты SBT токенов
    mapping(uint256 => string) public sbtAttributes;
    
    // === КОНСТРУКТОР ===
    
    constructor() ERC721("SoulIdentity", "SOUL") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(SOUL_MANAGER_ROLE, msg.sender);
        _grantRole(SOUL_VERIFIER_ROLE, msg.sender);
    }
    
    // === SBT CORE FUNCTIONS ===
    
    /**
     * @dev SBT токены не могут быть одобрены для делегирования управления
     * @notice всегда вызывает revert
     */
    function approve(address /* to */, uint256 /* tokenId */) public pure override(ERC721, ISoulIdentity) {
        revert("SBT: approval not allowed");
    }
    
    /**
     * @dev SBT токены не могут быть одобрены для глобального управления
     * @notice всегда вызывает revert
     */
    function setApprovalForAll(address /* operator */, bool /* approved */) public pure override(ERC721, ISoulIdentity) {
        revert("SBT: approval not allowed");
    }
    
    /**
     * @dev SBT токены не имеют одобренных операторов
     * @return address(0) всегда, так как SBT не могут быть одобрены
     */
    function getApproved(uint256 /* tokenId */) public pure override(ERC721, ISoulIdentity) returns (address) {
        return address(0);
    }
    
    /**
     * @dev SBT токены не имеют глобальных одобрений
     * @return false всегда, так как SBT не могут быть одобрены
     */
    function isApprovedForAll(address /* owner */, address /* operator */) public pure override(ERC721, ISoulIdentity) returns (bool) {
        return false;
    }
    
    /**
     * @dev Проверяет, заблокирован ли токен (всегда true для SBT)
     * @return true всегда, так как все токены являются SBT
     */
    function locked(uint256 /* tokenId */) public pure override returns (bool) {
        return true;
    }
    
    /**
     * @dev Поддержка интерфейсов
     */
    function supportsInterface(bytes4 interfaceId) public view override(ERC721, AccessControl) returns (bool) {
        return interfaceId == type(ISoulIdentity).interfaceId || 
               interfaceId == type(IERC5192).interfaceId ||
               super.supportsInterface(interfaceId);
    }
    
    // === SOUL СТАТУСЫ ===
    
    /**
     * @dev Получить уровень души пользователя
     * @param user адрес пользователя
     * @return уровень души
     */
    function getSoulLevel(address user) public view override returns (uint256) {
        return soulLevel[user];
    }
    
    /**
     * @dev Получить репутацию души пользователя
     * @param user адрес пользователя
     * @return репутация души
     */
    function getSoulReputation(address user) public view override returns (uint256) {
        return soulReputation[user];
    }
    
    /**
     * @dev Получить идентичность души пользователя
     * @param user адрес пользователя
     * @return DID идентификатор
     */
    function getSoulIdentity(address user) public view override returns (string memory) {
        return soulIdentity[user];
    }
    
    /**
     * @dev Получить уровень верификации души пользователя
     * @param user адрес пользователя
     * @return уровень верификации (0-5)
     */
    function getSoulVerificationLevel(address user) public view override returns (uint8) {
        return soulVerificationLevel[user];
    }
    
    /**
     * @dev Получить полный профиль души пользователя
     * @param user адрес пользователя
     * @return level уровень души
     * @return reputation репутация души
     * @return identity идентичность души (DID)
     * @return verificationLevel уровень верификации
     * @return guardians список доверенных лиц
     */
    function getSoulProfile(address user) public view override returns (
        uint256 level,
        uint256 reputation,
        string memory identity,
        uint8 verificationLevel,
        address[] memory guardians
    ) {
        return (
            soulLevel[user],
            soulReputation[user],
            soulIdentity[user],
            soulVerificationLevel[user],
            userGuardians[user]
        );
    }
    
    // === ОБНОВЛЕНИЕ SOUL СТАТУСА ===
    
    /**
     * @dev Обновить уровень души пользователя
     * @param user адрес пользователя
     * @param newLevel новый уровень души
     */
    function updateSoulLevel(address user, uint256 newLevel) public override onlyRole(SOUL_MANAGER_ROLE) {
        uint256 oldLevel = soulLevel[user];
        soulLevel[user] = newLevel;
        emit SoulLevelUpdated(user, oldLevel, newLevel, block.timestamp);
    }
    
    /**
     * @dev Изменить репутацию души пользователя
     * @param user адрес пользователя
     * @param change изменение репутации (может быть отрицательным)
     */
    function updateSoulReputation(address user, int256 change) public override onlyRole(SOUL_MANAGER_ROLE) {
        uint256 currentReputation = soulReputation[user];
        uint256 newReputation;
        
        if (change < 0) {
            // Предотвращаем отрицательную репутацию
            if (currentReputation >= uint256(-change)) {
                newReputation = currentReputation - uint256(-change);
            } else {
                newReputation = 0;
            }
        } else {
            newReputation = currentReputation + uint256(change);
        }
        
        soulReputation[user] = newReputation;
        emit SoulReputationChanged(user, change, newReputation, block.timestamp);
    }
    
    /**
     * @dev Связать идентичность души с DID
     * @param did DID идентификатор
     */
    function linkSoulIdentity(string memory did) public override {
        require(bytes(soulIdentity[msg.sender]).length == 0, "SoulIdentity: already linked");
        require(addressBySoulIdentity[did] == address(0), "SoulIdentity: DID already in use");
        
        soulIdentity[msg.sender] = did;
        addressBySoulIdentity[did] = msg.sender;
        emit SoulIdentityLinked(msg.sender, did, block.timestamp);
    }
    
    /**
     * @dev Отвязать идентичность души
     */
    function unlinkSoulIdentity() public override {
        string memory did = soulIdentity[msg.sender];
        require(bytes(did).length > 0, "SoulIdentity: not linked");
        
        delete soulIdentity[msg.sender];
        delete addressBySoulIdentity[did];
        emit SoulIdentityLinked(msg.sender, "", block.timestamp);
    }
    
    /**
     * @dev Обновить уровень верификации души
     * @param user адрес пользователя
     * @param level новый уровень верификации (0-5)
     */
    function updateSoulVerificationLevel(address user, uint8 level) public override onlyRole(SOUL_VERIFIER_ROLE) {
        require(level <= 5, "SoulIdentity: invalid verification level");
        
        uint8 oldLevel = soulVerificationLevel[user];
        soulVerificationLevel[user] = level;
        emit SoulVerificationLevelUpdated(user, oldLevel, level, block.timestamp);
    }
    
    /**
     * @dev Проверить, связана ли идентичность души
     * @param user адрес пользователя
     * @return true если идентичность связана
     */
    function hasSoulIdentityLinked(address user) public view override returns (bool) {
        return bytes(soulIdentity[user]).length > 0;
    }
    
    /**
     * @dev Получить адрес по DID идентичности
     * @param did DID идентификатор
     * @return адрес пользователя
     */
    function getAddressBySoulIdentity(string memory did) public view override returns (address) {
        return addressBySoulIdentity[did];
    }
    
    // === СИСТЕМА ВОССТАНОВЛЕНИЯ ДУШИ ===
    
    /**
     * @dev Добавить доверенное лицо для восстановления души
     * @param guardian адрес доверенного лица
     */
    function addTrustedGuardian(address guardian) public override {
        require(guardian != address(0), "SoulIdentity: invalid guardian");
        require(guardian != msg.sender, "SoulIdentity: cannot be own guardian");
        require(!trustedGuardians[msg.sender][guardian], "SoulIdentity: already a guardian");
        
        trustedGuardians[msg.sender][guardian] = true;
        userGuardians[msg.sender].push(guardian);
        emit GuardianAdded(msg.sender, guardian, block.timestamp);
    }
    
    /**
     * @dev Удалить доверенное лицо
     * @param guardian адрес доверенного лица
     */
    function removeTrustedGuardian(address guardian) public override {
        require(trustedGuardians[msg.sender][guardian], "SoulIdentity: not a guardian");
        
        trustedGuardians[msg.sender][guardian] = false;
        
        // Удаляем из массива
        address[] storage guardians = userGuardians[msg.sender];
        for (uint256 i = 0; i < guardians.length; i++) {
            if (guardians[i] == guardian) {
                guardians[i] = guardians[guardians.length - 1];
                guardians.pop();
                break;
            }
        }
        
        emit GuardianRemoved(msg.sender, guardian, block.timestamp);
    }
    
    /**
     * @dev Получить список доверенных лиц души пользователя
     * @param user адрес пользователя
     * @return массив адресов доверенных лиц
     */
    function getTrustedGuardians(address user) public view override returns (address[] memory) {
        return userGuardians[user];
    }
    
    /**
     * @dev Проверить, является ли адрес доверенным лицом души
     * @param user адрес пользователя
     * @param guardian адрес для проверки
     * @return true если адрес является доверенным лицом
     */
    function isTrustedGuardian(address user, address guardian) public view override returns (bool) {
        return trustedGuardians[user][guardian];
    }
    
    /**
     * @dev Инициировать процесс восстановления души
     * @param user адрес пользователя, для которого инициируется восстановление
     */
    function initiateRecovery(address user) public override {
        require(trustedGuardians[user][msg.sender], "SoulIdentity: not a trusted guardian");
        require(!recoveryInProgress[user], "SoulIdentity: recovery already in progress");
        
        recoveryInProgress[user] = true;
        recoveryInitiator[user] = msg.sender;
        emit RecoveryInitiated(user, msg.sender, block.timestamp);
    }
    
    /**
     * @dev Завершить процесс восстановления души
     * @param user адрес пользователя
     * @param newKey новый ключ доступа
     */
    function completeRecovery(address user, address newKey) public override {
        require(recoveryInProgress[user], "SoulIdentity: no recovery in progress");
        require(recoveryInitiator[user] == msg.sender, "SoulIdentity: not the initiator");
        require(newKey != address(0), "SoulIdentity: invalid new key");
        
        recoveryInProgress[user] = false;
        delete recoveryInitiator[user];
        
        // Здесь должна быть логика передачи токенов новому ключу
        // Пока что просто эмитируем событие
        emit RecoveryCompleted(user, newKey, block.timestamp);
    }
    
    /**
     * @dev Проверить, идет ли процесс восстановления души
     * @param user адрес пользователя
     * @return true если процесс восстановления активен
     */
    function isRecoveryInProgress(address user) public view override returns (bool) {
        return recoveryInProgress[user];
    }
    
    /**
     * @dev Создать временный ключ доступа к душе
     * @param tempKey адрес временного ключа
     * @param duration продолжительность действия в секундах
     */
    function createTemporaryKey(address tempKey, uint256 duration) public override {
        require(tempKey != address(0), "SoulIdentity: invalid temp key");
        require(duration > 0, "SoulIdentity: invalid duration");
        
        temporaryKeys[msg.sender] = tempKey;
        temporaryKeyExpiry[msg.sender] = block.timestamp + duration;
        emit TemporaryKeyCreated(msg.sender, tempKey, block.timestamp + duration, block.timestamp);
    }
    
    /**
     * @dev Получить временный ключ души пользователя
     * @param user адрес пользователя
     * @return адрес временного ключа
     */
    function getTemporaryKey(address user) public view override returns (address) {
        return temporaryKeys[user];
    }
    
    /**
     * @dev Проверить, действителен ли временный ключ души
     * @param tempKey адрес временного ключа
     * @return true если ключ действителен
     */
    function isTemporaryKeyValid(address tempKey) public view override returns (bool) {
        // Находим пользователя по временному ключу
        for (uint256 i = 0; i < userGuardians[msg.sender].length; i++) {
            address user = userGuardians[msg.sender][i];
            if (temporaryKeys[user] == tempKey && 
                temporaryKeyExpiry[user] > block.timestamp) {
                return true;
            }
        }
        return false;
    }
    
    // === SOUL МЕТАДАННЫЕ ===
    
    /**
     * @dev Получить расширенные метаданные души
     * @param tokenId идентификатор токена
     * @return soulType тип души
     * @return version версия души
     * @return attributes атрибуты души
     * @return isLocked заблокирован ли токен
     */
    function getSoulMetadata(uint256 tokenId) public view returns (
        string memory soulType,
        uint256 version,
        string memory attributes,
        bool isLocked
    ) {
        return (
            sbtType[tokenId],
            sbtVersion[tokenId],
            sbtAttributes[tokenId],
            true // SBT всегда заблокированы
        );
    }
    
    /**
     * @dev Обновить метаданные души (только владелец)
     * @param tokenId идентификатор токена
     * @param newSoulType новый тип души
     * @param newAttributes новые атрибуты души
     */
    function updateSoulMetadata(uint256 tokenId, string memory newSoulType, string memory newAttributes) public {
        require(ownerOf(tokenId) == msg.sender, "SoulIdentity: not token owner");
        
        sbtType[tokenId] = newSoulType;
        sbtAttributes[tokenId] = newAttributes;
        emit SBTMetadataUpdated(tokenId, newSoulType, newAttributes, block.timestamp);
    }
    
    /**
     * @dev Обновить версию души (только админ)
     * @param tokenId идентификатор токена
     * @param newVersion новая версия
     */
    function updateSoulVersion(uint256 tokenId, uint256 newVersion) public onlyRole(DEFAULT_ADMIN_ROLE) {
        sbtVersion[tokenId] = newVersion;
        emit SBTVersionUpdated(tokenId, newVersion, block.timestamp);
    }
    
    /**
     * @dev Получить версию души токена
     * @param tokenId идентификатор токена
     * @return версия души
     */
    function getSoulVersion(uint256 tokenId) public view returns (uint256) {
        return sbtVersion[tokenId];
    }
    
    /**
     * @dev Проверить, является ли токен душой
     * @param tokenId идентификатор токена
     * @return true если токен является душой
     */
    function isSoul(uint256 tokenId) public view returns (bool) {
        return ownerOf(tokenId) != address(0);
    }
    
    /**
     * @dev Получить тип души токена
     * @param tokenId идентификатор токена
     * @return тип души
     */
    function getSoulType(uint256 tokenId) public view returns (string memory) {
        return sbtType[tokenId];
    }
    
    /**
     * @dev Получить атрибуты души токена
     * @param tokenId идентификатор токена
     * @return атрибуты души
     */
    function getSoulAttributes(uint256 tokenId) public view returns (string memory) {
        return sbtAttributes[tokenId];
    }
    
    // === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
    
    /**
     * @dev Минт токена души (только для авторизованных контрактов)
     * @param to адрес получателя
     * @param tokenId идентификатор токена
     */
    function mintSoul(address to, uint256 tokenId) public onlyRole(SOUL_MANAGER_ROLE) {
        _mint(to, tokenId);
        sbtVersion[tokenId] = 1;
        sbtType[tokenId] = "SoulIdentity";
        sbtAttributes[tokenId] = "{}";
    }
    
    /**
     * @dev Базовый URI для токенов
     */
    function _baseURI() internal pure override returns (string memory) {
        return "https://api.amanita.com/soul/";
    }
    
    // === SBT METADATA FUNCTIONS (для совместимости с интерфейсом) ===
    
    /**
     * @dev Получить расширенные метаданные SBT
     * @param tokenId идентификатор токена
     * @return tokenSbtType тип SBT
     * @return version версия SBT
     * @return attributes дополнительные атрибуты
     * @return isLocked заблокирован ли токен
     */
    function getSBTMetadata(uint256 tokenId) public view returns (
        string memory tokenSbtType,
        uint256 version,
        string memory attributes,
        bool isLocked
    ) {
        return getSoulMetadata(tokenId);
    }
    
    /**
     * @dev Обновить метаданные SBT (только владелец)
     * @param tokenId идентификатор токена
     * @param newSbtType новый тип SBT
     * @param newAttributes новые атрибуты
     */
    function updateSBTMetadata(uint256 tokenId, string memory newSbtType, string memory newAttributes) public {
        updateSoulMetadata(tokenId, newSbtType, newAttributes);
    }
    
    /**
     * @dev Обновить версию SBT (только админ)
     * @param tokenId идентификатор токена
     * @param newVersion новая версия
     */
    function updateSBTVersion(uint256 tokenId, uint256 newVersion) public onlyRole(DEFAULT_ADMIN_ROLE) {
        updateSoulVersion(tokenId, newVersion);
    }
    
    /**
     * @dev Получить версию SBT токена
     * @param tokenId идентификатор токена
     * @return версия SBT
     */
    function getSBTVersion(uint256 tokenId) public view returns (uint256) {
        return getSoulVersion(tokenId);
    }
    
    /**
     * @dev Проверить, является ли токен SBT
     * @param tokenId идентификатор токена
     * @return true если токен является SBT
     */
    function isSBT(uint256 tokenId) public view returns (bool) {
        return isSoul(tokenId);
    }
    
    /**
     * @dev Получить тип SBT токена
     * @param tokenId идентификатор токена
     * @return тип SBT
     */
    function getSBTType(uint256 tokenId) public view returns (string memory) {
        return getSoulType(tokenId);
    }
    
    /**
     * @dev Получить атрибуты SBT токена
     * @param tokenId идентификатор токена
     * @return атрибуты SBT
     */
    function getSBTAttributes(uint256 tokenId) public view returns (string memory) {
        return getSoulAttributes(tokenId);
    }
}
