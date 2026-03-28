# Расслоение экосистемы: от метафоры к архитектуре

**Версия:** 1.0  
**Дата создания:** 2026-01-13  
**Методология:** @conceptual-architecture-bridge.mdc, @analysis.mdc  
**Статус:** ✅ Концептуальный анализ, готов к архитектурной трансформации

---

## 🎨 Метафорический слой (от оператора)

### Образ процесса: Электролиз воды

**Визуализация:**
```
Электричество (катализатор)
    ↓
Вода (плотная среда) 
    → Пузырьки (промежуточное состояние)
    → Поверхность (переходное состояние)
    → Воздух (свободное состояние, "среди своих")
```

**Ментальная проекция:**
- Каждая молекула кислорода = точка сознания = участник экосистемы
- Чем выше — тем выше частота вибрации (уровень энергии/сознания)
- Катализатор = запуск трансформации под действием внешнего фактора
- Очаги кристаллизации = точки, где начинается "всплытие" (центры активации)

**Ключевые смысловые векторы:**
1. **Органическая трансформация** — естественное движение вверх
2. **Слои как уровни** — от плотной среды к свободному состоянию
3. **Очаги активации** — точки кристаллизации для "всплытия"
4. **Рекомендация как путь** — значимые участники запускают трансформацию
5. **Спиралевидная динамика** — 12-инвайтовая модель формирует спираль связей

---

## 🔍 Концептуальный анализ

### Принципы трансформации

#### 1. Слои "всплытия" как уровни участия

**От метафоры к логике:**
- **Нулевой слой (вода)** = Базовое состояние: неактивированный пользователь, посетитель
- **Пузырьки внутри воды** = Промежуточное состояние: активированный пользователь, покупатель
- **На поверхности** = Переходное состояние: активный покупатель с репутацией/бейджами
- **Высоко в воздухе** = Свободное состояние: seller или buyer с высоким уровнем

**Архитектурная интерпретация:**
```
Layer 0: Visitor (неактивированный)
    ↓ [катализатор: инвайт]
Layer 1: Activated User / Buyer (активированный в SpiralEngine)
    ↓ [катализатор: активность + репутация]
Layer 2: Active Buyer with Badges (покупатель с бейджами/репутацией)
    ↓ [катализатор: достижения + рекомендации]
Layer 3: Seller Candidate (кандидат в sellers)
    ↓ [катализатор: рекомендации значимых участников]
Layer 4: Seller (SELLER_ROLE, ACTIVATOR_ROLE)
```

#### 2. Катализатор как комбинация факторов

**Принцип:** Разные роли требуют разных комбинаций факторов для трансформации.

**Компоненты катализатора:**
1. **Инвайт** — базовый катализатор для Layer 0 → Layer 1
2. **Активность** — покупки, участие в LoveDo, взаимодействие с экосистемой
3. **Репутация** — SoulIdentity level/reputation, LoveDo posts, superlikes
4. **Бейджи** — достижения, признание от других участников
5. **Рекомендации** — одобрение значимых участников (seller или buyer с бейджами)

**Архитектурная модель катализаторов:**
```solidity
enum CatalystType {
    INVITE_ONLY,              // Layer 0 → 1: только инвайт
    ACTIVITY_REPUTATION,      // Layer 1 → 2: активность + репутация
    ACHIEVEMENT_BADGES,       // Layer 2 → 3: достижения + бейджи
    RECOMMENDATIONS           // Layer 3 → 4: рекомендации значимых участников
}

struct Catalyst {
    CatalystType catalystType;
    uint256 minActivity;      // минимальная активность
    uint256 minReputation;    // минимальная репутация
    uint256 requiredBadges;   // требуемые бейджи
    uint256 minRecommendations; // минимальное количество рекомендаций
    address[] recommenders;   // кто может рекомендовать
}
```

#### 3. Значимые участники для рекомендаций

**Кто может рекомендовать:**
- **Seller** (SELLER_ROLE) — имеет полные права, активирует других
- **Buyer с системой бейджей** — высокий уровень активности и репутации

**Архитектурная интерпретация:**
```solidity
// Значимый участник = seller ИЛИ buyer с высоким уровнем
function isSignificantParticipant(address user) public view returns (bool) {
    // Seller всегда значимый
    if (spiralEngine.hasRole(SELLER_ROLE, user)) return true;
    
    // Buyer значимый если:
    // - soulLevel >= SIGNIFICANT_BUYER_LEVEL (например, 3)
    // - soulReputation >= SIGNIFICANT_BUYER_REPUTATION (например, 500)
    // - имеет определённые бейджи
    uint256 level = soulIdentity.getSoulLevel(user);
    uint256 reputation = soulIdentity.getSoulReputation(user);
    return level >= 3 && reputation >= 500;
}
```

