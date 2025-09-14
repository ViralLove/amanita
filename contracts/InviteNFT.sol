// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./IERC5192.sol";

contract InviteNFT is ERC721, AccessControl, IERC5192 {
    uint256 private _tokenIdCounter;

    // Роль продавца для доступа к минтингу инвайтов
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");
    
    // Роль активатора для активации пользователей и назначения ролей
    bytes32 public constant ACTIVATOR_ROLE = keccak256("ACTIVATOR_ROLE");

    // Маппинг: inviteCode (уникальный строковый код) => tokenId (NFT инвайта)
    // Позволяет быстро найти NFT по коду, который вводит пользователь
    mapping(string => uint256) public inviteCodeToTokenId;

    // Маппинг: tokenId (NFT инвайта) => inviteCode (уникальный строковый код)
    // Для обратного поиска inviteCode по tokenId (например, для отображения или аудита)
    mapping(uint256 => string) public tokenIdToInviteCode;

    // Маппинг: tokenId => использован ли инвайт
    // Гарантирует, что каждый инвайт может быть использован только один раз
    mapping(uint256 => bool) public isInviteUsed;

    // Маппинг: user (адрес) => использованный инвайт (tokenId)
    // Не позволяет одному пользователю использовать более одного инвайта
    mapping(address => uint256) public usedInviteByUser;

    // Маппинг: tokenId => срок действия инвайта (timestamp, 0 если бессрочный)
    // Позволяет делать инвайты временными (например, для акций)
    mapping(uint256 => uint256) public inviteExpiry;

    // Маппинг: tokenId => дата создания инвайта (timestamp)
    // Для аудита, статистики, отслеживания «свежести» инвайтов
    mapping(uint256 => uint256) public inviteCreatedAt;

    // Маппинг: tokenId => адрес создателя (minter)
    // Позволяет отслеживать, кто создал инвайт (например, продавец или админ)
    mapping(uint256 => address) public inviteMinter;

    // Маппинг: tokenId => адрес первого владельца инвайта
    // Для построения реферальных деревьев, аудита, статистики
    mapping(uint256 => address) public inviteFirstOwner;

    // Маппинг: user (адрес) => список всех его инвайтов (tokenId)
    // Быстрый доступ ко всем инвайтам пользователя (для личного кабинета, управления, аналитики)
    mapping(address => uint256[]) public userInvites;

    // Счётчик общего количества использованных инвайтов
    // Для мониторинга, лимитов, аналитики, контроля эмиссии
    uint256 public totalInvitesUsed;

    // Счётчик общего количества выданных инвайтов
    // Для мониторинга, лимитов, аналитики, контроля эмиссии
    uint256 public totalInvitesMinted;

    // Маппинг: tokenId => история всех владельцев (адреса)
    // Позволяет вести полный аудит всех передач инвайта (NFT) по времени
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

    // === СИСТЕМА ВОССТАНОВЛЕНИЯ ДОСТУПА ===
    // Маппинг: пользователь => список доверенных лиц
    mapping(address => address[]) public trustedGuardians;
    
    // Маппинг: пользователь => доверенное лицо => статус одобрения
    mapping(address => mapping(address => bool)) public guardianApproval;
    
    // Маппинг: пользователь => количество доверенных лиц
    mapping(address => uint256) public guardianCount;
    
    // Маппинг: пользователь => временный ключ доступа
    mapping(address => address) public temporaryAccessKey;
    
    // Маппинг: временный ключ => срок действия
    mapping(address => uint256) public temporaryKeyExpiry;
    
    // Маппинг: пользователь => статус восстановления
    mapping(address => bool) public isRecoveryInProgress;
    
    // Маппинг: пользователь => время последнего восстановления
    mapping(address => uint256) public lastRecoveryTime;

    // === ИНТЕГРАЦИЯ С DID (DECENTRALIZED IDENTIFIERS) ===
    // Маппинг: пользователь => DID идентификатор
    mapping(address => string) public userDID;
    
    // Маппинг: DID => адрес пользователя (обратный поиск)
    mapping(string => address) public didToAddress;
    
    // Маппинг: пользователь => репутационный счет
    mapping(address => uint256) public reputationScore;
    
    // Маппинг: пользователь => уровень верификации
    mapping(address => uint8) public verificationLevel; // 0-5
    
    // Маппинг: пользователь => время последней верификации
    mapping(address => uint256) public lastVerificationTime;
    
    // Маппинг: пользователь => количество успешных операций
    mapping(address => uint256) public successfulOperations;
    
    // Маппинг: пользователь => количество неудачных операций
    mapping(address => uint256) public failedOperations;

    // === РАСШИРЕННЫЕ МЕТАДАННЫЕ SBT ===
    // Маппинг: tokenId => версия SBT
    mapping(uint256 => uint256) public sbtVersion;
    
    // Маппинг: tokenId => тип SBT
    mapping(uint256 => string) public sbtType;
    
    // Маппинг: tokenId => дополнительные атрибуты
    mapping(uint256 => string) public sbtAttributes;
    
    // Базовая версия SBT
    uint256 public constant SBT_BASE_VERSION = 1;
    
    // Текущая версия SBT контракта
    uint256 public constant SBT_CONTRACT_VERSION = 2;

    event InviteActivated(address indexed user, string inviteCode, uint256 tokenId, uint256 timestamp);
    event BatchInvitesMinted(address indexed to, uint256[] tokenIds, string[] inviteCodes, uint256 expiry);
    event InviteTransferred(uint256 indexed tokenId, address from, address to, uint256 timestamp);
    
    // === НОВЫЕ СОБЫТИЯ ДЛЯ РАЗДЕЛЕННЫХ ПРОЦЕССОВ ===
    event UserActivated(address indexed activator, address indexed user, string inviteCode, uint256 tokenId, uint256 timestamp);
    event SellerRoleGranted(address indexed nominator, address indexed seller, uint256 timestamp);
    event UserSuspended(address indexed user, uint256 duration, string reason, uint256 timestamp);
    event ActivatorWarning(address indexed activator, string message);
    event ActivatorSuspended(address indexed activator, uint256 duration, string reason);
    event NominatorWarning(address indexed nominator, string message);
    event NominatorSuspended(address indexed nominator, uint256 duration, string reason);
    
    // === ДИФФЕРЕНЦИРОВАННЫЕ СОБЫТИЯ ДЛЯ МОНИТОРИНГА КРУГОВ ===
    event FirstCircleActivation(address indexed activator, address indexed user, string inviteCode, uint256 tokenId, uint256 timestamp);
    event CircleActivation(address indexed activator, address indexed user, string inviteCode, uint256 tokenId, uint256 timestamp);
    
    // === СОБЫТИЯ СИСТЕМЫ ВОССТАНОВЛЕНИЯ ДОСТУПА ===
    event GuardianAdded(address indexed user, address indexed guardian, uint256 timestamp);
    event GuardianRemoved(address indexed user, address indexed guardian, uint256 timestamp);
    event RecoveryInitiated(address indexed user, address indexed guardian, uint256 timestamp);
    event RecoveryCompleted(address indexed user, address indexed newAddress, uint256 timestamp);
    event TemporaryKeyCreated(address indexed user, address indexed tempKey, uint256 expiry, uint256 timestamp);
    event TemporaryKeyExpired(address indexed user, address indexed tempKey, uint256 timestamp);
    
    // === СОБЫТИЯ DID ИНТЕГРАЦИИ ===
    event DIDLinked(address indexed user, string did, uint256 timestamp);
    event DIDUnlinked(address indexed user, string did, uint256 timestamp);
    event IdentityVerified(address indexed user, uint8 verificationLevel, uint256 timestamp);
    event ReputationUpdated(address indexed user, uint256 newScore, uint256 timestamp);
    event OperationRecorded(address indexed user, bool success, uint256 timestamp);
    
    // === СОБЫТИЯ SBT МЕТАДАННЫХ ===
    event SBTMetadataUpdated(uint256 indexed tokenId, string sbtType, string attributes, uint256 timestamp);
    event SBTVersionUpdated(uint256 indexed tokenId, uint256 newVersion, uint256 timestamp);

    constructor() ERC721("Amanita Invite", "AINV") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    /**
     * @dev Внутренняя проверка валидности инвайта по inviteCode и адресу пользователя
     * @param inviteCode inviteCode (строка)
     * @param user адрес пользователя для активации
     * @return success true если инвайт валиден, false иначе
     * @return reason строка с причиной невалидности ("not_found", "already_used", "expired", "user_already_activated", "invite_not_from_activator")
     *
     * Критерии приёмки:
     * - inviteCode существует
     * - invite не использован
     * - invite не истёк
     * - Пользователь не активирован ранее
     * - Инвайт принадлежит активатору (кроме DEFAULT_ADMIN_ROLE)
     * - Возвращает (true, "") если всё валидно, иначе (false, причина)
     * - Только internal view
     */
    function _validateInviteCode(string memory inviteCode, address user) internal view returns (bool, string memory) {
        // 1. Проверка, что пользователь не активирован ранее
        if (usedInviteByUser[user] != 0) {
            return (false, "user_already_activated");
        }
        
        // 2. Получить tokenId по inviteCode
        uint256 tokenId = inviteCodeToTokenId[inviteCode];
        if (tokenId == 0) {
            return (false, "not_found");
        }
        
        // 3. КРИТИЧЕСКОЕ: Проверка принадлежности инвайта активатору
        if (!hasRole(DEFAULT_ADMIN_ROLE, msg.sender)) {
            if (inviteMinter[tokenId] != msg.sender) {
                return (false, "invite_not_from_activator");
            }
        }
        
        // 4. Проверка, был ли инвайт уже использован
        if (isInviteUsed[tokenId]) {
            return (false, "already_used");
        }
        
        // 5. Проверка срока действия (если не бессрочный)
        uint256 expiry = inviteExpiry[tokenId];
        if (expiry != 0 && expiry < block.timestamp) {
            return (false, "expired");
        }
        
        // 6. Все проверки пройдены — инвайт валиден
        return (true, "");
    }


    /**
     * @dev Проверка валидности инвайта по inviteCode и адресу пользователя
     * @param inviteCode inviteCode (строка)
     * @return success true если инвайт валиден, false иначе
     * @return reason строка с причиной невалидности ("not_found", "already_used", "expired", "user_already_activated")
     * 
     */
    function validateInviteCode(string memory inviteCode, address user) public view returns (bool, string memory) {
        return _validateInviteCode(inviteCode, user);
    }

    /**
     * @dev Активация инвайта и batch-минт новых инвайтов для пользователя
     * @param inviteCode код инвайта, который активируется (строка)
     * @param user адрес пользователя, который активирует инвайт
     * @param newInviteCodes массив новых inviteCode для раздачи друзьям
     * @param expiry срок действия новых инвайтов (timestamp, 0 если бессрочные)
     *
     * Критерии приёмки:
     * - Все проверки валидности и уникальности до изменения состояния
     * - inviteCode валиден, не использован, не истёк, user не активирован
     * - inviteCode отмечается как использованный, user добавляется в историю
     * - Минтятся новые инвайты на user, все маппинги инициализированы
     * - Эмитятся события InviteActivated и BatchInvitesMinted
     * - Счётчики обновляются
     * - Метод доступен только авторизованным (например, MINTER_ROLE)
     * - Любая ошибка — revert всей транзакции
     */
    function activateAndMintInvites(
        string memory inviteCode,
        address user,
        string[] memory newInviteCodes,
        uint256 expiry
    ) external onlyRole(SELLER_ROLE) {
        // 1. Проверка, что пользователь не активировал инвайт ранее
        require(usedInviteByUser[user] == 0, "User already activated invite");
        // 2. Проверка валидности inviteCode и expiry
        (bool valid, string memory reason) = _validateInviteCode(inviteCode, user);
        require(valid, reason);
        uint256 tokenId = inviteCodeToTokenId[inviteCode];
        // 3. Проверка уникальности newInviteCodes внутри массива
        uint256 len = newInviteCodes.length;
        for (uint256 i = 0; i < len; i++) {
            for (uint256 j = i + 1; j < len; j++) {
                require(keccak256(bytes(newInviteCodes[i])) != keccak256(bytes(newInviteCodes[j])), "Duplicate newInviteCode in batch");
            }
        }
        // 4. Проверка уникальности каждого newInviteCode в системе
        for (uint256 i = 0; i < len; i++) {
            require(inviteCodeToTokenId[newInviteCodes[i]] == 0, "New invite code already exists");
        }
        // 5. Отметить inviteCode как использованный
        isInviteUsed[tokenId] = true;
        usedInviteByUser[user] = tokenId;
        inviteTransferHistory[tokenId].push(user);
        totalInvitesUsed += 1;
        // Добавить пользователя в список активированных
        activatedUsers.push(user);
        emit InviteActivated(user, inviteCode, tokenId, block.timestamp);
        // 6. Минт новых инвайтов для user
        require(newInviteCodes.length == 12, "Must mint exactly 12 invites");
        uint256[] memory tokenIds = new uint256[](len);
        for (uint256 i = 0; i < len; i++) {
            string memory code = newInviteCodes[i];
            tokenIds[i] = _mintInvite(code, user, expiry);
        }
        totalInvitesMinted += len;
        // Обновляем счетчик инвайтов пользователя
        userInviteCount[user] = len;
        emit BatchInvitesMinted(user, tokenIds, newInviteCodes, expiry);
    }

    /**
     * @dev Получить tokenId по inviteCode
     * @param inviteCode inviteCode (строка)
     * @return tokenId идентификатор NFT инвайта
     */
    function getTokenIdByInviteCode(string memory inviteCode) public view returns (uint256) {
        return inviteCodeToTokenId[inviteCode];
    }

    /**
     * @dev Получить inviteCode по tokenId
     * @param tokenId идентификатор NFT инвайта
     * @return inviteCode inviteCode (строка)
     */
    function getInviteCodeByTokenId(uint256 tokenId) public view returns (string memory) {
        return tokenIdToInviteCode[tokenId];
    }

    /**
     * @dev Активация пользователя (отдельно от назначения роли)
     * @param inviteCode код инвайта, который активируется
     * @param user адрес пользователя, который активирует инвайт
     * @param newInviteCodes массив новых inviteCode для раздачи друзьям
     * @param expiry срок действия новых инвайтов (timestamp, 0 если бессрочные)
     */
    function activateUser(
        string memory inviteCode,
        address user,
        string[] memory newInviteCodes,
        uint256 expiry
    ) external onlyRole(ACTIVATOR_ROLE) {
        require(usedInviteByUser[user] == 0, "User already activated invite");
        
        // КРИТИЧЕСКОЕ: Проверка лимита круга активатора
        require(activatedBy[msg.sender].length < 12, "Circle limit reached (max 12 members)");
        
        // Валидация инвайт-кода
        (bool valid, string memory reason) = _validateInviteCode(inviteCode, user);
        require(valid, reason);
        
        uint256 tokenId = inviteCodeToTokenId[inviteCode];
        
        // Проверка уникальности новых инвайт-кодов
        _validateNewInviteCodes(newInviteCodes);
        
        // Отметить инвайт как использованный
        isInviteUsed[tokenId] = true;
        usedInviteByUser[user] = tokenId;
        inviteTransferHistory[tokenId].push(user);
        totalInvitesUsed += 1;
        
        // Записать кто активировал пользователя
        userActivator[user] = msg.sender;
        activatedBy[msg.sender].push(user);
        
        // Добавить пользователя в список активированных
        activatedUsers.push(user);
        
        // Дифференцированные события для мониторинга кругов
        if (hasRole(DEFAULT_ADMIN_ROLE, msg.sender)) {
            // Это деплоер - активация первого круга
            emit FirstCircleActivation(msg.sender, user, inviteCode, tokenId, block.timestamp);
        } else {
            // Это селлер - активация в своем круге
            emit CircleActivation(msg.sender, user, inviteCode, tokenId, block.timestamp);
        }
        
        // Общее событие активации (для обратной совместимости)
        emit UserActivated(msg.sender, user, inviteCode, tokenId, block.timestamp);
        
        // Минт новых инвайтов
        require(newInviteCodes.length == 12, "Must mint exactly 12 invites");
        uint256[] memory tokenIds = new uint256[](12);
        for (uint256 i = 0; i < 12; i++) {
            tokenIds[i] = _mintInvite(newInviteCodes[i], user, expiry);
        }
        totalInvitesMinted += 12;
        userInviteCount[user] += 12;
        
        emit BatchInvitesMinted(msg.sender, tokenIds, newInviteCodes, expiry);
    }

    /**
     * @dev Назначение роли SELLER_ROLE пользователю
     * @param user адрес пользователя для назначения роли
     */
    function grantSellerRole(address user) external {
        require(isUserActivated(user), "User must be activated first");
        require(hasRole(ACTIVATOR_ROLE, msg.sender) || hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "Not authorized to grant seller role");
        
        // Проверяем иерархическую спираль
        if (!hasRole(DEFAULT_ADMIN_ROLE, msg.sender)) {
            require(userActivator[user] == msg.sender, "Can only nominate users you activated");
        }
        
        _grantRole(SELLER_ROLE, user);
        
        // Записать кто назначил селлером
        sellerNominator[user] = msg.sender;
        nominatedSellers[msg.sender].push(user);
        
        emit SellerRoleGranted(msg.sender, user, block.timestamp);
    }

    /**
     * @dev Валидация уникальности новых инвайт-кодов
     * @param newInviteCodes массив новых инвайт-кодов для проверки
     */
    function _validateNewInviteCodes(string[] memory newInviteCodes) internal view {
        uint256 len = newInviteCodes.length;
        for (uint256 i = 0; i < len; i++) {
            for (uint256 j = i + 1; j < len; j++) {
                require(keccak256(bytes(newInviteCodes[i])) != keccak256(bytes(newInviteCodes[j])), "Duplicate newInviteCode in batch");
            }
        }
        for (uint256 i = 0; i < len; i++) {
            require(inviteCodeToTokenId[newInviteCodes[i]] == 0, "New invite code already exists");
        }
    }

    /**
     * @dev Применение санкций к пользователю с каскадными эффектами
     * @param user адрес пользователя для приостановки
     * @param duration длительность приостановки в секундах
     * @param reason причина приостановки
     */
    function suspendUser(address user, uint256 duration, string memory reason) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(isUserActivated(user), "User must be activated");
        
        suspensionUntil[user] = block.timestamp + duration;
        violationCount[user]++;
        
        emit UserSuspended(user, duration, reason, block.timestamp);
        
        // Каскадные санкции для активатора
        address activator = userActivator[user];
        if (activator != address(0)) {
            _applyActivatorSanctions(activator, violationCount[user]);
        }
        
        // Если это селлер, санкции для номинатора
        if (hasRole(SELLER_ROLE, user)) {
            address nominator = sellerNominator[user];
            if (nominator != address(0)) {
                _applyNominatorSanctions(nominator, violationCount[user]);
            }
        }
    }

    /**
     * @dev Внутренняя функция применения санкций к активатору
     * @param activator адрес активатора
     * @param violationLevel уровень нарушения
     */
    function _applyActivatorSanctions(address activator, uint256 violationLevel) internal {
        activationViolations[activator]++;
        
        if (activationViolations[activator] == 1) {
            // Первое нарушение - предупреждение
            emit ActivatorWarning(activator, "First violation from activated user");
        } else if (activationViolations[activator] == 2) {
            // Второе нарушение - временная приостановка
            _revokeRole(ACTIVATOR_ROLE, activator);
            emit ActivatorSuspended(activator, 7 days, "Second violation");
        } else if (activationViolations[activator] >= 3) {
            // Третье нарушение - долгосрочная приостановка
            _revokeRole(ACTIVATOR_ROLE, activator);
            emit ActivatorSuspended(activator, 30 days, "Third violation");
        }
    }

    /**
     * @dev Внутренняя функция применения санкций к номинатору
     * @param nominator адрес номинатора
     * @param violationLevel уровень нарушения
     */
    function _applyNominatorSanctions(address nominator, uint256 violationLevel) internal {
        nominationViolations[nominator]++;
        
        if (nominationViolations[nominator] == 1) {
            // Первое нарушение - предупреждение
            emit NominatorWarning(nominator, "First violation from nominated seller");
        } else if (nominationViolations[nominator] == 2) {
            // Второе нарушение - временная приостановка права назначать
            emit NominatorSuspended(nominator, 7 days, "Second violation");
        } else if (nominationViolations[nominator] >= 3) {
            // Третье нарушение - долгосрочная приостановка
            emit NominatorSuspended(nominator, 30 days, "Third violation");
        }
    }

    /**
     * @dev Получить историю всех владельцев инвайта (NFT)
     * @param tokenId идентификатор NFT инвайта
     * @return owners массив адресов всех владельцев по порядку
     *
     * Критерии приёмки:
     * - Принимает tokenId
     * - Возвращает inviteTransferHistory[tokenId]
     * - Не изменяет состояние
     * - Может быть вызван любым участником
     * - revert, если tokenId не существует (для UX)
     */
    function getInviteTransferHistory(uint256 tokenId) public view returns (address[] memory) {
        return inviteTransferHistory[tokenId];
    }

    /**
     * @dev Получить все инвайты пользователя
     * @param user адрес пользователя
     * @return tokenIds массив всех tokenId, которыми владел пользователь
     *
     * Критерии приёмки:
     * - Принимает адрес пользователя
     * - Возвращает userInvites[user]
     * - Не изменяет состояние
     * - Может быть вызван любым участником
     */
    function getUserInvites(address user) public view returns (uint256[] memory) {
        return userInvites[user];
    }

    /**
     * @dev Проверить, был ли использован инвайт
     * @param tokenId идентификатор NFT инвайта
     * @return true если использован, false если нет
     */
    function isInviteTokenUsed(uint256 tokenId) public view returns (bool) {
        return isInviteUsed[tokenId];
    }

    /**
     * @dev Получить дату создания инвайта
     * @param tokenId идентификатор NFT инвайта
     * @return timestamp дата создания (timestamp)
     */
    function getInviteCreatedAt(uint256 tokenId) public view returns (uint256) {
        return inviteCreatedAt[tokenId];
    }

    /**
     * @dev Получить срок действия инвайта
     * @param tokenId идентификатор NFT инвайта
     * @return expiry срок действия (timestamp, 0 если бессрочный)
     */
    function getInviteExpiry(uint256 tokenId) public view returns (uint256) {
        return inviteExpiry[tokenId];
    }

    /**
     * @dev Получить адрес минтера инвайта
     * @param tokenId идентификатор NFT инвайта
     * @return minter адрес минтера
     */
    function getInviteMinter(uint256 tokenId) public view returns (address) {
        return inviteMinter[tokenId];
    }

    /**
     * @dev Получить первого владельца инвайта
     * @param tokenId идентификатор NFT инвайта
     * @return owner адрес первого владельца
     */
    function getInviteFirstOwner(uint256 tokenId) public view returns (address) {
        return inviteFirstOwner[tokenId];
    }

    /**
     * @dev Проверка, активирован ли пользователь
     * @param user адрес пользователя
     * @return bool true если пользователь активирован, false иначе
     */
    function isUserActivated(address user) public view returns (bool) {
        return usedInviteByUser[user] != 0;
    }

    /**
     * @dev Проверить валидность массива inviteCodes для пользователя user (batch-валидация)
     * @param inviteCodes массив inviteCode для проверки
     * @param user адрес пользователя
     * @return success массив результатов проверки валидности
     * @return reasons массив строк с причинами невалидности
     *
     * Алгоритм:
     * 1. Для каждого inviteCode вызвать validateInviteCode(inviteCode, user)
     * 2. Сохранить результат success и reason в отдельные массивы
     * 3. Вернуть оба массива
     */
    function batchValidateInviteCodes(string[] memory inviteCodes, address user) public view returns (bool[] memory, string[] memory) {
        uint256 len = inviteCodes.length;
        bool[] memory success = new bool[](len);
        string[] memory reasons = new string[](len);
        for (uint256 i = 0; i < len; i++) {
            (bool ok, string memory reason) = _validateInviteCode(inviteCodes[i], user);
            success[i] = ok;
            reasons[i] = reason;
        }
        return (success, reasons);
    }

    /**
     * @dev Получить все активированные пользователи
     * @return users массив адресов всех активированных пользователей
     *
     * Критерии приёмки:
     * - Возвращает массив всех адресов, у которых usedInviteByUser[address] != 0
     * - Не изменяет состояние
     * - Может быть вызван любым участником
     */
    function getAllActivatedUsers() public view returns (address[] memory) {
        return activatedUsers;
    }

    /**
     * @dev Batch-минт новых инвайтов (NFT) с inviteCodes и сроком действия expiry для раздачи стартовой аудитории.
     * @param inviteCodes массив уникальных inviteCode, которые будут заминчены
     * @param expiry срок действия (timestamp, 0 если бессрочный)
     *
     * Доступ: только адреса с ролью SELLER_ROLE.
     * Минт всегда идёт на msg.sender (селлера), без лимитов на количество batch-ей и размер batch-а.
     */
    function mintInvites(string[] calldata inviteCodes, uint256 expiry) external onlyRole(SELLER_ROLE) {
        uint256 len = inviteCodes.length;
        require(len > 0, "No invite codes provided");
        // Проверка срока действия
        require(expiry == 0 || expiry > block.timestamp, "Expiry must be 0 or in the future");
        // Проверка уникальности inviteCodes внутри массива
        for (uint256 i = 0; i < len; i++) {
            for (uint256 j = i + 1; j < len; j++) {
                require(keccak256(bytes(inviteCodes[i])) != keccak256(bytes(inviteCodes[j])), "Duplicate inviteCode in batch");
            }
        }
        uint256[] memory tokenIds = new uint256[](len);
        for (uint256 i = 0; i < len; i++) {
            tokenIds[i] = _mintInvite(inviteCodes[i], msg.sender, expiry);
        }
        totalInvitesMinted += len;
        emit BatchInvitesMinted(msg.sender, tokenIds, inviteCodes, expiry);
    }

    /**
     * @dev Внутренний метод для минтинга одного инвайта (NFT)
     * @param inviteCode уникальный inviteCode
     * @param to адрес получателя
     * @param expiry срок действия (timestamp, 0 если бессрочный)
     * @return tokenId идентификатор заминченного NFT
     *
     * Критерии приёмки:
     * - inviteCode уникален (inviteCodeToTokenId[inviteCode] == 0)
     * - Генерируется новый tokenId
     * - NFT минтится на адрес to
     * - Все маппинги корректно инициализированы
     * - tokenId добавляется в userInvites[to] и inviteTransferHistory[tokenId]
     * - Возвращается новый tokenId
     * - Только internal
     */
    function _mintInvite(string memory inviteCode, address to, uint256 expiry) internal returns (uint256) {
        require(inviteCodeToTokenId[inviteCode] == 0, "Invite code already exists");
        _tokenIdCounter++;
        uint256 tokenId = _tokenIdCounter;
        _safeMint(to, tokenId);
        inviteCodeToTokenId[inviteCode] = tokenId;
        tokenIdToInviteCode[tokenId] = inviteCode;
        inviteExpiry[tokenId] = expiry;
        inviteCreatedAt[tokenId] = block.timestamp;
        inviteMinter[tokenId] = msg.sender;
        inviteFirstOwner[tokenId] = to;
        userInvites[to].push(tokenId);
        inviteTransferHistory[tokenId].push(to);
        // Увеличиваем счетчик инвайтов пользователя
        userInviteCount[to] += 1;
        return tokenId;
    }

    /**
     * @dev Внутреннее обновление статуса инвайта и пользователя при активации
     * @param tokenId идентификатор инвайта
     * @param user адрес пользователя
     *
     * Критерии приёмки:
     * - isInviteUsed[tokenId] = true
     * - usedInviteByUser[user] = tokenId
     * - inviteTransferHistory[tokenId].push(user)
     * - totalInvitesUsed увеличивается на 1
     * - Только internal
     * - Не эмитит события
     */
    function _updateInviteStatus(uint256 tokenId, address user) internal {
        isInviteUsed[tokenId] = true;
        usedInviteByUser[user] = tokenId;
        inviteTransferHistory[tokenId].push(user);
        totalInvitesUsed += 1;
    }

    /**
     * @dev Назначить адрес продавцом (SELLER_ROLE)
     * @param seller адрес продавца
     */
    function addSeller(address seller) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _grantRole(SELLER_ROLE, seller);
    }

    /**
     * @dev Убрать роль продавца у адреса
     * @param seller адрес продавца
     */
    function removeSeller(address seller) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _revokeRole(SELLER_ROLE, seller);
    }

    // === ФУНКЦИИ УПРАВЛЕНИЯ КРУГАМИ ===

    /**
     * @dev Получить список участников круга активатора
     * @param activator адрес активатора
     * @return members массив адресов участников круга
     */
    function getCircleMembers(address activator) external view returns (address[] memory) {
        return activatedBy[activator];
    }

    /**
     * @dev Получить размер круга активатора
     * @param activator адрес активатора
     * @return size количество участников в круге
     */
    function getCircleSize(address activator) external view returns (uint256) {
        return activatedBy[activator].length;
    }

    /**
     * @dev Проверить принадлежность инвайта активатору
     * @param inviteCode код инвайта
     * @param activator адрес активатора
     * @return isOwned true если инвайт принадлежит активатору
     */
    function isInviteFromActivator(string memory inviteCode, address activator) external view returns (bool) {
        uint256 tokenId = inviteCodeToTokenId[inviteCode];
        if (tokenId == 0) {
            return false;
        }
        return inviteMinter[tokenId] == activator;
    }


    function _update(address to, uint256 tokenId, address auth) internal virtual override returns (address) {
        address from = _ownerOf(tokenId);
        
        // Разрешаем только минт (from == address(0)) и сжигание (to == address(0))
        require(from == address(0) || to == address(0), "InviteNFT: soulbound");
        
        return super._update(to, tokenId, auth);
    }

    function isSeller(address user) public view returns (bool) {
        return hasRole(SELLER_ROLE, user);
    }

    // === SBT-СОВМЕСТИМОСТЬ: БЛОКИРОВКА ФУНКЦИЙ ОДОБРЕНИЯ ===
    
    /**
     * @dev SBT токены не могут быть одобрены для делегирования управления
     * @param to адрес, которому пытаются дать одобрение
     * @param tokenId идентификатор токена
     */
    function approve(address to, uint256 tokenId) public virtual override {
        revert("InviteNFT: SBT tokens cannot be approved");
    }

    /**
     * @dev SBT токены не могут быть одобрены для глобального управления
     * @param operator адрес оператора
     * @param approved статус одобрения
     */
    function setApprovalForAll(address operator, bool approved) public virtual override {
        revert("InviteNFT: SBT tokens cannot be approved");
    }

    /**
     * @dev SBT токены не имеют одобренных операторов
     * @param tokenId идентификатор токена
     * @return address(0) всегда, так как SBT не могут быть одобрены
     */
    function getApproved(uint256 tokenId) public view virtual override returns (address) {
        return address(0);
    }

    /**
     * @dev SBT токены не имеют глобальных одобрений
     * @param owner владелец токена
     * @param operator оператор
     * @return false всегда, так как SBT не могут быть одобрены
     */
    function isApprovedForAll(address owner, address operator) public view virtual override returns (bool) {
        return false;
    }

    // === EIP-5192 SBT СТАНДАРТ ===
    
    /**
     * @dev Проверяет, заблокирован ли токен (всегда true для SBT)
     * @param tokenId идентификатор токена для проверки
     * @return true всегда, так как все токены InviteNFT являются SBT
     */
    function locked(uint256 tokenId) external view override returns (bool) {
        // Проверяем, что токен существует
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return true; // Все токены InviteNFT заблокированы как SBT
    }

    /**
     * @dev Обновленная функция поддержки интерфейсов с EIP-5192
     * @param interfaceId идентификатор интерфейса для проверки
     * @return true если контракт поддерживает интерфейс
     */
    function supportsInterface(bytes4 interfaceId) public view override(ERC721, AccessControl) returns (bool) {
        return interfaceId == type(IERC5192).interfaceId || super.supportsInterface(interfaceId);
    }

    // === СИСТЕМА ВОССТАНОВЛЕНИЯ ДОСТУПА ===
    
    /**
     * @dev Добавить доверенное лицо для восстановления доступа
     * @param guardian адрес доверенного лица
     */
    function addTrustedGuardian(address guardian) external {
        require(guardian != address(0), "Guardian cannot be zero address");
        require(guardian != msg.sender, "Cannot be your own guardian");
        require(guardianCount[msg.sender] < 5, "Maximum 5 guardians allowed");
        require(!guardianApproval[msg.sender][guardian], "Guardian already added");
        
        trustedGuardians[msg.sender].push(guardian);
        guardianApproval[msg.sender][guardian] = true;
        guardianCount[msg.sender]++;
        
        emit GuardianAdded(msg.sender, guardian, block.timestamp);
    }

    /**
     * @dev Удалить доверенное лицо
     * @param guardian адрес доверенного лица
     */
    function removeTrustedGuardian(address guardian) external {
        require(guardianApproval[msg.sender][guardian], "Guardian not found");
        
        // Удаляем из массива
        address[] storage guardians = trustedGuardians[msg.sender];
        for (uint256 i = 0; i < guardians.length; i++) {
            if (guardians[i] == guardian) {
                guardians[i] = guardians[guardians.length - 1];
                guardians.pop();
                break;
            }
        }
        
        guardianApproval[msg.sender][guardian] = false;
        guardianCount[msg.sender]--;
        
        emit GuardianRemoved(msg.sender, guardian, block.timestamp);
    }

    /**
     * @dev Инициировать процесс восстановления доступа
     * @param user адрес пользователя, для которого инициируется восстановление
     */
    function initiateRecovery(address user) external {
        require(guardianApproval[user][msg.sender], "Not authorized guardian");
        require(!isRecoveryInProgress[user], "Recovery already in progress");
        require(block.timestamp - lastRecoveryTime[user] > 7 days, "Recovery cooldown active");
        
        isRecoveryInProgress[user] = true;
        lastRecoveryTime[user] = block.timestamp;
        
        emit RecoveryInitiated(user, msg.sender, block.timestamp);
    }

    /**
     * @dev Завершить восстановление доступа (только доверенные лица)
     * @param user адрес пользователя
     * @param newAddress новый адрес пользователя
     */
    function completeRecovery(address user, address newAddress) external {
        require(guardianApproval[user][msg.sender], "Not authorized guardian");
        require(isRecoveryInProgress[user], "No recovery in progress");
        require(newAddress != address(0), "New address cannot be zero");
        require(newAddress != user, "New address must be different");
        
        // Переносим все токены на новый адрес
        uint256[] memory userTokens = userInvites[user];
        for (uint256 i = 0; i < userTokens.length; i++) {
            uint256 tokenId = userTokens[i];
            if (_ownerOf(tokenId) == user) {
                _transfer(user, newAddress, tokenId);
            }
        }
        
        // Обновляем маппинги
        userInvites[newAddress] = userTokens;
        usedInviteByUser[newAddress] = usedInviteByUser[user];
        
        // Очищаем старые данные
        delete userInvites[user];
        delete usedInviteByUser[user];
        isRecoveryInProgress[user] = false;
        
        emit RecoveryCompleted(user, newAddress, block.timestamp);
    }

    /**
     * @dev Создать временный ключ доступа
     * @param tempKey адрес временного ключа
     * @param duration длительность действия в секундах
     */
    function createTemporaryKey(address tempKey, uint256 duration) external {
        require(tempKey != address(0), "Temporary key cannot be zero");
        require(duration <= 30 days, "Duration too long");
        require(temporaryAccessKey[msg.sender] == address(0), "Temporary key already exists");
        
        temporaryAccessKey[msg.sender] = tempKey;
        temporaryKeyExpiry[tempKey] = block.timestamp + duration;
        
        emit TemporaryKeyCreated(msg.sender, tempKey, block.timestamp + duration, block.timestamp);
    }

    /**
     * @dev Использовать временный ключ для операций
     * @param user адрес пользователя
     */
    modifier onlyTemporaryKey(address user) {
        require(
            msg.sender == user || 
            (temporaryAccessKey[user] == msg.sender && block.timestamp < temporaryKeyExpiry[msg.sender]),
            "Not authorized or temporary key expired"
        );
        _;
    }

    /**
     * @dev Отозвать временный ключ
     */
    function revokeTemporaryKey() external {
        address tempKey = temporaryAccessKey[msg.sender];
        require(tempKey != address(0), "No temporary key to revoke");
        
        emit TemporaryKeyExpired(msg.sender, tempKey, block.timestamp);
        
        delete temporaryAccessKey[msg.sender];
        delete temporaryKeyExpiry[tempKey];
    }

    /**
     * @dev Получить список доверенных лиц пользователя
     * @param user адрес пользователя
     * @return массив адресов доверенных лиц
     */
    function getTrustedGuardians(address user) external view returns (address[] memory) {
        return trustedGuardians[user];
    }

    /**
     * @dev Проверить, является ли адрес доверенным лицом
     * @param user адрес пользователя
     * @param guardian адрес для проверки
     * @return true если является доверенным лицом
     */
    function isTrustedGuardian(address user, address guardian) external view returns (bool) {
        return guardianApproval[user][guardian];
    }

    // === DID ИНТЕГРАЦИЯ И РЕПУТАЦИОННАЯ СИСТЕМА ===
    
    /**
     * @dev Связать DID с адресом пользователя
     * @param did децентрализованный идентификатор
     */
    function linkDID(string memory did) external {
        require(bytes(did).length > 0, "DID cannot be empty");
        require(didToAddress[did] == address(0), "DID already linked");
        require(bytes(userDID[msg.sender]).length == 0, "User already has DID linked");
        
        userDID[msg.sender] = did;
        didToAddress[did] = msg.sender;
        
        // Инициализируем репутацию
        reputationScore[msg.sender] = 100; // Базовый счет
        verificationLevel[msg.sender] = 1; // Базовый уровень
        lastVerificationTime[msg.sender] = block.timestamp;
        
        emit DIDLinked(msg.sender, did, block.timestamp);
    }

    /**
     * @dev Отвязать DID от адреса пользователя
     */
    function unlinkDID() external {
        string memory did = userDID[msg.sender];
        require(bytes(did).length > 0, "No DID linked");
        
        delete userDID[msg.sender];
        delete didToAddress[did];
        
        emit DIDUnlinked(msg.sender, did, block.timestamp);
    }

    /**
     * @dev Обновить уровень верификации (только админ)
     * @param user адрес пользователя
     * @param level новый уровень верификации (0-5)
     */
    function updateVerificationLevel(address user, uint8 level) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(level <= 5, "Invalid verification level");
        require(bytes(userDID[user]).length > 0, "User has no DID linked");
        
        verificationLevel[user] = level;
        lastVerificationTime[user] = block.timestamp;
        
        // Обновляем репутацию на основе уровня верификации
        reputationScore[user] = 100 + (level * 20);
        
        emit IdentityVerified(user, level, block.timestamp);
        emit ReputationUpdated(user, reputationScore[user], block.timestamp);
    }

    /**
     * @dev Записать успешную операцию
     * @param user адрес пользователя
     */
    function recordSuccessfulOperation(address user) internal {
        successfulOperations[user]++;
        
        // Увеличиваем репутацию за успешные операции
        if (reputationScore[user] < 1000) {
            reputationScore[user] += 1;
        }
        
        emit OperationRecorded(user, true, block.timestamp);
        emit ReputationUpdated(user, reputationScore[user], block.timestamp);
    }

    /**
     * @dev Записать неудачную операцию
     * @param user адрес пользователя
     */
    function recordFailedOperation(address user) internal {
        failedOperations[user]++;
        
        // Уменьшаем репутацию за неудачные операции
        if (reputationScore[user] > 50) {
            reputationScore[user] -= 2;
        }
        
        emit OperationRecorded(user, false, block.timestamp);
        emit ReputationUpdated(user, reputationScore[user], block.timestamp);
    }

    /**
     * @dev Получить репутационный профиль пользователя
     * @param user адрес пользователя
     * @return did DID пользователя
     * @return reputation репутационный счет
     * @return userVerificationLevel уровень верификации
     * @return successfulOps количество успешных операций
     * @return failedOps количество неудачных операций
     */
    function getReputationProfile(address user) external view returns (
        string memory did,
        uint256 reputation,
        uint8 userVerificationLevel,
        uint256 successfulOps,
        uint256 failedOps
    ) {
        return (
            userDID[user],
            reputationScore[user],
            verificationLevel[user],
            successfulOperations[user],
            failedOperations[user]
        );
    }

    /**
     * @dev Проверить, связан ли адрес с DID
     * @param user адрес пользователя
     * @return true если DID связан
     */
    function hasDIDLinked(address user) external view returns (bool) {
        return bytes(userDID[user]).length > 0;
    }

    /**
     * @dev Получить адрес по DID
     * @param did децентрализованный идентификатор
     * @return адрес пользователя
     */
    function getAddressByDID(string memory did) external view returns (address) {
        return didToAddress[did];
    }

    /**
     * @dev Проверить репутацию пользователя
     * @param user адрес пользователя
     * @return true если репутация достаточна для операций
     */
    function hasGoodReputation(address user) external view returns (bool) {
        return reputationScore[user] >= 50 && verificationLevel[user] >= 1;
    }

    // === РАСШИРЕННЫЕ МЕТАДАННЫЕ SBT ===
    
    /**
     * @dev Переопределенная функция tokenURI для SBT метаданных
     * @param tokenId идентификатор токена
     * @return URI метаданных токена
     */
    function tokenURI(uint256 tokenId) public view virtual override returns (string memory) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        
        // Упрощенные метаданные для избежания "Stack too deep"
        string memory name = string(abi.encodePacked("Amanita Invite SBT #", _toString(tokenId)));
        string memory description = "Soulbound Token for Amanita Ecosystem Invite System";
        string memory image = string(abi.encodePacked("https://amanita.ecosystem/sbt/", _toString(tokenId), ".png"));
        
        string memory json = string(abi.encodePacked(
            '{"name":"', name, '",',
            '"description":"', description, '",',
            '"image":"', image, '",',
            '"attributes":[',
            '{"trait_type":"Token Type","value":"Soulbound Token"},',
            '{"trait_type":"SBT Version","value":"', _toString(sbtVersion[tokenId]), '"}',
            ']}'
        ));
        
        return string(abi.encodePacked("data:application/json;base64,", _base64Encode(bytes(json))));
    }

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
    ) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        
        return (
            sbtType[tokenId],
            sbtVersion[tokenId],
            sbtAttributes[tokenId],
            true // Все SBT токены заблокированы
        );
    }

    /**
     * @dev Обновить метаданные SBT (только владелец)
     * @param tokenId идентификатор токена
     * @param newSbtType новый тип SBT
     * @param newAttributes новые атрибуты
     */
    function updateSBTMetadata(uint256 tokenId, string memory newSbtType, string memory newAttributes) external {
        require(_ownerOf(tokenId) == msg.sender, "Not token owner");
        
        sbtType[tokenId] = newSbtType;
        sbtAttributes[tokenId] = newAttributes;
        
        emit SBTMetadataUpdated(tokenId, newSbtType, newAttributes, block.timestamp);
    }

    /**
     * @dev Обновить версию SBT (только админ)
     * @param tokenId идентификатор токена
     * @param newVersion новая версия
     */
    function updateSBTVersion(uint256 tokenId, uint256 newVersion) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(newVersion > sbtVersion[tokenId], "Version must be higher");
        
        sbtVersion[tokenId] = newVersion;
        
        emit SBTVersionUpdated(tokenId, newVersion, block.timestamp);
    }

    /**
     * @dev Получить версию SBT токена
     * @param tokenId идентификатор токена
     * @return версия SBT
     */
    function getSBTVersion(uint256 tokenId) external view returns (uint256) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return sbtVersion[tokenId];
    }

    /**
     * @dev Проверить, является ли токен SBT
     * @param tokenId идентификатор токена
     * @return true если токен является SBT
     */
    function isSBT(uint256 tokenId) external view returns (bool) {
        return _ownerOf(tokenId) != address(0);
    }

    // === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ МЕТАДАННЫХ ===
    
    /**
     * @dev Конвертировать uint256 в строку
     */
    function _toString(uint256 value) internal pure returns (string memory) {
        if (value == 0) {
            return "0";
        }
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

    /**
     * @dev Конвертировать адрес в hex строку
     */
    function _toHexString(address addr) internal pure returns (string memory) {
        return _toHexString(abi.encodePacked(addr));
    }

    /**
     * @dev Конвертировать bytes в hex строку
     */
    function _toHexString(bytes memory data) internal pure returns (string memory) {
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(2 + data.length * 2);
        str[0] = "0";
        str[1] = "x";
        for (uint256 i = 0; i < data.length; i++) {
            str[2 + i * 2] = alphabet[uint256(uint8(data[i] >> 4))];
            str[3 + i * 2] = alphabet[uint256(uint8(data[i] & 0x0f))];
        }
        return string(str);
    }

    /**
     * @dev Base64 кодирование
     */
    function _base64Encode(bytes memory data) internal pure returns (string memory) {
        if (data.length == 0) return "";
        
        string memory table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        
        uint256 encodedLen = 4 * ((data.length + 2) / 3);
        
        string memory result = new string(encodedLen + 32);
        
        assembly {
            let tablePtr := add(table, 1)
            let resultPtr := add(result, 32)
            
            for {
                let i := 0
            } lt(i, mload(data)) {
                i := add(i, 3)
            } {
                let input := and(mload(add(data, add(32, i))), 0xffffff)
                
                let out := mload(add(tablePtr, and(shr(18, input), 0x3F)))
                out := shl(8, out)
                out := add(out, and(mload(add(tablePtr, and(shr(12, input), 0x3F))), 0xFF))
                out := shl(8, out)
                out := add(out, and(mload(add(tablePtr, and(shr(6, input), 0x3F))), 0xFF))
                out := shl(8, out)
                out := add(out, and(mload(add(tablePtr, and(input, 0x3F))), 0xFF))
                out := shl(224, out)
                
                mstore(resultPtr, out)
                
                resultPtr := add(resultPtr, 4)
            }
            
            switch mod(mload(data), 3)
            case 1 {
                mstore(sub(resultPtr, 2), shl(240, 0x3d3d))
            }
            case 2 {
                mstore(sub(resultPtr, 1), shl(248, 0x3d))
            }
        }
        
        return result;
    }
} 