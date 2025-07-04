// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";

/**
 * @title LoveDoPostNFT
 * @dev NFT-контракт для LoveDo постов в системе Amanita. Позволяет пользователям создавать отзывы-признания
 * для продавцов, на которые продавцы могут ставить суперлайки. Каждый суперлайк становится основой для эмиссии $AMANITA_GOV.
 */
contract LoveDoPostNFT is ERC721URIStorage, AccessControl {
    using EnumerableSet for EnumerableSet.UintSet;

    // --- Roles ---
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");

    /// @notice Структура одного LoveDo поста
    struct LoveDo {
        address author;          // пользователь, написавший пост
        address sellerTo;        // продавец, которому посвящён пост
        address linkedSeller;    // селлер, пригласивший автора
        uint8 superlikes;        // количество суперлайков
        uint256 timestamp;       // когда был создан пост, чтобы анализировать динамику и избегать манипуляций через старые посты
    }

    /// @notice Карта tokenId → LoveDo метаданные
    mapping(uint256 => LoveDo) public loveDos;

    /// @notice Массив tokenId всех постов, направленных на конкретного селлера
    mapping(address => uint256[]) private postsBySeller;


    /// @notice Мапа для суперлайков: tokenId => seller => liked
    mapping(uint256 => mapping(address => bool)) public hasSuperliked;

    /// @notice Отслеживание суперлайков по селлеру за месяц
    mapping(address => mapping(uint256 => uint8)) public monthlyLikesUsed;

    /// @notice Счётчик токенов
    uint256 public nextTokenId;

    /// @notice Лимит постов на одного участника
    uint8 public constant MAX_MONTHLY_POSTS_PER_USER = 8;

    /// @notice Сколько постов пользователь сделал за месяц
    mapping(address => mapping(uint256 => uint8)) public postsPerUserPerMonth;

    /// @notice Макс. LoveDo постов, в которых может быть упомянут один селлер
    uint8 public constant MAX_MENTIONS_PER_SELLER = 8;

    /// @notice Сколько раз каждый селлер уже был упомянут
    mapping(address => uint8) public mentionsOf;

    /// @notice Мапа: кто сколько постов уже создал
    mapping(address => uint8) public postsMintedBy;

    /// @notice Мапа: чтобы анализировать поведение аудитории.
    mapping(address => uint256[]) public superlikedPostsByUser;

    /// @notice Событие минта нового поста
    event LoveDoMinted(uint256 indexed tokenId, address indexed author, address indexed sellerTo);

    /// @notice Событие суперлайка
    event Superliked(uint256 indexed tokenId, address indexed bySeller, uint8 newTotal);

    /// @notice Ссылка на внешний контракт InviteNFT, реализующий граф инвайтов
    IInviteGraph public inviteGraph;

    /// @notice Мапа: Защита от фронтраннига
    mapping(address => uint256) public superlikeNonces;


    /// @notice Ссылка на AmanitaRegistry для проверки SELLER роли
    IAmanitaRegistry public amanitaRegistry;

    /// @notice Лимит суперлайков, которые пользователь может поставить за месяц
    uint8 public constant MAX_SUPERLIKES_PER_MONTH = 8;

    constructor(address _admin, address _inviteGraph, address _amanitaRegistry)
        ERC721("LoveDoPost", "LDP")
    {
        require(_admin != address(0), "Admin required");
        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(ADMIN_ROLE, _admin);
        inviteGraph = IInviteGraph(_inviteGraph);
        amanitaRegistry = IAmanitaRegistry(_amanitaRegistry);
    }

    /**
     * @notice Создание LoveDo поста
     * @param sellerTo Продавец, которому адресован пост
     * @param uri Ссылка на IPFS метаданные (отзыв)
     */
    function mintLoveDoPost(address sellerTo, string calldata uri) external {
        uint256 currentMonth = block.timestamp / 30 days;
        require(
            postsPerUserPerMonth[msg.sender][currentMonth] < MAX_MONTHLY_POSTS_PER_USER,
            "Monthly post limit reached"
        );

        address linkedSeller = inviteGraph.getInviterOf(msg.sender);
        require(linkedSeller != address(0), "User is not invited");
        require(sellerTo != msg.sender, "Cannot post to self");
        require(mentionsOf[sellerTo] < MAX_MENTIONS_PER_SELLER, "Seller mention limit reached");

        uint256 tokenId = nextTokenId++;
        postsBySeller[sellerTo].push(tokenId);
        _safeMint(msg.sender, tokenId);
        _setTokenURI(tokenId, uri);

        loveDos[tokenId] = LoveDo({
            author: msg.sender,
            sellerTo: sellerTo,
            linkedSeller: linkedSeller,
            superlikes: 0,
            timestamp: block.timestamp
        });

        postsPerUserPerMonth[msg.sender][currentMonth]++;
        mentionsOf[sellerTo]++;
        emit LoveDoMinted(tokenId, msg.sender, sellerTo);
    }

    /**
    * @notice Возвращает все LoveDo tokenId, где указанный селлер был целью поста
    * @param seller Адрес селлера
    * @return tokenIds Массив ID постов
    */
    function getLoveDoMentions(address seller) external view returns (uint256[] memory tokenIds) {
        return postsBySeller[seller];
    }


    function getRemainingMentionsForSeller(address seller) external view returns (uint8) {
        return MAX_MENTIONS_PER_SELLER - mentionsOf[seller];
    }

    function getRemainingPostsThisMonth(address user) external view returns (uint8) {
        uint256 currentMonth = block.timestamp / 30 days;
        return MAX_MONTHLY_POSTS_PER_USER - postsPerUserPerMonth[user][currentMonth];
    }


    /**
     * @notice Суперлайк от селлера на пост своей аудитории
     * @param tokenId ID поста
     */
    function addSuperlike(uint256 tokenId, uint256 expectedNonce) external {
        
        uint256 monthKey = block.timestamp / 30 days;
        require(monthlyLikesUsed[msg.sender][monthKey] < MAX_SUPERLIKES_PER_MONTH, "Monthly superlikes exhausted");

        // --- [0] Проверяем nonce
        require(superlikeNonces[msg.sender] == expectedNonce, "Invalid nonce");
        superlikeNonces[msg.sender]++;

        // --- [1] Проверяем, существует ли пост по указанному tokenId
        require(postExists(tokenId), "LoveDo: post does not exist");
        // Безопасность: не позволяем ставить лайк в несуществующий пост

        LoveDo storage post = loveDos[tokenId];

        // --- [2] Проверяем, не ставил ли этот адрес лайк уже ранее
        require(!hasSuperliked[tokenId][msg.sender], "LoveDo: already superliked");
        // Безопасность: один адрес может суперлайкнуть пост только один раз

        // --- [3] Запрещаем авторам лайкать свои собственные посты
        require(msg.sender != loveDos[tokenId].author, "LoveDo: cannot superlike own post");
        // Безопасность: предотвращает self-like и инфляцию

        // --- [4] Получаем адрес селлера, который пригласил автора поста
        address inviterOfAuthor = inviteGraph.invitedBy(loveDos[tokenId].author);
        require(inviterOfAuthor != address(0), "LoveDo: author not invited");
        // Защита: автор должен быть реально кем-то приглашён

        // --- [5] Получаем адрес инвайтера для лайкера и сравниваем с автором
        address inviterOfLiker = inviteGraph.invitedBy(msg.sender);
        require(inviterOfLiker == inviterOfAuthor, "LoveDo: liker not in same circle");
        // Социальная модель: суперлайк могут ставить только участники,
        // приглашённые тем же селлером — "горизонтальные связи доверия"

        // --- [6] Проверяем, что получатель (селлер) официально зарегистрирован
        require(amanitaRegistry.hasSellerRole(loveDos[tokenId].sellerTo), "LoveDo: target seller not registered");
        loveDos[tokenId].superlikes += 1;
        hasSuperliked[tokenId][msg.sender] = true;
        monthlyLikesUsed[msg.sender][monthKey]++;
        superlikedPostsByUser[msg.sender].push(tokenId);
        emit Superliked(tokenId, msg.sender, loveDos[tokenId].superlikes);
    }

    function getLoveDoCount(address seller) external view returns (uint8) {
        return uint8(postsBySeller[seller].length);
    }

    // --- View Getters ---

    function getPost(uint256 tokenId) external view returns (LoveDo memory) {
        require(postExists(tokenId), "Invalid post");
        return loveDos[tokenId];
    }

    function getSuperlikes(uint256 tokenId) external view returns (uint8) {
        return loveDos[tokenId].superlikes;
    }

    function getRemainingSuperlikes(address user) external view returns (uint8) {
        uint256 monthKey = block.timestamp / 30 days;
        return MAX_SUPERLIKES_PER_MONTH - monthlyLikesUsed[user][monthKey];
    }

    // --- Admin ---

    function setInviteGraph(address newGraph) external onlyRole(ADMIN_ROLE) {
        inviteGraph = IInviteGraph(newGraph);
    }

    function setAmanitaRegistry(address newRegistry) external onlyRole(ADMIN_ROLE) {
        amanitaRegistry = IAmanitaRegistry(newRegistry);
    }

    function postExists(uint256 tokenId) public view returns (bool) {
        // Если есть владелец, то пост существует
        return ownerOf(tokenId) != address(0);
    }

    // Обязательный override для поддержки интерфейсов (множественное наследование)
    function supportsInterface(bytes4 interfaceId) public view override(ERC721URIStorage, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}


/// @notice Интерфейс для InviteNFT или InviteGraph контракта
interface IInviteGraph {
    function getInviterOf(address user) external view returns (address);
    function invitedBy(address user) external view returns (address);
}

/// @notice Интерфейс для AmanitaRegistry
interface IAmanitaRegistry {
    function hasSellerRole(address user) external view returns (bool);
}
