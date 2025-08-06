# 🎯 ПЛАН РЕАЛИЗАЦИИ WEBASSEMBLY МОДУЛЯ ДЛЯ RSASSA-PSS

## 📋 ОБЗОР ПРОЕКТА

### 🎯 Цель
Создать WebAssembly модуль для подписи RSASSA-PSS с saltLength = 32, совместимый с требованиями ArWeave, работающий в среде Deno (Supabase Edge Functions).

### 🔍 Проблема
- Deno WebCrypto API не поддерживает RSASSA-PSS с saltLength = 32
- ArWeave требует именно этот алгоритм для валидации транзакций
- Существующие JS библиотеки не работают корректно с ArWeave

### 💡 Решение
WebAssembly модуль на основе asmcrypto.js, обеспечивающий нативную криптографию без ограничений Deno.

## 🚀 ПЛАН РЕАЛИЗАЦИИ

### Этап 1: ПОДГОТОВКА И АНАЛИЗ (1-2 часа)
- [ ] Скачать и изучить asmcrypto.js библиотеку
- [ ] Проанализировать структуру и зависимости
- [ ] Определить необходимые функции для RSASSA-PSS
- [ ] Изучить процесс компиляции в WebAssembly

### Этап 2: СОЗДАНИЕ WEBASSEMBLY МОДУЛЯ (2-3 часа)
- [ ] Создать базовую структуру проекта
- [ ] Настроить компиляцию asmcrypto.js в WebAssembly
- [ ] Создать pss.wasm модуль
- [ ] Протестировать базовую функциональность

### Этап 3: TYPESCRIPT ОБВЯЗКА (1-2 часа)
- [ ] Создать pss_wasm.ts интерфейс
- [ ] Реализовать функции загрузки WebAssembly
- [ ] Создать типизированный API для подписи
- [ ] Добавить обработку ошибок

### Этап 4: ИНТЕГРАЦИЯ В EDGE FUNCTION (1 час)
- [ ] Обновить compatible.ts для использования WebAssembly
- [ ] Удалить старые файлы (sign.ts, arweave-rsa-pss.ts)
- [ ] Протестировать интеграцию
- [ ] Обновить импорты и зависимости

### Этап 5: ТЕСТИРОВАНИЕ И ВАЛИДАЦИЯ (1-2 часа)
- [ ] Создать тесты для WebAssembly модуля
- [ ] Протестировать с реальными ArWeave транзакциями
- [ ] Проверить производительность (< 100мс)
- [ ] Валидировать Transaction ID (начинается с 'ar')

### Этап 6: ОПТИМИЗАЦИЯ И ДОКУМЕНТАЦИЯ (1 час)
- [ ] Оптимизировать производительность
- [ ] Создать документацию
- [ ] Обновить AI-Navigator.md
- [ ] Финальное тестирование

## 🔧 ТЕХНИЧЕСКИЕ ДЕТАЛИ

### Структура файлов
```
supabase/functions/arweave-upload/
├── crypto/
│   ├── pss_wasm.ts          # TypeScript обвязка
│   ├── pss.wasm             # WebAssembly модуль
│   └── asmcrypto.js         # Исходная библиотека
├── arweave/
│   └── compatible.ts        # Обновленный интерфейс
├── tests/
│   └── pss_wasm_test.ts     # Тесты WebAssembly
├── webassembly-implementation-plan.md
└── README.md                # Обновленная документация
```

### API интерфейс
```typescript
// Основной интерфейс
export interface RSASSA_PSS_Signer {
  sign(args: {
    key: JsonWebKey;           // приватный RSA ключ (2048 бит, JWK)
    msg: Uint8Array;           // данные для подписи
    hash: "SHA-256";           // хэш-алгоритм (фиксирован)
    saltLength: number;        // длина соли (обязательно = 32)
  }): Promise<Uint8Array>;     // возвращает подпись (256 байт)
}

// Экспорт модуля
export { RSASSA_PSS } from "./pss_wasm.ts";
```

### Интеграция в compatible.ts
```typescript
import { RSASSA_PSS } from "../crypto/pss_wasm.ts";

export async function signTransaction(
  arweave: any,
  transaction: any,
  privateKey: JsonWebKey
): Promise<void> {
  const signatureData = await transaction.getSignatureData();
  
  // Используем WebAssembly модуль
  const signature = await RSASSA_PSS.sign({
    key: privateKey,
    msg: signatureData,
    hash: "SHA-256",
    saltLength: 32
  });

  const signatureB64Url = arweave.utils.bufferTob64Url(signature);
  transaction.signature = signatureB64Url;
  
  // Вычисляем transaction ID
  const transactionId = await computeTransactionId(signature);
  transaction.id = transactionId;
}
```

## 📊 КРИТЕРИИ УСПЕХА

### Функциональные требования
- [ ] Подпись принимается сетью ArWeave
- [ ] Transaction ID начинается с 'ar'
- [ ] Модуль работает в Deno без ошибок
- [ ] Поддерживает RSA-2048 ключи в формате JWK

### Производительность
- [ ] Время подписи < 100мс для данных до 10KB
- [ ] Память < 50MB для Edge Function
- [ ] Размер WebAssembly модуля < 1MB

### Качество кода
- [ ] TypeScript типизация
- [ ] Обработка ошибок
- [ ] Документация и комментарии
- [ ] Тесты покрывают основные сценарии

## ⚠️ ПОТЕНЦИАЛЬНЫЕ ПРОБЛЕМЫ

### Технические сложности
1. **Компиляция asmcrypto.js** - может потребовать настройки
2. **Размер WebAssembly** - оптимизация для Edge Functions
3. **Совместимость Deno** - проверка WebAssembly поддержки
4. **Производительность** - баланс между скоростью и размером

### Альтернативные планы
- **План B**: Если WebAssembly сложен - переход на Node.js
- **План C**: Если не работает - поиск других библиотек
- **План D**: Если ничего не помогает - полная PSS реализация

## 🎯 СЛЕДУЮЩИЕ ШАГИ

1. **Начать с Этапа 1** - анализ asmcrypto.js
2. **Скачать библиотеку** и изучить структуру
3. **Настроить компиляцию** в WebAssembly
4. **Создать базовый модуль** и протестировать
5. **Интегрировать в Edge Function** и валидировать

---

**Время выполнения**: 6-8 часов
**Приоритет**: КРИТИЧЕСКИЙ
**Статус**: ГОТОВ К ВЫПОЛНЕНИЮ
**Зависимости**: asmcrypto.js, Emscripten/AssemblyScript 