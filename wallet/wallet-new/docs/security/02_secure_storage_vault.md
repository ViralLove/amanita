// docs/spec/02_secure_storage_vault.md

# 02_secure_storage_vault — Secure storage & Vault

## Цель
Некастодиально хранить секреты (seed/private key material) в RN, поддержать lock/unlock и опциональную биометрию.

## Инварианты безопасности
- Секреты хранятся только в OS secure storage (Keychain/Keystore).
- В памяти секреты живут минимально (zeroize где возможно).
- Vault зашифрован (AES-GCM/CTR+HMAC) ключом, защищённым устройством.
- Нет утечек в crash logs/analytics.

## MVP scope
- Setup vault при создании кошелька.
- Unlock с PIN/biometric (если доступно).
- Auto-lock по таймеру/фон.

## Публичный API (предложение)
- `initVault(): Promise<void>`
- `storeSeed(seedBytes): Promise<void>`
- `unlock(auth): Promise<UnlockedSession>`
- `lock(): Promise<void>`
- `isUnlocked(): boolean`
- `deleteVault(): Promise<void>` (dangerous, с подтверждением)

## Edge cases
- Миграция Keychain записи (смена bundle id / переустановка).
- Потеря biometric set.
- Android backups/keystore reset.

## Тесты
- Unit: шифрование/дешифрование.
- Интеграция: lock/unlock state machine.