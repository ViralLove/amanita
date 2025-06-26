// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AmanitaRegistry
 * @dev Универсальный on-chain-реестр адресов контрактов экосистемы Amanita.
 */
contract AmanitaRegistry {
    address public owner;

    mapping(string => address) private addresses;
    string[] private contractNames; // список всех имён (ключей)

    event AddressUpdated(string indexed name, address indexed newAddress);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "AmanitaRegistry: not owner");
        _;
    }

    /**
     * @notice Добавить или обновить адрес контракта.
     * @param name Человеко-читаемое имя (например, "InviteNFT")
     * @param newAddress Новый адрес контракта.
     */
    function setAddress(string calldata name, address newAddress) external onlyOwner {
        require(newAddress != address(0), "AmanitaRegistry: zero address");

        // Если это новый ключ, сохраняем имя в массив
        if (addresses[name] == address(0)) {
            contractNames.push(name);
        }

        addresses[name] = newAddress;
        emit AddressUpdated(name, newAddress);
    }

    /**
     * @notice Получить адрес контракта по имени.
     * @param name Имя контракта.
     */
    function getAddress(string calldata name) external view returns (address) {
        return addresses[name];
    }

    /**
     * @notice Получить список всех имён контрактов, зарегистрированных в реестре.
     * @return Список имён (ключей).
     */
    function getAllContractNames() external view returns (string[] memory) {
        return contractNames;
    }

    /**
     * @notice Передать права управления (новому owner).
     * @param newOwner Новый адрес владельца.
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "AmanitaRegistry: zero address");
        owner = newOwner;
    }
}
