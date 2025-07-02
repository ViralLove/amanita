// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title Orders
 * @dev On-chain registry of Amanita protocol orders with IPFS metadata and OTP validation.
 */
contract Orders is AccessControl {
    /// @notice Role for marking orders as paid (assigned to the Payment Router)
    bytes32 public constant ROUTER_ROLE = keccak256("ROUTER_ROLE");

    /// @notice Order structure stored on-chain
    struct Order {
        address buyer;
        address seller;
        uint256 amount;
        string otp;
        string ipfsHash;
        bool paid;
    }

    /// @notice Mapping of order hash to Order data
    mapping(bytes32 => Order) private orders;

    /// @notice Emitted when a new order is registered
    event OrderCreated(
        bytes32 indexed orderHash,
        address indexed seller,
        address indexed buyer,
        uint256 amount,
        string otp,
        string ipfsHash
    );

    /// @notice Emitted when an order is marked as paid
    event OrderPaid(bytes32 indexed orderHash);

    /**
     * @dev Initializes the contract, assigning DEFAULT_ADMIN_ROLE to the deployer.
     */
    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    /**
     * @notice Creates a new order and stores it on-chain.
     * @param buyer The buyer's wallet address.
     * @param seller The seller's wallet address.
     * @param amount Total order amount including OTP in decimal part.
     * @param otp Unique OTP string encoded in payment.
     * @param ipfsHash IPFS hash of the off-chain order metadata.
     * @return orderHash The keccak256 hash of the order.
     */
    function createOrder(
        address buyer,
        address seller,
        uint256 amount,
        string memory otp,
        string memory ipfsHash
    ) external returns (bytes32 orderHash) {
        orderHash = keccak256(abi.encodePacked(buyer, seller, amount, otp, ipfsHash));

        require(orders[orderHash].amount == 0, "OrderAlreadyExists");

        orders[orderHash] = Order({
            buyer: buyer,
            seller: seller,
            amount: amount,
            otp: otp,
            ipfsHash: ipfsHash,
            paid: false
        });

        emit OrderCreated(orderHash, seller, buyer, amount, otp, ipfsHash);
    }

    /**
     * @notice Marks a given order as paid.
     * @dev Can only be called by address with ROUTER_ROLE (e.g. Payment Router).
     * @param orderHash Hash of the order to mark as paid.
     */
    function markAsPaid(bytes32 orderHash) external onlyRole(ROUTER_ROLE) {
        Order storage o = orders[orderHash];

        require(o.amount != 0, "OrderNotFound");
        require(!o.paid, "OrderAlreadyPaid");

        o.paid = true;

        emit OrderPaid(orderHash);
    }

    /**
     * @notice Returns full order data for a given order hash.
     * @param orderHash The hash of the order.
     * @return o The Order struct.
     */
    function getOrder(bytes32 orderHash) external view returns (Order memory o) {
        o = orders[orderHash];
        require(o.amount != 0, "OrderNotFound");
    }
}
