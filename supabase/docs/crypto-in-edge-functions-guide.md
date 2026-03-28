# Гайд: криптография в Supabase Edge Functions

**Назначение:** руководство по использованию Deno и Web Crypto API в Supabase Edge Functions. Основано на реализации в `supabase/functions/arweave-upload`. Применимо к любому проекту с Edge Functions.

**Версия:** 1.0  
**Дата:** 2026-02-04

---

## 1. Контекст: что есть в Supabase Edge

Supabase Edge Functions выполняются в **Deno** (не Node.js). Доступны:

- **Web Crypto API** (`crypto.subtle`) — глобал, без импорта
- **Deno API** (`Deno.env`, `Deno.readTextFile` и т.д.) — глобал
- **ESM-импорты** — URL-модули (`https://deno.land/...`), npm (`npm:package@version`)

Библиотеки Node.js (например `node:crypto`) **не поддерживаются**. Используем только Web Crypto и Deno-совместимые пакеты.

---

## 2. Структура импортов

### 2.1 Deno-модули (URL)

```typescript
// HTTP-сервер (точная версия — стабильность)
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

// Тесты
import { assertEquals } from "https://deno.land/std@0.168.0/testing/asserts.ts";
```

**Правило:** указывать версию (`@0.168.0`), чтобы поведение не менялось после деплоя.

### 2.2 NPM-пакеты

```typescript
// Через npm: — Supabase/Deno резолвят автоматически
import Arweave from "npm:arweave@1.15.7";
```

В `deno.json` можно задать алиасы:

```json
{
  "imports": {
    "arweave": "npm:arweave@^1.15.7"
  }
}
```

Тогда: `import Arweave from "arweave"`.

### 2.3 Локальные модули

```typescript
// Расширение .ts обязательно
import { signArweaveTransaction } from "../crypto/arweave-rsa-pss.ts";
import { deepHash } from "./deep-hash.ts";
```

---

## 3. Deno API: env и файлы

### 3.1 Переменные окружения

```typescript
// Чтение — Deno.env.get()
const apiKey = Deno.env.get("API_KEY");
const path = Deno.env.get("ARWEAVE_PRIVATE_KEY_FILE");

// В тестах — set/delete
Deno.env.set("UPLOAD_TOKEN_JWT_PUBLIC_KEY", jsonString);
Deno.env.delete("BACKEND_USE_MOCK");
```

**Важно:** `Deno.env` — глобал. Не импортировать, не объявлять. В Edge Runtime он уже доступен.

### 3.2 Файлы (локальная разработка)

```typescript
const rawKey = await Deno.readTextFile(privateKeyFilePath);
const parsed = JSON.parse(rawKey);
```

В Supabase Cloud файловая система ограничена — для production ключи через **Secrets** (`ARWEAVE_PRIVATE_KEY` как JSON-строка).

---

## 4. Web Crypto API: использование

### 4.1 Общий принцип

`crypto` — глобал браузерного/Web Crypto API. Импорт не нужен:

```typescript
// Не нужно: import { crypto } from "..."
const hash = await crypto.subtle.digest("SHA-256", data);
```

### 4.2 Основные операции

#### SHA-256 (хэш)

```typescript
async function sha256(data: Uint8Array): Promise<Uint8Array> {
  const h = await crypto.subtle.digest("SHA-256", data);
  return new Uint8Array(h);
}
```

#### Импорт ключа (JWK)

```typescript
const key = await crypto.subtle.importKey(
  "jwk",
  { kty: "RSA", n: "...", e: "AQAB", d: "..." },
  { name: "RSA-PSS", hash: "SHA-256" },
  false,
  ["sign"]
);
```

#### Импорт ключа (PEM/SPKI)

```typescript
const pem = "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----";
const binary = Uint8Array.from(
  atob(pem.replace(/-----BEGIN PUBLIC KEY-----|-----END PUBLIC KEY-----|\s/g, "")),
  (c) => c.charCodeAt(0)
);
const key = await crypto.subtle.importKey(
  "spki",
  binary,
  { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
  false,
  ["verify"]
);
```

#### Подпись (RSA-PSS)

```typescript
const signature = await crypto.subtle.sign(
  { name: "RSA-PSS", saltLength: 32 },
  privateKey,
  dataToSign  // Uint8Array | ArrayBuffer
);
const signatureBytes = new Uint8Array(signature);
```

#### Проверка подписи (RSA-PSS)

```typescript
const valid = await crypto.subtle.verify(
  { name: "RSA-PSS", saltLength: 32 },
  publicKey,
  signature,   // ArrayBuffer | Uint8Array
  dataToVerify
);
```

#### Проверка подписи (RS256 / PKCS#1 v1.5)

```typescript
const valid = await crypto.subtle.verify(
  { name: "RSASSA-PKCS1-v1_5" },
  publicKey,
  signature,
  dataToVerify
);
```

#### Экспорт ключа в SPKI

```typescript
const exported = await crypto.subtle.exportKey("spki", publicKey);
const spkiBytes = new Uint8Array(exported);
```

