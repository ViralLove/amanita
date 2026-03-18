// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "./interfaces/ISoulIdentity.sol";
import "./IERC5192.sol";

/**
 * @title SpiralEngine
 * @author Zeya888 (https://zeya888.me)
 * @dev Фасад спиральной иерархии; инвайты — только лог (inviteId), без ERC721 (SBT-INV-1.4)
 * @notice SBT функциональность делегируется в SoulIdentity контракт
 */
contract SpiralEngine is AccessControl, IERC5192 {
    /// @notice Счётчик inviteId (логические записи инвайтов, без ERC721 минтинга)
    uint256 private _inviteIdCounter;

    // Роль продавца для доступа к минтингу инвайтов
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");
    
    // Роль активатора для активации пользователей и назначения ролей
    bytes32 public constant ACTIVATOR_ROLE = keccak256("ACTIVATOR_ROLE");

    // === ОСНОВНЫЕ ДАННЫЕ ИНВАЙТОВ ===
    
    // Маппинг: inviteCode → inviteId (id записи инвайта)
    mapping(string => uint256) public inviteCodeToTokenId;
    
    mapping(string => bool) public inviteCodeExists;

    // Маппинг: inviteId → inviteCode (совместимость имён с API)
    mapping(uint256 => string) public tokenIdToInviteCode;

    mapping(uint256 => bool) public isInviteUsed;

    // Маппинг: user → использованный инвайт (inviteId + 1)
    mapping(address => uint256) public usedInviteByUser;

    mapping(uint256 => uint256) public inviteExpiry;
    mapping(uint256 => uint256) public inviteCreatedAt;
    mapping(uint256 => address) public inviteMinter;
    mapping(uint256 => address) public inviteFirstOwner;

    // Маппинг: user → список inviteId (совместимость API)
    mapping(address => uint256[]) private userInvites;

    // Счётчик общего количества использованных инвайтов
    uint256 public totalInvitesUsed;

    // Счётчик общего количества выданных инвайтов
    uint256 public totalInvitesMinted;

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

    // === СТРУКТУРЫ ДЛЯ ДИАГНОСТИКИ ===
    
    /**
     * @dev Структура для хранения информации об инвайте (inviteId = id записи)
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

    // === СОБЫТИЯ ===
    
    event InviteMinted(address indexed minter, uint256 indexed tokenId, string inviteCode, uint256 expiry);
    event InviteUsed(address indexed user, uint256 indexed tokenId, string inviteCode);
    event UserActivated(address indexed user, address indexed activator, uint256 timestamp);
    event SellerRoleGranted(address indexed user, address indexed nominator, uint256 timestamp);
    event UserSuspended(address indexed user, uint256 until, string reason);
    event SoulIdentityUpdated(address indexed oldSoulIdentity, address indexed newSoulIdentity);

    // === КОНСТРУКТОР ===
    
    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(SELLER_ROLE, msg.sender);
        _grantRole(ACTIVATOR_ROLE, msg.sender);
    }

    // === ОСНОВНЫЕ ФУНКЦИИ ИНВАЙТОВ ===
    
    /**
     * @dev Создание новой записи инвайта (логический inviteId, без ERC721)
     * @param inviteCode уникальный код инвайта
     * @param expiry срок действия (0 = бессрочный)
     * @return inviteId идентификатор созданной записи
     */
    function mintInvite(string memory inviteCode, uint256 expiry) public onlyRole(SELLER_ROLE) returns (uint256) {
        require(bytes(inviteCode).length > 0, "SpiralEngine: empty invite code");
        require(!inviteCodeExists[inviteCode], "SpiralEngine: invite code already exists");
        
        uint256 inviteId = _inviteIdCounter++;
        
        inviteCodeToTokenId[inviteCode] = inviteId;
        inviteCodeExists[inviteCode] = true;
        tokenIdToInviteCode[inviteId] = inviteCode;
        inviteExpiry[inviteId] = expiry;
        inviteCreatedAt[inviteId] = block.timestamp;
        inviteMinter[inviteId] = msg.sender;
        inviteFirstOwner[inviteId] = msg.sender;
        
        userInvites[msg.sender].push(inviteId);
        userInviteCount[msg.sender]++;
        totalInvitesMinted++;
        
        emit InviteMinted(msg.sender, inviteId, inviteCode, expiry);
        return inviteId;
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
        
        // Создаем новые записи инвайтов (без _mint)
        for (uint256 i = 0; i < newInviteCodes.length; i++) {
            require(bytes(newInviteCodes[i]).length > 0, "SpiralEngine: empty invite code");
            require(!inviteCodeExists[newInviteCodes[i]], "SpiralEngine: invite code already exists");
            
            uint256 newInviteId = _inviteIdCounter++;
            
            inviteCodeToTokenId[newInviteCodes[i]] = newInviteId;
            inviteCodeExists[newInviteCodes[i]] = true;
            tokenIdToInviteCode[newInviteId] = newInviteCodes[i];
            inviteExpiry[newInviteId] = expiry;
            inviteCreatedAt[newInviteId] = block.timestamp;
            inviteMinter[newInviteId] = user;
            inviteFirstOwner[newInviteId] = user;
            
            userInvites[user].push(newInviteId);
            userInviteCount[user]++;
            totalInvitesMinted++;
            
            emit InviteMinted(user, newInviteId, newInviteCodes[i], expiry);
        }
        
        emit UserActivated(user, msg.sender, block.timestamp);
    }

    /**
     * @dev Назначение роли продавца (MVP: только админ)
     * @param user адрес пользователя
     * @notice Доступно только DEFAULT_ADMIN_ROLE (деплоер); при выдаче эмитится SellerRoleGranted для оффчейн
     */
    function grantSellerRole(address user) public onlyRole(DEFAULT_ADMIN_ROLE) {
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
     * @return inviteId идентификатор записи инвайта
     */
    function _validateInviteCode(string memory inviteCode, address activator) internal view returns (uint256) {
        require(inviteCodeExists[inviteCode], "SpiralEngine: invite code not found");
        uint256 inviteId = inviteCodeToTokenId[inviteCode];
        require(inviteMinter[inviteId] == activator, "SpiralEngine: invite not from activator");
        return inviteId;
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
     * @param inviteId id записи инвайта
     */
    function isInviteFromActivator(uint256 inviteId, address activator) public view returns (bool) {
        return inviteMinter[inviteId] == activator;
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

    // === СОВМЕСТИМОСТЬ API (inviteId, без ERC721) ===

    function name() public pure returns (string memory) { return "SpiralInvite"; }
    function symbol() public pure returns (string memory) { return "SPIRAL"; }

    function ownerOf(uint256 inviteId) public view returns (address) {
        address o = inviteFirstOwner[inviteId];
        require(o != address(0), "SpiralEngine: invite not found");
        return o;
    }

    function balanceOf(address owner) public view returns (uint256) {
        return userInviteCount[owner];
    }

    function locked(uint256 /* inviteId */) external pure override returns (bool) {
        return true;
    }

    function approve(address, uint256) public pure { revert("SpiralEngine: approvals not allowed"); }
    function setApprovalForAll(address, bool) public pure { revert("SpiralEngine: approvals not allowed"); }
    function transferFrom(address, address, uint256) public pure { revert("SpiralEngine: transfers not allowed"); }
    function safeTransferFrom(address, address, uint256) public pure { revert("SpiralEngine: transfers not allowed"); }
    function safeTransferFrom(address, address, uint256, bytes calldata) public pure { revert("SpiralEngine: transfers not allowed"); }
    function getApproved(uint256) public pure returns (address) { return address(0); }
    function isApprovedForAll(address, address) public pure returns (bool) { return false; }

    function supportsInterface(bytes4 interfaceId) public view override(AccessControl) returns (bool) {
        return interfaceId == type(IERC5192).interfaceId || super.supportsInterface(interfaceId);
    }

    // === ДИАГНОСТИЧЕСКИЕ ФУНКЦИИ ===
    
    /**
     * @dev Получить полную диагностику состояния селлера
     * @param seller адрес селлера для диагностики
     * @return диагностическая информация о состоянии селлера
     */
    function getSellerDiagnostics(address seller) public view returns (SellerDiagnostics memory) {
        // Только владелец или админ может получить полную диагностику
        require(
            msg.sender == seller || hasRole(DEFAULT_ADMIN_ROLE, msg.sender),
            "SpiralEngine: only owner or admin can access seller diagnostics"
        );
        
        SellerDiagnostics memory diagnostics;
        
        // Проверка активации пользователя
        uint256 usedInvite = usedInviteByUser[seller];
        diagnostics.isActivated = usedInvite > 0;
        diagnostics.usedInviteTokenId = usedInvite > 0 ? usedInvite - 1 : 0; // -1 чтобы избежать конфликта с tokenId = 0
        
        // Проверка ролей
        diagnostics.hasSellerRole = hasRole(SELLER_ROLE, seller);
        diagnostics.hasActivatorRole = hasRole(ACTIVATOR_ROLE, seller);
        
        // Получение инвайтов пользователя (теперь через private mapping)
        uint256[] memory userInviteIds = userInvites[seller];
        diagnostics.userInvites = new InviteInfo[](userInviteIds.length);
        
        for (uint256 i = 0; i < userInviteIds.length; i++) {
            uint256 tokenId = userInviteIds[i];
            diagnostics.userInvites[i] = InviteInfo({
                inviteCode: tokenIdToInviteCode[tokenId],
                tokenId: tokenId,
                isUsed: isInviteUsed[tokenId],
                activatedBy: address(0), // TODO: добавить отслеживание активатора инвайта
                activationTime: 0,       // TODO: добавить отслеживание времени активации
                expiry: inviteExpiry[tokenId]
            });
        }
        
        // Общее количество заминченных инвайтов
        diagnostics.totalInvitesMinted = userInviteCount[seller];
        
        return diagnostics;
    }
    
    /**
     * @dev Получить инвайты пользователя (только владелец или админ)
     * @param user адрес пользователя
     * @return массив ID токенов инвайтов пользователя
     */
    function getUserInvites(address user) public view returns (uint256[] memory) {
        // Только владелец может получить свои инвайты, или админ для аудита
        require(
            msg.sender == user || hasRole(DEFAULT_ADMIN_ROLE, msg.sender),
            "SpiralEngine: only owner or admin can access invites"
        );
        return userInvites[user];
    }
    
    /**
     * @dev Получить количество инвайтов пользователя (публичный доступ)
     * @param user адрес пользователя
     * @return количество инвайтов
     */
    function getUserInviteCount(address user) public view returns (uint256) {
        return userInvites[user].length;
    }
    
    /**
     * @dev Получить публичную информацию о селлере (без приватных данных)
     * @param seller адрес селлера
     * @return isActivated статус активации пользователя
     * @return hasSellerRole наличие роли SELLER_ROLE
     * @return hasActivatorRole наличие роли ACTIVATOR_ROLE
     * @return inviteCount количество инвайтов пользователя
     * @return userTotalInvites общее количество заминченных инвайтов пользователем
     */
    function getSellerPublicInfo(address seller) public view returns (
        bool isActivated,
        bool hasSellerRole,
        bool hasActivatorRole,
        uint256 inviteCount,
        uint256 userTotalInvites
    ) {
        // Публичная информация доступна всем
        uint256 usedInvite = usedInviteByUser[seller];
        isActivated = usedInvite > 0;
        hasSellerRole = hasRole(SELLER_ROLE, seller);
        hasActivatorRole = hasRole(ACTIVATOR_ROLE, seller);
        inviteCount = userInvites[seller].length;
        userTotalInvites = userInviteCount[seller];
    }
}
