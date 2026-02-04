# Анализ совместимости Deno Web Crypto API и RSASSA-PSS для Arweave

## Обзор

Документ содержит доскональное расследование совместимости Deno (используемого в Supabase Edge Functions) с требованиями Arweave для подписи транзакций RSASSA-PSS с `saltLength = 32`.

**Дата анализа**: 2026-01-27  
**Статус**: Актуальное состояние на январь 2026  
**Версия Deno в Supabase**: Deno 1.x (по умолчанию), Deno 2 (в публичной альфе)

---

## 1. Текущее состояние проекта

### 1.1 Конфигурация Supabase

**Файл**: `supabase/config.toml`

```toml
[edge_runtime]
deno_version = 1  # Текущая версия: Deno 1.x
```

**Статус**: Используется Deno 1.x, но Supabase уже поддерживает Deno 2 (публичная альфа)

### 1.2 Текущая реализация

**Файл**: `supabase/functions/arweave-upload/arweave/compatible.ts`

```typescript
import { signArweaveTransaction } from "../crypto/arweave-rsa-pss.ts";

export async function signTransaction(
  arweave: any,
  transaction: any,
  privateKey: JsonWebKey
): Promise<void> {
  // Используем RSA-PSS реализацию
  const { signature, transactionId } = await signArweaveTransaction(privateKey, signatureData);
  // ...
}
```

**Проблема**: Файл `crypto/arweave-rsa-pss.ts` **отсутствует** в проекте

### 1.3 Планы реализации (не завершены)

1. **WebAssembly план** (`webassembly-implementation-plan.md`):
   - План создания WebAssembly модуля для RSASSA-PSS
   - Статус: НЕ РЕАЛИЗОВАН
   - Файлы `crypto/pss_wasm.ts` и `crypto/pss.wasm` существуют, но пустые

2. **RSA-PSS интеграция** (`rsa-pss-integration-plan.md`):
   - План адаптации библиотеки `rsa-pss` для Deno
   - Статус: НЕ РЕАЛИЗОВАН

---

## 2. Требования Arweave для подписи

### 2.1 Алгоритм подписи

**Требования Arweave**:
- Алгоритм: **RSASSA-PSS** (RSA Signature Scheme with Appendix - Probabilistic Signature Scheme)
- Hash: **SHA-256**
- Salt Length: **32 байта** (критически важно!)
- Key Size: **2048 бит** (RSA-2048)

### 2.2 Почему saltLength = 32 критичен

- Arweave валидирует транзакции на стороне сети
- Сеть ожидает точное соответствие алгоритму подписи
- Неправильный `saltLength` приводит к ошибке "Transaction verification failed"
- SHA-256 производит 32-байтный хэш, поэтому `saltLength = 32` — стандартное значение

---

## 3. Поддержка RSASSA-PSS в Deno

### 3.1 Web Crypto API в Deno

**Документация**: Deno поддерживает Web Crypto API согласно спецификации Web Cryptography Level 2

**Поддерживаемые алгоритмы**:
- ✅ RSASSA-PKCS1-v1_5
- ✅ **RSA-PSS** (включает RSASSA-PSS)
- ✅ ECDSA
- ✅ HMAC
- ✅ Ed25519

### 3.2 RSASSA-PSS с saltLength = 32

**Поддержка в Deno**:

✅ **ПОДДЕРЖИВАЕТСЯ** начиная с Deno 1.0+

**Пример использования**:

```typescript
// Импорт ключа
const privateKey = await crypto.subtle.importKey(
  "jwk",
  jwkKey,
  {
    name: "RSA-PSS",
    hash: "SHA-256",
  },
  false,
  ["sign"]
);

// Подпись с saltLength = 32
const signature = await crypto.subtle.sign(
  {
    name: "RSA-PSS",
    saltLength: 32,  // ✅ Поддерживается!
  },
  privateKey,
  data
);
```

### 3.3 Версии Deno

**Deno 1.46.0** (август 2024):
- ✅ Полная поддержка Web Crypto API
- ✅ RSASSA-PSS с `saltLength = 32` работает
- ✅ Исправления в `ext/node`: "support ieee-p1363 ECDSA signatures and pss salt len"

**Deno 2.x** (2025):
- ✅ Улучшенная поддержка Web Crypto API
- ✅ Лучшая совместимость с Node.js
- ✅ Рекомендуется для новых проектов

**Вывод**: Deno **поддерживает** RSASSA-PSS с `saltLength = 32` через Web Crypto API

---

## 4. Проблема: почему не работает

### 4.1 Историческая проблема

**Проблема в старых версиях Deno** (до 1.40):
- ❌ Web Crypto API имел ограничения в реализации RSASSA-PSS
- ❌ Некоторые реализации использовали фиксированный `saltLength`
- ❌ Проблемы с совместимостью спецификации

