// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @notice Optional callbacks from `AmanitaCheckout` into commerce reputation layer (AMN-2.3).
 */
interface IAmanitaCommerceReputationHooks {
    function notifyAmanitaRedemption(address seller, uint256 grossAmount) external;

    function notifyOrderSettled(address seller) external;
}
