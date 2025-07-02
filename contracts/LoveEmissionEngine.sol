// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title LoveEmissionEngine
 * @dev Контракт эмиссии для Loveconomy: минтит $AMANITA (утилити) и $AGOV (голос)
 * на основе суперлайков в LoveDoPostNFT.
 */
contract LoveEmissionEngine is AccessControl {
    bytes32 public constant EMITTER_ROLE = keccak256("EMITTER_ROLE");
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");

    /// @notice Токены
    AmanitaToken public immutable amanitaToken;
    AmanitaGovToken public immutable agovToken;
    ILoveDoPostNFT public immutable loveDo;
    mapping(address => uint256) public amanitaAccrued;

    /// @notice Сколько накоплено AGOV, но не получено
    mapping(address => uint256) public agovAccrued;

    /// @notice Коэффициент эмиссии (на 1 суперлайк)
    uint256 public constant EMISSION_RATE = 1 ether;

    /// @notice События
    event Emission(address indexed seller, uint256 amanitaAmount, uint256 agovAccrued);
    event AGOVClaimed(address indexed seller, uint256 amount);

    constructor(
        address _amanita,
        address _agov,
        address _loveDo,
        address _admin
    ) {
        require(_admin != address(0), "admin required");

        amanitaToken = IERC20(_amanita);
        agovToken = IAGovToken(_agov);
        loveDo = ILoveDoPostNFT(_loveDo);

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(ADMIN_ROLE, _admin);
    }

    function emitForSuperlike(uint256 tokenId, address liker) external onlyRole(EMITTER_ROLE) {
        LoveDo memory post = loveDo.getPost(tokenId);

        address inviterOfAuthor = inviteGraph.inviteMinter(post.author);
        address inviterOfLiker = inviteGraph.inviteMinter(liker);

        require(inviterOfAuthor != address(0), "Post author not invited");
        require(inviterOfAuthor == inviterOfLiker, "Liker must be from same inviter group");
        require(liker != post.author, "Author can't like their own post");

        // 1. Записать superlike
        bool success = loveDo.addSuperlike(tokenId);
        require(success, "Superlike failed");

        // 2. Начислить накопленные токены
        amanitaAccrued[post.sellerTo] += EMISSION_RATE;
        agovAccrued[post.sellerTo] += EMISSION_RATE;

        emit Emission(post.sellerTo, EMISSION_RATE, agovAccrued[post.sellerTo]);

    }


    /**
    * @notice Позволяет селлеру забрать накопленные $AMANITA (утилити токены)
    * @dev Вызывается вручную, чтобы избежать газовых затрат при каждом суперлайке
    */
    function claimAMANITA() external {
        uint256 amount = amanitaAccrued[msg.sender];
        require(amount > 0, "LoveEmission: nothing to claim");

        // Обнуляем до трансфера — защита от reentrancy
        amanitaAccrued[msg.sender] = 0;

        bool success = amanita.transfer(msg.sender, amount);
        require(success, "LoveEmission: transfer failed");

        emit ClaimedAMANITA(msg.sender, amount);
    }

    /**
    * @notice Позволяет селлеру активировать $AGOV, если он заслужил репутацию (≥ 8 постов)
    * @dev $AGOV становится "реальным" governance-токеном только после подтверждённой репутации
    */
    function claimAGOV() external {
        require(!agovClaimed[msg.sender], "LoveEmission: already claimed");

        uint8 count = loveDo.getLoveDoCount(msg.sender);
        require(count >= LOVE_DO_THRESHOLD, "LoveEmission: not enough LoveDo posts");

        uint256 amount = agovAccrued[msg.sender];
        require(amount > 0, "LoveEmission: nothing to mint");

        agovAccrued[msg.sender] = 0;
        agovClaimed[msg.sender] = true;

        agov.mint(msg.sender, amount);

        emit ClaimedAGOV(msg.sender, amount);
    }

    /**
    * @notice Возвращает текущее состояние репутации селлера
    * @param seller Адрес селлера, чью репутацию проверяем
    * @return pending Количество накопленных, но ещё не активированных $AGOV
    * @return active Баланс уже заминченных $AGOV
    * @return loveDoCount Количество LoveDo постов в его пользу
    */
    function getReputationProgress(address seller) external view returns (
        uint256 pending,
        uint256 active,
        uint8 loveDoCount
    ) {
        // Накопленные, но ещё не активированные $AGOV
        pending = agovAccrued[seller];

        // Если уже был claim, репутация активна
        active = agovClaimed[seller] ? agov.balanceOf(seller) : 0;

        // Количество LoveDo постов, направленных на этого селлера
        loveDoCount = loveDo.getLoveDoCount(seller);
    }


}
interface IAGovToken {
    function mint(address to, uint256 amount) external;
}

interface ILoveDoPostNFT {
    function mentionsOf(address seller) external view returns (uint8);

    function addSuperlike(uint256 tokenId) external returns (bool);
    
    function getPost(uint256 tokenId) external view returns (
        address author,
        address sellerTo,
        address linkedSeller,
        uint8 superlikes
    );

    function getLoveDoCount(address seller) external view returns (uint8);

}

interface IInviteGraph {
    function inviteMinter(address user) external view returns (address);
}