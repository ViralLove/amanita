// SPDX-License-Identifier: MIT
pragma solidity ^0.8.18;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./Orders.sol";

/**
 * @title AmanitaPaymentRouter
 * @dev Receives stablecoin payments and links them to OTP-based orders in Orders.sol
 */
contract AmanitaPaymentRouter is AccessControl {
    /// @notice Admin role for access control (usually deployer or DAO)
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");

    /// @notice Address of the stablecoin used for payments (e.g., USDT)
    IERC20 public immutable stableToken;

    /// @notice Orders contract address
    Orders public immutable orders;

    event PaymentReceived(
        address indexed from,
        address indexed seller,
        uint256 amount,
        bytes32 indexed orderHash
    );

    /**
     * @param _stableToken The address of the ERC20 token used for payments (e.g. USDT)
     * @param _orders Address of deployed Orders.sol contract
     */
    constructor(address _stableToken, address _orders) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ADMIN_ROLE, msg.sender);

        stableToken = IERC20(_stableToken);
        orders = Orders(_orders);
    }

    /**
     * @notice Pay for an order in USDT with exact amount containing OTP.
     * @param seller The address of the seller to credit.
     * @param amount The exact amount (with OTP in decimal) to transfer.
     * @param orderHash The hash of the order (must be pre-created).
     */
    function pay(address seller, uint256 amount, bytes32 orderHash) external {
        require(seller != address(0), "Invalid seller");

        // Transfer USDT from msg.sender to this router
        require(
            stableToken.transferFrom(msg.sender, address(this), amount),
            "Token transfer failed"
        );

        // Forward funds to seller
        require(
            stableToken.transfer(seller, amount),
            "Payout failed"
        );

        // Mark order as paid in Orders.sol
        orders.markAsPaid(orderHash);

        emit PaymentReceived(msg.sender, seller, amount, orderHash);
    }
}
