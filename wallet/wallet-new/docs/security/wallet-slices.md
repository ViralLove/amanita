// docs/wallet-slices.md

# Wallet slices (Amanita Wallet)

Цель: разбить разработку кошелька на независимые “срезы” (вертикальные фичи), чтобы:
- не изобретать велосипед,
- подсматривать у MetaMask Mobile осмысленно,
- не копипастить код,
- держать TCB (trusted computing base) маленьким.

## Правила
1) Каждый срез = отдельный модуль + минимальный публичный API.
2) На каждый срез есть:
   - `docs/spec/<slice>.md` — твой дизайн (инварианты, API, edge cases).
   - `docs/reference/<slice>-metamask-map.md` — карта референса (где смотреть в MetaMask, что заимствовать, что избегать).
3) Сначала пишем Spec, потом смотрим Reference map, потом реализуем, потом тестируем.
4) Запрещено: копипаста больших блоков. Разрешено: перенять паттерн и реализовать по своему API.

## Срезы (v1)

### 01_key_generation
Генерация seed/mnemonic и derivation для EVM-аккаунтов (BIP39/BIP32, пути, entropy).

### 02_secure_storage_vault
Хранение секретов на устройстве: Keychain/Keystore, зашифрованный vault, unlock/lock, биометрия.

### 03_account_model
Модель аккаунтов: EOA в MVP, подготовка к smart accounts; сеть/chainId, адреса, индексация, импорт.

### 04_provider_rpc_layer
EIP-1193 provider слой, RPC клиенты, middleware, конфиги сетей, fallback RPC, rate limit.

### 05_signing_messages
Подпись сообщений: personal_sign, eth_sign, EIP-712 typed data; домены, анти-фишинг UX.

### 06_transactions_lifecycle
Жизненный цикл транзакции: построение, симуляция (опционально), комиссии, nonce, отправка, трекинг, замена/ускорение/отмена.

### 07_permissions_approvals
Approval pipeline: запросы от dapp/внутренних модулей, UI подтверждения, политики разрешений, журнал событий.

### 08_tokens_assets
Токены и ассеты: ERC20/721/1155, balances, decimals, metadata, caching, spam filtering, добавление токенов.

### 09_commerce_checkout_flows
E-commerce сценарии: approve/permit, “корзина→подпись заказа”, “оплата→mint/receipt”, статусы заказа.

### 10_multisig_and_delegation
Мультисиг/делегирование: Safe-подобные, delegation permissions, подготовка к AA; минимальный слой абстракции подписантов.

### 11_dao_governance
DAO-фичи: proposals, voting, delegation, signatures для голосований, интеграция с Governor/Snapshot (опционально).

### 12_security_hardening
Supply-chain безопасность и hardening: зависимостная политика, запрет скриптов, runtime lockdown, секреты, telemetry/логирование без утечек.

## MVP порядок реализации (рекомендовано)
1) 01, 02, 03, 04
2) 05, 06
3) 07, 08
4) 09
5) 10, 11 (после стабилизации ядра)
6) 12 — параллельно, но обязательный минимум с первого дня