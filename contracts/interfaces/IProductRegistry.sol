// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

/**
 * @title IProductRegistry
 * @author Zeya888 (https://zeya888.me)
 * @notice Интерфейс для ProductRegistry контракта
 * @dev Определяет публичный API для управления каталогом продуктов
 * 
 * Основные функции:
 * - Создание, обновление, активация, деактивация продуктов
 * - Получение списка продуктов продавца
 * - Очистка каталога продавца
 * - Интеграция с SpiralEngine для проверки ролей
 * 
 * @custom:security-contact security@amanita.com
 */
interface IProductRegistry {
    
    // ================================
    // ========== СТРУКТУРЫ ===========
    // ================================
    
    /**
     * @notice Структура товара
     * @param id Уникальный идентификатор товара
     * @param seller Адрес продавца (владельца товара)
     * @param ipfsCID IPFS CID с метаданными товара
     * @param active Активен ли товар в каталоге
     */
    struct Product {
        uint256 id;
        address seller;
        string ipfsCID;
        bool active;
    }
    
    // ================================
    // =========== СОБЫТИЯ ============
    // ================================
    
    /**
     * @notice Событие создания нового продукта
     * @param seller Адрес продавца
     * @param productId ID созданного продукта
     * @param ipfsCID IPFS CID с метаданными
     * @param status Статус продукта (0 - неактивный, 1 - активный)
     */
    event ProductCreated(
        address indexed seller,
        uint256 productId,
        string ipfsCID,
        uint256 status
    );
    
    /**
     * @notice Событие обновления продукта
     * @param seller Адрес продавца
     * @param productId ID обновлённого продукта
     * @param ipfsCID Новый IPFS CID с метаданными
     * @param price Цена (для совместимости, может быть 0)
     * @param status Новый статус продукта (0 - неактивный, 1 - активный)
     */
    event ProductUpdated(
        address indexed seller,
        uint256 productId,
        string ipfsCID,
        uint256 price,
        uint256 status
    );
    
    /**
     * @notice Событие деактивации продукта
     * @param productId ID деактивированного продукта
     */
    event ProductDeactivated(uint256 indexed productId);
    
    /**
     * @notice Событие обновления версии каталога продавца
     * @param seller Адрес продавца
     * @param newVersion Новый номер версии каталога
     */
    event CatalogUpdated(address indexed seller, uint256 newVersion);
    
    /**
     * @notice Событие полной очистки каталога продавца
     * @param seller Адрес продавца
     * @param productsCleared Количество удалённых продуктов
     */
    event CatalogCleared(address indexed seller, uint256 productsCleared);
    
    /**
     * @notice Событие обновления адреса SpiralEngine контракта
     * @param oldSpiralEngine Старый адрес SpiralEngine
     * @param newSpiralEngine Новый адрес SpiralEngine
     */
    event SpiralEngineUpdated(
        address indexed oldSpiralEngine,
        address indexed newSpiralEngine
    );
    
    // ================================
    // ======= ОСНОВНЫЕ ФУНКЦИИ =======
    // ================================
    
    /**
     * @notice Создать новый продукт
     * @param ipfsCID IPFS CID с метаданными товара
     * @return productId ID созданного продукта
     * @dev Требует: активированный продавец с SELLER_ROLE
     * @dev Создаёт продукт в неактивном состоянии
     */
    function createProduct(string calldata ipfsCID) external returns (uint256 productId);
    
    /**
     * @notice Обновить существующий продукт
     * @param productId ID продукта для обновления
     * @param newIpfsCID Новый IPFS CID с метаданными
     * @param newPrice Новая цена (для совместимости)
     * @dev Требует: msg.sender = seller продукта
     * @dev Продукт должен быть активным
     */
    function updateProduct(
        uint256 productId,
        string calldata newIpfsCID,
        uint256 newPrice
    ) external;
    
    /**
     * @notice Деактивировать продукт
     * @param productId ID продукта для деактивации
     * @dev Требует: msg.sender = seller продукта
     * @dev Продукт должен быть активным
     * @dev Удаляет продукт из списка активных (swap-and-pop)
     */
    function deactivateProduct(uint256 productId) external;
    
    /**
     * @notice Активировать продукт
     * @param productId ID продукта для активации
     * @dev Требует: msg.sender = seller продукта
     * @dev Продукт должен быть неактивным
     * @dev Добавляет продукт в список активных
     */
    function activateProduct(uint256 productId) external;
    
    /**
     * @notice Полностью очистить каталог продавца
     * @param seller Адрес продавца
     * @dev Требует: msg.sender = seller (можно очистить только свой каталог)
     * @dev Требует: seller имеет SELLER_ROLE
     * @dev Удаляет все продукты продавца из всех индексов
     * @dev Лимит: максимум 10000 продуктов за одну транзакцию
     */
    function clearSellerCatalog(address seller) external;
    
    // ================================
    // ======== VIEW ФУНКЦИИ ==========
    // ================================
    
    /**
     * @notice Получить данные продукта
     * @param productId ID продукта
     * @return product Структура Product с полными данными
     * @dev Ревертится если продукт не существует
     */
    function getProduct(uint256 productId) external view returns (Product memory product);
    
    /**
     * @notice Получить список ID всех активных продуктов
     * @return productIds Массив ID активных продуктов
     * @dev Возвращает snapshot на момент вызова
     */
    function getAllActiveProductIds() external view returns (uint256[] memory productIds);
    
    /**
     * @notice Получить список ID всех продуктов продавца
     * @param seller Адрес продавца
     * @return productIds Массив ID всех продуктов продавца (активных и неактивных)
     */
    function getProductsBySeller(address seller) external view returns (uint256[] memory productIds);
    
    /**
     * @notice Получить версию каталога текущего продавца
     * @return version Номер версии каталога
     * @dev Требует: msg.sender имеет SELLER_ROLE
     * @dev Версия увеличивается при каждом изменении каталога
     */
    function getMyCatalogVersion() external view returns (uint256 version);
    
    /**
     * @notice Получить полные данные всех продуктов текущего продавца
     * @return products Массив структур Product
     * @dev Требует: msg.sender имеет SELLER_ROLE
     * @dev Возвращает все продукты (активные и неактивные)
     */
    function getProductsBySellerFull() external view returns (Product[] memory products);
    
    // ================================
    // ======= ADMIN ФУНКЦИИ ==========
    // ================================
    
    /**
     * @notice Установить новый адрес SpiralEngine контракта
     * @param _spiralEngine Адрес нового SpiralEngine контракта
     * @dev Требует: ADMIN_ROLE
     * @dev Эмитирует событие SpiralEngineUpdated
     */
    function setSpiralEngine(address _spiralEngine) external;
}
