// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IERC5192
 * @dev Интерфейс для Soulbound Token (SBT) согласно EIP-5192
 * @notice Этот интерфейс определяет стандарт для непередаваемых токенов
 */
interface IERC5192 {
    /**
     * @dev Событие, эмитируемое при блокировке токена
     * @param tokenId идентификатор заблокированного токена
     */
    event Locked(uint256 indexed tokenId);

    /**
     * @dev Проверяет, заблокирован ли токен
     * @param tokenId идентификатор токена для проверки
     * @return true если токен заблокирован, false иначе
     * @notice Для SBT токенов всегда должно возвращать true
     */
    function locked(uint256 tokenId) external view returns (bool);
}
