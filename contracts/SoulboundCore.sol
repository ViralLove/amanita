// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/IERC721Metadata.sol";
import "@openzeppelin/contracts/utils/introspection/IERC165.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./IERC5192.sol";

/**
 * @dev Интерфейс для контракта метаданных
 */
interface ISoulMetadata {
    function getTokenURI(uint256 tokenId) external view returns (string memory);
}

/**
 * @dev Интерфейс для контракта восстановления
 */
interface ISoulRecovery {
    function canConfirmRecovery(uint256 tokenId) external view returns (bool);
}

/**
 * @dev Интерфейс для контракта интеграции
 */
interface ISoulIntegration {
    function notifySoulCreated(uint256 tokenId, address owner) external;
    function notifySoulRecovered(uint256 tokenId, address oldOwner, address newOwner) external;
}

/**
 * @title SoulboundCore
 * @author Zeya888 (https://zeya888.me)
 * @dev Минимальная, газоэффективная реализация Soulbound Token согласно EIP-5192
 * @notice Всегда заблокированные токены - нет дополнительных проверок для экономии газа
 */
contract SoulboundCore is IERC165, IERC721, IERC721Metadata, IERC5192, Ownable, AccessControl {

    /// @dev Роль минтера: только контракт SpiralEngine (proxy) может минтить души при активации (SBT-INV-1.1).
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    // === СОБЫТИЯ ===
    
    /**
     * @dev Событие при минтинге SBT токена
     * @param to получатель токена
     * @param tokenId идентификатор токена
     */
    event SoulMinted(address indexed to, uint256 indexed tokenId);
    
    /**
     * @dev Событие при сжигании SBT токена
     * @param tokenId идентификатор токена
     */
    event SoulBurned(uint256 indexed tokenId);
    
    // === ХРАНИЛИЩЕ ===
    
    string private _name;
    string private _symbol;
    uint256 private _nextTokenId = 1;
    uint256 private _totalSupply = 0;
    
    // Mapping от tokenId к владельцу
    mapping(uint256 => address) private _owners;
    
    // Mapping от адреса к количеству токенов
    mapping(address => uint256) private _balances;
    
    // Адрес контракта метаданных (опционально)
    address private _metadataContract;
    
    // Адрес контракта восстановления (опционально)
    address private _recoveryContract;
    
    // Адрес контракта интеграции (опционально)
    address private _integrationContract;
    
    // === КОНСТРУКТОР ===
    
    constructor(string memory name_, string memory symbol_) Ownable(msg.sender) {
        _name = name_;
        _symbol = symbol_;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }
    
    // === ERC721 VIEW FUNCTIONS ===
    
    function name() public view override returns (string memory) {
        return _name;
    }
    
    function symbol() public view override returns (string memory) {
        return _symbol;
    }
    
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        require(_owners[tokenId] != address(0), "ERC721: invalid token ID");
        
        // Если контракт метаданных установлен, используем его
        if (_metadataContract != address(0)) {
            try ISoulMetadata(_metadataContract).getTokenURI(tokenId) returns (string memory uri) {
                // Если метаданные пустые, используем базовые
                if (bytes(uri).length > 0) {
                    return uri;
                }
                return _getDefaultTokenURI(tokenId);
            } catch {
                // Fallback к базовым метаданным при ошибке
                return _getDefaultTokenURI(tokenId);
            }
        }
        
        // Базовые метаданные без внешнего контракта
        return _getDefaultTokenURI(tokenId);
    }
    
    function balanceOf(address owner) public view override returns (uint256) {
        require(owner != address(0), "ERC721: address zero is not a valid owner");
        return _balances[owner];
    }
    
    function ownerOf(uint256 tokenId) public view override returns (address) {
        return _requireOwned(tokenId);
    }
    
    function supportsInterface(bytes4 interfaceId) public view override(IERC165, AccessControl) returns (bool) {
        return interfaceId == type(IERC165).interfaceId ||
               interfaceId == type(IERC721).interfaceId ||
               interfaceId == type(IERC721Metadata).interfaceId ||
               interfaceId == type(IERC5192).interfaceId ||
               super.supportsInterface(interfaceId);
    }
    
    // === SBT CORE FUNCTIONS ===
    
    /**
     * @dev SBT токены заблокированы навсегда - всегда возвращает true
     * @return true всегда
     */
    function locked(uint256 /* tokenId */) external pure override returns (bool) {
        return true;
    }
    
    /**
     * @dev SBT токены не могут быть одобрены - всегда revert
     */
    function approve(address /* to */, uint256 /* tokenId */) public pure override {
        revert("SBT: approval not allowed");
    }
    
    /**
     * @dev SBT токены не могут быть одобрены глобально - всегда revert
     */
    function setApprovalForAll(address /* operator */, bool /* approved */) public pure override {
        revert("SBT: approval not allowed");
    }
    
    /**
     * @dev SBT токены не имеют одобренных операторов - всегда возвращает address(0)
     * @return address(0) всегда
     */
    function getApproved(uint256 /* tokenId */) public pure override returns (address) {
        return address(0);
    }
    
    /**
     * @dev SBT токены не имеют глобальных одобрений - всегда возвращает false
     * @return false всегда
     */
    function isApprovedForAll(address /* owner */, address /* operator */) public pure override returns (bool) {
        return false;
    }
    
    // === TRANSFER FUNCTIONS ===
    
    /**
     * @dev SBT токены не могут быть переданы - всегда revert
     */
    function transferFrom(address /* from */, address /* to */, uint256 /* tokenId */) public pure override {
        revert("SBT: transfer not allowed");
    }
    
    /**
     * @dev SBT токены не могут быть безопасно переданы - всегда revert
     */
    function safeTransferFrom(address /* from */, address /* to */, uint256 /* tokenId */) public pure override {
        revert("SBT: transfer not allowed");
    }
    
    /**
     * @dev SBT токены не могут быть безопасно переданы с данными - всегда revert
     */
    function safeTransferFrom(address /* from */, address /* to */, uint256 /* tokenId */, bytes memory /* data */) public pure override {
        revert("SBT: transfer not allowed");
    }
    
    // === MINTING FUNCTIONS ===
    
    /**
     * @dev Минтинг SBT токена (владелец контракта или держатель MINTER_ROLE, например SpiralEngine)
     * @param to получатель токена
     * @return tokenId идентификатор созданного токена
     */
    function mintSoul(address to) external returns (uint256) {
        require(owner() == msg.sender || hasRole(MINTER_ROLE, msg.sender), "SBT: not owner or minter");
        uint256 tokenId = _nextTokenId++;
        
        _safeMint(to, tokenId);
        
        emit SoulMinted(to, tokenId);
        emit Locked(tokenId);
        
        // Уведомление интеграционного контракта (опционально)
        _notifyIntegration(tokenId, to, "created");
        
        return tokenId;
    }
    
    /**
     * @dev Массовый минтинг SBT токенов (владелец контракта или держатель MINTER_ROLE)
     * @param to получатель токенов
     * @param amount количество токенов для минтинга
     * @return tokenIds массив идентификаторов созданных токенов
     */
    function mintSoulBatch(address to, uint256 amount) external returns (uint256[] memory) {
        require(owner() == msg.sender || hasRole(MINTER_ROLE, msg.sender), "SBT: not owner or minter");
        require(amount > 0 && amount <= 100, "SBT: invalid amount");
        
        uint256[] memory tokenIds = new uint256[](amount);
        
        for (uint256 i = 0; i < amount; i++) {
            uint256 tokenId = _nextTokenId++;
            
            _safeMint(to, tokenId);
            
            emit SoulMinted(to, tokenId);
            emit Locked(tokenId);
            
            // Уведомление интеграционного контракта (опционально)
            _notifyIntegration(tokenId, to, "created");
            
            tokenIds[i] = tokenId;
        }
        
        return tokenIds;
    }
    
    // === BURNING FUNCTIONS ===
    
    /**
     * @dev Сжигание SBT токена (только владелец токена или владелец контракта)
     * @param tokenId идентификатор токена для сжигания
     */
    function burnSoul(uint256 tokenId) external {
        require(
            _isAuthorized(ownerOf(tokenId), msg.sender, tokenId) || msg.sender == owner(),
            "SBT: not authorized to burn"
        );
        
        _burn(tokenId);
        
        emit SoulBurned(tokenId);
    }
    
    // === VIEW FUNCTIONS ===
    
    /**
     * @dev Получить следующий доступный tokenId
     * @return следующий tokenId
     */
    function getNextTokenId() external view returns (uint256) {
        return _nextTokenId;
    }
    
    /**
     * @dev Получить общее количество заминченных токенов
     * @return количество токенов
     */
    function getTotalSupply() external view returns (uint256) {
        return _totalSupply;
    }
    
    /**
     * @dev Проверить, существует ли токен
     * @param tokenId идентификатор токена
     * @return true если токен существует
     */
    function exists(uint256 tokenId) external view returns (bool) {
        return _owners[tokenId] != address(0);
    }
    
    // === METADATA MANAGEMENT ===
    
    /**
     * @dev Установить адрес контракта метаданных (только владелец)
     * @param metadataContract адрес контракта метаданных
     */
    function setMetadataContract(address metadataContract) external onlyOwner {
        _metadataContract = metadataContract;
    }
    
    /**
     * @dev Получить адрес контракта метаданных
     * @return адрес контракта метаданных
     */
    function getMetadataContract() external view returns (address) {
        return _metadataContract;
    }
    
    /**
     * @dev Установить адрес контракта восстановления (только владелец)
     * @param recoveryContract адрес контракта восстановления
     */
    function setRecoveryContract(address recoveryContract) external onlyOwner {
        _recoveryContract = recoveryContract;
    }
    
    /**
     * @dev Получить адрес контракта восстановления
     * @return адрес контракта восстановления
     */
    function getRecoveryContract() external view returns (address) {
        return _recoveryContract;
    }
    
    /**
     * @dev Установить адрес контракта интеграции (только владелец)
     * @param integrationContract адрес контракта интеграции
     */
    function setIntegrationContract(address integrationContract) external onlyOwner {
        _integrationContract = integrationContract;
    }
    
    /**
     * @dev Получить адрес контракта интеграции
     * @return адрес контракта интеграции
     */
    function getIntegrationContract() external view returns (address) {
        return _integrationContract;
    }
    
    /**
     * @dev Выполнить восстановление токена (только recovery контракт)
     * @param tokenId идентификатор токена
     * @param newOwner новый владелец
     */
    function executeRecovery(uint256 tokenId, address newOwner) external {
        require(msg.sender == _recoveryContract, "SoulboundCore: not recovery contract");
        require(_recoveryContract != address(0), "SoulboundCore: no recovery contract");
        require(_owners[tokenId] != address(0), "ERC721: invalid token ID");
        require(newOwner != address(0), "SoulboundCore: invalid new owner");
        
        // Проверяем, что recovery контракт подтверждает возможность восстановления
        require(
            ISoulRecovery(_recoveryContract).canConfirmRecovery(tokenId),
            "SoulboundCore: recovery not confirmed"
        );
        
        address oldOwner = _owners[tokenId];
        
        // Обновляем владение
        _balances[oldOwner] -= 1;
        _balances[newOwner] += 1;
        _owners[tokenId] = newOwner;
        
        emit Transfer(oldOwner, newOwner, tokenId);
        
        // Уведомление интеграционного контракта о восстановлении (опционально)
        _notifyIntegrationRecovery(tokenId, oldOwner, newOwner);
    }
    
    // === INTERNAL FUNCTIONS ===
    
    function _requireOwned(uint256 tokenId) internal view returns (address) {
        address owner = _owners[tokenId];
        require(owner != address(0), "ERC721: invalid token ID");
        return owner;
    }
    
    function _safeMint(address to, uint256 tokenId) internal {
        _mint(to, tokenId);
        require(_checkOnERC721Received(address(0), to, tokenId, ""), "ERC721: transfer to non ERC721Receiver implementer");
    }
    
    function _mint(address to, uint256 tokenId) internal {
        require(to != address(0), "ERC721: mint to the zero address");
        require(_owners[tokenId] == address(0), "ERC721: token already minted");
        
        _balances[to] += 1;
        _owners[tokenId] = to;
        _totalSupply += 1;
        
        emit Transfer(address(0), to, tokenId);
    }
    
    function _burn(uint256 tokenId) internal {
        address owner = ownerOf(tokenId);
        
        _balances[owner] -= 1;
        delete _owners[tokenId];
        _totalSupply -= 1;
        
        emit Transfer(owner, address(0), tokenId);
    }
    
    function _isAuthorized(address owner, address spender, uint256 tokenId) internal view returns (bool) {
        return (spender == owner || isApprovedForAll(owner, spender) || getApproved(tokenId) == spender);
    }
    
    /**
     * @dev Генерация базовых метаданных для токена
     * @param tokenId идентификатор токена
     * @return JSON строка с базовыми метаданными
     */
    function _getDefaultTokenURI(uint256 tokenId) internal view returns (string memory) {
        return string(abi.encodePacked(
            '{"name": "Soul #', _toString(tokenId), 
            '", "description": "Soulbound Token from Amanita Ecosystem",',
            '"type": "basic",',
            '"version": 1,',
            '"attributes": []',
            '}'
        ));
    }
    
    /**
     * @dev Преобразование uint256 в string
     * @param value число для преобразования
     * @return строковое представление числа
     */
    function _toString(uint256 value) internal pure returns (string memory) {
        if (value == 0) {
            return "0";
        }
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + uint256(value % 10)));
            value /= 10;
        }
        return string(buffer);
    }
    
    function _checkOnERC721Received(address from, address to, uint256 tokenId, bytes memory data) internal returns (bool) {
        if (to.code.length > 0) {
            try IERC721Receiver(to).onERC721Received(msg.sender, from, tokenId, data) returns (bytes4 retval) {
                return retval == IERC721Receiver.onERC721Received.selector;
            } catch (bytes memory reason) {
                if (reason.length == 0) {
                    revert("ERC721: transfer to non ERC721Receiver implementer");
                } else {
                    assembly {
                        revert(add(32, reason), mload(reason))
                    }
                }
            }
        } else {
            return true;
        }
    }
    
    /**
     * @dev Внутренняя функция для уведомления интеграционного контракта
     * @param tokenId идентификатор токена
     * @param owner владелец токена
     */
    function _notifyIntegration(uint256 tokenId, address owner, string memory /* eventType */) internal {
        if (_integrationContract != address(0)) {
            try ISoulIntegration(_integrationContract).notifySoulCreated(tokenId, owner) {
                // Успешное уведомление, ничего не делаем
            } catch {
                // Graceful degradation - игнорируем ошибки интеграции
            }
        }
    }
    
    /**
     * @dev Внутренняя функция для уведомления о восстановлении
     * @param tokenId идентификатор токена
     * @param oldOwner предыдущий владелец
     * @param newOwner новый владелец
     */
    function _notifyIntegrationRecovery(uint256 tokenId, address oldOwner, address newOwner) internal {
        if (_integrationContract != address(0)) {
            try ISoulIntegration(_integrationContract).notifySoulRecovered(tokenId, oldOwner, newOwner) {
                // Успешное уведомление, ничего не делаем
            } catch {
                // Graceful degradation - игнорируем ошибки интеграции
            }
        }
    }
}