#### 4. Очаги всплытия (кристаллизация)

**Концептуальный мост:**
Очаги кристаллизации = регионы высокой активности, где концентрируются участники и запускается процесс трансформации.

**Архитектурная интерпретация:**
1. **Seller Nodes** — центры активности вокруг конкретного селлера
2. **Regional Hubs** — географические или тематические кластеры активности
3. **Trust Circles** — группы участников, связанные общим активатором (12-инвайтовая модель)
4. **Activity Zones** — области с высокой концентрацией LoveDo posts, покупок, взаимодействий

**Техническая реализация:**
```solidity
struct ActivityHub {
    address hubOwner;         // seller или координатор
    address[] participants;   // участники в этом очаге
    uint256 activityScore;    // метрика активности
    uint256 transformationCount; // сколько трансформаций произошло
    HubType hubType;          // SELLER_NODE, REGIONAL, TRUST_CIRCLE, ACTIVITY_ZONE
}

enum HubType {
    SELLER_NODE,      // вокруг конкретного seller
    REGIONAL,         // географический кластер
    TRUST_CIRCLE,     // группа с общим активатором
    ACTIVITY_ZONE     // зона высокой активности
}
```

#### 5. "Среди своих" — что это означает технически

**Концептуальный мост:**
"Среди своих" = доступ к функциям и ролям, возможность влиять на экосистему, признание сообществом.

**Архитектурная интерпретация:**
1. **Доступ к функциям:**
   - Minting invites (SELLER_ROLE)
   - Активация других (ACTIVATOR_ROLE)
   - Создание LoveDo posts
   - Superliking posts (в том же trust circle)
   - Claiming tokens ($LOVECOIN, $LGOV)

2. **Уровни признания:**
   - **Layer 1:** Базовый доступ к каталогу, покупкам
   - **Layer 2:** Создание LoveDo posts, получение superlikes
   - **Layer 3:** Claiming governance tokens, влияние на репутацию
   - **Layer 4:** Активация других, минтинг инвайтов, управление каталогом

3. **Социальное признание:**
   - Высокая репутация (soulLevel, soulReputation)
   - Множество LoveDo posts
   - Много superlikes
   - Активированные участники в trust circle

---

## 🏗️ Архитектурные соответствия в текущей системе

### Что уже есть:

#### 1. SpiralEngine — базовая модель слоистости
```solidity
// Текущая структура:
- ACTIVATOR_ROLE: может активировать до 12 пользователей
- SELLER_ROLE: может минтить инвайты, управлять каталогом
- 12-инвайтовая модель: спиралевидная динамика
```

**Соответствие метафоре:**
- ✅ 12-инвайтовая модель = спиралевидная динамика
- ✅ Активация = катализатор Layer 0 → 1
- ⚠️ Нет промежуточных слоёв между покупателем и seller
- ⚠️ Нет системы бейджей для покупателей

#### 2. SoulIdentity — система уровней и репутации
```solidity
// Текущая структура:
- soulLevel: уровень души (1+)
- soulReputation: репутация (100+)
- SBT токены: непередаваемые токены идентичности
```

**Соответствие метафоре:**
- ✅ Уровни = частота вибрации (Layer 2, 3)
- ✅ Репутация = мера активности
- ⚠️ Нет явной связи с трансформацией покупатель → seller

#### 3. LoveEmissionEngine — система бейджей для sellers
```solidity
// Текущая структура:
- LoveDo posts: посты-признания для sellers
- Superlikes: одобрение от trust circle
- $LOVECOIN: утилити токены (claimable immediately)
- $LGOV: governance токены (require 8 LoveDo posts)
```

**Соответствие метафоре:**
- ✅ Бейджи через LoveDo posts (для sellers)
- ✅ Trust circle через inviteGraph
- ⚠️ Нет системы бейджей для buyers
- ⚠️ Нет связи с трансформацией покупатель → seller

---

## 🔄 Gap Analysis: что отсутствует

### Критические gaps:

1. **Нет промежуточных слоёв между покупателем и seller**
   - Текущая система: активированный пользователь → (прямо) → SELLER_ROLE
   - Нужно: Layer 2 (Active Buyer), Layer 3 (Seller Candidate)

2. **Нет системы бейджей для покупателей**
   - Текущая система: бейджи только для sellers (LoveDo posts)
   - Нужно: бейджи за покупки, активность, участие в LoveDo

3. **Нет катализатора "достижения + рекомендации"**
   - Текущая система: seller назначается ACTIVATOR_ROLE (ручное назначение)
   - Нужно: автоматическая трансформация на основе катализатора

4. **Нет механизма "очагов всплытия"**
   - Текущая система: активность распределена, нет концентрации
   - Нужно: метрики активности, региональные/тематические кластеры

