// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract AmanitaToken is ERC20, AccessControl {
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");

    uint256 public constant INITIAL_SUPPLY = 888_888_888 ether;
    address public spiralEngine;
    uint16 public constant MAX_BPS = 10_000;

    mapping(address => uint256) public sellerDebt;
    mapping(address => uint256) public sellerTotalEmitted;
    mapping(address => uint256) public sellerAcceptedPayments;
    mapping(address => uint256) public sellerLiquidityRefunds;
    /// @notice Cumulative debt repaid for order (used for one-time restore on cancel in AMN-2.7).
    mapping(bytes32 => uint256) public orderDebtRepaid;
    /// @notice One-shot guard: AMN buyer refund already minted for this order.
    mapping(bytes32 => bool) public orderBuyerRefunded;

    /// @notice Checkout contract allowed to apply order-scoped AMANITA redemption (burn + debt decrease).
    address public amanitaCheckout;

    bool public enforceAbsoluteDebtCap = true;
    bool public enforceDebtToLiquidityRatio = true;
    uint256 public absoluteDebtCap = 50_000 ether;
    uint16 public maxDebtToLiquidityBps = 10_000;

    event SpiralEngineUpdated(address indexed oldSpiralEngine, address indexed newSpiralEngine);
    event DebtPolicyUpdated(
        bool enforceAbsoluteDebtCap,
        bool enforceDebtToLiquidityRatio,
        uint256 absoluteDebtCap,
        uint16 maxDebtToLiquidityBps
    );
    event SellerDebtIncreased(address indexed seller, uint256 amount, uint256 newDebt);
    event SellerAcceptedPaymentRecorded(address indexed seller, uint256 amount, uint256 newAcceptedPayments);
    event SellerLiquidityRefundRecorded(address indexed seller, uint256 amount, uint256 newLiquidityRefunds);
    /// @param grossAmount AMANITA received and burned (full gross).
    /// @param debtRepaid Portion applied to reduce `sellerDebt` (min(gross, prior debt)).
    event SellerOrderDebtRepaid(
        address indexed seller,
        bytes32 indexed orderHash,
        uint256 grossAmount,
        uint256 debtRepaid,
        uint256 newSellerDebt
    );
    event SellerOrderDebtRestoredOnCancel(
        address indexed seller,
        bytes32 indexed orderHash,
        uint256 restoredAmount,
        uint256 newSellerDebt
    );
    event BuyerOrderAmnRefunded(address indexed buyer, bytes32 indexed orderHash, uint256 amount);

    constructor(address owner) ERC20("Amanita", "AMANITA") {
        _mint(owner, INITIAL_SUPPLY);
        _grantRole(DEFAULT_ADMIN_ROLE, owner);
    }

    function decimals() public view virtual override returns (uint8) {
        return 18;
    }

    /**
     * @notice Sets SpiralEngine source of truth for SELLER eligibility checks.
     */
    function setSpiralEngine(address newSpiralEngine) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newSpiralEngine != address(0), "AmanitaToken: spiral engine required");
        address oldSpiralEngine = spiralEngine;
        spiralEngine = newSpiralEngine;
        emit SpiralEngineUpdated(oldSpiralEngine, newSpiralEngine);
    }

    /**
     * @notice Registers `AmanitaCheckout` for `applyOrderDebtRepayment`.
     */
    function setAmanitaCheckout(address newCheckout) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newCheckout != address(0), "AmanitaToken: checkout required");
        amanitaCheckout = newCheckout;
    }

    /**
     * @notice Burns `grossAmount` of AMANITA held by this contract and reduces `sellerDebt[seller]` by min(gross, debt).
     * @dev Caller must be `amanitaCheckout`. Tokens must already be transferred to this contract (e.g. buyer → this).
     */
    function applyOrderDebtRepayment(address seller, bytes32 orderHash, uint256 grossAmount) external {
        require(msg.sender == amanitaCheckout, "AmanitaToken: only checkout");
        require(amanitaCheckout != address(0), "AmanitaToken: checkout not set");
        require(seller != address(0), "AmanitaToken: invalid seller");
        require(grossAmount > 0, "AmanitaToken: amount");
        require(balanceOf(address(this)) >= grossAmount, "AmanitaToken: insufficient AMN received");

        uint256 debt = sellerDebt[seller];
        uint256 repay = grossAmount <= debt ? grossAmount : debt;
        unchecked {
            sellerDebt[seller] = debt - repay;
        }
        if (repay > 0) {
            orderDebtRepaid[orderHash] += repay;
        }
        _burn(address(this), grossAmount);
        emit SellerOrderDebtRepaid(seller, orderHash, grossAmount, repay, sellerDebt[seller]);
    }

    /**
     * @notice Restores previously repaid debt for `orderHash` when checkout cancels the order (AMN-2.7).
     * @dev One-time operation per order. Does not mint AMANITA back to buyer; only restores seller debt ledger.
     * @return restoredAmount Amount added back to `sellerDebt`.
     */
    function restoreOrderDebtOnCancel(address seller, bytes32 orderHash) external returns (uint256 restoredAmount) {
        require(msg.sender == amanitaCheckout, "AmanitaToken: only checkout");
        require(amanitaCheckout != address(0), "AmanitaToken: checkout not set");
        require(seller != address(0), "AmanitaToken: invalid seller");

        restoredAmount = orderDebtRepaid[orderHash];
        require(restoredAmount > 0, "AmanitaToken: nothing to restore");

        orderDebtRepaid[orderHash] = 0;
        sellerDebt[seller] += restoredAmount;
        emit SellerOrderDebtRestoredOnCancel(seller, orderHash, restoredAmount, sellerDebt[seller]);
    }

    /**
     * @notice Mints AMANITA back to buyer on cancelled order (AMN-2.8 DG-approved mint-back).
     * @dev One-time per `orderHash`; callable only by `amanitaCheckout`.
     */
    function refundBuyerOnOrderCancel(address buyer, bytes32 orderHash, uint256 amount) external {
        require(msg.sender == amanitaCheckout, "AmanitaToken: only checkout");
        require(amanitaCheckout != address(0), "AmanitaToken: checkout not set");
        require(buyer != address(0), "AmanitaToken: invalid buyer");
        require(amount > 0, "AmanitaToken: amount");
        require(!orderBuyerRefunded[orderHash], "AmanitaToken: buyer already refunded");

        orderBuyerRefunded[orderHash] = true;
        _mint(buyer, amount);
        emit BuyerOrderAmnRefunded(buyer, orderHash, amount);
    }

    function mint(address to, uint256 amount) external {
        _requireEligibleSeller(msg.sender);
        _requireDebtWithinLimits(msg.sender, amount);
        sellerTotalEmitted[msg.sender] += amount;
        sellerDebt[msg.sender] += amount;
        emit SellerDebtIncreased(msg.sender, amount, sellerDebt[msg.sender]);
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _burn(from, amount);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    /**
     * @notice Updates debt policy for seller emission gating.
     */
    function setDebtPolicy(
        bool newEnforceAbsoluteDebtCap,
        bool newEnforceDebtToLiquidityRatio,
        uint256 newAbsoluteDebtCap,
        uint16 newMaxDebtToLiquidityBps
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newMaxDebtToLiquidityBps <= MAX_BPS, "AmanitaToken: invalid bps");
        enforceAbsoluteDebtCap = newEnforceAbsoluteDebtCap;
        enforceDebtToLiquidityRatio = newEnforceDebtToLiquidityRatio;
        absoluteDebtCap = newAbsoluteDebtCap;
        maxDebtToLiquidityBps = newMaxDebtToLiquidityBps;
        emit DebtPolicyUpdated(
            newEnforceAbsoluteDebtCap,
            newEnforceDebtToLiquidityRatio,
            newAbsoluteDebtCap,
            newMaxDebtToLiquidityBps
        );
    }

    /**
     * @notice Records accepted AMANITA payments for seller liquidity accounting.
     */
    function recordAcceptedPayment(address seller, uint256 amount) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(seller != address(0), "AmanitaToken: invalid seller");
        require(amount > 0, "AmanitaToken: amount must be positive");
        sellerAcceptedPayments[seller] += amount;
        emit SellerAcceptedPaymentRecorded(seller, amount, sellerAcceptedPayments[seller]);
    }

    /**
     * @notice Records liquidity refunds/corrections from seller active liquidity.
     */
    function recordLiquidityRefund(address seller, uint256 amount) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(seller != address(0), "AmanitaToken: invalid seller");
        require(amount > 0, "AmanitaToken: amount must be positive");
        require(amount <= getSellerActiveLiquidity(seller), "AmanitaToken: refund exceeds active liquidity");
        sellerLiquidityRefunds[seller] += amount;
        emit SellerLiquidityRefundRecorded(seller, amount, sellerLiquidityRefunds[seller]);
    }

    function getSellerActiveLiquidity(address seller) public view returns (uint256) {
        return sellerAcceptedPayments[seller] - sellerLiquidityRefunds[seller];
    }

    function _requireEligibleSeller(address account) internal view {
        require(spiralEngine != address(0), "AmanitaToken: spiral engine not set");
        require(
            ISpiralSellerSource(spiralEngine).hasRole(SELLER_ROLE, account),
            "AmanitaToken: seller role required"
        );
        require(
            ISpiralSellerSource(spiralEngine).usedInviteByUser(account) > 0,
            "AmanitaToken: seller not activated"
        );
        require(
            ISpiralSellerSource(spiralEngine).suspensionUntil(account) <= block.timestamp,
            "AmanitaToken: seller suspended"
        );
    }

    function _requireDebtWithinLimits(address seller, uint256 mintAmount) internal view {
        uint256 newDebt = sellerDebt[seller] + mintAmount;

        if (enforceAbsoluteDebtCap) {
            require(newDebt <= absoluteDebtCap, "AmanitaToken: debt cap exceeded");
        }

        if (enforceDebtToLiquidityRatio) {
            uint256 activeLiquidity = getSellerActiveLiquidity(seller);
            if (activeLiquidity > 0) {
                uint256 ratioCap = (activeLiquidity * maxDebtToLiquidityBps) / MAX_BPS;
                require(newDebt <= ratioCap, "AmanitaToken: debt/liquidity cap exceeded");
            }
        }
    }
} 

interface ISpiralSellerSource {
    function hasRole(bytes32 role, address account) external view returns (bool);
    function usedInviteByUser(address user) external view returns (uint256);
    function suspensionUntil(address user) external view returns (uint256);
}