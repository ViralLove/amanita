// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ProductRegistry
 * @dev Хранит реестр товаров для децентрализованного маркетплейса Amanita.
 * - Хранит только ссылку (ipfsCID) на JSON-метаданные товара.
 * - Не хранит фото и большие данные on-chain (экономия газа).
 * - Продавцы могут создавать, обновлять, деактивировать свои товары.
 * - Другие пользователи могут читать товары.
 * - Все запросы читаемые (view), минимальный газ.
 */
interface IInviteNFT {
    function isUserActivated(address user) external view returns (bool);
    function isSeller(address user) external view returns (bool);
}

contract ProductRegistry {
    /// @notice Структура товара
    struct Product {
        uint256 id;          // Уникальный идентификатор товара
        address seller;      // Продавец (автор записи)
        string ipfsCID;      // Ссылка на JSON-описание (IPFS CID)
        bool active;         // Активен ли товар
    }

    /// @notice InviteNFT для проверки активации пользователя
    IInviteNFT public inviteNFT;

    /// @notice Конструктор
    /// @param _inviteNFT адрес контракта InviteNFT
    constructor(address _inviteNFT) {
        require(_inviteNFT != address(0), "Invalid InviteNFT address");
        inviteNFT = IInviteNFT(_inviteNFT);
    }

    // Версия каталога продавца
    mapping(address => uint256) public catalogVersion;

    /// @notice Маппинг: productId => Product
    mapping(uint256 => Product) private products;

    /// @notice Счётчик всех товаров (для генерации id)
    uint256 private _productIdCounter;

    /// @notice Маппинг: продавец => список всех productId
    /// Это помогает быстро получить товары продавца (экономия off-chain фильтра)
    mapping(address => uint256[]) private productsBySeller;

    /// @notice Список всех активных товаров (id)
    /// Можно вернуть список всех id для фронтенда — дешевле, чем Product[]
    uint256[] private activeProductIds;

    // --------------------------------
    // ------- События ---------------
    // --------------------------------

    /// @notice Событие: создан новый товар
    event ProductCreated(address indexed seller,
        uint256 productId,
        string ipfsCID,
        uint256 status);

    /// @notice Событие: обновлён товар
    event ProductUpdated(
        address indexed seller,
        uint256 productId,
        string ipfsCID,
        uint256 price,
        uint256 status
    );

    /// @notice Событие: товар деактивирован
    event ProductDeactivated(uint256 indexed productId);

    /// @notice Событие: обновлена версия каталога продавца
    event CatalogUpdated(address indexed seller, uint256 newVersion);

    // --------------------------------
    // ------- Модификаторы ----------
    // --------------------------------

    /**
     * @dev Проверка, что msg.sender — активированный пользователь (InviteNFT).
     */
    modifier onlyActivatedUser() {
        require(inviteNFT.isUserActivated(msg.sender), "Not activated in InviteNFT");
        _;
    }

    /**
     * @dev Проверка, что msg.sender — продавец указанного товара.
     * @param productId id товара
     */
    modifier onlyOwnSellerProduct(uint256 productId) {
        require(products[productId].seller == msg.sender, "Not product seller");
        _;
    }

    // --------------------------------
    // ------- Основные методы -------
    // --------------------------------

    /**
    * @notice Создать новый товар.
    * @dev
    * - Проверяет, что пользователь активирован (InviteNFT).
    * - Проверяет, что CID не пустой и цена > 0.
    * - Генерирует уникальный productId.
    * - Сохраняет товар в маппинг продуктов.
    * - Добавляет productId в общий список активных товаров и в индекс продавца.
    * - Эмиттирует событие ProductCreated для трекинга.
    *
    * Критерии приёмки:
    * - Пользователь активирован.
    * - CID не пустой.
    * - Цена > 0.
    * - Все индексы обновлены (activeProductIds, productsBySeller).
    * - Данные доступны через getProduct, getAllActiveProductIds и getProductsBySeller.
    * - Событие ProductCreated доступно для фронтенда.
    *
    * Эффективность газа:
    * - O(1) операции без циклов.
    * - Минимальные storage-записи (только 3 массива и 1 mapping).
    */
    function createProduct(string calldata ipfsCID) external {
        require(bytes(ipfsCID).length > 0, "ProductRegistry: empty CID");

        // Генерируем новый productId
        _productIdCounter += 1;
        uint256 newProductId = _productIdCounter;

        // Создаём продукт в памяти (неактивный по умолчанию)
        Product memory newProduct = Product({
            id: newProductId,
            seller: msg.sender,
            ipfsCID: ipfsCID,
            active: false
        });

        // Сохраняем в storage
        products[newProductId] = newProduct;

        // НЕ добавляем в список активных товаров (продукт создается неактивным)

        // Добавляем productId в индекс продавца
        productsBySeller[msg.sender].push(newProductId);

        // Эмитим событие для фронтенда (статус 0 - неактивный)
        emit ProductCreated(msg.sender, newProductId, ipfsCID, 0);

        catalogVersion[msg.sender] += 1;
        emit CatalogUpdated(msg.sender, catalogVersion[msg.sender]);
    }


    /**
    * @notice Обновить товар (ipfsCID или цену).
    * @dev
    * - Продавец может обновлять только свой товар.
    * - CID и цена должны быть валидными (не пустой и > 0).
    * - Обновления сохраняются в storage.
    * - Эмиттируется событие ProductUpdated.
    *
    * Acceptance criteria:
    * - Продавец = msg.sender (onlySeller)
    * - CID != пустой, цена > 0
    * - Товар активен (не обновляем архивные)
    * - Поля ipfsCID и price обновлены
    * - Эмиттирован ProductUpdated
    *
    * Gas-эффективность:
    * - Прямой доступ к storage (O(1))
    * - Нет циклов или лишних вычислений
    */
    function updateProduct(uint256 productId, string calldata newIpfsCID, uint256 newPrice) external onlyOwnSellerProduct(productId) {
        require(bytes(newIpfsCID).length > 0, "ProductRegistry: empty CID");
        require(newPrice > 0, "ProductRegistry: price must be > 0");

        Product storage product = products[productId];
        require(product.active, "ProductRegistry: product not active");

        product.ipfsCID = newIpfsCID;

        emit ProductUpdated(msg.sender, productId, newIpfsCID, newPrice, 1);

        catalogVersion[msg.sender] += 1;  // обновляем только для этого продавца
        emit CatalogUpdated(msg.sender, catalogVersion[msg.sender]);
    }

    /**
    * @notice Деактивировать товар (сделать его невидимым в каталоге).
    * @dev
    * - Продавец может деактивировать только свой товар.
    * - Товар должен быть активным.
    * - Статус `active = false`.
    * - Удаляет productId из списка активных товаров через swap-and-pop (газ-эффективно).
    * - Эмиттирует событие ProductDeactivated.
    *
    * Acceptance criteria:
    * - Проверка продавца (onlySeller)
    * - Проверка, что товар активен
    * - Обновлён статус в storage
    * - Удалён из массива активных
    * - Эмиттировано событие
    *
    * Газ-эффективность:
    * - O(n) поиск + O(1) удаление (swap-and-pop)
    * - Никаких лишних storage-переменных
    */
    function deactivateProduct(uint256 productId) external onlyOwnSellerProduct(productId) {
        Product storage product = products[productId];
        require(product.active, "ProductRegistry: already deactivated");

        product.active = false;

        // Удаляем productId из списка активных товаров (экономия газа через swap-and-pop)
        uint256 len = activeProductIds.length;
        for (uint256 i = 0; i < len; i++) {
            if (activeProductIds[i] == productId) {
                // Меняем местами с последним элементом и убираем
                activeProductIds[i] = activeProductIds[len - 1];
                activeProductIds.pop();
                break;
            }
        }

        emit ProductDeactivated(productId);

        catalogVersion[msg.sender] += 1;  // обновляем только для этого продавца
        emit CatalogUpdated(msg.sender, catalogVersion[msg.sender]);
    }

    /**
    * @notice Активировать товар (сделать его видимым в каталоге).
    * @dev
    * - Продавец может активировать только свой товар.
    * - Товар должен быть неактивным.
    * - Статус `active = true`.
    * - Добавляет productId в список активных товаров.
    * - Эмиттирует событие ProductUpdated.
    *
    * Acceptance criteria:
    * - Проверка продавца (onlyOwnSellerProduct)
    * - Проверка, что товар неактивен
    * - Обновлён статус в storage
    * - Добавлен в массив активных
    * - Эмиттировано событие
    *
    * Газ-эффективность:
    * - O(1) операции без циклов
    * - Минимальные storage-операции
    */
    function activateProduct(uint256 productId) external onlyOwnSellerProduct(productId) {
        Product storage product = products[productId];
        require(!product.active, "ProductRegistry: already active");

        product.active = true;

        // Добавляем productId в список активных товаров
        activeProductIds.push(productId);

        emit ProductUpdated(msg.sender, productId, product.ipfsCID, 0, 1);

        catalogVersion[msg.sender] += 1;  // обновляем только для этого продавца
        emit CatalogUpdated(msg.sender, catalogVersion[msg.sender]);
    }

    // --------------------------------
    // ------- View функции ----------
    // --------------------------------

    /**
    * @notice Получить данные товара.
    * @dev
    * - Доступна любому (public view).
    * - Проверяет существование (product.id != 0).
    * - Возвращает полные данные: id, seller, ipfsCID, price, active.
    *
    * Acceptance criteria:
    * - Возвращает существующую структуру Product.
    * - Реверт, если товар не существует.
    *
    * Газ-эффективность:
    * - Только чтение (view).
    * - Никаких циклов или лишних storage-запросов.
    */
    function getProduct(uint256 productId) external view returns (Product memory) {
        Product memory product = products[productId];
        require(product.id != 0, "ProductRegistry: product does not exist");
        return product;
    }

    /**
    * @notice Получить список id всех активных товаров.
    * @dev
    * - Публичная view-функция.
    * - Отдаёт snapshot массива activeProductIds.
    * - Экономично по газу (только чтение, нет циклов).
    *
    * Acceptance criteria:
    * - Отдаёт все id активных товаров (актуально в момент запроса).
    * - Прозрачность — любой может получить каталог.
    *
    * Газ-эффективность:
    * - O(1) чтение ссылки на storage-массив (view → memory).
    * - Нет вычислений/фильтрации.
    */
    function getAllActiveProductIds() external view returns (uint256[] memory) {
        return activeProductIds;
    }
    
    /**
    * @notice Получить список id всех товаров продавца.
    * @dev
    * - Public view.
    * - Не фильтрует по active — возвращает все товары (для прозрачности и истории).
    * - Лёгкое, дешёвое по газу (view → memory).
    *
    * Acceptance criteria:
    * - Возвращает массив id всех товаров продавца.
    * - Прозрачность — любой может получить историю продаж.
    *
    * Газ-эффективность:
    * - O(1) чтение ссылки на storage-массив.
    * - Никаких вычислений внутри функции.
    */
    function getProductsBySeller(address seller) external view returns (uint256[] memory) {
        return productsBySeller[seller];
    }

    /**
    * @notice Получить версию каталога продавца.
    * @dev
    * - Public view.
    * - Возвращает текущую версию каталога номер которой увеличивается при каждом 
    * обновлении или добавлении любого товара.
    *
    */
    function getMyCatalogVersion() external view returns (uint256) {
        require(inviteNFT.isSeller(msg.sender), "Not a seller");
        return catalogVersion[msg.sender];
    }

    /**
    * @notice Получить все товары продавца вместе со структурой Product.
    * @dev
    * - Public view.
    * - Возвращает все товары продавца.
    *
    */
    /**
    * @notice Получить все товары продавца вместе со структурой Product.
    * @dev
    * - Public view.
    * - Возвращает все товары продавца.
    */
    function getProductsBySellerFull() external view returns (Product[] memory) {
        require(inviteNFT.isSeller(msg.sender), "Not a seller");

        uint256[] memory sellerProductIds = productsBySeller[msg.sender];
        Product[] memory sellerProducts = new Product[](sellerProductIds.length);
        for (uint256 i = 0; i < sellerProductIds.length; i++) {
            sellerProducts[i] = products[sellerProductIds[i]];
        }
        return sellerProducts;
    }

}
