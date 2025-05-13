// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
 
contract AmanitaToken is ERC20 {
    constructor() ERC20("Amanita Coin", "AMANITA") {}
} 