// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

/**
 * @title ActivityRegistryProxy
 * @author Zeya888 (https://zeya888.me)
 * @notice UUPS Proxy для ActivityRegistry
 * @dev Минимальный Proxy: делегирует вызовы в ActivityRegistryLogic.
 * @custom:security-contact security@amanita.com
 */
contract ActivityRegistryProxy is ERC1967Proxy {
    constructor(address implementation, bytes memory initData)
        ERC1967Proxy(implementation, initData)
    {}
}
