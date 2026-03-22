// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "./interfaces/IAmanitaCommerceReputationHooks.sol";

/**
 * @title AmanitaCommerceReputationAdapter
 * @notice Hybrid commerce metrics for SBT/off-chain consumers: **live** counters (updated by checkout)
 *         and **anchored** snapshots (explicit commit for stable metadata).
 * @dev Trust assumptions:
 *      - `notify*` may only be called by the registered `checkout` address; metrics reflect checkout truth, not independent verification.
 *      - `recordRefund` / `recordDispute` are **operator/admin** inputs until automated sources (e.g. AMN-2.7) exist.
 *      - Live values can change anytime; anchored values change only on `anchorSeller` / `anchorBuyer`.
 *      - AMN-2.6: buyer/seller signal metrics are **non-punitive** operational hints; see `docs/commerce-reputation-disclaimers.md`.
 */
contract AmanitaCommerceReputationAdapter is AccessControl, IAmanitaCommerceReputationHooks {
    bytes32 public constant ANCHOR_ROLE = keccak256("ANCHOR_ROLE");
    bytes32 public constant REPUTATION_OPS_ROLE = keccak256("REPUTATION_OPS_ROLE");

    address public checkout;

    /// @notice Rolling metrics (live), keyed by seller (redemption + settlement + AMN-2.6 seller signals).
    struct CommerceMetrics {
        uint256 sellerRedemptionCount;
        uint256 sellerTotalRedeemedAmount;
        uint256 sellerSuccessfulOrdersCount;
        uint256 sellerRefundCount;
        uint256 sellerDisputeCount;
        uint64 sellerLastRedemptionAt;
        /// @notice Settled orders where buyer had declared full payment before settle (denominator for unsettled-after-declare bps).
        uint256 sellerSettledWithBuyerDeclareCount;
        /// @notice Subset: buyer declared but seller never accepted (e.g. emergency `Paid`); numerator for bps above.
        uint256 sellerSettledWithoutSellerAcceptCount;
    }

    struct AnchoredSnapshot {
        CommerceMetrics metrics;
        uint64 anchoredAt;
    }

    /// @notice Buyer-side voluntary signals (AMN-2.6); keyed by buyer address.
    struct BuyerSignalMetrics {
        uint256 settledReceivedCount;
        uint256 settledReceivedMissingDeclareCount;
        uint256 weakExternalClaimCount;
    }

    struct BuyerAnchoredSnapshot {
        BuyerSignalMetrics metrics;
        uint64 anchoredAt;
    }

    mapping(address => CommerceMetrics) private _live;
    mapping(address => AnchoredSnapshot) private _anchored;

    mapping(address => BuyerSignalMetrics) private _buyerLive;
    mapping(address => BuyerAnchoredSnapshot) private _buyerAnchored;

    event CheckoutUpdated(address indexed oldCheckout, address indexed newCheckout);
    event LiveMetricsUpdated(
        address indexed seller,
        uint256 redemptionCount,
        uint256 totalRedeemedAmount,
        uint256 successfulOrdersCount,
        uint256 refundCount,
        uint256 disputeCount,
        uint64 lastRedemptionAt,
        uint256 settledWithBuyerDeclareCount,
        uint256 settledWithoutSellerAcceptCount
    );
    event BuyerLiveMetricsUpdated(
        address indexed buyer,
        uint256 settledReceivedCount,
        uint256 settledReceivedMissingDeclareCount,
        uint256 weakExternalClaimCount
    );
    event SellerAnchored(address indexed seller, uint64 anchoredAt);
    event BuyerAnchored(address indexed buyer, uint64 anchoredAt);
    event RefundRecorded(address indexed seller, uint256 newRefundCount);
    event DisputeRecorded(address indexed seller, uint256 newDisputeCount);

    constructor(address admin, address checkout_) {
        require(admin != address(0), "CommerceReputation: invalid admin");
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ANCHOR_ROLE, admin);
        _grantRole(REPUTATION_OPS_ROLE, admin);

        checkout = checkout_;
        emit CheckoutUpdated(address(0), checkout_);
    }

    function setCheckout(address newCheckout) external onlyRole(DEFAULT_ADMIN_ROLE) {
        address old = checkout;
        checkout = newCheckout;
        emit CheckoutUpdated(old, newCheckout);
    }

    /// @inheritdoc IAmanitaCommerceReputationHooks
    function notifyAmanitaRedemption(address seller, uint256 grossAmount) external override {
        require(msg.sender == checkout, "CommerceReputation: only checkout");
        require(seller != address(0), "CommerceReputation: invalid seller");
        require(grossAmount > 0, "CommerceReputation: amount");

        CommerceMetrics storage m = _live[seller];
        m.sellerRedemptionCount += 1;
        m.sellerTotalRedeemedAmount += grossAmount;
        m.sellerLastRedemptionAt = uint64(block.timestamp);

        _emitLiveUpdate(seller, m);
    }

    /// @inheritdoc IAmanitaCommerceReputationHooks
    function notifyOrderSettled(
        address seller,
        address buyer,
        bool buyerDeclaredFullPayment,
        bool sellerAcceptedFullPayment,
        bool buyerConfirmedReceivedBeforeSettle
    ) external override {
        require(msg.sender == checkout, "CommerceReputation: only checkout");
        require(seller != address(0), "CommerceReputation: invalid seller");
        require(buyer != address(0), "CommerceReputation: invalid buyer");

        CommerceMetrics storage m = _live[seller];
        m.sellerSuccessfulOrdersCount += 1;

        if (buyerDeclaredFullPayment) {
            m.sellerSettledWithBuyerDeclareCount += 1;
            if (!sellerAcceptedFullPayment) {
                m.sellerSettledWithoutSellerAcceptCount += 1;
            }
        }

        if (buyerConfirmedReceivedBeforeSettle) {
            BuyerSignalMetrics storage b = _buyerLive[buyer];
            b.settledReceivedCount += 1;
            if (!buyerDeclaredFullPayment) {
                b.settledReceivedMissingDeclareCount += 1;
            }
            _emitBuyerUpdate(buyer, b);
        }

        _emitLiveUpdate(seller, m);
    }

    /// @inheritdoc IAmanitaCommerceReputationHooks
    function notifyWeakExternalPaymentClaim(address buyer, address seller) external override {
        require(msg.sender == checkout, "CommerceReputation: only checkout");
        require(buyer != address(0), "CommerceReputation: invalid buyer");
        require(seller != address(0), "CommerceReputation: invalid seller");

        BuyerSignalMetrics storage b = _buyerLive[buyer];
        b.weakExternalClaimCount += 1;
        _emitBuyerUpdate(buyer, b);
    }

    /**
     * @notice Increment refund counter (off-chain / ops until automated refund flow).
     */
    function recordRefund(address seller) external onlyRole(REPUTATION_OPS_ROLE) {
        require(seller != address(0), "CommerceReputation: invalid seller");
        CommerceMetrics storage m = _live[seller];
        m.sellerRefundCount += 1;
        emit RefundRecorded(seller, m.sellerRefundCount);
        _emitLiveUpdate(seller, m);
    }

    /**
     * @notice Increment dispute counter (off-chain / ops).
     */
    function recordDispute(address seller) external onlyRole(REPUTATION_OPS_ROLE) {
        require(seller != address(0), "CommerceReputation: invalid seller");
        CommerceMetrics storage m = _live[seller];
        m.sellerDisputeCount += 1;
        emit DisputeRecorded(seller, m.sellerDisputeCount);
        _emitLiveUpdate(seller, m);
    }

    /**
     * @notice Copy current live seller metrics into the anchored snapshot.
     */
    function anchorSeller(address seller) external onlyRole(ANCHOR_ROLE) {
        require(seller != address(0), "CommerceReputation: invalid seller");
        CommerceMetrics memory m = _live[seller];
        _anchored[seller] = AnchoredSnapshot({metrics: m, anchoredAt: uint64(block.timestamp)});
        emit SellerAnchored(seller, uint64(block.timestamp));
    }

    /**
     * @notice Copy current live buyer signal metrics into the anchored snapshot.
     */
    function anchorBuyer(address buyer) external onlyRole(ANCHOR_ROLE) {
        require(buyer != address(0), "CommerceReputation: invalid buyer");
        BuyerSignalMetrics memory b = _buyerLive[buyer];
        _buyerAnchored[buyer] = BuyerAnchoredSnapshot({metrics: b, anchoredAt: uint64(block.timestamp)});
        emit BuyerAnchored(buyer, uint64(block.timestamp));
    }

    function getLiveMetrics(address seller) external view returns (CommerceMetrics memory) {
        return _live[seller];
    }

    function getAnchoredSnapshot(address seller) external view returns (AnchoredSnapshot memory) {
        return _anchored[seller];
    }

    function anchoredAt(address seller) external view returns (uint64) {
        return _anchored[seller].anchoredAt;
    }

    function getLiveBuyerMetrics(address buyer) external view returns (BuyerSignalMetrics memory) {
        return _buyerLive[buyer];
    }

    function getAnchoredBuyerSnapshot(address buyer) external view returns (BuyerAnchoredSnapshot memory) {
        return _buyerAnchored[buyer];
    }

    function buyerAnchoredAt(address buyer) external view returns (uint64) {
        return _buyerAnchored[buyer].anchoredAt;
    }

    /**
     * @notice Basis points: share of settled orders (with buyer declare) that reached settle without seller accept.
     * @dev Returns 0 if denominator is 0.
     */
    function getSellerUnsettledAfterDeclareBps(address seller) external view returns (uint256) {
        CommerceMetrics memory m = _live[seller];
        if (m.sellerSettledWithBuyerDeclareCount == 0) return 0;
        return (m.sellerSettledWithoutSellerAcceptCount * 10_000) / m.sellerSettledWithBuyerDeclareCount;
    }

    /**
     * @notice Basis points: among orders where buyer confirmed receipt before settle, share missing buyer declare.
     * @dev Returns 0 if denominator is 0.
     */
    function getBuyerReceivedWithoutDeclareBps(address buyer) external view returns (uint256) {
        BuyerSignalMetrics memory b = _buyerLive[buyer];
        if (b.settledReceivedCount == 0) return 0;
        return (b.settledReceivedMissingDeclareCount * 10_000) / b.settledReceivedCount;
    }

    function _emitLiveUpdate(address seller, CommerceMetrics storage m) internal {
        emit LiveMetricsUpdated(
            seller,
            m.sellerRedemptionCount,
            m.sellerTotalRedeemedAmount,
            m.sellerSuccessfulOrdersCount,
            m.sellerRefundCount,
            m.sellerDisputeCount,
            m.sellerLastRedemptionAt,
            m.sellerSettledWithBuyerDeclareCount,
            m.sellerSettledWithoutSellerAcceptCount
        );
    }

    function _emitBuyerUpdate(address buyer, BuyerSignalMetrics storage b) internal {
        emit BuyerLiveMetricsUpdated(
            buyer,
            b.settledReceivedCount,
            b.settledReceivedMissingDeclareCount,
            b.weakExternalClaimCount
        );
    }
}