5. **Нет формализации "значимого участника" для buyers**
   - Текущая система: значимый = seller (SELLER_ROLE)
   - Нужно: buyer с высоким уровнем/репутацией также значимый

---

## 💡 Архитектурные решения

### Решение 1: Система слоёв участников (User Layers)

**Концепция:** Формализовать слои трансформации через enum и mapping.

```solidity
enum UserLayer {
    VISITOR,           // Layer 0: неактивированный
    ACTIVATED_BUYER,   // Layer 1: активированный покупатель
    ACTIVE_BUYER,      // Layer 2: активный покупатель с бейджами
    SELLER_CANDIDATE,  // Layer 3: кандидат в sellers
    SELLER             // Layer 4: seller (SELLER_ROLE)
}

mapping(address => UserLayer) public userLayer;
mapping(UserLayer => Catalyst) public layerCatalysts;

struct Catalyst {
    CatalystType catalystType;
    uint256 minActivity;
    uint256 minReputation;
    uint256 requiredBadges;
    uint256 minRecommendations;
}
```

**Преимущества:**
- ✅ Явная модель слоистости
- ✅ Прозрачные условия трансформации
- ✅ Отслеживание прогресса участников

---

### Решение 2: Система бейджей для покупателей

**Концепция:** Расширить систему бейджей на покупателей через SoulIdentity metadata.

```solidity
// В SoulIdentity добавить:
struct BuyerBadge {
    BadgeType badgeType;
    uint256 achievedAt;
    string metadataURI;  // IPFS ссылка на метаданные бейджа
}

enum BadgeType {
    FIRST_PURCHASE,      // Первая покупка
    LOYAL_CUSTOMER,      // 10+ покупок
    LOVE_DO_AUTHOR,      // Создал LoveDo post
    SUPERLIKED,          // Получил superlike на LoveDo post
    TRUST_CIRCLE_MEMBER, // Активный член trust circle
    REPUTATION_CHAMPION  // Высокая репутация (500+)
}

mapping(address => BuyerBadge[]) public buyerBadges;
mapping(address => mapping(BadgeType => bool)) public hasBadge;
```

**Преимущества:**
- ✅ Мотивация покупателей через достижения
- ✅ Прозрачная система прогресса
- ✅ Интеграция с существующей SoulIdentity

---

### Решение 3: Катализатор трансформации (Transformation Catalyst)

**Концепция:** Автоматическая проверка условий и трансформация между слоями.

```solidity
contract TransformationEngine {
    function checkCatalyst(
        address user,
        UserLayer targetLayer
    ) public view returns (bool canTransform, string memory reason) {
        UserLayer currentLayer = userLayer[user];
        Catalyst memory catalyst = layerCatalysts[targetLayer];
        
        // Проверка типа катализатора
        if (catalyst.catalystType == CatalystType.INVITE_ONLY) {
            // Проверка активации в SpiralEngine
            return (spiralEngine.usedInviteByUser(user) > 0, "User not activated");
        }
        
        if (catalyst.catalystType == CatalystType.ACTIVITY_REPUTATION) {
            uint256 activity = getUserActivity(user);
            uint256 reputation = soulIdentity.getSoulReputation(user);
            bool activityOK = activity >= catalyst.minActivity;
            bool repOK = reputation >= catalyst.minReputation;
            return (activityOK && repOK, 
                !activityOK ? "Insufficient activity" : "Insufficient reputation");
        }
        
        if (catalyst.catalystType == CatalystType.ACHIEVEMENT_BADGES) {
            BuyerBadge[] memory badges = buyerBadges[user];
            uint256 badgeCount = 0;
            for (uint i = 0; i < badges.length; i++) {
                if (_isRequiredBadge(badges[i].badgeType, catalyst.requiredBadges)) {
                    badgeCount++;
                }
            }
            return (badgeCount >= catalyst.requiredBadges, "Insufficient badges");
        }
        
        if (catalyst.catalystType == CatalystType.RECOMMENDATIONS) {
            address[] memory recommenders = getRecommendations(user);
            uint256 significantCount = 0;
            for (uint i = 0; i < recommenders.length; i++) {
                if (isSignificantParticipant(recommenders[i])) {
                    significantCount++;
                }
            }
            return (significantCount >= catalyst.minRecommendations,
                "Insufficient recommendations from significant participants");
        }
        
        return (false, "Unknown catalyst type");
    }
    
    function transformLayer(address user, UserLayer targetLayer) external {
        (bool canTransform, string memory reason) = checkCatalyst(user, targetLayer);
        require(canTransform, reason);
        
        UserLayer currentLayer = userLayer[user];
        
        // Логика трансформации
        if (targetLayer == UserLayer.SELLER) {
            // Назначение SELLER_ROLE
            spiralEngine.grantSellerRole(user);
        }
        
        userLayer[user] = targetLayer;
        emit LayerTransformed(user, currentLayer, targetLayer, block.timestamp);
    }
}
```

