// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./LoveDoPostNFT.sol";
import "./Lovecoin.sol";
import "./AmanitaGovToken.sol";
import "./SpiralEngine.sol";

/**
 * @title LoveEmissionEngine
 * @dev Контракт эмиссии для Loveconomy: минтит $LOVECOIN (утилити) и $LGOV (голос)
 * на основе суперлайков в LoveDoPostNFT.
 */
contract LoveEmissionEngine is AccessControl {
    bytes32 public constant EMITTER_ROLE = keccak256("EMITTER_ROLE");
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");

    /// @notice Токены
    IERC20 public immutable lovecoin;
    ILGovToken public immutable lgovToken;
    ILoveDoPostNFT public immutable loveDo;
    IInviteGraph public inviteGraph;
    mapping(address => uint256) public loveAccrued;

    /// @notice Сколько накоплено LGOV, но не получено
    mapping(address => uint256) public lgovAccrued;
    mapping(uint256 => mapping(address => bool)) public emittedForLike;

    /// @notice Коэффициент эмиссии (на 1 суперлайк)
    uint256 public constant EMISSION_RATE = 1 ether;

    /// @notice События
    event Emission(address indexed seller, uint256 lovecoinAmount, uint256 lgovAccrued);
    event LGOVClaimed(address indexed seller, uint256 amount);
    event ClaimedLOVECOIN(address indexed seller, uint256 amount);
    event ClaimedLGOV(address indexed seller, uint256 amount);

    mapping(address => bool) public lgovClaimed;
    uint8 public constant LOVE_DO_THRESHOLD = 8;

    constructor(
        address _lovecoin,
        address _lgov,
        address _loveDo,
        address _inviteGraph,
        address _admin
    ) {
        require(_admin != address(0), "admin required");

        lovecoin = IERC20(_lovecoin);
        lgovToken = ILGovToken(_lgov);
        loveDo = ILoveDoPostNFT(_loveDo);
        inviteGraph = IInviteGraph(_inviteGraph);

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(ADMIN_ROLE, _admin);
    }

    function emitForSuperlike(uint256 tokenId, address liker) external onlyRole(EMITTER_ROLE) {
        (address author, address sellerTo, , , ) = loveDo.getPost(tokenId);
        require(liker != author, "Author can't like their own post");
        require(loveDo.hasSuperliked(tokenId, liker), "LoveEmission: superlike not found for liker");
        require(!emittedForLike[tokenId][liker], "LoveEmission: emission already processed for like");

        emittedForLike[tokenId][liker] = true;

        // 2. Начислить накопленные токены
        loveAccrued[sellerTo] += EMISSION_RATE;
        lgovAccrued[sellerTo] += EMISSION_RATE;

        emit Emission(sellerTo, EMISSION_RATE, lgovAccrued[sellerTo]);
    }

    /**
    * @notice Позволяет селлеру забрать накопленные $LOVECOIN (утилити токены)
    * @dev Вызывается вручную, чтобы избежать газовых затрат при каждом суперлайке
    */
    function claimLOVECOIN() external {
        uint256 amount = loveAccrued[msg.sender];
        require(amount > 0, "LoveEmission: nothing to claim");

        // Обнуляем до трансфера — защита от reentrancy
        loveAccrued[msg.sender] = 0;

        bool success = lovecoin.transfer(msg.sender, amount);
        require(success, "LoveEmission: transfer failed");

        emit ClaimedLOVECOIN(msg.sender, amount);
    }

    /**
    * @notice Позволяет селлеру активировать $LGOV, если он заслужил репутацию (≥ 8 постов)
    * @dev $LGOV становится "реальным" governance-токеном только после подтверждённой репутации
    */
    function claimLGOV() external {
        require(!lgovClaimed[msg.sender], "LoveEmission: already claimed");

        uint8 count = loveDo.getLoveDoCount(msg.sender);
        require(count >= LOVE_DO_THRESHOLD, "LoveEmission: not enough LoveDo posts");

        uint256 amount = lgovAccrued[msg.sender];
        require(amount > 0, "LoveEmission: nothing to mint");

        lgovAccrued[msg.sender] = 0;
        lgovClaimed[msg.sender] = true;

        lgovToken.mint(msg.sender, amount);

        emit ClaimedLGOV(msg.sender, amount);
    }

    /**
    * @notice Возвращает текущее состояние репутации селлера
    * @param seller Адрес селлера, чью репутацию проверяем
    * @return pending Количество накопленных, но ещё не активированных $LGOV
    * @return active Баланс уже заминченных $LGOV
    * @return loveDoCount Количество LoveDo постов в его пользу
    */
    function getReputationProgress(address seller) external view returns (
        uint256 pending,
        uint256 active,
        uint8 loveDoCount
    ) {
        // Накопленные, но ещё не активированные $LGOV
        pending = lgovAccrued[seller];

        // Если уже был claim, репутация активна
        active = lgovClaimed[seller] ? lgovToken.balanceOf(seller) : 0;

        // Количество LoveDo постов, направленных на этого селлера
        loveDoCount = loveDo.getLoveDoCount(seller);
    }
}

interface ILGovToken {
    function mint(address to, uint256 amount) external;
    function balanceOf(address account) external view returns (uint256);
}

interface ILoveDoPostNFT {
    function mentionsOf(address seller) external view returns (uint8);
    function hasSuperliked(uint256 tokenId, address liker) external view returns (bool);

    function getPost(uint256 tokenId) external view returns (
        address author,
        address sellerTo,
        address linkedSeller,
        uint8 superlikes,
        uint256 timestamp
    );

    function getLoveDoCount(address seller) external view returns (uint8);
}