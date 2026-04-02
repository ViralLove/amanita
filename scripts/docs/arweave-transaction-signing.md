# Подпись транзакций Arweave в цепочке `deploy_full.js`

Кратко: загрузка в Arweave в проекте делается через пакет **`arweave`** (JS). Подпись — это **подпись Arweave-транзакции JWK-кошельком** (RSA), а не подпись Ethereum. Отдельно для контрактов используются **ethers** и приватный ключ seller/deployer — это другой слой (см. ниже).

---

## Где в процессе `deploy_full.js` появляется Arweave

1. **`scripts/deploy_full.js`** при старте создаёт **`ArweaveManager`** (`./lib/services/ArweaveManager.js`) и передаёт его в **`ActionsManager`** → **`ComponentActions`**.

2. Типичный сценарий с реальной загрузкой в сеть Arweave — **Action 555** (пайплайн 51 → 52 → 53) или отдельные шаги, где включена полная загрузка компонентов:
   - **Action 52** / внутри **555** вызывается **`uploadComponentFull`** в `ComponentActions.js`.
   - Перед этим **`ArweaveManager.initialize()`** читает JWK с диска (`ARWEAVE_KEY_PATH` / конфиг), поднимает клиент `Arweave.init({ host, port, protocol, ... })`.

3. Для каждого компонента собирается **`context`** для `upload_steps.js`, в том числе:

```javascript
arweave: {
  client: arweaveClient,  // из ArweaveManager.getClient()
  key: arweaveKey         // JWK из ArweaveManager.getKey()
}
```

См. фрагмент в `scripts/lib/actions/ComponentActions.js` (создание `context` перед `uploadSimpleFields` / `uploadComplexFields` / …).

4. Функция **`uploadToArweave`** в **`scripts/lib/upload_steps.js`** (и параллельно **`ArweaveManager.uploadData`** в **`ArweaveManager.js`**) выполняет одну и ту же последовательность:
   - **`createTransaction({ data }, key)`** — собрать транзакцию с полезной нагрузкой и учётом ключа (размер, reward).
   - **`transaction.addTag(...)`** — теги (Content-Type, имена файлов и т.д.).
   - **`transactions.sign(transaction, key)`** — **здесь выполняется криптографическая подпись** Arweave-транзакции ключом JWK.
   - **`transactions.post(transaction)`** — отправка на gateway (например `arweave.net`).

Итог: **подпись Arweave делается только на стороне скриптов деплоя / upload_steps**, в момент создания и отправки транзакции хранения данных.

---

## Что не является «Arweave-подписью» в этом пайплайне

- **Ethereum-транзакции** (вызовы `OrganicComponentRegistry`, `SpiralEngine` и т.д.) подписываются **`ethers`** через `sellerSigner` / `deployerSigner` — это **другой ключ** и другой тип подписи.
- В **Floou / бот / uploader** загрузка может идти через отдельный сервис; там схема «кто держит JWK» может отличаться. Этот документ привязан к **проверенному коду в `scripts/`** (`upload_steps` + `ArweaveManager`).

---

## Минимальный рабочий пример на JS (как в кодовой базе)

Зависимость: `arweave` (та же, что использует проект). Ключ — JSON **JWK** Arweave-кошелька (как в `.arweave-key.json`).

```javascript
const Arweave = require('arweave');
const fs = require('fs');

async function signAndPostExample() {
  const arweave = Arweave.init({
    host: 'arweave.net',
    port: 443,
    protocol: 'https',
  });

  const key = JSON.parse(fs.readFileSync(process.env.ARWEAVE_KEY_PATH || './.arweave-key.json', 'utf8'));

  const data = Buffer.from(JSON.stringify({ hello: 'from Amanita-style upload' }), 'utf8');

  const tx = await arweave.createTransaction({ data }, key);
  tx.addTag('Content-Type', 'application/json');
  tx.addTag('App-Name', 'Example');

  await arweave.transactions.sign(tx, key);

  const res = await arweave.transactions.post(tx);
  if (res.status !== 200) {
    throw new Error(`post failed: ${res.status}`);
  }
  console.log('tx id:', tx.id);
  console.log('url:', `https://arweave.net/${tx.id}`);
}

signAndPostExample().catch((e) => {
  console.error(e);
  process.exit(1);
});
```

Это тот же паттерн, что в **`ArweaveManager.uploadData`** (строки с `createTransaction` → `sign` → `post`) и в **`upload_steps.uploadToArweave`**.

---

## Ссылки на исходники

| Место | Роль |
|--------|------|
| `scripts/lib/services/ArweaveManager.js` | Инициализация клиента, загрузка JWK, `uploadData` / `uploadJSON` с подписью |
| `scripts/lib/upload_steps.js` → `uploadToArweave` | Пошаговая загрузка метаданных компонентов, теги, проверка баланса |
| `scripts/lib/actions/ComponentActions.js` → `uploadComponentFull` | Сборка `context.arweave`, вызов шагов upload_steps |
| `scripts/deploy_full.js` | Роутер actions; `ArweaveManager` создаётся в `DeployRouter.initialize()` |

---

## Эксплуатация

- Нужен **баланс AR** на Arweave-кошельке для оплаты хранения (в `uploadToArweave` есть проверка баланса перед первой реальной загрузкой).
- **Dry-run** в `upload_steps` подменяет TX ID без сети — подпись реальной транзакции не выполняется.
