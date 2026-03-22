// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title AmanitaCheckout
 * @notice Order lifecycle registry for AMANITA commerce flow.
 * @dev Payment routing and debt repayment are handled in AMN-2.2.
 */
contract AmanitaCheckout is AccessControl {
    bytes32 public constant CHECKOUT_WRITER_ROLE = keccak256("CHECKOUT_WRITER_ROLE");

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
    }

    mapping(bytes32 => Order) private _orders;

    event OrderCreated(
        bytes32 indexed orderHash,
        address indexed buyer,
        address indexed seller,
        uint256 amount,
        bytes32 referenceId
    );
    event OrderPaid(bytes32 indexed orderHash, address indexed writer, uint64 paidAt);
    event OrderSettled(bytes32 indexed orderHash, address indexed writer, uint64 settledAt);
    event OrderCancelled(bytes32 indexed orderHash, address indexed actor, uint64 cancelledAt);

    constructor(address admin) {
        require(admin != address(0), "AmanitaCheckout: invalid admin");
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CHECKOUT_WRITER_ROLE, admin);
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
            cancelledAt: 0
        });

        emit OrderCreated(orderHash, msg.sender, seller, amount, referenceId);
    }

    function markOrderPaid(bytes32 orderHash) external onlyRole(CHECKOUT_WRITER_ROLE) {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid transition to paid");

        order.status = OrderStatus.Paid;
        order.paidAt = uint64(block.timestamp);
        emit OrderPaid(orderHash, msg.sender, order.paidAt);
    }

    function markOrderSettled(bytes32 orderHash) external onlyRole(CHECKOUT_WRITER_ROLE) {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Paid, "AmanitaCheckout: invalid transition to settled");

        order.status = OrderStatus.Settled;
        order.settledAt = uint64(block.timestamp);
        emit OrderSettled(orderHash, msg.sender, order.settledAt);
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