### 4.3 Поддерживаемые алгоритмы (Deno)

| Алгоритм | importKey | sign | verify | digest |
|----------|-----------|------|--------|--------|
| RSA-PSS (saltLength 32) | ✅ | ✅ | ✅ | — |
| RSASSA-PKCS1-v1_5 (RS256) | ✅ | ✅ | ✅ | — |
| SHA-256 | — | — | — | ✅ |
| HMAC | ✅ | ✅ | ✅ | — |

---

## 5. Кодирование: base64 и base64url

Встроенные `btoa`/`atob` работают с base64. Для base64url — явное преобразование:

```typescript
function base64UrlDecode(s: string): Uint8Array {
  const base64 = s.replace(/-/g, "+").replace(/_/g, "/");
  const pad = base64.length % 4;
  const padded = pad ? base64 + "=".repeat(4 - pad) : base64;
  const binary = atob(padded);
  return new Uint8Array(binary.length).map((_, i) => binary.charCodeAt(i));
}

function base64UrlEncode(data: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < data.length; i++) binary += String.fromCharCode(data[i]);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
```

`TextEncoder` / `TextDecoder` — глобалы, доступны без импорта.

---

## 6. Конфигурация IDE и TypeScript

### 6.0 Ошибка: Cannot find module 'https://deno.land/std@0.168.0/http/server.ts'

**Симптом (ts 2307):**
```
Cannot find module 'https://deno.land/std@0.168.0/http/server.ts' or its corresponding type declarations.
```

**Причина:** IDE использует **встроенный TypeScript LSP**, который не резолвит URL-импорты. Deno же понимает их нативно — но только если за обработку файла отвечает **Deno LSP**, а не TypeScript.

**Диагностика:** открой файл в `supabase/functions/` и посмотри статус-бар (справа внизу). Если там **"TypeScript"** — работает встроенный TS, URL-импорты он не понимает. Если **"Deno"** — Deno LSP активен, ошибки быть не должно.

#### Решение A (рекомендуется): Deno extension + enablePaths

1. Установи расширение **Deno** (denoland.vscode-deno).
2. В `.vscode/settings.json`:

```json
{
  "deno.enable": true,
  "deno.enablePaths": ["supabase/functions"]
}
```

3. Перезагрузи окно (Cmd+Shift+P → "Developer: Reload Window").
4. Убедись, что в статус-баре для файлов в `supabase/functions/` отображается **Deno**.

Если `deno.json` лежит внутри `supabase/functions/arweave-upload/`, Deno сам найдёт его. Альтернатива — явно указать конфиг:

```json
{
  "deno.enable": true,
  "deno.enablePaths": ["supabase/functions"],
  "deno.config": "./supabase/functions/arweave-upload/deno.json"
}
```

#### Решение B: deno_shim.d.ts (когда Deno LSP недоступен)

Если Deno extension не ставишь или он не срабатывает — TypeScript должен подхватить `declare module` из shim.

1. **deno_shim.d.ts** в папке функции:

```typescript
declare module "https://deno.land/std@0.168.0/http/server.ts" {
  export function serve(
    handler: (req: Request) => Response | Promise<Response>,
    options?: { port?: number; hostname?: string }
  ): Promise<void>;
}
```

2. В **index.ts** в начале файла:

```typescript
/// <reference path="./deno_shim.d.ts" />
```

3. **tsconfig.json** в папке функции должен включать shim:

```json
{
  "include": ["**/*.ts", "deno_shim.d.ts", "deno_global.d.ts"]
}
```

4. Убедись, что IDE использует именно этот tsconfig. В монорепо корневой tsconfig может перехватывать файлы — тогда добавь в корень `references` или исключи `supabase/functions` из корневого include.

#### Решение C: Import map (workaround без смены LSP)

Замени URL на алиас, для которого легче написать `declare module`:

**deno.json:**
```json
{
  "imports": {
    "@std/server": "https://deno.land/std@0.168.0/http/server.ts"
  }
}
```

**index.ts:**
```typescript
import { serve } from "@std/server";
```

**deno_shim.d.ts:**
```typescript
declare module "@std/server" {
  export function serve(
    handler: (req: Request) => Response | Promise<Response>,
    options?: { port?: number; hostname?: string }
  ): Promise<void>;
}
```

#### Верификация

| Критерий | Проверка |
|----------|----------|
| Ошибка ts(2307) исчезла | Открыть `index.ts`, нет подсветки на `import { serve }` |
| Deno LSP активен (Решение A) | Статус-бар: "Deno" |
| Shim работает (Решение B/C) | Статус-бар: "TypeScript", но ошибки нет |

---

### 6.1 Проблема

IDE (VS Code, Cursor) может не знать `Deno` и `crypto` при работе с Edge Functions. Нужны декларации.

### 6.2 Решение: минимальные .d.ts

**deno_shim.d.ts** — для URL-модулей:

