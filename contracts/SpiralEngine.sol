// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./interfaces/ISoulIdentity.sol";

/**
 * @title SpiralEngine
 * @author Zeya888 (https://zeya888.me)
 * @dev Основной контракт спиральной иерархии через 12-гранные круги
 * @notice Управляет инвайтами, активацией пользователей и назначением ролей в спиральной системе
 * @notice SBT функциональность делегируется в SoulIdentity контракт
 */
contract SpiralEngine is ERC721, AccessControl {
    uint256 private _tokenIdCounter;

    // Роль продавца для доступа к минтингу инвайтов
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");
    
    // Роль активатора для активации пользователей и назначения ролей
    bytes32 public constant ACTIVATOR_ROLE = keccak256("ACTIVATOR_ROLE");

    // === ОСНОВНЫЕ ДАННЫЕ ИНВАЙТОВ ===
    
    // Маппинг: inviteCode (уникальный строковый код) => tokenId (NFT инвайта)
    mapping(string => uint256) public inviteCodeToTokenId;
    
    // Маппинг: inviteCode => существует ли код (для корректной проверки дублирования)
    mapping(string => bool) public inviteCodeExists;

    // Маппинг: tokenId (NFT инвайта) => inviteCode (уникальный строковый код)
    mapping(uint256 => string) public tokenIdToInviteCode;

    // Маппинг: tokenId => использован ли инвайт
    mapping(uint256 => bool) public isInviteUsed;

    // Маппинг: user (адрес) => использованный инвайт (tokenId)
    mapping(address => uint256) public usedInviteByUser;

    // Маппинг: tokenId => срок действия инвайта (timestamp, 0 если бессрочный)
    mapping(uint256 => uint256) public inviteExpiry;

    // Маппинг: tokenId => дата создания инвайта (timestamp)
    mapping(uint256 => uint256) public inviteCreatedAt;

    // Маппинг: tokenId => адрес создателя (minter)
    mapping(uint256 => address) public inviteMinter;

    // Маппинг: tokenId => адрес первого владельца инвайта
    mapping(uint256 => address) public inviteFirstOwner;

    // Маппинг: user (адрес) => список всех его инвайтов (tokenId)
    mapping(address => uint256[]) public userInvites;

    // Счётчик общего количества использованных инвайтов
    uint256 public totalInvitesUsed;

    // Счётчик общего количества выданных инвайтов
    uint256 public totalInvitesMinted;

    // Маппинг: tokenId => история всех владельцев (адреса)
    mapping(uint256 => address[]) public inviteTransferHistory;

    // Массив всех активированных пользователей
    address[] public activatedUsers;

    // Маппинг: user (адрес) => количество заминченных инвайтов для этого пользователя
    mapping(address => uint256) public userInviteCount;

    // === ОТСЛЕЖИВАНИЕ ОТВЕТСТВЕННОСТИ ===
    
    // Маппинг: кто активировал пользователя
    mapping(address => address) public userActivator;
    
    // Маппинг: кто назначил роль SELLER_ROLE
    mapping(address => address) public sellerNominator;
    
    // Маппинг: кого активировал данный активатор
    mapping(address => address[]) public activatedBy;
    
    // Маппинг: кого назначил селлером данный номинатор
    mapping(address => address[]) public nominatedSellers;

    // === СИСТЕМА САНКЦИЙ ===
    
    // Маппинг: счетчик нарушений для каждого пользователя
    mapping(address => uint256) public violationCount;
    
    // Маппинг: до какого времени заблокирован пользователь
    mapping(address => uint256) public suspensionUntil;
    
    // Маппинг: нарушения активированных пользователей (для активатора)
    mapping(address => uint256) public activationViolations;
    
    // Маппинг: нарушения назначенных селлеров (для номинатора)
    mapping(address => uint256) public nominationViolations;

    // === ССЫЛКА НА SOUL IDENTITY ===
    
    // Адрес контракта SoulIdentity для делегирования SBT функций
    ISoulIdentity public soulIdentity;

    // === СОБЫТИЯ ===
    
    event InviteMinted(address indexed minter, uint256 indexed tokenId, string inviteCode, uint256 expiry);
    event InviteUsed(address indexed user, uint256 indexed tokenId, string inviteCode);
    event UserActivated(address indexed user, address indexed activator, uint256 timestamp);
    event SellerRoleGranted(address indexed user, address indexed nominator, uint256 timestamp);
    event UserSuspended(address indexed user, uint256 until, string reason);
    event SoulIdentityUpdated(address indexed oldSoulIdentity, address indexed newSoulIdentity);

    // === КОНСТРУКТОР ===
    
    constructor() ERC721("SpiralInvite", "SPIRAL") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(SELLER_ROLE, msg.sender);
        _grantRole(ACTIVATOR_ROLE, msg.sender);
    }

    // === ОСНОВНЫЕ ФУНКЦИИ ИНВАЙТОВ ===
    
    /**
     * @dev Минт нового инвайта
     * @param inviteCode уникальный код инвайта
     * @param expiry срок действия (0 = бессрочный)
     * @return tokenId идентификатор созданного NFT
     */
    function mintInvite(string memory inviteCode, uint256 expiry) public onlyRole(SELLER_ROLE) returns (uint256) {
        require(bytes(inviteCode).length > 0, "SpiralEngine: empty invite code");
        require(!inviteCodeExists[inviteCode], "SpiralEngine: invite code already exists");
        
        uint256 tokenId = _tokenIdCounter++;
        _mint(msg.sender, tokenId);
        
        inviteCodeToTokenId[inviteCode] = tokenId;
        inviteCodeExists[inviteCode] = true;
        tokenIdToInviteCode[tokenId] = inviteCode;
        inviteExpiry[tokenId] = expiry;
        inviteCreatedAt[tokenId] = block.timestamp;
        inviteMinter[tokenId] = msg.sender;
        inviteFirstOwner[tokenId] = msg.sender;
        
        userInvites[msg.sender].push(tokenId);
        userInviteCount[msg.sender]++;
        totalInvitesMinted++;
        
        emit InviteMinted(msg.sender, tokenId, inviteCode, expiry);
        return tokenId;
    }

    /**
     * @dev Активация пользователя с помощью инвайта
     * @param inviteCode код инвайта
     * @param user адрес пользователя для активации
     * @param newInviteCodes новые инвайты для пользователя
     * @param expiry срок действия новых инвайтов
     */
    function activateUser(
        string memory inviteCode, 
        address user, 
        string[] memory newInviteCodes, 
        uint256 expiry
    ) public onlyRole(ACTIVATOR_ROLE) {
        require(user != address(0), "SpiralEngine: invalid user address");
        require(usedInviteByUser[user] == 0, "SpiralEngine: user already activated");
        require(newInviteCodes.length == 12, "SpiralEngine: must provide exactly 12 invite codes");
        require(activatedBy[msg.sender].length < 12, "SpiralEngine: activator circle limit reached");
        
        uint256 tokenId = _validateInviteCode(inviteCode, msg.sender);
        require(!isInviteUsed[tokenId], "SpiralEngine: invite already used");
        require(inviteExpiry[tokenId] == 0 || inviteExpiry[tokenId] > block.timestamp, "SpiralEngine: invite expired");
        
        // Используем инвайт
        isInviteUsed[tokenId] = true;
        usedInviteByUser[user] = tokenId + 1; // +1 чтобы избежать конфликта с tokenId = 0
        totalInvitesUsed++;
        
        // Записываем активатора
        userActivator[user] = msg.sender;
        activatedBy[msg.sender].push(user);
        activatedUsers.push(user);
        
        // Создаем новые инвайты для пользователя
        for (uint256 i = 0; i < newInviteCodes.length; i++) {
            require(bytes(newInviteCodes[i]).length > 0, "SpiralEngine: empty invite code");
            require(!inviteCodeExists[newInviteCodes[i]], "SpiralEngine: invite code already exists");
            
            uint256 newTokenId = _tokenIdCounter++;
            _mint(user, newTokenId);
            
            inviteCodeToTokenId[newInviteCodes[i]] = newTokenId;
            inviteCodeExists[newInviteCodes[i]] = true;
            tokenIdToInviteCode[newTokenId] = newInviteCodes[i];
            inviteExpiry[newTokenId] = expiry;
            inviteCreatedAt[newTokenId] = block.timestamp;
            inviteMinter[newTokenId] = user;
            inviteFirstOwner[newTokenId] = user;
            
            userInvites[user].push(newTokenId);
            userInviteCount[user]++;
            totalInvitesMinted++;
            
            emit InviteMinted(user, newTokenId, newInviteCodes[i], expiry);
        }
        
        emit UserActivated(user, msg.sender, block.timestamp);
    }

    /**
     * @dev Назначение роли продавца
     * @param user адрес пользователя
     */
    function grantSellerRole(address user) public onlyRole(ACTIVATOR_ROLE) {
        require(user != address(0), "SpiralEngine: invalid user address");
        require(usedInviteByUser[user] > 0, "SpiralEngine: user not activated");
        require(!hasRole(SELLER_ROLE, user), "SpiralEngine: user already has seller role");
        
        _grantRole(SELLER_ROLE, user);
        sellerNominator[user] = msg.sender;
        nominatedSellers[msg.sender].push(user);
        
        emit SellerRoleGranted(user, msg.sender, block.timestamp);
    }

    /**
     * @dev Приостановка пользователя
     * @param user адрес пользователя
     * @param duration продолжительность приостановки в секундах
     * @param reason причина приостановки
     */
    function suspendUser(address user, uint256 duration, string memory reason) public onlyRole(DEFAULT_ADMIN_ROLE) {
        require(user != address(0), "SpiralEngine: invalid user address");
        require(usedInviteByUser[user] > 0, "SpiralEngine: user not activated");
        require(duration > 0, "SpiralEngine: invalid duration");
        
        suspensionUntil[user] = block.timestamp + duration;
        violationCount[user]++;
        
        // Каскадные санкции
        if (userActivator[user] != address(0)) {
            activationViolations[userActivator[user]]++;
        }
        if (sellerNominator[user] != address(0)) {
            nominationViolations[sellerNominator[user]]++;
        }
        
        emit UserSuspended(user, suspensionUntil[user], reason);
    }

    // === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
    
    /**
     * @dev Валидация инвайт кода
     * @param inviteCode код инвайта
     * @param activator адрес активатора
     * @return tokenId идентификатор токена
     */
    function _validateInviteCode(string memory inviteCode, address activator) internal view returns (uint256) {
        require(inviteCodeExists[inviteCode], "SpiralEngine: invite code not found");
        uint256 tokenId = inviteCodeToTokenId[inviteCode];
        require(inviteMinter[tokenId] == activator, "SpiralEngine: invite not from activator");
        return tokenId;
    }

    /**
     * @dev Получить размер круга активатора
     * @param activator адрес активатора
     * @return размер круга
     */
    function getCircleSize(address activator) public view returns (uint256) {
        return activatedBy[activator].length;
    }

    /**
     * @dev Получить членов круга активатора
     * @param activator адрес активатора
     * @return массив адресов членов круга
     */
    function getCircleMembers(address activator) public view returns (address[] memory) {
        return activatedBy[activator];
    }

    /**
     * @dev Проверить, является ли инвайт от активатора
     * @param tokenId идентификатор токена
     * @param activator адрес активатора
     * @return true если инвайт от активатора
     */
    function isInviteFromActivator(uint256 tokenId, address activator) public view returns (bool) {
        return inviteMinter[tokenId] == activator;
    }

    // === УПРАВЛЕНИЕ SOUL IDENTITY ===
    
    /**
     * @dev Установить адрес контракта SoulIdentity
     * @param _soulIdentity адрес контракта SoulIdentity
     */
    function setSoulIdentity(address _soulIdentity) public onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_soulIdentity != address(0), "SpiralEngine: invalid soul identity address");
        address oldSoulIdentity = address(soulIdentity);
        soulIdentity = ISoulIdentity(_soulIdentity);
        emit SoulIdentityUpdated(oldSoulIdentity, _soulIdentity);
    }

    // === ДЕЛЕГИРОВАНИЕ К SOUL IDENTITY ===
    
    /**
     * @dev Получить уровень души пользователя
     * @param user адрес пользователя
     * @return уровень души
     */
    function getSoulLevel(address user) public view returns (uint256) {
        require(address(soulIdentity) != address(0), "SpiralEngine: soul identity not set");
        return soulIdentity.getSoulLevel(user);
    }

    /**
     * @dev Получить репутацию души пользователя
     * @param user адрес пользователя
     * @return репутация души
     */
    function getSoulReputation(address user) public view returns (uint256) {
        require(address(soulIdentity) != address(0), "SpiralEngine: soul identity not set");
        return soulIdentity.getSoulReputation(user);
    }

    /**
     * @dev Получить идентичность души пользователя
     * @param user адрес пользователя
     * @return DID идентификатор
     */
    function getSoulIdentity(address user) public view returns (string memory) {
        require(address(soulIdentity) != address(0), "SpiralEngine: soul identity not set");
        return soulIdentity.getSoulIdentity(user);
    }

    /**
     * @dev Получить уровень верификации души пользователя
     * @param user адрес пользователя
     * @return уровень верификации
     */
    function getSoulVerificationLevel(address user) public view returns (uint8) {
        require(address(soulIdentity) != address(0), "SpiralEngine: soul identity not set");
        return soulIdentity.getSoulVerificationLevel(user);
    }

    /**
     * @dev Получить полный профиль души пользователя
     * @param user адрес пользователя
     * @return level уровень души
     * @return reputation репутация души
     * @return identity идентичность души
     * @return verificationLevel уровень верификации
     * @return guardians список доверенных лиц
     */
    function getSoulProfile(address user) public view returns (
        uint256 level,
        uint256 reputation,
        string memory identity,
        uint8 verificationLevel,
        address[] memory guardians
    ) {
        require(address(soulIdentity) != address(0), "SpiralEngine: soul identity not set");
        return soulIdentity.getSoulProfile(user);
    }

    // === ПЕРЕОПРЕДЕЛЕНИЕ ФУНКЦИЙ ERC721 ===
    
    /**
     * @dev Поддержка интерфейсов
     */
    function supportsInterface(bytes4 interfaceId) public view override(ERC721, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    /**
     * @dev Переопределение transferFrom для предотвращения передачи
     */
    function transferFrom(address /* from */, address /* to */, uint256 /* tokenId */) public pure override {
        revert("SpiralEngine: transfers not allowed");
    }

    /**
     * @dev Базовый URI для токенов
     */
    function _baseURI() internal pure override returns (string memory) {
        return "https://api.amanita.com/spiral/";
    }
}
