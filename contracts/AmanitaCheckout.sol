// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import "./AmanitaToken.sol";
import "./interfaces/IAmanitaCommerceReputationHooks.sol";

/**
 * @title AmanitaCheckout
 * @notice Composite commerce checkout: AmanitaCoin + LoveCoin on-chain funding; external leg is off-chain only.
 * @dev `Paid` means buyer + seller attested full payment — not automatic from token receipts alone.
 *      Protocol does not verify external (fiat/PSP) payments. Emergency `markOrderPaid` is admin-only.
 *      AMN-2.6: `confirmOrderReceived` and `signalWeakExternalPaymentClaim` emit **optional** reputation signals;
 *      they do not prove delivery or PSP settlement.
 */
contract AmanitaCheckout is AccessControl, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant CHECKOUT_WRITER_ROLE = keccak256("CHECKOUT_WRITER_ROLE");

    /// @notice On-chain funding rail for indexed events.
    enum FundingRail {
        AmanitaCoin,
        LoveCoin
    }

    enum OrderStatus {
        None,
        Created,
        Paid,
        Settled,
        Cancelled
    }

    struct Order {
        address buyer;
        address seller;
        uint256 amount;
        bytes32 referenceId;
        OrderStatus status;
        uint64 createdAt;
        uint64 paidAt;
        uint64 settledAt;
        uint64 cancelledAt;
        /// @dev Cumulative AmanitaCoin in order.amount units (canonical AMN wei).
        uint256 capturedAmanita;
        /// @dev Cumulative LoveCoin in native Love token units (no FX to order.amount in MVP).
        uint256 capturedLove;
        bool buyerDeclaredFullPayment;
        bool sellerAcceptedFullPayment;
        uint64 fullPaymentDeclaredAt;
        uint64 fullPaymentAcceptedAt;
        /// @dev Buyer confirmed receipt while `Paid` (AMN-2.6); read at settle for hook.
        uint64 receivedByBuyerAt;
        /// @dev One-time weak external-leg claim in `Created` (AMN-2.6).
        bool weakExternalPaymentClaimed;
    }

    IERC20 public immutable amanitaCoin;
    IERC20 public immutable loveCoin;
    AmanitaToken public immutable amanitaToken;

    /// @notice Optional AMN-2.3 reputation hooks (zero = disabled).
    IAmanitaCommerceReputationHooks public reputationHooks;

    mapping(bytes32 => Order) private _orders;

    event OrderCreated(
        bytes32 indexed orderHash,
        address indexed buyer,
        address indexed seller,
        uint256 amount,
        bytes32 referenceId
    );
    /// @notice Emitted when order reaches `Paid` via buyer/seller attestation. `actor` is the seller who accepted.
    event OrderPaid(bytes32 indexed orderHash, address indexed actor, uint64 paidAt);
    /// @notice Emergency / legacy: admin forced `Paid` without attestation. Do not use for normal UX.
    event OrderPaidEmergency(bytes32 indexed orderHash, address indexed admin, uint64 paidAt);
    event OrderSettled(bytes32 indexed orderHash, address indexed writer, uint64 settledAt);
    event OrderCancelled(bytes32 indexed orderHash, address indexed actor, uint64 cancelledAt);
    event OrderOnChainFunded(
        bytes32 indexed orderHash,
        FundingRail indexed rail,
        uint256 increment,
        uint256 cumulativeOnRail
    );
    event OrderFullPaymentDeclared(bytes32 indexed orderHash, address indexed buyer, uint64 declaredAt);
    event OrderFullPaymentAccepted(bytes32 indexed orderHash, address indexed seller, uint64 acceptedAt);
    /// @notice Voluntary buyer signal: claims order received (does not prove delivery; AMN-2.6).
    event OrderReceivedByBuyer(bytes32 indexed orderHash, address indexed buyer, uint64 receivedAt);
    /// @notice Weak optional signal while `Created`; does not move status or imply `Paid` (AMN-2.6).
    event WeakExternalPaymentClaimed(bytes32 indexed orderHash, address indexed buyer, address indexed seller, uint64 claimedAt);
    event ReputationHooksUpdated(address indexed hooks);

    constructor(address admin, address amanitaToken_, address loveCoin_) {
        require(admin != address(0), "AmanitaCheckout: invalid admin");
        require(amanitaToken_ != address(0), "AmanitaCheckout: invalid amanita token");
        require(loveCoin_ != address(0), "AmanitaCheckout: invalid love token");

        amanitaToken = AmanitaToken(amanitaToken_);
        amanitaCoin = IERC20(amanitaToken_);
        loveCoin = IERC20(loveCoin_);

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CHECKOUT_WRITER_ROLE, admin);
    }

    /**
     * @notice Wire `AmanitaCommerceReputationAdapter` (or any `IAmanitaCommerceReputationHooks` impl). Pass zero to disable.
     */
    function setReputationHooks(address hooks) external onlyRole(DEFAULT_ADMIN_ROLE) {
        reputationHooks = IAmanitaCommerceReputationHooks(hooks);
        emit ReputationHooksUpdated(hooks);
    }

    function createOrder(
        address seller,
        uint256 amount,
        bytes32 referenceId
    ) external returns (bytes32 orderHash) {
        require(seller != address(0), "AmanitaCheckout: invalid seller");
        require(amount > 0, "AmanitaCheckout: invalid amount");
        require(referenceId != bytes32(0), "AmanitaCheckout: invalid reference");

        orderHash = keccak256(
            abi.encodePacked(block.chainid, address(this), msg.sender, seller, amount, referenceId)
        );
        require(_orders[orderHash].status == OrderStatus.None, "AmanitaCheckout: order exists");

        _orders[orderHash] = Order({
            buyer: msg.sender,
            seller: seller,
            amount: amount,
            referenceId: referenceId,
            status: OrderStatus.Created,
            createdAt: uint64(block.timestamp),
            paidAt: 0,
            settledAt: 0,
            cancelledAt: 0,
            capturedAmanita: 0,
            capturedLove: 0,
            buyerDeclaredFullPayment: false,
            sellerAcceptedFullPayment: false,
            fullPaymentDeclaredAt: 0,
            fullPaymentAcceptedAt: 0,
            receivedByBuyerAt: 0,
            weakExternalPaymentClaimed: false
        });

        emit OrderCreated(orderHash, msg.sender, seller, amount, referenceId);
    }

    /**
     * @notice Pull AmanitaCoin from buyer, forward to `AmanitaToken`, apply incremental debt repayment for seller.
     */
    function captureAmanitaCoin(bytes32 orderHash, uint256 amount) external nonReentrant {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid status for capture");
        require(!order.buyerDeclaredFullPayment, "AmanitaCheckout: funding locked after declare");
        require(msg.sender == order.buyer, "AmanitaCheckout: only buyer");
        require(amount > 0, "AmanitaCheckout: invalid capture amount");
        require(order.capturedAmanita + amount <= order.amount, "AmanitaCheckout: amanita exceeds order amount");

        order.capturedAmanita += amount;
        amanitaCoin.safeTransferFrom(msg.sender, address(amanitaToken), amount);
        amanitaToken.applyOrderDebtRepayment(order.seller, orderHash, amount);

        emit OrderOnChainFunded(orderHash, FundingRail.AmanitaCoin, amount, order.capturedAmanita);

        if (address(reputationHooks) != address(0)) {
            reputationHooks.notifyAmanitaRedemption(order.seller, amount);
        }
    }

    /**
     * @notice Pull LoveCoin from buyer into this contract (escrow). Does not affect `sellerDebt`.
     */
    function captureLoveCoin(bytes32 orderHash, uint256 amount) external nonReentrant {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid status for capture");
        require(!order.buyerDeclaredFullPayment, "AmanitaCheckout: funding locked after declare");
        require(msg.sender == order.buyer, "AmanitaCheckout: only buyer");
        require(amount > 0, "AmanitaCheckout: invalid capture amount");

        order.capturedLove += amount;
        loveCoin.safeTransferFrom(msg.sender, address(this), amount);

        emit OrderOnChainFunded(orderHash, FundingRail.LoveCoin, amount, order.capturedLove);
    }

    /**
     * @notice Buyer attests that the order is fully paid across all agreed rails (on-chain + external).
     */
    function declareFullPayment(bytes32 orderHash) external {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid status for declare");
        require(msg.sender == order.buyer, "AmanitaCheckout: only buyer");
        require(!order.buyerDeclaredFullPayment, "AmanitaCheckout: already declared");

        order.buyerDeclaredFullPayment = true;
        order.fullPaymentDeclaredAt = uint64(block.timestamp);
        emit OrderFullPaymentDeclared(orderHash, msg.sender, order.fullPaymentDeclaredAt);
    }

    /**
     * @notice Buyer voluntarily signals that the order was received (AMN-2.6). One call per order while `Paid`.
     * @dev Does not change `OrderStatus`; not proof of delivery. Used at settlement for reputation hook.
     */
    function confirmOrderReceived(bytes32 orderHash) external {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Paid, "AmanitaCheckout: invalid status for received");
        require(msg.sender == order.buyer, "AmanitaCheckout: only buyer");
        require(order.receivedByBuyerAt == 0, "AmanitaCheckout: already confirmed received");

        order.receivedByBuyerAt = uint64(block.timestamp);
        emit OrderReceivedByBuyer(orderHash, msg.sender, order.receivedByBuyerAt);
    }

    /**
     * @notice Weak optional signal: buyer claims external payment leg was sent (AMN-2.6). Only in `Created`, once per order.
     * @dev Does not set `Paid` or verify PSP/fiat.
     */
    function signalWeakExternalPaymentClaim(bytes32 orderHash) external {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid status for weak claim");
        require(msg.sender == order.buyer, "AmanitaCheckout: only buyer");
        require(!order.weakExternalPaymentClaimed, "AmanitaCheckout: weak claim already used");

        order.weakExternalPaymentClaimed = true;
        uint64 t = uint64(block.timestamp);
        emit WeakExternalPaymentClaimed(orderHash, order.buyer, order.seller, t);

        if (address(reputationHooks) != address(0)) {
            reputationHooks.notifyWeakExternalPaymentClaim(order.buyer, order.seller);
        }
    }

    /**
     * @notice Seller accepts buyer's full-payment attestation; transitions to `Paid`.
     */
    function acceptFullPayment(bytes32 orderHash) external nonReentrant {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid status for accept");
        require(msg.sender == order.seller, "AmanitaCheckout: only seller");
        require(order.buyerDeclaredFullPayment, "AmanitaCheckout: full payment not declared");

        order.status = OrderStatus.Paid;
        order.paidAt = uint64(block.timestamp);
        order.sellerAcceptedFullPayment = true;
        order.fullPaymentAcceptedAt = order.paidAt;

        emit OrderFullPaymentAccepted(orderHash, msg.sender, order.paidAt);
        emit OrderPaid(orderHash, msg.sender, order.paidAt);
    }

    /**
     * @notice **Emergency only.** Forces `Paid` without buyer/seller attestation. Not a normal payment path.
     */
    function markOrderPaid(bytes32 orderHash) external onlyRole(DEFAULT_ADMIN_ROLE) {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid transition to paid");

        order.status = OrderStatus.Paid;
        order.paidAt = uint64(block.timestamp);
        emit OrderPaidEmergency(orderHash, msg.sender, order.paidAt);
        emit OrderPaid(orderHash, msg.sender, order.paidAt);
    }

    function markOrderSettled(bytes32 orderHash) external onlyRole(CHECKOUT_WRITER_ROLE) {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Paid, "AmanitaCheckout: invalid transition to settled");

        order.status = OrderStatus.Settled;
        order.settledAt = uint64(block.timestamp);
        emit OrderSettled(orderHash, msg.sender, order.settledAt);

        if (address(reputationHooks) != address(0)) {
            reputationHooks.notifyOrderSettled(
                order.seller,
                order.buyer,
                order.buyerDeclaredFullPayment,
                order.sellerAcceptedFullPayment,
                order.receivedByBuyerAt != 0
            );
        }
    }

    function cancelOrder(bytes32 orderHash) external onlyRole(CHECKOUT_WRITER_ROLE) {
        Order storage order = _getOrder(orderHash);
        require(
            order.status == OrderStatus.Created || order.status == OrderStatus.Paid,
            "AmanitaCheckout: invalid transition to cancelled"
        );

        order.status = OrderStatus.Cancelled;
        order.cancelledAt = uint64(block.timestamp);
        emit OrderCancelled(orderHash, msg.sender, order.cancelledAt);
    }

    function cancelOwnOrder(bytes32 orderHash) external {
        Order storage order = _getOrder(orderHash);
        require(msg.sender == order.buyer, "AmanitaCheckout: only buyer can self-cancel");
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid self-cancel status");

        order.status = OrderStatus.Cancelled;
        order.cancelledAt = uint64(block.timestamp);
        emit OrderCancelled(orderHash, msg.sender, order.cancelledAt);
    }

    function getOrder(bytes32 orderHash) external view returns (Order memory) {
        Order memory order = _orders[orderHash];
        require(order.status != OrderStatus.None, "AmanitaCheckout: order not found");
        return order;
    }

    function _getOrder(bytes32 orderHash) internal view returns (Order storage order) {
        order = _orders[orderHash];
        require(order.status != OrderStatus.None, "AmanitaCheckout: order not found");
    }
}