```typescript
declare module "https://deno.land/std@0.168.0/http/server.ts" {
  export function serve(
    handler: (req: Request) => Response | Promise<Response>,
    options?: { port?: number; hostname?: string }
  ): Promise<void>;
}
```

**deno_global.d.ts** — для глобала Deno (только то, что реально используется):

```typescript
declare global {
  const Deno: {
    env: { get(key: string): string | undefined; set?(key: string, value: string): void; delete?(key: string): void };
    readTextFile(path: string): Promise<string>;
  };
}
export {};
```

**Важно:** не объявлять `crypto` — он уже есть в `lib: ["deno.ns", "dom"]`. Если tsconfig использует `"types": []`, может понадобиться `"lib": ["ES2022", "DOM"]` для Web Crypto.

### 6.3 tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "noEmit": true,
    "skipLibCheck": true,
    "strict": true,
    "allowImportingTsExtensions": true,
    "types": []
  },
  "include": ["**/*.ts", "deno_shim.d.ts", "deno_global.d.ts"]
}
```

### 6.4 Подключение в index.ts

```typescript
/// <reference path="./deno_shim.d.ts" />
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
```

`deno_global.d.ts` подхватывается через `include` в tsconfig, без явной ссылки в index.ts (избегаем конфликта с lib.deno.ns.d.ts при `deno check`).

### 6.5 deno.json

```json
{
  "imports": { "arweave": "npm:arweave@^1.15.7" },
  "compilerOptions": {
    "lib": ["deno.ns", "dom", "deno.window"]
  }
}
```

`deno.ns` даёт Deno API, `dom` — Web Crypto, `TextEncoder`, `btoa`, `atob`.

---

## 7. Тесты: Deno.test и crypto

```typescript
import { assertEquals } from "https://deno.land/std@0.168.0/testing/asserts.ts";

Deno.test("sign and verify", async () => {
  const keyPair = await crypto.subtle.generateKey(
    { name: "RSA-PSS", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" },
    true,
    ["sign", "verify"]
  );
  const data = new TextEncoder().encode("hello");
  const sig = await crypto.subtle.sign(
    { name: "RSA-PSS", saltLength: 32 },
    keyPair.privateKey,
    data
  );
  const ok = await crypto.subtle.verify(
    { name: "RSA-PSS", saltLength: 32 },
    keyPair.publicKey,
    sig,
    data
  );
  assertEquals(ok, true);
});
```

Запуск: `deno test tests/ --allow-env --allow-read`

---

## 8. Чеклист для нового проекта

- [ ] Импорт `serve` из `https://deno.land/std@0.168.0/http/server.ts`
- [ ] Ошибка ts(2307) на URL-импорте устранена (раздел 6.0: Deno LSP или shim)
- [ ] NPM-пакеты через `npm:name@version`
- [ ] `crypto.subtle` — без импорта, как глобал
- [ ] `Deno.env.get()` — для секретов и конфигурации
- [ ] `deno.json` с `lib: ["deno.ns", "dom"]`
- [ ] `deno_shim.d.ts` и `deno_global.d.ts` при необходимости для IDE
- [ ] Тесты: `deno test --allow-env --allow-read`
- [ ] Base64/base64url: свои утилиты или `atob`/`btoa` с заменой символов

---

## 9. Частые ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `Cannot find module 'https://deno.land/std@...'` (ts 2307) | TypeScript LSP не резолвит URL-импорты | Раздел 6.0: Deno extension + enablePaths, или deno_shim.d.ts, или import map |
| `crypto is not defined` | Среда без Web Crypto (старый Node) | Edge Functions = Deno, crypto доступен |
| `Deno is not defined` | IDE не знает глобал | Добавить deno_global.d.ts |
| `Transaction verification failed` (Arweave) | Неверный saltLength | Использовать `saltLength: 32` для RSA-PSS |
| `importKey failed` | Неверный формат JWK/SPKI | Проверить структуру ключа и алфавит base64 |

---

## 10. Референс: файлы проекта arweave-upload

| Файл | Назначение |
|------|------------|
| `index.ts` | Entry, `serve`, `Deno.env.get`, `Deno.readTextFile` |
| `crypto/arweave-rsa-pss.ts` | RSA-PSS sign, `crypto.subtle.importKey/sign/digest` |
| `publish/validate-token.ts` | JWT RS256 verify, PEM/JWK import, `crypto.subtle.verify` |
| `publish/validate-data-item.ts` | RSA-PSS verify, SPKI import, `crypto.subtle.digest` |
| `publish/deep-hash.ts` | SHA-256 chain, `crypto.subtle.digest` |
| `deno_shim.d.ts` | Декларация URL-модуля serve |
| `deno_global.d.ts` | Декларация Deno для IDE |
| `deno.json` | imports, compilerOptions.lib |

---

**Связанные документы:** [arweave-upload-security.md](./arweave-upload-security.md), [deno-webcrypto-rsassa-pss-analysis.md](../functions/arweave-upload/deno-webcrypto-rsassa-pss-analysis.md)
