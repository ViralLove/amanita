# ProductRegistry - Контракт реестра продуктов

## Обзор

`ProductRegistry` - это смарт-контракт для управления каталогом продуктов в экосистеме Amanita. Контракт позволяет продавцам создавать, активировать и управлять своими продуктами в децентрализованном каталоге.

## Основные функции

### Управление продуктами

#### `createProduct(string memory ipfsCID)`
Создает новый продукт с метаданными, хранящимися в IPFS.

**Параметры:**
- `ipfsCID` - IPFS хеш метаданных продукта

**Требования:**
- Вызывающий должен быть активированным продавцом
- IPFS CID должен быть валидным

#### `activateProduct(uint256 productId)`
Активирует существующий продукт, делая его видимым в каталоге.

**Параметры:**
- `productId` - ID продукта для активации

**Требования:**
- Вызывающий должен быть владельцем продукта
- Продукт должен существовать

#### `deactivateProduct(uint256 productId)`
Деактивирует продукт, скрывая его из каталога.

**Параметры:**
- `productId` - ID продукта для деактивации

**Требования:**
- Вызывающий должен быть владельцем продукта
- Продукт должен существовать

### Новый метод: Очистка каталога

#### `clearSellerCatalog(address seller)`
**Полностью очищает каталог указанного продавца**, удаляя все его продукты из реестра.

**Параметры:**
- `seller` - адрес продавца, каталог которого нужно очистить

**Требования:**
- Вызывающий должен быть активированным продавцом
- `seller` должен быть валидным адресом (не нулевым)
- `seller` должен быть самим вызывающим (можно очищать только свой каталог)
- У продавца должен быть каталог для очистки

**Функциональность:**
- Удаляет все продукты продавца из основного реестра
- Удаляет продукты из активного списка (если они были активны)
- Очищает маппинг `productsBySeller`
- Увеличивает версию каталога продавца
- Эмитирует события `CatalogCleared` и `CatalogUpdated`

**Ограничения:**
- Максимум 10,000 продуктов за одну операцию (защита от переполнения газа)
- Можно очистить только свой собственный каталог

**События:**
```solidity
event CatalogCleared(address indexed seller, uint256 productsCleared);
event CatalogUpdated(address indexed seller, uint256 newVersion);
```

### Получение данных

#### `getProduct(uint256 productId)`
Возвращает информацию о конкретном продукте.

#### `getProductsBySeller(address seller)`
Возвращает массив ID всех продуктов продавца.

#### `getProductsBySellerFull(address seller)`
Возвращает полную информацию о всех продуктах продавца.

#### `getAllActiveProductIds()`
Возвращает массив ID всех активных продуктов в системе.

#### `getMyCatalogVersion()`
Возвращает текущую версию каталога вызывающего продавца.

## Структуры данных

### Product
```solidity
struct Product {
    uint256 id;           // Уникальный ID продукта
    address seller;       // Адрес продавца
    string ipfsCID;       // IPFS хеш метаданных
    bool active;          // Статус активности
    uint256 createdAt;    // Время создания
}
```

## Безопасность

### Модификаторы доступа
- `onlyActivatedUser` - требует активации пользователя через InviteNFT
- `onlyOwnSellerProduct` - требует, чтобы продукт принадлежал вызывающему

### Проверки безопасности в `clearSellerCatalog`:
1. **Проверка роли продавца** - только активированные продавцы
2. **Проверка владения** - можно очистить только свой каталог
3. **Проверка адреса** - защита от нулевых адресов
4. **Проверка существования каталога** - нельзя очистить пустой каталог
5. **Ограничение размера** - защита от переполнения газа

## Оптимизация газа

### Алгоритм удаления из активного списка
Используется техника "swap-and-pop" для эффективного удаления элементов из массива:

```solidity
function _removeFromActiveProducts(uint256 productId) private {
    uint256 lastIndex = activeProductIds.length - 1;
    uint256 productIndex = activeProductIndex[productId];
    
    if (productIndex != lastIndex) {
        uint256 lastProductId = activeProductIds[lastIndex];
        activeProductIds[productIndex] = lastProductId;
        activeProductIndex[lastProductId] = productIndex;
    }
    
    activeProductIds.pop();
    delete activeProductIndex[productId];
}
```

## События

### Основные события
- `ProductCreated` - продукт создан
- `ProductActivated` - продукт активирован
- `ProductDeactivated` - продукт деактивирован
- `CatalogCleared` - каталог полностью очищен
- `CatalogUpdated` - каталог обновлен

### События очистки каталога
```solidity
event CatalogCleared(address indexed seller, uint256 productsCleared);
```
- `seller` - адрес продавца, чей каталог был очищен
- `productsCleared` - количество удаленных продуктов

## Использование

### Пример очистки каталога
```javascript
// Подключение к контракту
const productRegistry = new ethers.Contract(address, abi, signer);

// Очистка каталога продавца
const tx = await productRegistry.clearSellerCatalog(sellerAddress);
await tx.wait();

// Проверка результата
const remainingProducts = await productRegistry.getProductsBySeller(sellerAddress);
console.log(`Осталось продуктов: ${remainingProducts.length}`); // Должно быть 0
```

### Проверка состояния после очистки
```javascript
// Проверка каталога продавца
const sellerCatalog = await productRegistry.getProductsBySeller(sellerAddress);
assert(sellerCatalog.length === 0, "Каталог должен быть пустым");

// Проверка активных продуктов
const activeProducts = await productRegistry.getAllActiveProductIds();
// Активных продуктов должно стать меньше на количество удаленных

// Проверка версии каталога
const catalogVersion = await productRegistry.getMyCatalogVersion();
// Версия должна увеличиться
```

## Интеграция с экосистемой

### Зависимости
- **InviteNFT** - для проверки ролей и активации пользователей
- **IPFS** - для хранения метаданных продуктов

### Роли
- **SELLER_ROLE** - роль продавца в InviteNFT
- **Активированный пользователь** - пользователь, использовавший инвайт

## Версионирование

Каждый продавец имеет свою версию каталога, которая увеличивается при:
- Создании нового продукта
- Активации/деактивации продукта
- **Полной очистке каталога** (новое в версии с `clearSellerCatalog`)

## Заключение

Метод `clearSellerCatalog` предоставляет продавцам возможность полностью очистить свой каталог, что полезно для:
- Сброса каталога при ошибках
- Подготовки к загрузке нового каталога
- Управления жизненным циклом продуктов
- Тестирования и отладки

Метод безопасен, эффективен и полностью интегрирован с существующей системой управления продуктами.
