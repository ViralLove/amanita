// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ISoulRecovery
 * @dev Минимальный интерфейс SoulRecovery для делегирования из SoulIdentity (SBT-REC-1)
 */
interface ISoulRecovery {
    function setGuardian(uint256 tokenId, address guardian) external;
    function removeGuardian(uint256 tokenId) external;
    function setGuardianFor(uint256 tokenId, address guardian, address owner) external;
    function removeGuardianFor(uint256 tokenId, address owner) external;
    function getGuardian(uint256 tokenId) external view returns (address);
    function initiateRecovery(uint256 tokenId, address newOwner) external;
    function confirmRecovery(uint256 tokenId) external;
    function initiateRecoveryFor(uint256 tokenId, address newOwner, address guardian) external;
    function confirmRecoveryFor(uint256 tokenId, address guardian) external;
    function isRecoveryActive(uint256 tokenId) external view returns (bool);
}
