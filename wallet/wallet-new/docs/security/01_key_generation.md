// docs/spec/01_key_generation.md

# 01_key_generation — Key generation & derivation (EVM)

## Цель
Создать безопасную генерацию seed/mnemonic и деривацию EVM-ключей/адресов для кошелька в React Native.

## Инварианты безопасности
- Энтропия генерируется криптостойко (RN secure RNG).
- Mnemonic/seed никогда не пишется в логи/аналитику.
- Деривация детерминирована и тестируется на векторах.
- Поддержка нескольких аккаунтов через index, без “прыжков” путей.

## MVP scope
- BIP39 mnemonic (12/24 слова).
- BIP32 derivation.
- Один стандартный путь: `m/44'/60'/0'/0/i` (i = index).
- Получение: address + publicKey + (внутренне) privateKey handle.

## Не делаем в MVP
- Мультичейн пути, SLIP-44 матрица.
- Smart accounts derivation.
- Seedless onboarding.

## Публичный API (предложение)
- `generateMnemonic(words: 12|24): Mnemonic`
- `mnemonicToSeed(mnemonic, passphrase?): SeedBytes`
- `deriveAccount(seed, index): { address, publicKey, privateKeyBytes }`
- `validateMnemonic(mnemonic): boolean`

## Edge cases
- Неверная мнемоника (checksum).
- Повторная генерация при отсутствии RNG.
- Тест совместимости адресов (EIP-55 checksum отображение).

## Тесты (минимум)
- BIP39 test vectors (mnemonic → seed).
- Derivation test vectors (seed → address).
- Regression: один и тот же seed/index даёт тот же address.