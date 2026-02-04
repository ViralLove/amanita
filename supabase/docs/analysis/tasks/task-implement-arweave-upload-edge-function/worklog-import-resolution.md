# Worklog: Импорт в index.ts не работает (IDE)

**Дата:** 2026-01-29  
**Проблема:** В `supabase/functions/arweave-upload/index.ts` импорт и глобал Deno помечаются IDE как ошибки.

---

## 1. Описание ошибки

### Симптомы (ReadLints)
```
L1:23 - Cannot find module 'https://deno.land/std@0.168.0/http/server.ts' or its corresponding type declarations. (ts)
L23:30 - Cannot find name 'Deno'. (ts)
L29:26 - Cannot find name 'Deno'. (ts)
```

### Контекст
- Файл: `supabase/functions/arweave-upload/index.ts`
- Импорты: URL (`https://deno.land/std@0.168.0/http/server.ts`), import map (`arweave`), локальные пути
- Окружение: Cursor, workspace root = Amanita (не arweave-upload)
- `deno check index.ts` из папки arweave-upload — **успешен** (Deno CLI резолвит всё)
- Линтер: источник ошибок — **(ts)** — TypeScript language server

---

## 2. Гипотезы

### 2.1 IDE использует TypeScript LSP, а не Deno LSP
**Гипотеза:** Для этого файла активен обычный TypeScript/Node language server; он не знает URL-импортов и глобала `Deno`.  
**Обоснование:** Ошибки помечены как `(ts)`; Deno CLI резолвит те же импорты.  
**Вероятность:** Высокая  
**Влияние:** P1 (подсветка и навигация, не блокирует `deno run`)

### 2.2 Конфиг Deno не применяется к файлу (корень workspace — Amanita)
**Гипотеза:** `deno.json` лежит в `supabase/functions/arweave-upload/`, а корень workspace — Amanita; LSP не связывает файл с этим конфигом.  
**Обоснование:** В корне нет deno.json; в .vscode заданы `deno.enablePaths: ["supabase/functions"]`.  
**Вероятность:** Средняя (если бы Deno LSP был активен, enablePaths должен был бы помочь).  
**Влияние:** P1

### 2.3 В Cursor нет/не используется расширение Deno
**Гипотеза:** Cursor не использует denoland.vscode-deno (ранее formatter с этим ID был недоступен), поэтому Deno LSP не запускается.  
**Обоснование:** В списке допустимых formatter'ов не было denoland.vscode-deno.  
**Вероятность:** Высокая  
**Влияние:** P1

---

## 3. Приоритизация

Проверять в порядке: **2.1 → 2.3 → 2.2**. Итог: причина в том, что для файла работает **TypeScript (ts)**, а не Deno LSP.

---

## 4. Решение: удовлетворить TypeScript без Deno LSP

Раз Cursor, по всей видимости, не использует Deno LSP для этого файла, убираем ошибки **на стороне TypeScript**: объявить модуль по URL и глобал `Deno`, чтобы ts не ругался.

**Действия:**
1. Добавить декларационный файл (например, `deno_shim.d.ts`) в `supabase/functions/arweave-upload/`.
2. В нём: объявить модуль `https://deno.land/std@0.168.0/http/server.ts` (экспорт `serve`) и глобал `Deno` (как минимум `Deno.env.get`).
3. Подключить этот файл через `/// <reference path="..." />` в начале `index.ts` или через `include`/`compilerOptions.types` в `deno.json`, если ts подхватывает deno.json.

---

## 5. Результат теста и применение

**Гипотеза 2.1 подтверждена:** для файла использовался TypeScript LSP (ts), а не Deno LSP.

**Применённое решение:**
1. **deno_shim.d.ts** — объявление только модуля `https://deno.land/std@0.168.0/http/server.ts` (export serve). Подключается через `/// <reference path="./deno_shim.d.ts" />` в index.ts. Deno при `deno check` загружает этот файл; глобал Deno в нём не объявляем, чтобы не конфликтовать с lib.deno.ns.d.ts.
2. **deno_global.d.ts** — объявление глобала `Deno` (env.get, readTextFile). Подключается только через tsconfig.json (include). Из index.ts не ссылаем, чтобы deno check не загружал и не конфликтовал с типами Deno.
3. **tsconfig.json** — создан в arweave-upload: include `**/*.ts`, deno_shim.d.ts, deno_global.d.ts; compilerOptions allowImportingTsExtensions, types []. IDE подхватывает этот проект и получает типы из обоих .d.ts.

**Проверка:**
- `deno check index.ts` — успешен.
- ReadLints для index.ts — ошибок нет.

**Итог:** Импорт и глобал Deno в IDE больше не подсвечиваются; Deno CLI по-прежнему работает.
