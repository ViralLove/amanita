// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "./interfaces/ISoulIdentity.sol";
import "./interfaces/ISoulRecovery.sol";

/**
 * @dev Интерфейс для SoulboundCore - существующий SBT контракт
 */
interface ISoulboundCore {
    function balanceOf(address owner) external view returns (uint256);
    function ownerOf(uint256 tokenId) external view returns (address);
    function mintSoul(address to) external;
    function exists(uint256 tokenId) external view returns (bool);
    function getTotalSupply() external view returns (uint256);
    function getNextTokenId() external view returns (uint256);
}

/**
 * @dev Интерфейс для SoulMetadata - существующая система метаданных
 */
interface ISoulMetadata {
    struct SoulData {
        string metadataType;
        uint256 version;
        string attributes;
        string ipfsHash;
    }
    
    function getMetadata(uint256 tokenId) external view returns (SoulData memory);
    function initializeMetadata(uint256 tokenId, string memory metadataType, string memory attributes, string memory ipfsHash) external;
    function updateMetadata(uint256 tokenId, string memory attributes, string memory ipfsHash) external;
    function isInitialized(uint256 tokenId) external view returns (bool);
}

/**
 * @title SoulIdentity
 * @author Zeya888 (https://zeya888.me)
 * @dev МОСТ-контракт между SpiralEngine и существующей SBT экосистемой
 * @notice НЕ создает новые SBT токены - использует существующие SoulboundCore!
 * @notice Добавляет только DID функциональность к существующим SBT
 */
