# Ретроспективный анализ: Фаза 2 — ActivityRegistry Logic

**Методология:** @run-analysis.md (analysis)  
**Источник:** solution-architecture-task1-activity-registry.md, строки 368–393 (Фаза 2)  
**Дата:** 2026-01-29  
**Цель:** Выявить, что из Фазы 2 сделано, а что не начиналось.

---

## 1. Рамки анализа

- **Фаза 2:** Реализация Logic (минимальная; по факту реализован полный Logic с UUPS).
- **Артефакты для сверки:** `contracts/ActivityRegistryLogic.sol`, `contracts/interfaces/IActivityRegistry.sol`, результат `npx hardhat compile`.

---

## 2. Пошаговая сверка (Фаза 2)

| Шаг | Действие по плану | Статус | Доказательство в коде |
|-----|-------------------|--------|------------------------|
| **2.1** | Создать `contracts/ActivityRegistryLogic.sol` | ✅ Сделано | Файл существует, контракт объявлен. |
| **2.2** | Импорты: Initializable, UUPSUpgradeable, AccessControlUpgradeable, PausableUpgradeable, ReentrancyGuardUpgradeable, IActivityRegistry, ISpiralEngine | ✅ Сделано | Стр. 4–10 ActivityRegistryLogic.sol — все перечисленные импорты есть. |
| **2.3** | Константы: LOGIC_VERSION, UPGRADER_ROLE, ADMIN_ROLE; ACTIVITY_CREATOR_ROLE — в Logic или из spiralEngine | ✅ Сделано | Выбран вариант «в Logic задать ACTIVITY_CREATOR_ROLE»: стр. 32–37 — все четыре константы объявлены в Logic. |
| **2.4** | State: spiralEngine, activities, activitiesByCreator, publishedActivityIds, _activityIdCounter, __gap | ✅ Сделано | Стр. 66–78: порядок и типы совпадают с планом; __gap = uint256[48]. |
| **2.5** | initialize(admin, _spiralEngine): проверки адресов, init модулей, spiralEngine, _grantRole | ✅ Сделано | Стр. 89–101: ZeroAddress/InvalidSpiralEngine, __AccessControl_init, __UUPSUpgradeable_init, __Pausable_init, __ReentrancyGuard_init, spiralEngine = …, _grantRole(DEFAULT_ADMIN_ROLE, ADMIN_ROLE, UPGRADER_ROLE, admin). |
| **2.6** | _authorizeUpgrade(newImplementation): onlyRole(UPGRADER_ROLE), newImplementation != address(0) | ✅ Сделано | Стр. 111–114: override, onlyRole(UPGRADER_ROLE), revert ZeroAddress при address(0). |
| **2.7** | Custom errors: ZeroAddress, InvalidSpiralEngine, EmptyCID, ActivityNotFound, ActivityNotActive, ActivityAlreadyActive, NotActivityCreator, NotActivatedActivityCreator | ✅ Сделано | Стр. 44–59: все восемь ошибок объявлены. |
| **2.8** | Модификаторы onlyActivatedActivityCreator (hasRole + usedInviteByUser != 0), onlyOwnActivity(activityId) | ✅ Сделано | Стр. 142–154: оба модификатора с требуемой логикой. |
| **2.9** | createActivity: whenNotPaused, nonReentrant, onlyActivatedActivityCreator; валидация CID; инкремент счётчика; запись; emit; return | ✅ Сделано | Стр. 165–190: модификаторы, EmptyCID, unchecked ++_activityIdCounter, запись в activities и activitiesByCreator, ActivityCreated, return activityId. |
| **2.10** | getActivity(activityId): возврат activities[activityId]; revert при несуществующей (id == 0) | ✅ Сделано | Стр. 193–196: проверка activityId == 0 \|\| creator == address(0) → ActivityNotFound; return activities[activityId]. |
| **2.11** | activateActivity: whenNotPaused, nonReentrant, onlyOwnActivity; !active; active = true; push; emit | ✅ Сделано | Стр. 199–205: все условия и действия, включая ActivityActivated(activityId, msg.sender). |
| **2.12** | deactivateActivity: whenNotPaused, nonReentrant, onlyOwnActivity; active; active = false; swap-and-pop; emit | ✅ Сделано | Стр. 208–215 и 217–229: проверки, active = false, _removeFromPublished (swap-and-pop), ActivityDeactivated. |
| **2.13** | getActivitiesByCreator(creator), getPublishedActivityIds() — возврат массивов | ✅ Сделано | Стр. 234–240: обе view-функции возвращают требуемые массивы. |
| **2.14** | pause(), unpause(): onlyRole(ADMIN_ROLE), nonReentrant; setSpiralEngine: onlyRole(ADMIN_ROLE), whenNotPaused, nonReentrant, ZeroAddress, emit SpiralEngineUpdated | ✅ Сделано | Стр. 119–135: pause, unpause, setSpiralEngine с указанными модификаторами и проверками. |
| **2.15** | IActivityRegistry — недостающие сигнатуры (если есть); `npx hardhat compile` | ✅ Сделано | IActivityRegistry содержит все нужные события и функции; Logic реализует IActivityRegistry; компиляция проходит. |

---

## 3. Итог

- **Сделано:** все шаги Фазы 2 (2.1–2.15) реализованы в коде и подтверждены сверкой с `ActivityRegistryLogic.sol` и `IActivityRegistry.sol`.
- **Не начиналось:** шагов из Фазы 2, которые не трогали, нет.

**Проверка по плану:** ActivityRegistryLogic компилируется; интерфейс IActivityRegistry реализован в Logic (implements IActivityRegistry) — выполняется.

---

## 4. Замечания по расхождению с формулировкой плана

- **2.3:** В плане допускается «константу ACTIVITY_CREATOR_ROLE не хранить в Logic — брать из spiralEngine». Фактически выбран вариант «в Logic задать ACTIVITY_CREATOR_ROLE» (как альтернатива в том же пункте). ISpiralEngine в моке даёт ту же константу; поведение эквивалентно.
- **2.10:** В плане указано «revert при несуществующей (id == 0)». В коде дополнительно проверяется `activities[activityId].creator == address(0)` для несуществующих id — усиление, не противоречие плану.

---

**Версия:** 1.0  
**Статус:** Ретроспектива Фазы 2 завершена.
