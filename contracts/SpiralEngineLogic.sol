// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts-upgradeable/token/ERC721/ERC721Upgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "./interfaces/ISoulIdentity.sol";
import "./interfaces/ISpiralEngine.sol";
import "./IERC5192.sol";

/**
 * @title SpiralEngineLogic
 * @author Zeya888 (https://zeya888.me)
 * @dev Полная UUPS имплементация для SpiralEngine
 * @notice Содержит ВСЮ бизнес-логику спиральной иерархии и state variables
 * @notice Версия: 1.0.0 - UUPS Standard Migration
 * 
 * Архитектура:
 * - Все state variables объявлены в Logic
 * - При delegatecall state физически хранится в Proxy
 * - Прямой доступ к переменным (без StorageSlot)
 * - Роли и пауза управляются через Logic
 * - Апгрейды через _authorizeUpgrade (UPGRADER_ROLE)
 * 
 * Ключевые улучшения от оригинала:
 * - ✅ Upgradeable архитектура (UUPS паттерн)
 * - ✅ ReentrancyGuard на критических функциях
 * - ✅ Pausable для emergency ситуаций
 * - ✅ Custom errors для экономии gas
 * - ✅ Gas optimizations (unchecked, calldata, caching)
 * - ✅ Storage gap для будущих обновлений
 * 
 * @custom:security-contact security@amanita.com
 */
