// docs/reference/01_key_generation-metamask-map.md

# 01_key_generation — MetaMask reference map

## Что подсматривать (паттерны)
- Их “keyring” подход: HD keyring, account tree, key-tree.
- Как они организуют derivation и индексацию аккаунтов.
- Как они минимизируют риск RNG/полифиллов в RN.

## Где искать в metamask-mobile
Ищи по репо (локально через rg/поиск Cursor):
- `eth-hd-keyring`
- `KeyringController`
- `account-tree-controller` / `AccountTreeController`
- `key-tree`
- `scure-bip39` / `bip32`
- `get-random-values` / `randombytes`

Примеры запросов:
- `KeyringController`
- `EthHdKeyring`
- `derive` + `m/44'/60'`
- `bip39` / `mnemonic`

## Что НЕ копировать
- Их сложную мультичейн/снап архитектуру на старте.
- Их dependency patching как “код”, а взять идею дисциплины.
- Любые куски, которые завязаны на internal services/feature flags.

## Как перевести в свой дизайн
- Вынести derivation в отдельный модуль `crypto/hd.ts`.
- Дать тонкий API (generate/validate/derive).
- В RN обеспечить secure RNG через `react-native-get-random-values` (и/или expo-random).

## Красные флаги
- Любая генерация entropy через Math.random.
- Хранение seed вне secure storage.
- Логи с mnemonic/seed.