**Преимущества:**
- ✅ Автоматическая проверка условий
- ✅ Прозрачный процесс трансформации
- ✅ Гибкая настройка катализаторов

---

### Решение 4: Очаги активности (Activity Hubs)

**Концепция:** Отслеживание и усиление активности в регионах/кластерах.

```solidity
contract ActivityHubRegistry {
    mapping(address => ActivityHub) public hubs;
    mapping(address => address) public userHub;  // user → hub owner
    
    function registerHub(
        address hubOwner,
        HubType hubType
    ) external {
        require(hubs[hubOwner].hubOwner == address(0), "Hub already exists");
        
        hubs[hubOwner] = ActivityHub({
            hubOwner: hubOwner,
            participants: new address[](0),
            activityScore: 0,
            transformationCount: 0,
            hubType: hubType
        });
    }
    
    function joinHub(address hubOwner, address user) external {
        require(hubs[hubOwner].hubOwner != address(0), "Hub does not exist");
        require(userHub[user] == address(0), "User already in a hub");
        
        hubs[hubOwner].participants.push(user);
        userHub[user] = hubOwner;
        
        emit HubJoined(user, hubOwner, block.timestamp);
    }
    
    function updateActivityScore(address hubOwner) external {
        ActivityHub storage hub = hubs[hubOwner];
        
        // Рассчитываем активность на основе:
        // - Количество участников
        // - LoveDo posts от участников
        // - Покупки участников
        // - Трансформации в hub
        
        uint256 score = 0;
        for (uint i = 0; i < hub.participants.length; i++) {
            score += getUserActivity(hub.participants[i]);
        }
        
        hub.activityScore = score;
        emit ActivityScoreUpdated(hubOwner, score, block.timestamp);
    }
    
    // Очаги с высокой активностью получают бонусы к трансформации
    function getTransformationBonus(address user) public view returns (uint256) {
        address hubOwner = userHub[user];
        if (hubOwner == address(0)) return 0;
        
        ActivityHub memory hub = hubs[hubOwner];
        // Высокая активность = бонус к трансформации
        if (hub.activityScore >= HIGH_ACTIVITY_THRESHOLD) {
            return TRANSFORMATION_BONUS;  // например, 10% снижение требований
        }
        
        return 0;
    }
}
```

**Преимущества:**
- ✅ Концентрация активности в очагах
- ✅ Бонусы для активных участников
- ✅ Метрики для анализа экосистемы

---

## 📊 Интеграция с существующей архитектурой

### Связь с SpiralEngine:

```solidity
// SpiralEngine остаётся основой, но расширяется:
- ACTIVATOR_ROLE: может активировать (Layer 0 → 1)
- SELLER_ROLE: может минтить инвайты (Layer 4)
- TransformationEngine: автоматическая трансформация Layer 1 → 4
```

### Связь с SoulIdentity:

```solidity
// SoulIdentity хранит метаданные слоёв:
- userLayer: текущий слой участника
- buyerBadges: бейджи покупателя
- soulLevel, soulReputation: метрики для катализаторов
```

### Связь с LoveEmissionEngine:

```solidity
// LoveEmissionEngine расширяется для покупателей:
- Buyer badges за создание LoveDo posts
- Buyer badges за получение superlikes
- Интеграция с TransformationEngine
```

---

## ✅ Чеклист трансформации

### Концептуальный слой
- [x] Метафора отзеркалена и понята
- [x] Ключевые принципы выделены
- [x] Метафоры трансформированы в логику
- [x] Неявные требования выявлены

### Архитектурный слой
- [x] Найдены существующие паттерны
- [x] Выявлены gaps между концепцией и реализацией
- [x] Предложены конкретные технические решения
- [x] Решения соответствуют принципам концепции

### Документирование
- [x] Создан документ анализа
- [x] Описан процесс трансформации
- [x] Предоставлены рекомендации
- [x] Связаны с существующей документацией

---

## 🚀 Следующие шаги

1. **Уточнить детали катализаторов** с оператором
2. **Проектировать контракты** для TransformationEngine, ActivityHubRegistry
3. **Интегрировать с существующими контрактами** (SpiralEngine, SoulIdentity)
4. **Создать тесты** для новых механизмов
5. **Обновить документацию** контрактов

---

**Версия:** 1.0  
**Последнее обновление:** 2026-01-13  
**Автор:** Методология через @conceptual-architecture-bridge.mdc  
**Статус:** ✅ Концептуальный анализ завершён, готов к архитектурному проектированию