contract SpiralEngineLogic is 
    Initializable,
    UUPSUpgradeable,
    ERC721Upgradeable,
    AccessControlUpgradeable,
    PausableUpgradeable,
    ReentrancyGuardUpgradeable,
    IERC5192,
    ISpiralEngine
{
    // === КОНСТАНТЫ ===
    
    /// @notice Версия Logic контракта для апгрейдов
    uint256 public constant LOGIC_VERSION = 1;
    
    /// @notice Роль продавца для минтинга инвайтов
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");
    
    /// @notice Роль активатора для активации пользователей
    bytes32 public constant ACTIVATOR_ROLE = keccak256("ACTIVATOR_ROLE");
    
    /// @notice Роль для обновления контракта
    bytes32 public constant UPGRADER_ROLE = keccak256("UPGRADER_ROLE");
    
    /// @notice Роль администратора для управления системой
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    
    /// @notice Максимальный размер batch для mintInviteBatch (защита от переполнения газа)
    uint256 public constant MAX_BATCH_SIZE = 50;
    
    // === CUSTOM ERRORS ===
    // Custom errors для экономии gas и улучшения читаемости
    
    /// @notice Ошибка: пустой код инвайта
    error EmptyInviteCode();
    
    /// @notice Ошибка: инвайт код уже существует
    error InviteCodeAlreadyExists();
    
    /// @notice Ошибка: инвайт не найден
    error InviteNotFound();
    
    /// @notice Ошибка: инвайт уже использован
    error InviteAlreadyUsed();
    
    /// @notice Ошибка: инвайт истек
    error InviteExpired();
    
    /// @notice Ошибка: пользователь уже активирован
    error UserAlreadyActivated();
    
    /// @notice Ошибка: пользователь не активирован
    error UserNotActivated();
    
    /// @notice Ошибка: недопустимый адрес пользователя
    error InvalidUserAddress();
    
    /// @notice Ошибка: неправильное количество инвайт кодов (требуется 12)
    error InvalidInviteCount();
    
    /// @notice Ошибка: достигнут лимит круга (12 человек)
    error CircleLimitReached();
    
    /// @notice Ошибка: инвайт не принадлежит активатору
    error InviteNotFromActivator();
    
    /// @notice Ошибка: нулевой адрес
    error ZeroAddress();
    
    /// @notice Ошибка: недопустимая продолжительность
    error InvalidDuration();
    
    /// @notice Ошибка: SoulIdentity не установлен
    error SoulIdentityNotSet();
    
    /// @notice Ошибка: передача токенов запрещена (SBT)
    error TransfersNotAllowed();
    
    /// @notice Ошибка: одобрение токенов запрещено (SBT)
    error ApprovalsNotAllowed();
    
    /// @notice Ошибка: несанкционированный доступ к диагностике
    error UnauthorizedDiagnosticAccess();
    
    /// @notice Ошибка: несанкционированный доступ к инвайтам
    error UnauthorizedInviteAccess();
    
    /// @notice Ошибка: пользователь уже имеет роль продавца
    error UserAlreadyHasSellerRole();
    
    /// @notice Ошибка: пустой batch (длина массивов 0)
    error BatchEmpty();
    
    /// @notice Ошибка: несовпадение длин массивов inviteCodes и expiries
    error BatchLengthMismatch();
    
    /// @notice Ошибка: размер batch превышает MAX_BATCH_SIZE
    /// @param size текущий размер
    /// @param max максимально допустимый размер
    error BatchTooLarge(uint256 size, uint256 max);
    
    // === STATE VARIABLES ===
    // ⚠️ КРИТИЧНО: Порядок переменных должен совпадать с оригинальным контрактом
    // При delegatecall данные физически хранятся в Proxy
    // Прямой доступ к переменным (без StorageSlot)
    
    /// @notice Счётчик tokenId для ERC721
    uint256 private _tokenIdCounter;
    
    // === ОСНОВНЫЕ ДАННЫЕ ИНВАЙТОВ ===
    
    /// @notice Маппинг: inviteCode → tokenId (NFT инвайта)
    mapping(string => uint256) public inviteCodeToTokenId;
    
    /// @notice Маппинг: inviteCode → существует ли код
    mapping(string => bool) public inviteCodeExists;
    
    /// @notice Маппинг: tokenId → inviteCode
    mapping(uint256 => string) public tokenIdToInviteCode;
    
    /// @notice Маппинг: tokenId → использован ли инвайт
    mapping(uint256 => bool) public isInviteUsed;
    
    /// @notice Маппинг: user → использованный инвайт (tokenId + 1)
    mapping(address => uint256) public usedInviteByUser;
    
    /// @notice Маппинг: tokenId → срок действия инвайта (0 если бессрочный)
    mapping(uint256 => uint256) public inviteExpiry;
    
    /// @notice Маппинг: tokenId → дата создания инвайта
    mapping(uint256 => uint256) public inviteCreatedAt;
    
    /// @notice Маппинг: tokenId → адрес создателя (minter)
    mapping(uint256 => address) public inviteMinter;
    
    /// @notice Маппинг: tokenId → адрес первого владельца инвайта
    mapping(uint256 => address) public inviteFirstOwner;
    
    /// @notice Маппинг: user → список всех его инвайтов (tokenId)
    mapping(address => uint256[]) private userInvites;
    
    /// @notice Счётчик общего количества использованных инвайтов
    uint256 public totalInvitesUsed;
    
    /// @notice Счётчик общего количества выданных инвайтов
    uint256 public totalInvitesMinted;
    
    /// @notice Маппинг: tokenId → история всех владельцев
    mapping(uint256 => address[]) public inviteTransferHistory;
    
    /// @notice Массив всех активированных пользователей
    address[] public activatedUsers;
    
    /// @notice Маппинг: user → количество заминченных инвайтов
    mapping(address => uint256) public userInviteCount;
    
    // === ОТСЛЕЖИВАНИЕ ОТВЕТСТВЕННОСТИ ===
    
    /// @notice Маппинг: кто активировал пользователя
    mapping(address => address) public userActivator;
    
    /// @notice Маппинг: кто назначил роль SELLER_ROLE
    mapping(address => address) public sellerNominator;
    
    /// @notice Маппинг: кого активировал данный активатор
    mapping(address => address[]) public activatedBy;
    
    /// @notice Маппинг: кого назначил селлером данный номинатор
    mapping(address => address[]) public nominatedSellers;
    
    // === СИСТЕМА САНКЦИЙ ===
    
    /// @notice Маппинг: счетчик нарушений для каждого пользователя
    mapping(address => uint256) public violationCount;
    
    /// @notice Маппинг: до какого времени заблокирован пользователь
    mapping(address => uint256) public suspensionUntil;
    
    /// @notice Маппинг: нарушения активированных пользователей
    mapping(address => uint256) public activationViolations;
    
    /// @notice Маппинг: нарушения назначенных селлеров
    mapping(address => uint256) public nominationViolations;
    
    // === ИНТЕГРАЦИЯ С ЭКОСИСТЕМОЙ ===
    
    /// @notice Адрес контракта SoulIdentity для делегирования SBT функций
    ISoulIdentity public soulIdentity;
    
    // === STORAGE GAP ===
    // Резерв для будущих переменных в апгрейдах
    // При добавлении новых переменных уменьшайте размер gap
    uint256[50] private __gap;
    
    // === СОБЫТИЯ ===
    // События определены в ISpiralEngine интерфейсе и наследуются
    
    // === ИНИЦИАЛИЗАЦИЯ ===
    
    /**
     * @dev Инициализация Logic контракта (UUPS-совместимый)
     * @param admin Адрес администратора, получающего все роли
     * @notice Инициализация должна происходить через Proxy при деплое
     * @notice Заменяет constructor для upgradeable контрактов
     */
    function initialize(address admin) public initializer {
        if (admin == address(0)) revert ZeroAddress();
        
        // Инициализация всех модулей OpenZeppelin в правильном порядке
        __ERC721_init("SpiralInvite", "SPIRAL");
        __AccessControl_init();
        __UUPSUpgradeable_init();
        __Pausable_init();
        __ReentrancyGuard_init();
        
        // Выдаем все роли админу
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
        _grantRole(SELLER_ROLE, admin);
        _grantRole(ACTIVATOR_ROLE, admin);
    }
    
    // === UUPS UPGRADE PROTECTION ===
    
    /**
     * @dev Авторизация обновления контракта
     * @param newImplementation адрес новой Logic имплементации
     * @notice Только UPGRADER_ROLE может обновлять контракт
     * @custom:oz-upgrades-unsafe-allow-reachable delegatecall
     */
    function _authorizeUpgrade(address newImplementation) 
        internal 
        override 
        onlyRole(UPGRADER_ROLE) 
        view // Warning fix: функция только проверяет, не модифицирует
    {
        if (newImplementation == address(0)) revert ZeroAddress();
        // Дополнительные проверки можно добавить здесь
    }
    
    // === ФУНКЦИИ ПАУЗЫ ===
    
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
    
    // === ОСНОВНЫЕ ФУНКЦИИ УПРАВЛЕНИЯ ИНВАЙТАМИ ===
    
    /**
     * @dev Минт нового инвайта
     * @param inviteCode уникальный код инвайта
     * @param expiry срок действия (0 = бессрочный)
     * @return tokenId идентификатор созданного NFT
     * 
     * @notice Доступно только пользователям с SELLER_ROLE
     * @notice Создаёт новый NFT инвайт с уникальным кодом
     */
    function mintInvite(
        string calldata inviteCode,
        uint256 expiry
    ) 
        external 
        whenNotPaused 
        nonReentrant 
        onlyRole(SELLER_ROLE) 
        override 
        returns (uint256) 
    {
        return _mintInviteSingle(inviteCode, expiry);
    }
    
    /**
     * @dev Внутренняя логика минта одного инвайта (без модификаторов). Вызывается из mintInvite и mintInviteBatch.
     * @param inviteCode уникальный код инвайта
     * @param expiry срок действия (0 = бессрочный)
     * @return tokenId идентификатор созданного NFT
     */
    function _mintInviteSingle(string calldata inviteCode, uint256 expiry) internal returns (uint256 tokenId) {
        if (bytes(inviteCode).length == 0) revert EmptyInviteCode();
        if (inviteCodeExists[inviteCode]) revert InviteCodeAlreadyExists();
        
        unchecked {
            tokenId = _tokenIdCounter++;
        }
        
        _mint(msg.sender, tokenId);
        
        inviteCodeToTokenId[inviteCode] = tokenId;
        inviteCodeExists[inviteCode] = true;
        tokenIdToInviteCode[tokenId] = inviteCode;
        inviteExpiry[tokenId] = expiry;
        inviteCreatedAt[tokenId] = block.timestamp;
        inviteMinter[tokenId] = msg.sender;
        inviteFirstOwner[tokenId] = msg.sender;
        
        userInvites[msg.sender].push(tokenId);
        
        unchecked {
            userInviteCount[msg.sender]++;
            totalInvitesMinted++;
        }
        
        emit InviteMinted(msg.sender, tokenId, inviteCode, expiry);
        
        return tokenId;
    }
    
    /**
     * @dev Минт нескольких инвайтов в одной транзакции (batch)
     * @param inviteCodes массив уникальных кодов инвайтов
     * @param expiries массив сроков действия (0 = бессрочный) для каждого инвайта
     * @return tokenIds массив идентификаторов созданных NFT
     * @notice Доступно только пользователям с SELLER_ROLE; размер batch не более MAX_BATCH_SIZE
     */
    function mintInviteBatch(
        string[] calldata inviteCodes,
        uint256[] calldata expiries
    )
        external
        whenNotPaused
        nonReentrant
        onlyRole(SELLER_ROLE)
        override
        returns (uint256[] memory tokenIds)
    {
        if (inviteCodes.length == 0) revert BatchEmpty();
        if (inviteCodes.length != expiries.length) revert BatchLengthMismatch();
        if (inviteCodes.length > MAX_BATCH_SIZE) revert BatchTooLarge(inviteCodes.length, MAX_BATCH_SIZE);
        
        tokenIds = new uint256[](inviteCodes.length);
        for (uint256 i; i < inviteCodes.length;) {
            tokenIds[i] = _mintInviteSingle(inviteCodes[i], expiries[i]);
            unchecked {
                ++i;
            }
        }
        return tokenIds;
    }
    
    /**
     * @dev Активация пользователя с помощью инвайта
     * @param inviteCode код инвайта
     * @param user адрес пользователя для активации
     * @param newInviteCodes новые инвайты для пользователя (ровно 12)
     * @param expiry срок действия новых инвайтов
     * 
     * @notice Доступно только пользователям с ACTIVATOR_ROLE
     * @notice Создаёт 12 новых инвайтов для активированного пользователя
     * @notice Инвайт должен принадлежать активатору
     */
    function activateUser(
        string calldata inviteCode,
        address user,
        string[] calldata newInviteCodes,
        uint256 expiry
    ) 
        external 
        whenNotPaused 
        nonReentrant 
        onlyRole(ACTIVATOR_ROLE) 
        override 
    {
        // Валидация входных параметров
        if (user == address(0)) revert InvalidUserAddress();
        if (usedInviteByUser[user] != 0) revert UserAlreadyActivated();
        if (newInviteCodes.length != 12) revert InvalidInviteCount();
        
        // Проверка лимита круга активатора (12 человек max)
        if (activatedBy[msg.sender].length >= 12) revert CircleLimitReached();
        
        // Валидация инвайт кода
        uint256 tokenId = _validateInviteCode(inviteCode, msg.sender);
        if (isInviteUsed[tokenId]) revert InviteAlreadyUsed();
        
        // Проверка срока действия
        uint256 expiration = inviteExpiry[tokenId];
        if (expiration != 0 && expiration <= block.timestamp) revert InviteExpired();
        
        // Используем инвайт
        isInviteUsed[tokenId] = true;
        usedInviteByUser[user] = tokenId + 1; // +1 чтобы избежать конфликта с tokenId = 0
        
        unchecked {
            totalInvitesUsed++;
        }
        
        // Записываем активатора
        userActivator[user] = msg.sender;
        activatedBy[msg.sender].push(user);
        activatedUsers.push(user);
        
        // Создаем 12 новых инвайтов для пользователя
        // Газовая оптимизация: кэшируем length
        uint256 codesLength = newInviteCodes.length;
        for (uint256 i = 0; i < codesLength;) {
            string calldata code = newInviteCodes[i];
            
            // Валидация каждого кода
            if (bytes(code).length == 0) revert EmptyInviteCode();
            if (inviteCodeExists[code]) revert InviteCodeAlreadyExists();
            
            // Минтим новый инвайт
            uint256 newTokenId;
            unchecked {
                newTokenId = _tokenIdCounter++;
            }
            
            _mint(user, newTokenId);
            
            // Сохраняем данные нового инвайта
            inviteCodeToTokenId[code] = newTokenId;
            inviteCodeExists[code] = true;
            tokenIdToInviteCode[newTokenId] = code;
            inviteExpiry[newTokenId] = expiry;
            inviteCreatedAt[newTokenId] = block.timestamp;
            inviteMinter[newTokenId] = user;
            inviteFirstOwner[newTokenId] = user;
            
            userInvites[user].push(newTokenId);
            
            unchecked {
                userInviteCount[user]++;
                totalInvitesMinted++;
            }
            
            emit InviteMinted(user, newTokenId, code, expiry);
            
            unchecked { ++i; }
        }

        // Auto-grant ACTIVATOR_ROLE: каждый активированный пользователь становится Activator (Roles Policy, MVP Scope)
        _grantRole(ACTIVATOR_ROLE, user);
        
        emit UserActivated(user, msg.sender, block.timestamp);
    }
    
    /**
     * @dev Валидация инвайт кода (internal)
     * @param inviteCode код инвайта
     * @param activator адрес активатора
     * @return tokenId идентификатор токена
     */
    function _validateInviteCode(
        string calldata inviteCode,
        address activator
    ) internal view returns (uint256) {
        if (!inviteCodeExists[inviteCode]) revert InviteNotFound();
        
        uint256 tokenId = inviteCodeToTokenId[inviteCode];
        
        if (inviteMinter[tokenId] != activator) revert InviteNotFromActivator();
        
        return tokenId;
    }

    /**
     * @dev Проверка права на ACTIVATOR_ROLE (активированный пользователь)
     * @param user адрес пользователя
     * @return true если usedInviteByUser[user] != 0 (единый источник истины для eligibility)
     * @notice Используется для пост-MVP restoreActivatorRole после отзыва; в MVP в activateUser не вызывается
     */
    function _isEligibleForActivatorRole(address user) internal view returns (bool) {
        return usedInviteByUser[user] != 0;
    }
    
    /**
     * @dev Назначение роли продавца (MVP: только ADMIN)
     * @param user адрес пользователя
     *
     * @notice Доступно только ADMIN_ROLE (MVP Scope: выдача SELLER только админом)
     * @notice Пользователь должен быть активирован (usedInviteByUser != 0)
     * @notice При успешной выдаче эмитится SellerRoleGranted(user, msg.sender, block.timestamp) для оффчейн-аудита и мониторинга
     */
    function grantSellerRole(address user)
        external
        whenNotPaused
        nonReentrant
        onlyRole(ADMIN_ROLE)
        override
    {
        if (user == address(0)) revert InvalidUserAddress();
        if (usedInviteByUser[user] == 0) revert UserNotActivated();
        if (hasRole(SELLER_ROLE, user)) revert UserAlreadyHasSellerRole();

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
     * 
     * @notice Доступно только пользователям с ADMIN_ROLE
     * @notice Применяет каскадные санкции к активатору и номинатору
     */
    function suspendUser(
        address user,
        uint256 duration,
        string calldata reason
    ) 
        external 
        whenNotPaused 
        nonReentrant 
        onlyRole(ADMIN_ROLE) 
        override 
    {
        if (user == address(0)) revert InvalidUserAddress();
        if (usedInviteByUser[user] == 0) revert UserNotActivated();
        if (duration == 0) revert InvalidDuration();
        
        suspensionUntil[user] = block.timestamp + duration;
        
        unchecked {
            violationCount[user]++;
        }
        
        // Каскадные санкции: увеличиваем счётчик нарушений у активатора
        address activator = userActivator[user];
        if (activator != address(0)) {
            unchecked {
                activationViolations[activator]++;
            }
        }
        
        // Каскадные санкции: увеличиваем счётчик нарушений у номинатора
        address nominator = sellerNominator[user];
        if (nominator != address(0)) {
            unchecked {
                nominationViolations[nominator]++;
            }
        }
        
        emit UserSuspended(user, suspensionUntil[user], reason);
    }
    
    // === VIEW FUNCTIONS ===
    // inviteTransferHistory уже объявлен как public mapping (автоматический getter)
    
    /**
     * @dev Получить размер круга активатора
     * @param activator адрес активатора
     * @return размер круга (количество активированных пользователей)
     */
    function getCircleSize(address activator) external view override returns (uint256) {
        return activatedBy[activator].length;
    }
    
    /**
     * @dev Получить членов круга активатора
     * @param activator адрес активатора
     * @return массив адресов членов круга
     */
    function getCircleMembers(address activator) external view override returns (address[] memory) {
        return activatedBy[activator];
    }
    
    /**
     * @dev Проверить, является ли инвайт от активатора
     * @param tokenId идентификатор токена
     * @param activator адрес активатора
     * @return true если инвайт от активатора
     */
    function isInviteFromActivator(uint256 tokenId, address activator) external view override returns (bool) {
        return inviteMinter[tokenId] == activator;
    }
    
    // === SOUL IDENTITY INTEGRATION ===
    
    /**
     * @dev Установить адрес контракта SoulIdentity
     * @param _soulIdentity адрес контракта SoulIdentity
     * 
     * @notice Доступно только ADMIN_ROLE
     */
    function setSoulIdentity(address _soulIdentity) 
        external 
        whenNotPaused 
        nonReentrant 
        onlyRole(ADMIN_ROLE) 
        override 
    {
        if (_soulIdentity == address(0)) revert ZeroAddress();
        
        address oldSoulIdentity = address(soulIdentity);
        soulIdentity = ISoulIdentity(_soulIdentity);
        
        emit SoulIdentityUpdated(oldSoulIdentity, _soulIdentity);
    }
    
    /**
     * @dev Получить уровень души пользователя (делегирование к SoulIdentity)
     * @param user адрес пользователя
     * @return уровень души
     */
    function getSoulLevel(address user) external view override returns (uint256) {
        if (address(soulIdentity) == address(0)) revert SoulIdentityNotSet();
        return soulIdentity.getSoulLevel(user);
    }
    
    /**
     * @dev Получить репутацию души пользователя (делегирование к SoulIdentity)
     * @param user адрес пользователя
     * @return репутация души
     */
    function getSoulReputation(address user) external view override returns (uint256) {
        if (address(soulIdentity) == address(0)) revert SoulIdentityNotSet();
        return soulIdentity.getSoulReputation(user);
    }
    
    /**
     * @dev Получить идентичность души пользователя (делегирование к SoulIdentity)
     * @param user адрес пользователя
     * @return DID идентификатор
     */
    function getSoulIdentity(address user) external view override returns (string memory) {
        if (address(soulIdentity) == address(0)) revert SoulIdentityNotSet();
        return soulIdentity.getSoulIdentity(user);
    }
    
    /**
     * @dev Получить уровень верификации души пользователя (делегирование к SoulIdentity)
     * @param user адрес пользователя
     * @return уровень верификации
     */
    function getSoulVerificationLevel(address user) external view override returns (uint8) {
        if (address(soulIdentity) == address(0)) revert SoulIdentityNotSet();
        return soulIdentity.getSoulVerificationLevel(user);
    }
    
    /**
     * @dev Получить полный профиль души пользователя (делегирование к SoulIdentity)
     * @param user адрес пользователя
     * @return level уровень души
     * @return reputation репутация души
     * @return identity идентичность души
     * @return verificationLevel уровень верификации
     * @return guardians список доверенных лиц
     */
    function getSoulProfile(address user) external view override returns (
        uint256 level,
        uint256 reputation,
        string memory identity,
        uint8 verificationLevel,
        address[] memory guardians
    ) {
        if (address(soulIdentity) == address(0)) revert SoulIdentityNotSet();
        return soulIdentity.getSoulProfile(user);
    }
    
    // === DIAGNOSTIC FUNCTIONS ===
    
    /**
     * @dev Получить полную диагностику состояния селлера
     * @param seller адрес селлера для диагностики
     * @return диагностическая информация о состоянии селлера
     * 
     * @notice Доступно только владельцу или админу для защиты приватных данных
     */
    function getSellerDiagnostics(address seller) external view override returns (SellerDiagnostics memory) {
        // Только владелец или админ может получить полную диагностику
        if (msg.sender != seller && !hasRole(ADMIN_ROLE, msg.sender)) {
            revert UnauthorizedDiagnosticAccess();
        }
        
        SellerDiagnostics memory diagnostics;
        
        // Проверка активации пользователя
        uint256 usedInvite = usedInviteByUser[seller];
        diagnostics.isActivated = usedInvite > 0;
        diagnostics.usedInviteTokenId = usedInvite > 0 ? usedInvite - 1 : 0; // -1 для обратного offset
        
        // Проверка ролей
        diagnostics.hasSellerRole = hasRole(SELLER_ROLE, seller);
        diagnostics.hasActivatorRole = hasRole(ACTIVATOR_ROLE, seller);
        
        // Получение инвайтов пользователя
        uint256[] memory userInviteIds = userInvites[seller];
        diagnostics.userInvites = new InviteInfo[](userInviteIds.length);
        
        for (uint256 i = 0; i < userInviteIds.length; i++) {
            uint256 tokenId = userInviteIds[i];
            diagnostics.userInvites[i] = InviteInfo({
                inviteCode: tokenIdToInviteCode[tokenId],
                tokenId: tokenId,
                isUsed: isInviteUsed[tokenId],
                activatedBy: address(0), // TODO: отслеживание активатора инвайта
                activationTime: 0,       // TODO: отслеживание времени активации
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
    function getUserInvites(address user) external view override returns (uint256[] memory) {
        // Только владелец может получить свои инвайты, или админ для аудита
        if (msg.sender != user && !hasRole(ADMIN_ROLE, msg.sender)) {
            revert UnauthorizedInviteAccess();
        }
        return userInvites[user];
    }
    
    /**
     * @dev Получить количество инвайтов пользователя (публичный доступ)
     * @param user адрес пользователя
     * @return количество инвайтов
     */
    function getUserInviteCount(address user) external view override returns (uint256) {
        return userInvites[user].length;
    }
    
    /**
     * @dev Получить публичную информацию о селлере (без приватных данных)
     * @param seller адрес селлера
     * @return isActivated статус активации пользователя
     * @return hasSellerRole_ наличие роли SELLER_ROLE
     * @return hasActivatorRole_ наличие роли ACTIVATOR_ROLE
     * @return inviteCount количество инвайтов пользователя
     * @return userTotalInvites общее количество заминченных инвайтов пользователем
     */
    function getSellerPublicInfo(address seller) external view override returns (
        bool isActivated,
        bool hasSellerRole_,
        bool hasActivatorRole_,
        uint256 inviteCount,
        uint256 userTotalInvites
    ) {
        // Публичная информация доступна всем
        uint256 usedInvite = usedInviteByUser[seller];
        isActivated = usedInvite > 0;
        hasSellerRole_ = hasRole(SELLER_ROLE, seller);
        hasActivatorRole_ = hasRole(ACTIVATOR_ROLE, seller);
        inviteCount = userInvites[seller].length;
        userTotalInvites = userInviteCount[seller];
    }
    
    // === ERC5192 (SOULBOUND) IMPLEMENTATION ===
    
    /**
     * @dev Проверка заблокированности токена (EIP-5192)
     * @return всегда true (SBT токены всегда заблокированы)
     */
    function locked(uint256 /* tokenId */) external pure override returns (bool) {
        // Все SpiralEngine токены - Soulbound (не передаваемые)
        return true;
    }
    
    // === ERC721 OVERRIDES ===
    
    /**
     * @dev Блокировка approve - SBT токены не могут быть approved
     */
    function approve(address, uint256) public pure override {
        revert ApprovalsNotAllowed();
    }
    
    /**
     * @dev Блокировка setApprovalForAll - SBT токены не могут быть approved
     */
    function setApprovalForAll(address, bool) public pure override {
        revert ApprovalsNotAllowed();
    }
    
    /**
     * @dev Переопределение transferFrom для предотвращения передачи
     */
    function transferFrom(address, address, uint256) public pure override {
        revert TransfersNotAllowed();
    }
    
    /**
     * @dev Базовый URI для токенов
     */
    function _baseURI() internal pure override returns (string memory) {
        return "https://api.amanita.com/spiral/";
    }
    
    /**
     * @dev Поддержка интерфейсов
     * @param interfaceId идентификатор интерфейса
     * @return поддерживается ли интерфейс
     */
    function supportsInterface(bytes4 interfaceId) 
        public 
        view 
        override(ERC721Upgradeable, AccessControlUpgradeable) 
        returns (bool) 
    {
        return interfaceId == type(IERC5192).interfaceId || super.supportsInterface(interfaceId);
    }
    
    /**
     * @dev Переопределение hasRole для правильного разрешения конфликта
     * @param role идентификатор роли
     * @param account адрес для проверки
     * @return имеет ли пользователь роль
     */
    function hasRole(bytes32 role, address account) 
        public 
        view 
        override(AccessControlUpgradeable, ISpiralEngine) 
        returns (bool) 
    {
        return super.hasRole(role, account);
    }
}

