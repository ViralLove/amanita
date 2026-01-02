# task: Несоответствия docs ↔ code ↔ tests в `contracts/`

**Статус:** TODO (не исправлялось)  
**Цель:** зафиксировать найденные несоответствия, чтобы позже синхронизировать документацию/контракты/тесты.  
**Правило:** никаких предположений — только то, что подтверждено кодом/тестами в репозитории.

---

## 1) `contracts/docs/LoveEmissionEngine.md` не соответствует `contracts/LoveEmissionEngine.sol`

### 1.1 Нейминг storage/ивентов
- **В docs**: используются `amanitaAccrued` / `agovAccrued`, и `Emission(... amanitaAmount, agovAccrued)`
  - файл: `contracts/docs/LoveEmissionEngine.md`
- **В коде**: используются `loveAccrued` / `lgovAccrued`, и `Emission(... lovecoinAmount, lgovAccrued)`
  - файл: `contracts/LoveEmissionEngine.sol`
  - примеры:
    - `mapping(address => uint256) public loveAccrued;`
    - `mapping(address => uint256) public lgovAccrued;`
    - `event Emission(address indexed seller, uint256 lovecoinAmount, uint256 lgovAccrued);`

### 1.2 Несовпадение API с LoveDo контрактом (см. п.2)
`LoveEmissionEngine` описан как тесно интегрированный с LoveDo, но текущие сигнатуры **не совпадают** с текущей реализацией `LoveDoPostNFT.sol` (см. ниже).

---

## 2) `contracts/LoveEmissionEngine.sol` ↔ `contracts/LoveDoPostNFT.sol`: несовместимые сигнатуры

### 2.1 `addSuperlike`
- **В `LoveEmissionEngine.sol`** (ожидается):
  - `function addSuperlike(uint256 tokenId) external returns (bool);`
  - `bool success = loveDo.addSuperlike(tokenId);`
- **В `LoveDoPostNFT.sol`** (реально есть):
  - `function addSuperlike(uint256 tokenId, uint256 expectedNonce) external`
  - return value отсутствует (не `bool`)

### 2.2 `getPost`
- **В `LoveEmissionEngine.sol`** (ожидается tuple):
  - `function getPost(uint256 tokenId) external view returns (address author, address sellerTo, address linkedSeller, uint8 superlikes);`
- **В `LoveDoPostNFT.sol`** (реально есть):
  - `function getPost(uint256 tokenId) external view returns (LoveDo memory)`

### 2.3 Вывод
Текущая пара `LoveEmissionEngine.sol` и `LoveDoPostNFT.sol` **не компилируется/не линкуется как единая связка** без правок интерфейса/адаптера. Это видно по несовпадающим сигнатурам вызовов (`addSuperlike`, `getPost`).

---

## 3) `contracts/LoveDoPostNFT.sol` ↔ `contracts/AmanitaRegistry.sol`: несовместимый контрактный API

### 3.1 `hasSellerRole`
- **В `LoveDoPostNFT.sol`** контракт ожидает:
  - `IAmanitaRegistry public amanitaRegistry;`
  - `require(amanitaRegistry.hasSellerRole(...), "...");`
  - интерфейс определён внизу файла:
    - `interface IAmanitaRegistry { function hasSellerRole(address user) external view returns (bool); }`
- **В `AmanitaRegistry.sol`** (реально есть):
  - только `setAddress/getAddress/getAllContractNames/transferOwnership`
  - **нет** `hasSellerRole(address)`

### 3.2 Вывод
Текущий `LoveDoPostNFT.sol` нельзя корректно связать с текущим `AmanitaRegistry.sol` как с “реестром sellers” — отсутствует требуемый метод.

---

## 4) Тесты по LoveEmission/LoveDo выглядят написанными под другой `LoveDoPostNFT` (или старую версию)

### 4.1 `contracts/tests/LoveEmissionEngine.lovecoin.test.js`
В тесте используются сущности/сигнатуры, которых нет в текущих контрактах:

