// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";

/**
 * @title AmanitaGovToken
 * @dev Governance-токен на базе ERC20Votes с делегированием и snapshot-голосованием.
 */
contract AmanitaGovToken is ERC20Votes, ERC20Permit, AccessControl {
    /// @notice Роль для аккаунтов, которые могут минтить токены
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    /**
     * @notice Конструктор токена
     * @param admin Адрес администратора, получающего DEFAULT_ADMIN_ROLE и MINTER_ROLE
     */
    constructor(address admin)
        ERC20("Amanita Governance", "AGOV")
        ERC20Permit("Amanita Governance")
    {
        require(admin != address(0), "Admin address required");
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
    }

    /**
     * @notice Минтит токены заданному адресу
     * @param to Получатель токенов
     * @param amount Количество токенов (в wei)
     */
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        _mint(to, amount);
    }

    /// @inheritdoc ERC20Votes
    function _afterTokenTransfer(address from, address to, uint256 amount)
        internal
        override(ERC20, ERC20Votes)
    {
        super._afterTokenTransfer(from, to, amount);
    }

    /// @inheritdoc ERC20Votes
    function _mint(address to, uint256 amount)
        internal
        override(ERC20, ERC20Votes)
    {
        super._mint(to, amount);
    }

    /// @inheritdoc ERC20Votes
    function _burn(address account, uint256 amount)
        internal
        override(ERC20, ERC20Votes)
    {
        super._burn(account, amount);
    }

    /**
     * @notice Проверка поддержки интерфейса (ERC165)
     * @param interfaceId ID интерфейса
     */
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
