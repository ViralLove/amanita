// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @notice Optional callbacks from `AmanitaCheckout` into commerce reputation (AMN-2.3 core + AMN-2.6 signals).
 * @dev Does not verify external payments; metrics are operational signals, not legal proof.
 */
interface IAmanitaCommerceReputationHooks {
    function notifyAmanitaRedemption(address seller, uint256 grossAmount) external;

    /**
     * @param buyerConfirmedReceivedBeforeSettle true iff buyer called `confirmOrderReceived` while order was `Paid`
     *        before this settlement (AMN-2.6 signal discipline denominator).
     */
    function notifyOrderSettled(
        address seller,
        address buyer,
        bool buyerDeclaredFullPayment,
        bool sellerAcceptedFullPayment,
        bool buyerConfirmedReceivedBeforeSettle
    ) external;

    /// @notice Weak optional signal: buyer claims external leg sent (does not affect `Paid`; AMN-2.6).
    function notifyWeakExternalPaymentClaim(address buyer, address seller) external;
}
