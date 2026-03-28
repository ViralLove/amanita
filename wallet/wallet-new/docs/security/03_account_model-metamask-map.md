// docs/reference/03_account_model-metamask-map.md

# 03_account_model — MetaMask reference map

## Что подсматривать
- Account controllers и keyring types.
- Разделение “accounts metadata” и “key material”.

## Где искать
- `accounts-controller`
- `preferences-controller` (active account)
- `keyring-controller`
- `eth-hd-keyring`
- `account-tree-controller`

## Не копировать
- Их мультичейн account service целиком.
- Их UI state shape (слишком большой).

## Перевод
- Свой `AccountsStore` + `KeyringAdapter` интерфейс.
- Метаданные аккаунта (name, createdAt) отдельно от секретов.