// docs/reference/02_secure_storage_vault-metamask-map.md

# 02_secure_storage_vault — MetaMask reference map

## Что подсматривать
- Как они отделяют “vault blob” от secure storage ключа.
- Их подход к passworder/encryption (концептуально).
- Их защита от supply-chain (LavaMoat) как обязательная часть безопасности.

## Где искать
Поиск:
- `react-native-keychain`
- `vault`
- `encrypt` / `decrypt`
- `passworder`
- `aes` (`react-native-aes-crypto`)
- `lock` / `unlock` / `biometric`

## Что НЕ копировать
- Их конкретный формат стора/миграций без понимания.
- Их сложные flows seedless onboarding.

## Перевод в твой дизайн
- Сделать свой `VaultService` с маленьким API.
- Ключ шифрования хранить в keychain; данные vault — отдельным blob (MMKV/FS) но только в зашифрованном виде.
- Минимизировать lifetime секретов в JS.