// docs/spec/03_account_model.md

# 03_account_model — Account model (EOA now, hooks for smart accounts)

## Цель
Единая модель аккаунтов: адреса, индексы, метаданные, выбор активного аккаунта, импорт.

## Инварианты
- Источник истины: локальный state + derivation index (для HD).
- Адреса не зависят от RPC.
- Любой импорт ключа проходит через secure storage.

## MVP scope
- HD accounts: index 0..N.
- Import private key (опционально) как отдельный “keyring type”.
- Active account selection.

## Публичный API
- `listAccounts(): Account[]`
- `createNextHdAccount(): Account`
- `importPrivateKey(pk): Account`
- `setActiveAccount(id): void`

## Hooks for future
- account type: `EOA | SMART | WATCH`
- signer abstraction