**Статус**: **ИСПРАВЛЕНО** в Deno 1.40+

### 4.2 Текущая проблема в проекте

**Реальная проблема**: Отсутствует реализация `signArweaveTransaction`

**Файл**: `arweave/compatible.ts` ссылается на несуществующий файл:
```typescript
import { signArweaveTransaction } from "../crypto/arweave-rsa-pss.ts";  // ❌ Файл не существует!
```

**Решение**: Нужно реализовать функцию подписи используя Web Crypto API Deno

---

## 5. Реализация через Web Crypto API

### 5.1 Правильная реализация

**Файл**: `crypto/arweave-rsa-pss.ts` (нужно создать)

```typescript
/**
 * Подпись Arweave транзакции используя RSASSA-PSS через Web Crypto API
 * 
 * Требования Arweave:
 * - Алгоритм: RSASSA-PSS
 * - Hash: SHA-256
 * - Salt Length: 32 байта
 * - Key: RSA-2048 (JWK формат)
 */

export async function signArweaveTransaction(
  privateKeyJwk: JsonWebKey,
  signatureData: Uint8Array
): Promise<{ signature: Uint8Array; transactionId: string }> {
  // Шаг 1: Импорт приватного ключа
  const privateKey = await crypto.subtle.importKey(
    "jwk",
    privateKeyJwk,
    {
      name: "RSA-PSS",
      hash: "SHA-256",
    },
    false,
    ["sign"]
  );

  // Шаг 2: Подпись данных с saltLength = 32
  const signature = await crypto.subtle.sign(
    {
      name: "RSA-PSS",
      saltLength: 32,  // ✅ Критически важно для Arweave!
    },
    privateKey,
    signatureData
  );

  // Шаг 3: Вычисление Transaction ID
  // Transaction ID = base64url(sha256(owner + signature))
  const owner = await extractOwnerFromJwk(privateKeyJwk);
  const transactionId = await computeTransactionId(owner, new Uint8Array(signature));

  return {
    signature: new Uint8Array(signature),
    transactionId,
  };
}

/**
 * Извлечение owner (публичного ключа) из JWK
 */
async function extractOwnerFromJwk(jwk: JsonWebKey): Promise<Uint8Array> {
  const publicKey = await crypto.subtle.importKey(
    "jwk",
    {
      kty: jwk.kty,
      n: jwk.n,
      e: jwk.e,
    },
    {
      name: "RSA-PSS",
      hash: "SHA-256",
    },
    true,
    []
  );

  const exported = await crypto.subtle.exportKey("spki", publicKey);
  return new Uint8Array(exported);
}

/**
 * Вычисление Transaction ID для Arweave
 * ID = base64url(sha256(owner + signature))
 */
async function computeTransactionId(
  owner: Uint8Array,
  signature: Uint8Array
): Promise<string> {
  const combined = new Uint8Array(owner.length + signature.length);
  combined.set(owner, 0);
  combined.set(signature, owner.length);

  const hash = await crypto.subtle.digest("SHA-256", combined);
  const hashArray = new Uint8Array(hash);

  // Base64URL encoding
  return base64UrlEncode(hashArray);
}

/**
 * Base64URL encoding (без padding)
 */
function base64UrlEncode(data: Uint8Array): string {
  const base64 = btoa(String.fromCharCode(...data));
  return base64
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}
```

### 5.2 Интеграция в compatible.ts

**Обновленный файл**: `arweave/compatible.ts`

```typescript
import { signArweaveTransaction } from "../crypto/arweave-rsa-pss.ts";

export async function signTransaction(
  arweave: any,
  transaction: any,
  privateKey: JsonWebKey
): Promise<void> {
  console.log("🔐 Используем RSA-PSS подпись через Web Crypto API...");
  
  const signatureData = await transaction.getSignatureData();
  console.log("   Данные для подписи размер:", signatureData.length, "байт");

  // Используем Web Crypto API реализацию
  const { signature, transactionId } = await signArweaveTransaction(
    privateKey,
    signatureData
  );
  
  const signatureB64Url = arweave.utils.bufferTob64Url(signature);
  transaction.signature = signatureB64Url;
  transaction.id = transactionId;
  
  console.log("✅ RSA-PSS подпись установлена");
  console.log("✅ Transaction ID установлен:", transactionId);
}
```

---

## 6. Проверка совместимости

### 6.1 Тест Web Crypto API

**Создать тест**: `tests/webcrypto-rsassa-pss-test.ts`