contract SoulIdentity is AccessControl, ISoulIdentity {
    
    // === РОЛИ ===
    bytes32 public constant SPIRAL_ENGINE_ROLE = keccak256("SPIRAL_ENGINE_ROLE");
    
    // === ИНТЕГРАЦИЯ С СУЩЕСТВУЮЩИМИ КОНТРАКТАМИ ===
    ISoulboundCore public soulboundCore;
    ISoulMetadata public soulMetadata;
    ISoulRecovery public soulRecovery;
    
    // === НОВЫЕ DID ДАННЫЕ ===
    mapping(address => ExternalIdentity[]) private userIdentities;
    mapping(address => uint256) private primaryIdentityIndex;
    mapping(address => mapping(string => uint256)) private identityTypeToIndex;

    // === PASSPORT MVP: displayName и handle (SBT-PAS-1) ===
    uint256 public constant MAX_DISPLAY_NAME_LENGTH = 64;
    uint256 public constant MAX_HANDLE_LENGTH = 32;
    string public constant DEFAULT_COMMUNITY_ID = "spiral";
    mapping(address => string) private _displayNameByUser;
    mapping(address => string) private _handleByUser;
    
    // === Индекс owner → tokenId (SBT-IDX-1): O(1) поиск души по владельцу ===
    mapping(address => uint256) private _ownerToTokenId;
    
    // === Временный ключ B2: один активный на пользователя ===
    uint256 public constant MAX_TEMP_KEY_DURATION = 30 days;
    mapping(address => address) private _tempKeyByUser;
    mapping(address => uint256) private _tempKeyExpiryByUser;
    mapping(address => address) private _userByTempKey; // обратный lookup для isTemporaryKeyValid
    
    // === СОБЫТИЯ ===
    event SoulIdentityContractsUpdated(address soulboundCore, address soulMetadata);
    event SoulRecoverySet(address soulRecovery);
    
    // === КОНСТРУКТОР ===
    
    /**
     * @dev Инициализация моста с существующими SBT контрактами
     * @param _soulboundCore адрес существующего SoulboundCore контракта
     * @param _soulMetadata адрес существующего SoulMetadata контракта
     */
    constructor(address _soulboundCore, address _soulMetadata) {
        require(_soulboundCore != address(0), "SoulIdentity: invalid soulbound core address");
        require(_soulMetadata != address(0), "SoulIdentity: invalid soul metadata address");
        
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(SPIRAL_ENGINE_ROLE, msg.sender);
        
        soulboundCore = ISoulboundCore(_soulboundCore);
        soulMetadata = ISoulMetadata(_soulMetadata);
        
        emit SoulIdentityContractsUpdated(_soulboundCore, _soulMetadata);
    }
    
    /**
     * @dev Установить адрес SoulRecovery для делегирования guardians/recovery (SBT-REC-1)
     * @param _soulRecovery адрес контракта SoulRecovery или address(0) для сброса
     */
    function setSoulRecovery(address _soulRecovery) external onlyRole(DEFAULT_ADMIN_ROLE) {
        soulRecovery = ISoulRecovery(_soulRecovery);
        emit SoulRecoverySet(_soulRecovery);
    }
    
    /**
     * @dev ISoulIntegration: вызов только с SoulboundCore при минте души (SBT-IDX-1)
     */
    function notifySoulCreated(uint256 tokenId, address owner) external {
        require(msg.sender == address(soulboundCore), "SoulIdentity: only SoulboundCore");
        _ownerToTokenId[owner] = tokenId;
    }
    
    /**
     * @dev ISoulIntegration: вызов только с SoulboundCore при recovery (SBT-IDX-1)
     */
    function notifySoulRecovered(uint256 tokenId, address oldOwner, address newOwner) external {
        require(msg.sender == address(soulboundCore), "SoulIdentity: only SoulboundCore");
        _ownerToTokenId[newOwner] = tokenId;
        delete _ownerToTokenId[oldOwner];
    }
    
    /**
     * @dev Ретроспективная регистрация пары (owner, tokenId) в индекс (SBT-IDX-1). Только DEFAULT_ADMIN_ROLE.
     */
    function registerSoulTokenId(address owner, uint256 tokenId) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(soulboundCore.exists(tokenId), "SoulIdentity: token does not exist");
        require(soulboundCore.ownerOf(tokenId) == owner, "SoulIdentity: not token owner");
        _ownerToTokenId[owner] = tokenId;
    }
    
    // === ДЕЛЕГИРОВАНИЕ К СУЩЕСТВУЮЩИМ SBT КОНТРАКТАМ ===
    
    /**
     * @dev Получить уровень души через делегирование к SoulMetadata
     * @param user адрес пользователя
     * @return уровень души (1 если нет данных)
     */
    function getSoulLevel(address user) external view override returns (uint256) {
        uint256 tokenId = _getUserTokenId(user);
        if (tokenId == 0) return 0; // Нет SBT токена
        
        try soulMetadata.getMetadata(tokenId) returns (ISoulMetadata.SoulData memory data) {
            return _parseLevel(data.attributes); // Парсим level из JSON
        } catch {
            return 1; // Дефолтный уровень
        }
    }
    
    /**
     * @dev Получить репутацию души через делегирование к SoulMetadata
     * @param user адрес пользователя
     * @return репутация души (100 если нет данных)
     */
    function getSoulReputation(address user) external view override returns (uint256) {
        uint256 tokenId = _getUserTokenId(user);
        if (tokenId == 0) return 0; // Нет SBT токена
        
        try soulMetadata.getMetadata(tokenId) returns (ISoulMetadata.SoulData memory data) {
            return _parseReputation(data.attributes); // Парсим reputation из JSON
        } catch {
            return 100; // Дефолтная репутация
        }
    }
    
    /**
     * @dev Обновить уровень души через SoulMetadata
     * @param user адрес пользователя
     * @param newLevel новый уровень души
     */
    function updateSoulLevel(address user, uint256 newLevel) external override onlyRole(SPIRAL_ENGINE_ROLE) {
        uint256 tokenId = _getUserTokenId(user);
        require(tokenId > 0, "SoulIdentity: user has no SBT token");
        
        // Обновляем метаданные через существующую систему
        try soulMetadata.getMetadata(tokenId) returns (ISoulMetadata.SoulData memory data) {
            string memory updatedAttributes = _updateLevelInJSON(data.attributes, newLevel);
            soulMetadata.updateMetadata(tokenId, updatedAttributes, data.ipfsHash);
        } catch {
            // Создаем базовые метаданные если их нет
            string memory newAttributes = string(abi.encodePacked('{"level":', _toString(newLevel), ',"reputation":100}'));
            soulMetadata.initializeMetadata(tokenId, "identity", newAttributes, "");
        }
    }
    
    /**
     * @dev Изменить репутацию души через SoulMetadata
     * @param user адрес пользователя
     * @param change изменение репутации (может быть отрицательным)
     */
    function updateSoulReputation(address user, int256 change) external override onlyRole(SPIRAL_ENGINE_ROLE) {
        uint256 tokenId = _getUserTokenId(user);
        require(tokenId > 0, "SoulIdentity: user has no SBT token");
        
        uint256 currentRep = this.getSoulReputation(user);
        uint256 newRep = change >= 0 ? currentRep + uint256(change) : 
                         (currentRep > uint256(-change) ? currentRep - uint256(-change) : 0);
        
        try soulMetadata.getMetadata(tokenId) returns (ISoulMetadata.SoulData memory data) {
            string memory updatedAttributes = _updateReputationInJSON(data.attributes, newRep);
            soulMetadata.updateMetadata(tokenId, updatedAttributes, data.ipfsHash);
        } catch {
            string memory newAttributes = string(abi.encodePacked('{"level":1,"reputation":', _toString(newRep), '}'));
            soulMetadata.initializeMetadata(tokenId, "identity", newAttributes, "");
        }
    }
    
    // === НОВАЯ DID ФУНКЦИОНАЛЬНОСТЬ ===
    
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
    ) external override onlyRole(SPIRAL_ENGINE_ROLE) {
        require(user != address(0), "SoulIdentity: invalid user address");
        require(bytes(identityType).length > 0, "SoulIdentity: empty identity type");
        require(bytes(identityValue).length > 0, "SoulIdentity: empty identity value");
        require(_getUserTokenId(user) > 0, "SoulIdentity: user has no SBT token");
        
        // Проверяем, есть ли уже такой тип идентичности
        uint256 existingIndex = identityTypeToIndex[user][identityType];
        
        if (existingIndex > 0) {
            // Обновляем существующую идентичность
            uint256 index = existingIndex - 1;
            userIdentities[user][index].identityValue = identityValue;
            userIdentities[user][index].verified = verified;
            userIdentities[user][index].verifiedBy = verified ? msg.sender : address(0);
        } else {
            // Добавляем новую идентичность
            ExternalIdentity memory newIdentity = ExternalIdentity({
                identityType: identityType,
                identityValue: identityValue,
                verified: verified,
                createdAt: block.timestamp,
                verifiedBy: verified ? msg.sender : address(0)
            });
            
            userIdentities[user].push(newIdentity);
            identityTypeToIndex[user][identityType] = userIdentities[user].length;
            
            // Если это первая идентичность, делаем её основной
            if (userIdentities[user].length == 1) {
                primaryIdentityIndex[user] = 0;
            }
        }
        
        emit ExternalIdentityLinked(user, identityType, identityValue, verified, block.timestamp);
    }
    
    /**
     * @dev Получить основную идентичность пользователя
     * @param user адрес пользователя
     * @return identity структура основной идентичности
     */
    function getPrimaryIdentity(address user) 
        external view override returns (ExternalIdentity memory identity) {
        require(userIdentities[user].length > 0, "SoulIdentity: no identities found");
        return userIdentities[user][primaryIdentityIndex[user]];
    }
    
    /**
     * @dev Получить все идентичности пользователя
     * @param user адрес пользователя
     * @return identities массив всех идентичностей
     */
    function getAllIdentities(address user) 
        external view override returns (ExternalIdentity[] memory identities) {
        return userIdentities[user];
    }
    
    /**
     * @dev Проверить наличие идентичности определенного типа
     * @param user адрес пользователя
     * @param identityType тип идентичности
     * @return hasIdentity есть ли идентичность данного типа
     */
    function hasIdentityType(address user, string memory identityType) 
        external view override returns (bool hasIdentity) {
        return identityTypeToIndex[user][identityType] > 0;
    }
    
    // === ОБРАТНАЯ СОВМЕСТИМОСТЬ ===
    
    /**
     * @dev Связать идентичность души с DID (DEPRECATED)
     * Автоматически создает ExternalIdentity с типом "did:spiral"
     * @param did DID идентификатор
     */
    function linkSoulIdentity(string memory did) external override {
        require(bytes(did).length > 0, "SoulIdentity: empty DID");
        address owner = _getEffectiveOwner();
        require(_getUserTokenId(owner) > 0, "SoulIdentity: user has no SBT token");
        
        userIdentities[owner].push(ExternalIdentity({
            identityType: "did:spiral",
            identityValue: did,
            verified: false, // legacy всегда не верифицирована
            createdAt: block.timestamp,
            verifiedBy: address(0) // legacy не имеет верификатора
        }));
        
        if (userIdentities[owner].length == 1) {
            primaryIdentityIndex[owner] = 0;
        }
        
        emit ExternalIdentityLinked(owner, "did:spiral", did, false, block.timestamp);
    }
    
    /**
     * @dev Получить идентичность души пользователя (DEPRECATED)
     * Возвращает значение основной идентичности
     * @param user адрес пользователя
     * @return DID идентификатор основной идентичности
     */
    function getSoulIdentity(address user) external view override returns (string memory) {
        if (userIdentities[user].length == 0) return "";
        return userIdentities[user][primaryIdentityIndex[user]].identityValue;
    }
    
    /**
     * @dev Отвязать идентичность души (DEPRECATED)
     */
    function unlinkSoulIdentity() external override {
        address owner = _getEffectiveOwner();
        ExternalIdentity[] storage identities = userIdentities[owner];
        for (uint256 i = 0; i < identities.length; i++) {
            if (keccak256(bytes(identities[i].identityType)) == keccak256(bytes("did:spiral"))) {
                identities[i] = identities[identities.length - 1];
                identities.pop();
                break;
            }
        }
        if (identities.length == 0) {
            primaryIdentityIndex[owner] = 0;
        }
    }
    
    // === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
    
    /**
     * @dev Найти первый SBT токен пользователя в существующей системе
     * @param user адрес пользователя
     * @return tokenId идентификатор токена (0 если не найден)
     */
    /**
     * @dev Поиск tokenId по владельцу: сначала индекс O(1) (SBT-IDX-1), при отсутствии — fallback перебор без лимита 1000.
     */
    function _getUserTokenId(address user) private view returns (uint256) {
        if (_ownerToTokenId[user] != 0) return _ownerToTokenId[user];
        
        uint256 balance = soulboundCore.balanceOf(user);
        if (balance == 0) return 0;
        
        uint256 totalSupply = soulboundCore.getTotalSupply();
        for (uint256 i = 1; i <= totalSupply; i++) {
            try soulboundCore.ownerOf(i) returns (address owner) {
                if (owner == user) return i;
            } catch {
                continue;
            }
        }
        return 0;
    }
    
    /**
     * @dev Эффективный владелец для вызова: msg.sender если у него есть SBT, иначе user, для которого msg.sender — валидный временный ключ (B2).
     */
    function _getEffectiveOwner() private view returns (address) {
        if (_getUserTokenId(msg.sender) > 0) return msg.sender;
        address user = _userByTempKey[msg.sender];
        if (user != address(0) && block.timestamp < _tempKeyExpiryByUser[user]) return user;
        revert("SoulIdentity: not owner or valid temporary key");
    }
    
    /**
     * @dev Парсинг level из JSON атрибутов (упрощенная реализация)
     * @param attributes JSON строка с атрибутами
     * @return level уровень души
     */
    function _parseLevel(string memory attributes) private pure returns (uint256) {
        // TODO: Реализовать полноценный JSON парсинг
        // Пока возвращаем дефолтное значение
        bytes memory attributesBytes = bytes(attributes);
        if (attributesBytes.length == 0) return 1;
        
        // Простой поиск "level":X в JSON
        // В production заменить на библиотеку JSON парсинга
        return 1; // Заглушка
    }
    
    /**
     * @dev Парсинг reputation из JSON атрибутов (упрощенная реализация)
     * @param attributes JSON строка с атрибутами
     * @return reputation репутация души
     */
    function _parseReputation(string memory attributes) private pure returns (uint256) {
        // TODO: Реализовать полноценный JSON парсинг
        bytes memory attributesBytes = bytes(attributes);
        if (attributesBytes.length == 0) return 100;
        
        // Простой поиск "reputation":X в JSON
        return 100; // Заглушка
    }
    
    /**
     * @dev Обновление level в JSON атрибутах (упрощенная реализация)
     * @param attributes текущие JSON атрибуты
     * @param newLevel новый уровень
     * @return updatedAttributes обновленные атрибуты
     */
    function _updateLevelInJSON(string memory attributes, uint256 newLevel) private pure returns (string memory) {
        // TODO: Реализовать полноценное обновление JSON
        return string(abi.encodePacked('{"level":', _toString(newLevel), ',"reputation":100}'));
    }
    
    /**
     * @dev Обновление reputation в JSON атрибутах (упрощенная реализация)
     * @param attributes текущие JSON атрибуты
     * @param newReputation новая репутация
     * @return updatedAttributes обновленные атрибуты
     */
    function _updateReputationInJSON(string memory attributes, uint256 newReputation) private pure returns (string memory) {
        // TODO: Реализовать полноценное обновление JSON
        return string(abi.encodePacked('{"level":1,"reputation":', _toString(newReputation), '}'));
    }
    
    /**
     * @dev Конвертация uint256 в string
     * @param value число для конвертации
     * @return строковое представление
     */
    function _toString(uint256 value) private pure returns (string memory) {
        if (value == 0) return "0";
        
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + uint256(value % 10)));
            value /= 10;
        }
        
        return string(buffer);
    }
    
    // === ЗАГЛУШКИ ДЛЯ ОСТАЛЬНЫХ ФУНКЦИЙ ISoulIdentity ===
    
    function getSoulVerificationLevel(address user) external pure override returns (uint8) {
        return 0; // Заглушка
    }
    
    function getSoulProfile(address user) external view override returns (
        uint256 level,
        uint256 reputation,
        string memory identity,
        uint8 verificationLevel,
        address[] memory guardians,
        string memory displayName,
        string memory handle
    ) {
        level = this.getSoulLevel(user);
        reputation = this.getSoulReputation(user);
        identity = this.getSoulIdentity(user);
        verificationLevel = 0;
        guardians = this.getTrustedGuardians(user);
        displayName = _displayNameByUser[user];
        handle = _handleByUser[user];
    }

    function getDisplayName(address user) external view override returns (string memory) {
        return _displayNameByUser[user];
    }

    function getHandle(address user) external view override returns (string memory) {
        return _handleByUser[user];
    }

    function setDisplayName(string calldata displayName) external override {
        uint256 tokenId = _getUserTokenId(msg.sender);
        require(tokenId > 0, "SoulIdentity: no SBT");
        require(soulboundCore.ownerOf(tokenId) == msg.sender, "SoulIdentity: not soul owner");
        require(bytes(displayName).length <= MAX_DISPLAY_NAME_LENGTH, "SoulIdentity: displayName too long");
        _displayNameByUser[msg.sender] = displayName;
    }

    function setHandle(string calldata handle) external override {
        uint256 tokenId = _getUserTokenId(msg.sender);
        require(tokenId > 0, "SoulIdentity: no SBT");
        require(soulboundCore.ownerOf(tokenId) == msg.sender, "SoulIdentity: not soul owner");
        require(bytes(handle).length <= MAX_HANDLE_LENGTH, "SoulIdentity: handle too long");
        require(_isValidHandleFormat(handle), "SoulIdentity: handle must be @communityId:localHandle");
        _handleByUser[msg.sender] = handle;
    }

    function _isValidHandleFormat(string calldata handle) private pure returns (bool) {
        bytes memory b = bytes(handle);
        if (b.length < 4) return false; // at least "@a:b"
        if (b[0] != 0x40) return false; // '@'
        for (uint256 i = 1; i < b.length; i++) {
            if (b[i] == 0x3a) return true; // found ':'
        }
        return false;
    }
    
    function updateSoulVerificationLevel(address user, uint8 level) external override {
        // Заглушка - можно реализовать через метаданные
    }
    
    function hasSoulIdentityLinked(address user) external view override returns (bool) {
        return userIdentities[user].length > 0;
    }
    
    function getAddressBySoulIdentity(string memory did) external view override returns (address) {
        // TODO: Реализовать обратный поиск по DID
        return address(0); // Заглушка
    }
    
    // === ERC5192 ЗАГЛУШКИ (НЕ ИСПОЛЬЗУЮТСЯ - ДЕЛЕГИРУЕМ К SOULBOUNDCORE) ===
    
    function locked(uint256 tokenId) external pure override returns (bool) {
        return true; // Все SBT заблокированы
    }
    
    function approve(address to, uint256 tokenId) external pure override {
        revert("SoulIdentity: soulbound tokens cannot be approved");
    }
    
    function setApprovalForAll(address operator, bool approved) external pure override {
        revert("SoulIdentity: soulbound tokens cannot be approved");
    }
    
    function getApproved(uint256 tokenId) external pure override returns (address) {
        return address(0); // SBT не могут быть одобрены
    }
    
    function isApprovedForAll(address owner, address operator) external pure override returns (bool) {
        return false; // SBT не могут быть одобрены
    }
    
    // === ОСТАЛЬНЫЕ ЗАГЛУШКИ ===
    
    function addTrustedGuardian(address guardian) external override {
        uint256 tokenId = _getUserTokenId(msg.sender);
        require(tokenId > 0, "SoulIdentity: no SBT");
        require(address(soulRecovery) != address(0), "SoulIdentity: SoulRecovery not set");
        soulRecovery.setGuardianFor(tokenId, guardian, msg.sender);
    }
    
    function removeTrustedGuardian(address guardian) external override {
        require(address(soulRecovery) != address(0), "SoulIdentity: SoulRecovery not set");
        uint256 tokenId = _getUserTokenId(msg.sender);
        require(tokenId > 0, "SoulIdentity: no SBT");
        soulRecovery.removeGuardianFor(tokenId, msg.sender);
    }
    
    function getTrustedGuardians(address user) external view override returns (address[] memory) {
        if (address(soulRecovery) == address(0)) return new address[](0);
        uint256 tokenId = _getUserTokenId(user);
        if (tokenId == 0) return new address[](0);
        address g = soulRecovery.getGuardian(tokenId);
        if (g == address(0)) return new address[](0);
        address[] memory out = new address[](1);
        out[0] = g;
        return out;
    }
    
    function isTrustedGuardian(address user, address guardian) external view override returns (bool) {
        if (address(soulRecovery) == address(0)) return false;
        uint256 tokenId = _getUserTokenId(user);
        if (tokenId == 0) return false;
        return soulRecovery.getGuardian(tokenId) == guardian;
    }
    
    function initiateRecovery(address user, address newKey) external override {
        require(address(soulRecovery) != address(0), "SoulIdentity: SoulRecovery not set");
        uint256 tokenId = _getUserTokenId(user);
        soulRecovery.initiateRecoveryFor(tokenId, newKey, msg.sender);
    }
    
    function completeRecovery(address user, address newKey) external override {
        require(address(soulRecovery) != address(0), "SoulIdentity: SoulRecovery not set");
        uint256 tokenId = _getUserTokenId(user);
        soulRecovery.confirmRecoveryFor(tokenId, msg.sender);
    }
    
    function isRecoveryInProgress(address user) external view override returns (bool) {
        if (address(soulRecovery) == address(0)) return false;
        uint256 tokenId = _getUserTokenId(user);
        return soulRecovery.isRecoveryActive(tokenId);
    }
    
    function createTemporaryKey(address tempKey, uint256 duration) external override {
        require(_getUserTokenId(msg.sender) > 0, "SoulIdentity: only soul owner");
        require(tempKey != address(0), "SoulIdentity: zero temp key");
        require(tempKey != msg.sender, "SoulIdentity: temp key cannot be owner");
        require(duration > 0 && duration <= MAX_TEMP_KEY_DURATION, "SoulIdentity: invalid duration");
        
        address oldTempKey = _tempKeyByUser[msg.sender];
        if (oldTempKey != address(0)) {
            delete _userByTempKey[oldTempKey];
        }
        
        uint256 expiry = block.timestamp + duration;
        _tempKeyByUser[msg.sender] = tempKey;
        _tempKeyExpiryByUser[msg.sender] = expiry;
        _userByTempKey[tempKey] = msg.sender;
        
        emit TemporaryKeyCreated(msg.sender, tempKey, expiry, block.timestamp);
    }
    
    function revokeTemporaryKey() external override {
        require(_getUserTokenId(msg.sender) > 0, "SoulIdentity: only soul owner");
        address tempKey = _tempKeyByUser[msg.sender];
        if (tempKey == address(0)) return;
        
        delete _tempKeyByUser[msg.sender];
        delete _tempKeyExpiryByUser[msg.sender];
        delete _userByTempKey[tempKey];
        
        emit TemporaryKeyRevoked(msg.sender, tempKey);
    }
    
    function getTemporaryKey(address user) external view override returns (address) {
        if (block.timestamp >= _tempKeyExpiryByUser[user]) return address(0);
        return _tempKeyByUser[user];
    }
    
    function isTemporaryKeyValid(address tempKey) external view override returns (bool) {
        address user = _userByTempKey[tempKey];
        if (user == address(0)) return false;
        return block.timestamp < _tempKeyExpiryByUser[user];
    }
    
    function getSBTMetadata(uint256 tokenId) external view override returns (
        string memory tokenSbtType,
        uint256 version,
        string memory attributes,
        bool isLocked
    ) {
        try soulMetadata.getMetadata(tokenId) returns (ISoulMetadata.SoulData memory data) {
            return (data.metadataType, data.version, data.attributes, true);
        } catch {
            return ("", 0, "", true);
        }
    }
    
    function updateSBTMetadata(uint256 tokenId, string memory newSbtType, string memory newAttributes) external override {
        // TODO: Делегировать к SoulMetadata
    }
    
    function updateSBTVersion(uint256 tokenId, uint256 newVersion) external override {
        // TODO: Реализовать через метаданные
    }
    
    function getSBTVersion(uint256 tokenId) external view override returns (uint256) {
        try soulMetadata.getMetadata(tokenId) returns (ISoulMetadata.SoulData memory data) {
            return data.version;
        } catch {
            return 0;
        }
    }
    
    function isSBT(uint256 tokenId) external view override returns (bool) {
        return soulboundCore.exists(tokenId);
    }
    
    function getSBTType(uint256 tokenId) external view override returns (string memory) {
        try soulMetadata.getMetadata(tokenId) returns (ISoulMetadata.SoulData memory data) {
            return data.metadataType;
        } catch {
            return "";
        }
    }
    
    function getSBTAttributes(uint256 tokenId) external view override returns (string memory) {
        try soulMetadata.getMetadata(tokenId) returns (ISoulMetadata.SoulData memory data) {
            return data.attributes;
        } catch {
            return "";
        }
    }
    
}
