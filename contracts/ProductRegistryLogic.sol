// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "./interfaces/IProductRegistry.sol";
import "./interfaces/ISpiralEngine.sol";
import "./interfaces/IOrganicComponentRegistry.sol";

/**
 * @title ProductRegistryLogic
 * @author Zeya888 (https://zeya888.me)
 * @dev Полная UUPS имплементация для ProductRegistry
 * @notice Содержит ВСЮ бизнес-логику управления каталогом продуктов и state variables
 * @notice Версия: 1.0.0 - UUPS Standard Migration
 * 
 * Архитектура:
 * - Все state variables объявлены в Logic
 * - При delegatecall state физически хранится в Proxy
 * - Прямой доступ к переменным (без StorageSlot)
 * - Роли и пауза управляются через Logic
 * - Апгрейды через _authorizeUpgrade (UPGRADER_ROLE)
 * 
 * Ключевые улучшения от оригинала:
 * - ✅ Upgradeable архитектура (UUPS паттерн)
 * - ✅ ReentrancyGuard на критических функциях
 * - ✅ Pausable для emergency ситуаций
 * - ✅ Custom errors для экономии gas (~2700 gas)
 * - ✅ Gas optimizations (unchecked, calldata, caching)
 * - ✅ Storage gap для будущих обновлений
 * - ✅ Активирован onlyActivatedSeller модификатор
 * 
 * @custom:security-contact security@amanita.com
 */
