// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./SoulboundCore.sol";

/**
 * @title SoulMetadata
 * @author Zeya888 (https://zeya888.me)
 * @dev Газоэффективная система метаданных для SoulboundCore токенов
 * @notice Управляет метаданными SBT с оптимизацией storage layout
 */
contract SoulMetadata {
    
    // === СОБЫТИЯ ===
    
    /**
     * @dev Событие обновления метаданных
     * @param tokenId идентификатор токена
     * @param metadataType тип метаданных
     * @param version версия метаданных
     */
    event MetadataUpdated(uint256 indexed tokenId, string metadataType, uint256 version);
    
    /**
     * @dev Событие пакетного обновления метаданных
     * @param tokenIds массив идентификаторов токенов
     * @param count количество обновленных токенов
     */
    event MetadataBatchUpdated(uint256[] tokenIds, uint256 count);
    
    // === СТРУКТУРЫ ДАННЫХ ===
    
    /**
     * @dev Упакованная структура метаданных (оптимизирована для 2 storage slots)
     * Slot 1: metadataType (32 bytes)
     * Slot 2: version (32 bytes) 
     * Slot 3: attributes (32 bytes)
     * Slot 4: ipfsHash (32 bytes)
     */
    struct SoulData {
        string metadataType;    // "identity", "achievement", "reputation" и т.д.
        uint256 version;        // Версия метаданных для отслеживания изменений
        string attributes;      // JSON строка с атрибутами
        string ipfsHash;        // IPFS хеш для дополнительных данных
    }
    
    // === ХРАНИЛИЩЕ ===
    
    // Ссылка на основной SoulboundCore контракт
    SoulboundCore public immutable soulboundCore;
    
    // Mapping от tokenId к метаданным
    mapping(uint256 => SoulData) private _soulData;
    
    // Mapping для отслеживания инициализации метаданных
    mapping(uint256 => bool) private _metadataInitialized;
    
    // === МОДИФИКАТОРЫ ===
    
    /**
     * @dev Проверяет, что токен существует в SoulboundCore
     */
    modifier tokenExists(uint256 tokenId) {
        require(soulboundCore.exists(tokenId), "SoulMetadata: token does not exist");
        _;
    }
    
    /**
     * @dev Проверяет, что вызывающий является владельцем токена или владельцем контракта
     */
    modifier onlyTokenOwnerOrContractOwner(uint256 tokenId) {
        address tokenOwner = soulboundCore.ownerOf(tokenId);
        address contractOwner = soulboundCore.owner();
        require(
            msg.sender == tokenOwner || msg.sender == contractOwner,
            "SoulMetadata: not authorized"
        );
        _;
    }
    
    // === КОНСТРУКТОР ===
    
    constructor(address _soulboundCore) {
        require(_soulboundCore != address(0), "SoulMetadata: invalid address");
        soulboundCore = SoulboundCore(_soulboundCore);
    }
    
    // === ОСНОВНЫЕ ФУНКЦИИ ===
    
    /**
     * @dev Инициализация метаданных для токена
     * @param tokenId идентификатор токена
     * @param metadataType тип метаданных
     * @param attributes JSON строка с атрибутами
     * @param ipfsHash IPFS хеш (опционально)
     */
    function initializeMetadata(
        uint256 tokenId,
        string memory metadataType,
        string memory attributes,
        string memory ipfsHash
    ) external tokenExists(tokenId) onlyTokenOwnerOrContractOwner(tokenId) {
        require(!_metadataInitialized[tokenId], "SoulMetadata: already initialized");
        
        _soulData[tokenId] = SoulData({
            metadataType: metadataType,
            version: 1,
            attributes: attributes,
            ipfsHash: ipfsHash
        });
        
        _metadataInitialized[tokenId] = true;
        
        emit MetadataUpdated(tokenId, metadataType, 1);
    }
    
    /**
     * @dev Обновление метаданных токена
     * @param tokenId идентификатор токена
     * @param attributes новые атрибуты
     * @param ipfsHash новый IPFS хеш (опционально)
     */
    function updateMetadata(
        uint256 tokenId,
        string memory attributes,
        string memory ipfsHash
    ) external tokenExists(tokenId) onlyTokenOwnerOrContractOwner(tokenId) {
        require(_metadataInitialized[tokenId], "SoulMetadata: not initialized");
        
        SoulData storage data = _soulData[tokenId];
        data.attributes = attributes;
        data.ipfsHash = ipfsHash;
        data.version += 1;
        
        emit MetadataUpdated(tokenId, data.metadataType, data.version);
    }
    
    /**
     * @dev Пакетное обновление метаданных
     * @param tokenIds массив идентификаторов токенов
     * @param attributesArray массив атрибутов
     * @param ipfsHashes массив IPFS хешей
     */
    function batchUpdateMetadata(
        uint256[] memory tokenIds,
        string[] memory attributesArray,
        string[] memory ipfsHashes
    ) external {
        require(
            tokenIds.length == attributesArray.length && 
            tokenIds.length == ipfsHashes.length,
            "SoulMetadata: arrays length mismatch"
        );
        require(tokenIds.length <= 50, "SoulMetadata: batch too large");
        
        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];
            
            require(soulboundCore.exists(tokenId), "SoulMetadata: token does not exist");
            require(_metadataInitialized[tokenId], "SoulMetadata: not initialized");
            
            address tokenOwner = soulboundCore.ownerOf(tokenId);
            address contractOwner = soulboundCore.owner();
            require(
                msg.sender == tokenOwner || msg.sender == contractOwner,
                "SoulMetadata: not authorized"
            );
            
            SoulData storage data = _soulData[tokenId];
            data.attributes = attributesArray[i];
            data.ipfsHash = ipfsHashes[i];
            data.version += 1;
        }
        
        emit MetadataBatchUpdated(tokenIds, tokenIds.length);
    }
    
    // === VIEW FUNCTIONS ===
    
    /**
     * @dev Получить метаданные токена
     * @param tokenId идентификатор токена
     * @return SoulData структура с метаданными
     */
    function getMetadata(uint256 tokenId) external view tokenExists(tokenId) returns (SoulData memory) {
        require(_metadataInitialized[tokenId], "SoulMetadata: not initialized");
        return _soulData[tokenId];
    }
    
    /**
     * @dev Проверить, инициализированы ли метаданные
     * @param tokenId идентификатор токена
     * @return true если метаданные инициализированы
     */
    function isInitialized(uint256 tokenId) external view returns (bool) {
        return _metadataInitialized[tokenId];
    }
    
    /**
     * @dev Получить JSON URI для токена (совместимость с OpenSea)
     * @param tokenId идентификатор токена
     * @return JSON строка с метаданными
     */
    function getTokenURI(uint256 tokenId) external view tokenExists(tokenId) returns (string memory) {
        if (!_metadataInitialized[tokenId]) {
            // Возвращаем пустую строку для fallback к базовым метаданным SoulboundCore
            return "";
        }
        
        SoulData memory data = _soulData[tokenId];
        
        // Формируем JSON метаданные
        return string(abi.encodePacked(
            '{"name": "Soul #', _toString(tokenId), 
            '", "description": "Soulbound Token from Amanita Ecosystem",',
            '"type": "', data.metadataType, '",',
            '"version": ', _toString(data.version), ',',
            '"attributes": ', data.attributes,
            bytes(data.ipfsHash).length > 0 ? string(abi.encodePacked(',"ipfs": "', data.ipfsHash, '"')) : '',
            '}'
        ));
    }
    
    /**
     * @dev Получить версию метаданных
     * @param tokenId идентификатор токена
     * @return версия метаданных
     */
    function getMetadataVersion(uint256 tokenId) external view tokenExists(tokenId) returns (uint256) {
        require(_metadataInitialized[tokenId], "SoulMetadata: not initialized");
        return _soulData[tokenId].version;
    }
    
    // === ВНУТРЕННИЕ ФУНКЦИИ ===
    
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
}