- **Деплой `LoveDoPostNFT`**:
  - в тесте: `LoveDoPostNFT.deploy(deployer.address, deployer.address, deployer.address)`
  - в текущем контракте: `constructor(address _admin, address _inviteGraph, address _amanitaRegistry)`
- **Минт поста**:
  - в тесте вызывается `loveDoPostNFT.mintLoveDo(...)`
  - в текущем контракте есть `mintLoveDoPost(address sellerTo, string calldata uri)`
- **Получение tokenId**:
  - в тесте: `getCurrentTokenId()`
  - в текущем контракте: публичная переменная `nextTokenId` (и нет `getCurrentTokenId`)
- **Суперлайк**:
  - в тесте суперлайк идёт через `LoveEmissionEngine.emitForSuperlike(tokenId, liker)`
  - но внутри `LoveEmissionEngine` вызов `loveDo.addSuperlike(tokenId)` не совпадает с текущей сигнатурой `LoveDoPostNFT.addSuperlike(tokenId, expectedNonce)`

### 4.2 Вывод
С высокой вероятностью в репозитории одновременно присутствуют:
- новая версия `LoveDoPostNFT.sol` (nonce-based, registry-check),
- и тесты/движок эмиссии, написанные под другую (старую) версию LoveDo.

Это нужно разрулить: либо обновить тесты и `LoveEmissionEngine` под текущий `LoveDoPostNFT`, либо вернуть/хранить “старый” LoveDo как отдельный контракт (и явно назвать).

---

## 5) Несоответствие “какой реестр адресов используется” (`AmanitaRegistry` vs `MagicRegistry`) и качество текущей реализации

### 5.1 `AmanitaRegistry.sol` дублирует имена
- В `AmanitaRegistry.sol`:
  - при каждом `setAddress(name, addr)` имя **всегда** пушится в `contractNames` (возможны дубликаты)

### 5.2 `MagicRegistry.sol` аналогично хранит список имён без дедупликации
- `MagicRegistry.sol` делает `names.push(key)` на каждый `set()`

### 5.3 Вывод
Документация может описывать “чистый список уникальных имён”, но по факту оба реестра сейчас позволяют дубликаты в массиве имён.

---

## 6) Нейминг governance-токена: docs часто пишут LGOV, но в коде символ AGOV

### 6.1 `AmanitaGovToken.sol`
- контракт разворачивается как:
  - `ERC20("Amanita Governance", "AGOV")`

### 6.2 Вывод
Если в docs/внешних интерфейсах используется термин `$LGOV`, нужно явно описать связь “LGOV (в терминах экономики) = AGOV (on-chain symbol)” либо синхронизировать нейминг.

---

## 7) SpiralEngine: две реализации (UUPS и non-UUPS) — важно не смешивать в docs

В репозитории присутствуют:
- `contracts/SpiralEngineLogic.sol` + `contracts/SpiralEngineProxy.sol` (UUPS)
- `contracts/SpiralEngine.sol` (не UUPS)

Если docs/интеграции/деплой-скрипты ссылаются на “SpiralEngine”, нужно фиксировать, **какой адрес ожидается** (proxy или не-proxy), иначе легко получить несовпадение ABI/поведения.

---

## Мини-чеклист для будущего исправления (когда будет время)
- [ ] Принять решение: какая версия LoveDo является канонической (nonce-based vs “старый” интерфейс).
- [ ] Привести `LoveEmissionEngine.sol` и `LoveDoPostNFT.sol` к единому интерфейсу (или сделать адаптер).
- [ ] Привести `LoveEmissionEngine.lovecoin.test.js` в соответствие с канонической версией LoveDo.
- [ ] Решить, кто является “source of truth” по `hasSellerRole`:
  - [ ] добавить метод в реестр, или
  - [ ] заменить проверку в LoveDo на SpiralEngine (если это канон), или
  - [ ] ввести отдельный контракт “SellerRegistry” и документировать его.
- [ ] Синхронизировать `contracts/docs/LoveEmissionEngine.md` с реальным `LoveEmissionEngine.sol` (нейминг + события).
- [ ] Синхронизировать документацию по токенам: LGOV термин ↔ AGOV символ.