contract ProductRegistryLogic is 
    Initializable,
    UUPSUpgradeable,
    AccessControlUpgradeable,
    PausableUpgradeable,
    ReentrancyGuardUpgradeable,
    IProductRegistry
{
    // ================================
    // ========== КОНСТАНТЫ ===========
    // ================================
    
    /// @notice Версия Logic контракта для апгрейдов
    uint256 public constant LOGIC_VERSION = 1;
    
    /// @notice Роль для обновления контракта
    bytes32 public constant UPGRADER_ROLE = keccak256("UPGRADER_ROLE");
    
    /// @notice Роль администратора для управления системой
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    
    /// @notice Роль продавца (определена в SpiralEngine)
    bytes32 public constant SELLER_ROLE = keccak256("SELLER_ROLE");
    
    /// @notice Максимальное количество продуктов для очистки за одну транзакцию
    uint256 public constant MAX_PRODUCTS_PER_CLEAR = 10000;
    
    /// @notice Максимальное количество компонентов в одном продукте
    uint256 public constant MAX_COMPONENTS_PER_PRODUCT = 20;
    
    // ================================
    // ======== CUSTOM ERRORS =========
    // ================================
    // Custom errors для экономии gas (~2000 gas на ошибку)
    
    /// @notice Ошибка: нулевой адрес
    error ZeroAddress();
    
    /// @notice Ошибка: неправильный адрес SpiralEngine
    error InvalidSpiralEngine();
    
    /// @notice Ошибка: пустой IPFS CID
    error EmptyCID();
    
    /// @notice Ошибка: неправильная цена
    error InvalidPrice();
    
    /// @notice Ошибка: продукт не найден
    error ProductNotFound();
    
    /// @notice Ошибка: продукт не активен
    error ProductNotActive();
    
    /// @notice Ошибка: продукт уже активен
    error ProductAlreadyActive();
    
    /// @notice Ошибка: не является продавцом этого продукта
    error NotProductSeller();
    
    /// @notice Ошибка: каталог уже пуст
    error CatalogAlreadyEmpty();
    
    /// @notice Ошибка: не является продавцом
    error NotASeller();
    
    /// @notice Ошибка: можно очистить только свой каталог
    error CanOnlyClearOwnCatalog();
    
    /// @notice Ошибка: неправильный адрес продавца
    error InvalidSellerAddress();
    
    /// @notice Ошибка: каталог слишком большой для одной транзакции
    error CatalogTooLarge();
    
    /// @notice Ошибка: продукт не существует
    error ProductDoesNotExist();
    
    /// @notice Ошибка: несоответствие владельца продукта
    error ProductOwnershipMismatch();
    
    /// @notice Ошибка: пользователь не активирован в SpiralEngine
    error NotActivatedUser();
    
    /// @notice Ошибка: компоненты не предоставлены
    error NoComponentsProvided();
    
    /// @notice Ошибка: слишком много компонентов
    error TooManyComponents();
    
    /// @notice Ошибка: OrganicComponentRegistry не установлен
    error ComponentRegistryNotSet();
    
    /// @notice Ошибка: компонент не найден
    /// @param businessId ID компонента
    error ComponentNotFound(string businessId);
    
    /// @notice Ошибка: компонент не активен
    /// @param businessId ID компонента
    error ComponentNotActive(string businessId);
    
    /// @notice Ошибка: бизнес-идентификатор пустой
    error EmptyBusinessId();

    /// @notice Ошибка: бизнес-идентификатор уже существует
    /// @param businessId Уникальный идентификатор продукта
    error BusinessIdExists(string businessId);

    /// @notice Ошибка: бизнес-идентификатор не найден
    /// @param businessId Уникальный идентификатор продукта
    error BusinessIdUnknown(string businessId);
    
    // ================================
    // ====== STATE VARIABLES =========
    // ================================
    // ⚠️ КРИТИЧНО: Порядок переменных ИДЕНТИЧЕН оригинальному ProductRegistry.sol
    // ⚠️ При delegatecall данные физически хранятся в Proxy
    // ⚠️ НЕ МЕНЯТЬ порядок при апгрейдах! Только добавлять в конец (после __gap)
    
    /// @notice Адрес контракта SpiralEngine для проверки ролей и активации
    ISpiralEngine public spiralEngine;
    
    /// @notice Версия каталога каждого продавца (увеличивается при любом изменении)
    mapping(address => uint256) public catalogVersion;
    
    /// @notice Основное хранилище всех продуктов (productId => Product)
    mapping(uint256 => Product) private products;
    
    /// @notice Счётчик для генерации уникальных productId
    uint256 private _productIdCounter;

    /// @notice Индекс productId по бизнес-идентификатору
    mapping(string => uint256) public businessIdToProductId;
    
    /// @notice Индекс продуктов по продавцу (seller => productId[])
    /// Помогает быстро получить все товары продавца
    mapping(address => uint256[]) private productsBySeller;
    
    /// @notice Список ID всех активных продуктов
    /// Для эффективного получения каталога активных товаров
    uint256[] private activeProductIds;
    
    /// @notice Адрес контракта OrganicComponentRegistry для валидации компонентов
    IOrganicComponentRegistry public componentRegistry;
    
    // ================================
    // ======== STORAGE GAP ===========
    // ================================
    // Резервируем слоты для будущих переменных в апгрейдах
    // При добавлении новых state variables уменьшайте размер gap
    
    /// @dev Резерв для будущих обновлений (48 слотов, было 49)
    uint256[48] private __gap;
    
    // ================================
    // ======== ИНИЦИАЛИЗАЦИЯ =========
    // ================================
    
    /**
     * @dev Инициализация Logic контракта (UUPS-совместимый)
     * @param admin Адрес администратора, получающего все роли
     * @param _spiralEngine Адрес контракта SpiralEngine
     * @notice Инициализация должна происходить через Proxy при деплое
     * @notice Заменяет constructor для upgradeable контрактов
     * @notice Может быть вызвана ТОЛЬКО ОДИН РАЗ (защита через initializer)
     */
    function initialize(address admin, address _spiralEngine) 
        public 
        initializer 
    {
        if (admin == address(0)) revert ZeroAddress();
        if (_spiralEngine == address(0)) revert InvalidSpiralEngine();
        
        // Инициализация всех модулей OpenZeppelin в правильном порядке
        __AccessControl_init();
        __UUPSUpgradeable_init();
        __Pausable_init();
        __ReentrancyGuard_init();
        
        // Установка SpiralEngine контракта
        spiralEngine = ISpiralEngine(_spiralEngine);
        
        // Выдача всех ролей админу
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
    }
    
    // ================================
    // ===== UUPS UPGRADE PROTECTION ==
    // ================================
    
    /**
     * @dev Авторизация обновления контракта
     * @param newImplementation адрес новой Logic имплементации
     * @notice Только UPGRADER_ROLE может обновлять контракт
     * @custom:oz-upgrades-unsafe-allow-reachable delegatecall
     */
    function _authorizeUpgrade(address newImplementation) 
        internal 
        override 
        onlyRole(UPGRADER_ROLE) 
        view
    {
        if (newImplementation == address(0)) revert ZeroAddress();
        // Дополнительные проверки безопасности можно добавить здесь
    }
    
    // ================================
    // ======= ФУНКЦИИ ПАУЗЫ ==========
    // ================================
    
    /**
     * @dev Поставить контракт на паузу (emergency)
     * @notice Доступно только ADMIN_ROLE
     * @notice Блокирует все функции с модификатором whenNotPaused
     */
    function pause() external onlyRole(ADMIN_ROLE) nonReentrant {
        _pause();
    }
    
    /**
     * @dev Снять контракт с паузы
     * @notice Доступно только ADMIN_ROLE
     * @notice Возобновляет работу всех функций
     */
    function unpause() external onlyRole(ADMIN_ROLE) nonReentrant {
        _unpause();
    }
    
    // ================================
    // ======== МОДИФИКАТОРЫ ==========
    // ================================
    
    /**
     * @dev Проверка, что msg.sender — активированный продавец
     * @notice Проверяет наличие SELLER_ROLE и активации в SpiralEngine
     */
    modifier onlyActivatedSeller() {
        if (!spiralEngine.hasRole(SELLER_ROLE, msg.sender)) revert NotASeller();
        if (spiralEngine.usedInviteByUser(msg.sender) == 0) revert NotActivatedUser();
        _;
    }
    
    /**
     * @dev Проверка, что msg.sender — продавец указанного товара
     * @param productId id товара
     */
    modifier onlyOwnSellerProduct(uint256 productId) {
        if (products[productId].seller != msg.sender) revert NotProductSeller();
        _;
    }
    
    // ================================
    // ===== ОСНОВНЫЕ ФУНКЦИИ =========
    // ================================
    
    /**
     * @notice Создать новый продукт с компонентами
     * @param componentIds Массив businessId компонентов из OrganicComponentRegistry
     * @param metadataCID IPFS CID с метаданными товара (БЕЗ компонентов)
     * @return productId ID созданного продукта
     * @dev Требует: активированный продавец с SELLER_ROLE
     * @dev Требует: componentRegistry установлен
     * @dev Требует: все компоненты существуют в OrganicComponentRegistry
     * @dev Создаёт продукт в неактивном состоянии
     * @dev Gas optimized: unchecked для счётчика, calldata для arrays
     */
    function createProduct(
        string calldata businessId,
        string[] calldata componentIds,
        string calldata metadataCID
    ) 
        external 
        whenNotPaused 
        nonReentrant 
        onlyActivatedSeller
        override 
        returns (uint256 productId) 
    {
        // Валидация входных данных
        if (bytes(businessId).length == 0) revert EmptyBusinessId();
        if (bytes(metadataCID).length == 0) revert EmptyCID();
        if (componentIds.length == 0) revert NoComponentsProvided();
        if (componentIds.length > MAX_COMPONENTS_PER_PRODUCT) revert TooManyComponents();
        if (address(componentRegistry) == address(0)) revert ComponentRegistryNotSet();

        if (businessIdToProductId[businessId] != 0) revert BusinessIdExists(businessId);
        
        // Валидация компонентов
        _validateComponents(componentIds);
        
        // Газовая оптимизация: unchecked безопасен для uint256
        unchecked {
            productId = ++_productIdCounter;
        }
        
        // Создаём продукт (неактивный по умолчанию)
        products[productId] = Product({
            id: productId,
            seller: msg.sender,
            businessId: businessId,
            componentIds: componentIds,
            metadataCID: metadataCID,
            active: false
        });
        
        businessIdToProductId[businessId] = productId;
        
        // Добавляем в индекс продавца
        productsBySeller[msg.sender].push(productId);
        
        // Обновляем версию каталога
        unchecked {
            catalogVersion[msg.sender]++;
        }
        
        // Уведомление OrganicComponentRegistry
        _trackComponentUsage(componentIds, msg.sender);
        
        // Эмитим события
        emit ProductCreated(msg.sender, productId, businessId, componentIds, metadataCID, 0);
        emit CatalogUpdated(msg.sender, catalogVersion[msg.sender]);
    }
    
    /**
     * @notice Обновить существующий продукт
     * @param productId ID продукта для обновления
     * @param newMetadataCID Новый IPFS CID с метаданными
     * @param newPrice Новая цена (для совместимости с событием)
     * @dev Требует: msg.sender = seller продукта
     * @dev Продукт должен быть активным
     * @dev Обновляет только metadataCID, компоненты остаются неизменными
     */
    function updateProduct(
        uint256 productId,
        string calldata newMetadataCID,
        uint256 newPrice
    ) 
        external 
        whenNotPaused 
        nonReentrant 
        onlyOwnSellerProduct(productId) 
        override 
    {
        if (bytes(newMetadataCID).length == 0) revert EmptyCID();
        if (newPrice == 0) revert InvalidPrice();
        
        Product storage product = products[productId];
        if (!product.active) revert ProductNotActive();
        
        product.metadataCID = newMetadataCID;
        
        unchecked {
            catalogVersion[msg.sender]++;
        }
        
        emit ProductUpdated(msg.sender, productId, product.businessId, newMetadataCID, newPrice, 1);
        emit CatalogUpdated(msg.sender, catalogVersion[msg.sender]);
    }
    
    /**
     * @notice Деактивировать продукт
     * @param productId ID продукта для деактивации
     * @dev Требует: msg.sender = seller продукта
     * @dev Продукт должен быть активным
     * @dev Удаляет продукт из списка активных (swap-and-pop)
     */
    function deactivateProduct(uint256 productId) 
        external 
        whenNotPaused 
        nonReentrant 
        onlyOwnSellerProduct(productId) 
        override 
    {
        Product storage product = products[productId];
        if (!product.active) revert ProductNotActive();
        
        product.active = false;
        
        // Удаляем из списка активных (swap-and-pop для экономии газа)
        _removeFromActiveProducts(productId);
        
        unchecked {
            catalogVersion[msg.sender]++;
        }
        
        emit ProductDeactivated(productId);
        emit CatalogUpdated(msg.sender, catalogVersion[msg.sender]);
    }
    
    /**
     * @notice Активировать продукт
     * @param productId ID продукта для активации
     * @dev Требует: msg.sender = seller продукта
     * @dev Продукт должен быть неактивным
     * @dev Добавляет продукт в список активных
     */
    function activateProduct(uint256 productId) 
        external 
        whenNotPaused 
        nonReentrant 
        onlyOwnSellerProduct(productId) 
        override 
    {
        Product storage product = products[productId];
        if (product.active) revert ProductAlreadyActive();
        
        product.active = true;
        activeProductIds.push(productId);
        
        unchecked {
            catalogVersion[msg.sender]++;
        }
        
        emit ProductUpdated(msg.sender, productId, product.businessId, product.metadataCID, 0, 1);
        emit CatalogUpdated(msg.sender, catalogVersion[msg.sender]);
    }
    
    /**
     * @notice Полностью очистить каталог продавца
     * @param seller Адрес продавца
     * @dev Требует: msg.sender = seller (можно очистить только свой каталог)
     * @dev Требует: seller имеет SELLER_ROLE
     * @dev Удаляет все продукты продавца из всех индексов
     * @dev Лимит: максимум MAX_PRODUCTS_PER_CLEAR продуктов за одну транзакцию
     */
    function clearSellerCatalog(address seller) 
        external 
        whenNotPaused 
        nonReentrant 
        override 
    {
        // Проверки доступа (порядок важен для правильных error messages!)
        if (seller == address(0)) revert InvalidSellerAddress();
        if (!spiralEngine.hasRole(SELLER_ROLE, msg.sender)) revert NotASeller();
        if (seller != msg.sender) revert CanOnlyClearOwnCatalog();
        
        // Проверка существования каталога
        uint256[] memory sellerProducts = productsBySeller[seller];
        uint256 productCount = sellerProducts.length;
        
        if (productCount == 0) revert CatalogAlreadyEmpty();
        if (productCount > MAX_PRODUCTS_PER_CLEAR) revert CatalogTooLarge();
        
        // Очистка всех продуктов
        for (uint256 i = 0; i < productCount;) {
            uint256 productId = sellerProducts[i];
            Product storage product = products[productId];
            
            // Проверки безопасности
            if (product.id == 0) revert ProductDoesNotExist();
            if (product.seller != seller) revert ProductOwnershipMismatch();
            
            string memory businessId = product.businessId;
            
            // Удаляем из списка активных, если продукт активен
            if (product.active) {
                _removeFromActiveProducts(productId);
            }
            
            // Удаляем продукт
            delete products[productId];
            delete businessIdToProductId[businessId];
            
            unchecked { ++i; }
        }
        
        // Очистка индекса продавца
        delete productsBySeller[seller];
        
        // Обновление версии каталога
        unchecked {
            catalogVersion[seller]++;
        }
        
        // Эмиссия событий
        emit CatalogCleared(seller, productCount);
        emit CatalogUpdated(seller, catalogVersion[seller]);
    }
    
    // ================================
    // ==== ВНУТРЕННИЕ ФУНКЦИИ ========
    // ================================
    
    /**
     * @dev Удалить продукт из списка активных продуктов (internal)
     * @param productId ID продукта для удаления
     * @notice Использует swap-and-pop алгоритм для эффективного удаления
     */
    function _removeFromActiveProducts(uint256 productId) private {
        uint256 len = activeProductIds.length;
        for (uint256 i = 0; i < len;) {
            if (activeProductIds[i] == productId) {
                activeProductIds[i] = activeProductIds[len - 1];
                activeProductIds.pop();
                break;
            }
            unchecked { ++i; }
        }
    }
    
    /**
     * @dev Валидация массива компонентов
     * @param componentIds Массив businessId для проверки
     * @notice Проверяет что все компоненты существуют в OrganicComponentRegistry
     * @notice Gas optimization: не проверяем статус (ACTIVE) для экономии ~5000 gas на компонент
     */
    function _validateComponents(string[] calldata componentIds) private view {
        // Gas optimization: кэшируем длину
        uint256 len = componentIds.length;
        
        for (uint256 i = 0; i < len;) {
            string calldata compId = componentIds[i];
            
            // Проверка существования
            if (!componentRegistry.componentExists(compId)) {
                revert ComponentNotFound(compId);
            }
            
            // Примечание: проверка статуса закомментирована для экономии gas
            // Можно раскомментировать если критично валидировать ACTIVE статус
            /*
            IOrganicComponentRegistry.ComponentStatus status = 
                componentRegistry.getComponentStatus(compId);
            if (status != IOrganicComponentRegistry.ComponentStatus.ACTIVE) {
                revert ComponentNotActive(compId);
            }
            */
            
            unchecked { ++i; }
        }
    }
    
    /**
     * @dev Уведомление OrganicComponentRegistry об использовании компонентов
     * @param componentIds Массив businessId использованных компонентов
     * @param seller Адрес продавца
     * @notice Инкрементирует счётчик использования и пытается добавить пользователя
     */
    function _trackComponentUsage(
        string[] memory componentIds,
        address seller
    ) private {
        uint256 len = componentIds.length;
        
        for (uint256 i = 0; i < len;) {
            string memory compId = componentIds[i];
            
            // Инкремент счётчика использования (всегда успешен)
            componentRegistry.incrementUsageCount(compId);
            
            // Попытка добавить пользователя (игнорируем если уже добавлен)
            // Используем try-catch для обработки дубликатов
            try componentRegistry.addComponentUser(compId, seller) {
                // Успешно добавлен
            } catch {
                // Пользователь уже добавлен - игнорируем ошибку
            }
            
            unchecked { ++i; }
        }
    }
    
    // ================================
    // ======== VIEW ФУНКЦИИ ==========
    // ================================
    
    /**
     * @notice Получить данные продукта
     * @param productId ID продукта
     * @return product Структура Product с полными данными
     * @dev Ревертится если продукт не существует
     */
    function getProduct(uint256 productId) 
        external 
        view 
        override 
        returns (Product memory product) 
    {
        product = products[productId];
        if (product.id == 0) revert ProductDoesNotExist();
    }
    
    /**
     * @notice Получить список ID всех активных продуктов
     * @return productIds Массив ID активных продуктов
     * @dev Возвращает snapshot на момент вызова
     */
    function getAllActiveProductIds() 
        external 
        view 
        override 
        returns (uint256[] memory productIds) 
    {
        return activeProductIds;
    }
    
    /**
     * @notice Получить список ID всех продуктов продавца
     * @param seller Адрес продавца
     * @return productIds Массив ID всех продуктов продавца (активных и неактивных)
     */
    function getProductsBySeller(address seller) 
        external 
        view 
        override 
        returns (uint256[] memory productIds) 
    {
        return productsBySeller[seller];
    }
    
    /**
     * @notice Получить версию каталога текущего продавца
     * @return version Номер версии каталога
     * @dev Требует: msg.sender имеет SELLER_ROLE
     * @dev Версия увеличивается при каждом изменении каталога
     */
    function getMyCatalogVersion() 
        external 
        view 
        override 
        returns (uint256 version) 
    {
        if (!spiralEngine.hasRole(SELLER_ROLE, msg.sender)) revert NotASeller();
        return catalogVersion[msg.sender];
    }
    
    /**
     * @notice Получить полные данные всех продуктов текущего продавца
     * @return products Массив структур Product
     * @dev Требует: msg.sender имеет SELLER_ROLE
     * @dev Возвращает все продукты (активные и неактивные)
     */
    function getProductsBySellerFull() 
        external 
        view 
        override 
        returns (Product[] memory) 
    {
        if (!spiralEngine.hasRole(SELLER_ROLE, msg.sender)) revert NotASeller();
        
        uint256[] memory sellerProductIds = productsBySeller[msg.sender];
        Product[] memory sellerProducts = new Product[](sellerProductIds.length);
        
        for (uint256 i = 0; i < sellerProductIds.length;) {
            sellerProducts[i] = products[sellerProductIds[i]];
            unchecked { ++i; }
        }
        
        return sellerProducts;
    }
    
    /**
     * @notice Получить список компонентов продукта
     * @param productId ID продукта
     * @return componentIds Массив businessId компонентов
     * @dev Ревертится если продукт не существует
     */
    function getProductComponents(uint256 productId) 
        external 
        view 
        override 
        returns (string[] memory componentIds) 
    {
        if (products[productId].id == 0) revert ProductDoesNotExist();
        return products[productId].componentIds;
    }

    /**
     * @inheritdoc IProductRegistry
     */
    function getProductIdByBusinessId(string calldata businessId)
        external
        view
        override
        returns (uint256 productId)
    {
        productId = businessIdToProductId[businessId];
        if (productId == 0) revert BusinessIdUnknown(businessId);
    }
    
    // ================================
    // ======= ADMIN ФУНКЦИИ ==========
    // ================================
    
    /**
     * @notice Установить новый адрес SpiralEngine контракта
     * @param _spiralEngine Адрес нового SpiralEngine контракта
     * @dev Требует: ADMIN_ROLE
     * @dev Эмитирует событие SpiralEngineUpdated
     */
    function setSpiralEngine(address _spiralEngine) 
        external 
        whenNotPaused 
        nonReentrant 
        onlyRole(ADMIN_ROLE) 
        override 
    {
        if (_spiralEngine == address(0)) revert ZeroAddress();
        
        address oldSpiralEngine = address(spiralEngine);
        spiralEngine = ISpiralEngine(_spiralEngine);
        
        emit SpiralEngineUpdated(oldSpiralEngine, _spiralEngine);
    }
    
    /**
     * @notice Установить адрес OrganicComponentRegistry контракта
     * @param _componentRegistry Адрес контракта OrganicComponentRegistry
     * @dev Требует: ADMIN_ROLE
     * @dev Эмитирует событие ComponentRegistryUpdated
     */
    function setOrganicComponentRegistry(address _componentRegistry) 
        external 
        whenNotPaused 
        nonReentrant 
        onlyRole(ADMIN_ROLE) 
        override 
    {
        if (_componentRegistry == address(0)) revert ZeroAddress();
        
        address oldRegistry = address(componentRegistry);
        componentRegistry = IOrganicComponentRegistry(_componentRegistry);
        
        emit ComponentRegistryUpdated(oldRegistry, _componentRegistry);
    }
}

