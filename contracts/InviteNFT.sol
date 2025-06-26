// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract InviteNFT is ERC721, AccessControl {
    uint256 private _tokenIdCounter;

    // Роль продавца для доступа к минтингу инвайтов
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");

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

    event InviteActivated(address indexed user, string inviteCode, uint256 tokenId, uint256 timestamp);
    event BatchInvitesMinted(address indexed to, uint256[] tokenIds, string[] inviteCodes, uint256 expiry);
    event InviteTransferred(uint256 indexed tokenId, address from, address to, uint256 timestamp);

    constructor() ERC721("Amanita Invite", "AINV") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    /**
     * @dev Внутренняя проверка валидности инвайта по inviteCode и адресу пользователя
     * @param inviteCode inviteCode (строка)
     * @return success true если инвайт валиден, false иначе
     * @return reason строка с причиной невалидности ("not_found", "already_used", "expired", "user_already_activated")
     *
     * Критерии приёмки:
     * - inviteCode существует
     * - invite не использован
     * - invite не истёк
     * - Возвращает (true, "") если всё валидно, иначе (false, причина)
     * - Только internal view
     */
    function _validateInviteCode(string memory inviteCode) internal view returns (bool, string memory) {
        // 1. Получить tokenId по inviteCode
        uint256 tokenId = inviteCodeToTokenId[inviteCode];
        // 2. Проверка существования инвайта
        if (tokenId == 0) {
            return (false, "not_found");
        }
        // 3. Проверка, был ли инвайт уже использован
        if (isInviteUsed[tokenId]) {
            return (false, "already_used");
        }
        // 4. Проверка срока действия (если не бессрочный)
        uint256 expiry = inviteExpiry[tokenId];
        if (expiry != 0 && expiry < block.timestamp) {
            return (false, "expired");
        }
        // 5. Все проверки пройдены — инвайт валиден
        return (true, "");
    }

    function _validateInviteCode(string memory inviteCode, address user) internal view returns (bool, string memory) {
        if (usedInviteByUser[user] != 0) {
            return (false, "user_already_activated");
        }
        (bool valid, string memory reason) = _validateInviteCode(inviteCode);
        if (!valid) {
            return (false, reason);
        }
        return (true, "");
    }

    /**
     * @dev Проверка валидности инвайта по inviteCode и адресу пользователя
     * @param inviteCode inviteCode (строка)
     * @return success true если инвайт валиден, false иначе
     * @return reason строка с причиной невалидности ("not_found", "already_used", "expired", "user_already_activated")
     * 
     */
    function validateInviteCode(string memory inviteCode) public view returns (bool, string memory) {
        return _validateInviteCode(inviteCode);
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

    function supportsInterface(bytes4 interfaceId) public view override(ERC721, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
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
} 