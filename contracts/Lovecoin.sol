// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title Lovecoin
 * @dev Основной токен экосистемы Amanita для социального майнинга через суперлайки.
 * Утилити токен для Loveconomy.
 */
contract Lovecoin is ERC20, AccessControl {
    /// @notice Роль для эмиссии токенов
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    /// @notice Начальное предложение токенов
    uint256 public constant INITIAL_SUPPLY = 888_888_888 ether;

    /**
     * @notice Конструктор создает Lovecoin токен с начальной эмиссией
     * @param owner Адрес владельца, который получает начальную эмиссию и роли
     */
    constructor(address owner) ERC20("Lovecoin", "LOVECOIN") {
        require(owner != address(0), "Lovecoin: owner cannot be zero address");
        
        // Минтим начальную эмиссию владельцу
        _mint(owner, INITIAL_SUPPLY);
        
        // Назначаем роли владельцу
        _grantRole(DEFAULT_ADMIN_ROLE, owner);
        _grantRole(MINTER_ROLE, owner);
    }

    /**
     * @notice Возвращает количество децималей (18)
     * @return Количество децималей токена
     */
    function decimals() public view virtual override returns (uint8) {
        return 18;
    }

    /**
     * @notice Минтит новые токены (только для MINTER_ROLE)
     * @param to Адрес получателя токенов
     * @param amount Количество токенов для минта
     */
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        require(to != address(0), "Lovecoin: mint to zero address");
        require(amount > 0, "Lovecoin: mint amount must be positive");
        
        _mint(to, amount);
    }

    /**
     * @notice Сжигает токены с указанного адреса (только для MINTER_ROLE)
     * @param from Адрес, с которого сжигаются токены
     * @param amount Количество токенов для сжигания
     */
    function burn(address from, uint256 amount) external onlyRole(MINTER_ROLE) {
        require(from != address(0), "Lovecoin: burn from zero address");
        require(amount > 0, "Lovecoin: burn amount must be positive");
        require(balanceOf(from) >= amount, "Lovecoin: burn amount exceeds balance");
        
        _burn(from, amount);
    }

    /**
     * @notice Поддержка интерфейсов для совместимости
     * @param interfaceId Идентификатор интерфейса
     * @return true если интерфейс поддерживается
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
