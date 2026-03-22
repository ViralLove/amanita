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
 *      - Live values can change anytime; anchored values change only on `anchorSeller`.
 */
contract AmanitaCommerceReputationAdapter is AccessControl, IAmanitaCommerceReputationHooks {
    bytes32 public constant ANCHOR_ROLE = keccak256("ANCHOR_ROLE");
    bytes32 public constant REPUTATION_OPS_ROLE = keccak256("REPUTATION_OPS_ROLE");

    address public checkout;

    /// @notice Rolling metrics (live), keyed by seller.
    struct CommerceMetrics {
        uint256 sellerRedemptionCount;
        uint256 sellerTotalRedeemedAmount;
        uint256 sellerSuccessfulOrdersCount;
        uint256 sellerRefundCount;
        uint256 sellerDisputeCount;
        uint64 sellerLastRedemptionAt;
    }

    struct AnchoredSnapshot {
        CommerceMetrics metrics;
        uint64 anchoredAt;
    }

    mapping(address => CommerceMetrics) private _live;
    mapping(address => AnchoredSnapshot) private _anchored;

    event CheckoutUpdated(address indexed oldCheckout, address indexed newCheckout);
    event LiveMetricsUpdated(
        address indexed seller,
        uint256 redemptionCount,
        uint256 totalRedeemedAmount,
        uint256 successfulOrdersCount,
        uint256 refundCount,
        uint256 disputeCount,
        uint64 lastRedemptionAt
    );
    event SellerAnchored(address indexed seller, uint64 anchoredAt);
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
    function notifyOrderSettled(address seller) external override {
        require(msg.sender == checkout, "CommerceReputation: only checkout");
        require(seller != address(0), "CommerceReputation: invalid seller");

        CommerceMetrics storage m = _live[seller];
        m.sellerSuccessfulOrdersCount += 1;

        _emitLiveUpdate(seller, m);
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
     * @notice Copy current live metrics into the anchored snapshot for `seller`.
     */
    function anchorSeller(address seller) external onlyRole(ANCHOR_ROLE) {
        require(seller != address(0), "CommerceReputation: invalid seller");
        CommerceMetrics memory m = _live[seller];
        _anchored[seller] = AnchoredSnapshot({metrics: m, anchoredAt: uint64(block.timestamp)});
        emit SellerAnchored(seller, uint64(block.timestamp));
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

    function _emitLiveUpdate(address seller, CommerceMetrics storage m) internal {
        emit LiveMetricsUpdated(
            seller,
            m.sellerRedemptionCount,
            m.sellerTotalRedeemedAmount,
            m.sellerSuccessfulOrdersCount,
            m.sellerRefundCount,
            m.sellerDisputeCount,
            m.sellerLastRedemptionAt
        );
    }
}
