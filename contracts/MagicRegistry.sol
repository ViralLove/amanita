// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MagicRegistry {
    address public owner;
    mapping(string => address) private data;
    string[] private names;
    
    event MagicEvent(string indexed key, address indexed value);
    
    constructor() {
        owner = msg.sender;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "MagicRegistry: not owner");
        _;
    }
    
    function set(string calldata key, address value) external onlyOwner {
        require(value != address(0), "MagicRegistry: zero address");
        data[key] = value;
        names.push(key);
        emit MagicEvent(key, value);
    }
    
    function get(string calldata key) external view returns (address) {
        return data[key];
    }
    
    function getNames() external view returns (string[] memory) {
        return names;
    }
    
    function changeOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "MagicRegistry: zero address");
        owner = newOwner;
    }
}