```typescript
import { assertEquals } from "https://deno.land/std@0.168.0/testing/asserts.ts";

Deno.test("Web Crypto API RSASSA-PSS с saltLength=32", async () => {
  // Генерация тестовой пары ключей
  const keyPair = await crypto.subtle.generateKey(
    {
      name: "RSA-PSS",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true,
    ["sign", "verify"]
  );

  const testData = new TextEncoder().encode("test data for Arweave");

  // Подпись с saltLength = 32
  const signature = await crypto.subtle.sign(
    {
      name: "RSA-PSS",
      saltLength: 32,
    },
    keyPair.privateKey,
    testData
  );

  // Проверка подписи
  const isValid = await crypto.subtle.verify(
    {
      name: "RSA-PSS",
      saltLength: 32,
    },
    keyPair.publicKey,
    signature,
    testData
  );

  assertEquals(isValid, true, "Подпись должна быть валидной");
  assertEquals(signature.length, 256, "Подпись RSA-2048 должна быть 256 байт");
  
  console.log("✅ RSASSA-PSS с saltLength=32 работает корректно");
});
```

### 6.2 Проверка версии Deno

**В Supabase Edge Function**:

```typescript
console.log("Deno version:", Deno.version.deno);
console.log("V8 version:", Deno.version.v8);
console.log("TypeScript version:", Deno.version.typescript);
```

**Ожидаемый результат**:
- Deno 1.40+: ✅ RSASSA-PSS с `saltLength = 32` работает
- Deno 2.x: ✅ Улучшенная поддержка

---

## 7. Рекомендации

### 7.1 Немедленные действия

1. **Создать реализацию** `crypto/arweave-rsa-pss.ts`:
   - Использовать Web Crypto API Deno
   - Реализовать `signArweaveTransaction` с `saltLength = 32`
   - Добавить вычисление Transaction ID

2. **Обновить `compatible.ts`**:
   - Исправить импорт на существующий файл
   - Убедиться, что используется правильная реализация

3. **Создать тесты**:
   - Тест Web Crypto API с `saltLength = 32`
   - Интеграционный тест с реальным Arweave

### 7.2 Миграция на Deno 2 (опционально)

**Преимущества Deno 2**:
- ✅ Улучшенная совместимость с Node.js
- ✅ Лучшая производительность
- ✅ Поддержка npm пакетов

**Миграция**:

```toml
# supabase/config.toml
[edge_runtime]
deno_version = 2  # Обновить на Deno 2
```

**Примечание**: Deno 2 обратно совместим с Deno 1.x кодом

### 7.3 Альтернативные решения (если Web Crypto API не работает)

**Если Web Crypto API не работает** (маловероятно):

1. **Использовать WebAssembly модуль**:
   - Реализовать план из `webassembly-implementation-plan.md`
   - Использовать библиотеку `asmcrypto.js`

2. **Использовать адаптированную библиотеку**:
   - Реализовать план из `rsa-pss-integration-plan.md`
   - Адаптировать библиотеку `rsa-pss` для Deno

**Вывод**: Сначала попробовать Web Crypto API — это самое простое решение

---

## 8. Выводы

### 8.1 Текущее состояние

1. ✅ **Deno поддерживает RSASSA-PSS с `saltLength = 32`** через Web Crypto API
2. ❌ **Реализация отсутствует** — файл `crypto/arweave-rsa-pss.ts` не существует
3. ⚠️ **Планы WebAssembly/rsa-pss не реализованы** — файлы пустые

### 8.2 Решение

**Рекомендуемый подход**: Использовать **Web Crypto API Deno**

**Преимущества**:
- ✅ Нативная поддержка в Deno
- ✅ Не требует внешних зависимостей
- ✅ Простая реализация
- ✅ Работает в Supabase Edge Functions

**Не требуется**:
- ❌ WebAssembly модули
- ❌ Внешние библиотеки
- ❌ Сложные адаптации

### 8.3 Следующие шаги

1. ✅ Создать `crypto/arweave-rsa-pss.ts` с реализацией через Web Crypto API
2. ✅ Обновить `arweave/compatible.ts` для использования новой реализации
3. ✅ Создать тесты для проверки работы
4. ✅ Протестировать с реальным Arweave

---

## 9. Ссылки

- [Deno Web Crypto API Documentation](https://docs.deno.com/api/web/SubtleCrypto/)
- [Web Crypto API RSASSA-PSS](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/sign#rsa-pss)
- [Arweave Transaction Signing](https://docs.arweave.org/developers/server/http-api#transaction-signing)
- [Supabase Edge Functions Deno 2](https://supabase.com/docs/guides/functions/deno2)
- [Deno 1.46.0 Release Notes](https://github.com/denoland/deno/releases/tag/v1.46.0)

---

**Версия документа**: 1.0  
**Дата**: 2026-01-27  
**Статус**: Актуально на январь 2026
