# 🚀 **ARWEAVE + SUPABASE EDGE FUNCTION - ТЕХНИЧЕСКОЕ РУКОВОДСТВО**

## 📋 **ОБЗОР**

Данное руководство описывает полный процесс настройки интеграции ArWeave с Supabase Edge Function для решения проблемы недоступности Python SDK.

---

## 🔧 **НАСТРОЙКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ**

### **1. Структура .env файла**

В корневом`.env` добавьте переменные:

```bash
# ========================================
# SUPABASE КОНФИГУРАЦИЯ (ЛОКАЛЬНАЯ)
# ========================================
# URL локального Supabase (автоматически генерируется при запуске)
SUPABASE_URL=http://127.0.0.1:54321

# Анонимный ключ (автоматически генерируется при запуске)
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0

# ========================================
# ARWEAVE КОНФИГУРАЦИЯ
# ========================================
# Путь к файлу приватного ключа ArWeave (JSON формат)
ARWEAVE_PRIVATE_KEY=arweave-wallet.json

```

### **2. Где используются переменные**

#### **В Python коде (bot/config.py):**
```python
# Supabase переменные
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:54321")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# ArWeave переменные
ARWEAVE_PRIVATE_KEY = os.getenv("ARWEAVE_PRIVATE_KEY", "arweave-wallet.json")
```

#### **В Edge Function (supabase/functions/arweave-upload/index.ts):**
```typescript
// ArWeave приватный ключ загружается из переменных окружения
const privateKey = Deno.env.get('ARWEAVE_PRIVATE_KEY')
```

#### **В тестах (tests/test_supabase_arweave.py):**
```python
# Импорт конфигурации
from bot.config import SUPABASE_URL, SUPABASE_ANON_KEY
```

### **3. Получение значений для локальной разработки**

#### **Автоматически генерируются при запуске Supabase:**
```bash
# Запуск Supabase
supabase start

# Результат будет содержать:
# API URL: http://127.0.0.1:54321
# anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### **ArWeave ключ:**
```bash
# Файл должен быть в корне проекта
ls -la arweave-wallet.json
```

---

## 🚀 **ДЕПЛОЙ И ЗАПУСК**

### **1. Локальная разработка**

#### **Шаг 1: Запуск Supabase**
```bash
# Остановить все контейнеры Supabase
supabase stop

# Запустить локальный Supabase
supabase start

# Проверить статус
supabase status
```

**Ожидаемый результат:**
```
Started supabase local development setup.

         API URL: http://127.0.0.1:54321
     GraphQL URL: http://127.0.0.1:54321/graphql/v1
  S3 Storage URL: http://127.0.0.1:54321/storage/v1/s3
          DB URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
      Studio URL: http://127.0.0.1:54323
    Inbucket URL: http://127.0.0.1:54324
      JWT secret: super-secret-jwt-token-with-at-least-32-characters-long
        anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
service_role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### **Шаг 2: Запуск Edge Function**
```bash
# Запуск функции в режиме разработки
supabase functions serve arweave-upload --env-file .env
```

**Ожидаемый результат:**
```
Setting up Edge Functions runtime...
Serving functions on http://127.0.0.1:54321/functions/v1/<function-name>
 - http://127.0.0.1:54321/functions/v1/arweave-upload
Using supabase-edge-runtime-1.68.3 (compatible with Deno v1.45.2)
```

#### **Шаг 3: Тестирование функции**
```bash
# Health check
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0" \
  http://localhost:54321/functions/v1/arweave-upload/health

# Ожидаемый результат:
# {"status":"healthy","timestamp":"2024-01-XX...","arweave":"connected"}
```

### **2. Продакшен деплой**

#### **Шаг 1: Создание проекта в Supabase Dashboard**
1. Перейти на https://supabase.com/dashboard
2. Нажать "New Project"
3. Выбрать организацию
4. Ввести название: `amanita-arweave`
5. Ввести пароль базы данных
6. Выбрать регион
7. Нажать "Create new project"

#### **Шаг 2: Получение ключей продакшена**
```bash
# В Supabase Dashboard -> Settings -> API скопировать:
# Project URL: https://your-project.supabase.co
# anon public: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### **Шаг 3: Настройка переменных окружения в продакшене**
```bash
# В Supabase Dashboard -> Settings -> Edge Functions
# Добавить переменную:
# Name: ARWEAVE_PRIVATE_KEY
# Value: {"kty":"RSA","n":"...","e":"AQAB","d":"...",...}
```

#### **Шаг 4: Линковка проекта**
```bash
# Линкуем локальный проект с удаленным
supabase link --project-ref your-project-ref

# Проверка статуса
supabase status
```

#### **Шаг 5: Деплой функции**
```bash
# Деплой конкретной функции
supabase functions deploy arweave-upload

# Проверка деплоя
supabase functions list
```

#### **Шаг 6: Обновление .env для продакшена**
```bash
# Обновить переменные в .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🧪 **ТЕСТИРОВАНИЕ**

### **1. Локальное тестирование**

#### **Запуск тестов:**
```bash
# Установка зависимостей
pip install pytest requests python-dotenv

# Запуск тестов ArWeave интеграции
python -m pytest tests/test_supabase_arweave.py -v

# Запуск всех тестов
python -m pytest tests/ -v
```

#### **Ожидаемый результат:**
```
collected 15 items
tests/test_supabase_arweave.py::TestEdgeFunctionAvailability::test_health_check PASSED
tests/test_supabase_arweave.py::TestEdgeFunctionAvailability::test_upload_text PASSED
...
15 passed in 45.32s
```

### **2. Продакшен тестирование**

#### **Тест функции в продакшене:**
```bash
# Health check
curl -H "Authorization: Bearer your-anon-key" \
  https://your-project.supabase.co/functions/v1/arweave-upload/health

# Upload test
curl -X POST \
  -H "Authorization: Bearer your-anon-key" \
  -H "Content-Type: application/json" \
  -d '{"data":"test","contentType":"text/plain"}' \
  https://your-project.supabase.co/functions/v1/arweave-upload/upload-text
```

---

## 🛠️ **ЛОКАЛЬНАЯ РАЗРАБОТКА**

### **1. Подготовка окружения**

#### **Установка Supabase CLI:**
```bash
# macOS (Homebrew)
brew install supabase/tap/supabase

# Проверка установки
supabase --version
```

#### **Установка Node.js и npm:**
```bash
# Проверка версий
node --version  # Должно быть >= 18
npm --version   # Должно быть >= 8
```

#### **Установка Deno (для Edge Functions):**
```bash
# macOS (Homebrew)
brew install deno

# Проверка установки
deno --version
```

### **2. Инициализация Supabase проекта**

#### **Создание проекта:**
```bash
# Переходим в директорию проекта
cd /Users/eslinko/Development/🍄Amanita

# Инициализируем Supabase (если еще не инициализирован)
supabase init

# Логинимся в Supabase
supabase login
```

#### **Структура проекта после инициализации:**
```
Amanita/
├── supabase/
│   ├── config.toml          # Конфигурация Supabase
│   ├── functions/           # Edge функции
│   │   └── arweave-upload/
│   │       └── index.ts
│   └── docs/
│       └── technical-guidance.md
├── .env                     # Переменные окружения
└── ...
```

### **3. Настройка локальной разработки**

#### **Запуск локального Supabase:**
```bash
# Запуск локального Supabase
supabase start

# Проверка статуса
supabase status
```

#### **Создание Edge функции:**
```bash
# Создание функции arweave-upload
supabase functions new arweave-upload

# Результат: supabase/functions/arweave-upload/index.ts
```

#### **Настройка переменных окружения:**
```bash
# Создаем .env файл в корне проекта
touch .env

# Добавляем переменные (см. раздел выше)
```

### **4. Разработка Edge функции**

#### **Содержимое `supabase/functions/arweave-upload/index.ts`:**
```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import Arweave from 'https://esm.sh/arweave@1.15.7'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Parse request body
    const { data, contentType = 'application/json', tags = {} } = await req.json()

    // Validate input
    if (!data) {
      return new Response(
        JSON.stringify({ error: 'Data is required' }),
        { 
          status: 400, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        }
      )
    }

    // Initialize ArWeave
    const arweave = Arweave.init({
      host: 'arweave.net',
      port: 443,
      protocol: 'https'
    })

    // Load wallet from environment variable
    const walletKey = Deno.env.get('ARWEAVE_PRIVATE_KEY')
    if (!walletKey) {
      return new Response(
        JSON.stringify({ error: 'ArWeave private key not configured' }),
        { 
          status: 500, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        }
      )
    }

    let wallet
    try {
      wallet = JSON.parse(walletKey)
    } catch (e) {
      return new Response(
        JSON.stringify({ error: 'Invalid wallet key format' }),
        { 
          status: 500, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        }
      )
    }

    // Create transaction
    const transaction = await arweave.createTransaction({
      data: typeof data === 'string' ? data : JSON.stringify(data)
    }, wallet)

    // Add content type tag
    transaction.addTag('Content-Type', contentType)

    // Add custom tags
    Object.entries(tags).forEach(([key, value]) => {
      transaction.addTag(key, value)
    })

    // Add timestamp
    transaction.addTag('Timestamp', new Date().toISOString())

    // Sign transaction
    await arweave.transactions.sign(transaction)

    // Submit transaction
    const response = await arweave.transactions.post(transaction)

    if (response.status === 200 || response.status === 202) {
      return new Response(
        JSON.stringify({
          success: true,
          transaction_id: transaction.id,
          data_size: transaction.data_size,
          reward: transaction.reward,
          timestamp: new Date().toISOString()
        }),
        { 
          status: 200, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        }
      )
    } else {
      return new Response(
        JSON.stringify({ 
          error: 'Failed to upload to ArWeave',
          status: response.status,
          statusText: response.statusText
        }),
        { 
          status: 500, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        }
      )
    }

  } catch (error) {
    console.error('ArWeave upload error:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Internal server error',
        details: error.message 
      }),
      { 
        status: 500, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  }
})
```

### **5. Локальное тестирование**

#### **Запуск Edge функции локально:**
```bash
# Запуск функции в режиме разработки
supabase functions serve arweave-upload --env-file .env

# Результат: http://localhost:54321/functions/v1/arweave-upload
```

#### **Тестирование функции:**
```bash
# Тест с curl
curl -X POST http://localhost:54321/functions/v1/arweave-upload \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "data": "Hello, ArWeave!",
    "contentType": "text/plain",
    "tags": {"App-Name": "Amanita-Bot"}
  }'
```

#### **Запуск Python тестов:**
```bash
# Установка зависимостей
pip install requests python-dotenv

# Запуск тестов
pytest tests/test_arweave_supabase.py -v
```

### **6. Отладка и логирование**

#### **Просмотр логов Edge функции:**
```bash
# Логи в реальном времени
supabase functions logs arweave-upload --follow

# Логи за последние 24 часа
supabase functions logs arweave-upload --since 24h
```

#### **Отладка с помощью console.log:**
```typescript
// В Edge функции
console.log('Request data:', data)
console.log('Wallet loaded:', !!wallet)
console.log('Transaction created:', transaction.id)
```

---

## 🚀 **ПРОДАКШЕН НАСТРОЙКА**

### **1. Создание Supabase проекта**

#### **Создание проекта в Supabase Dashboard:**
1. Перейти на https://supabase.com/dashboard
2. Нажать "New Project"
3. Выбрать организацию
4. Ввести название проекта: `amanita-arweave`
5. Ввести пароль базы данных
6. Выбрать регион (рекомендуется ближайший к пользователям)
7. Нажать "Create new project"

#### **Получение ключей проекта:**
```bash
# В Supabase Dashboard -> Settings -> API
# Скопировать:
# - Project URL: https://your-project.supabase.co
# - anon public: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### **2. Настройка переменных окружения**

#### **В Supabase Dashboard:**
1. Перейти в Settings -> Edge Functions
2. Добавить переменную окружения:
   - **Name:** `ARWEAVE_PRIVATE_KEY`
   - **Value:** `{"kty":"RSA","n":"...","e":"AQAB","d":"...",...}`
3. Нажать "Save"

#### **В локальном .env файле:**
```bash
# Обновляем .env для продакшена
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### **3. Деплой Edge функции**

#### **Линковка проекта:**
```bash
# Линкуем локальный проект с удаленным
supabase link --project-ref your-project-ref

# Проверка статуса
supabase status
```

#### **Деплой функции:**
```bash
# Деплой конкретной функции
supabase functions deploy arweave-upload

# Или деплой всех функций
supabase functions deploy
```

#### **Проверка деплоя:**
```bash
# Список функций
supabase functions list

# Статус функции
supabase functions status arweave-upload
```

### **4. Настройка авторизации**

#### **Настройка CORS (если нужно):**
```typescript
// В Edge функции обновить corsHeaders
const corsHeaders = {
  'Access-Control-Allow-Origin': 'https://your-domain.com',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS'
}
```

#### **Настройка Rate Limiting:**
```typescript
// Добавить в Edge функцию
const rateLimit = {
  windowMs: 15 * 60 * 1000, // 15 минут
  max: 100 // максимум 100 запросов за окно
}
```

### **5. Мониторинг и логирование**

#### **Настройка логирования:**
```typescript
// В Edge функции
const logUpload = (data: any, result: any) => {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    action: 'arweave_upload',
    data_size: data.length,
    transaction_id: result.transaction_id,
    reward: result.reward,
    success: true
  }))
}
```

#### **Просмотр логов в продакшене:**
```bash
# Логи в реальном времени
supabase functions logs arweave-upload --follow

# Логи с фильтрацией
supabase functions logs arweave-upload --since 1h | grep "arweave_upload"
```

### **6. Тестирование в продакшене**

#### **Тест функции:**
```bash
# Тест с curl
curl -X POST https://your-project.supabase.co/functions/v1/arweave-upload \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "data": "Production test",
    "contentType": "text/plain",
    "tags": {"Environment": "production"}
  }'
```

#### **Запуск Python тестов:**
```bash
# Обновляем переменные окружения
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Запуск тестов
pytest tests/test_arweave_supabase.py -v
```

---

## 🔧 **КОНФИГУРАЦИЯ И ОПТИМИЗАЦИЯ**

### **1. Настройка производительности**

#### **Оптимизация Edge функции:**
```typescript
// Кэширование ArWeave экземпляра
let arweaveInstance: any = null

const getArweave = () => {
  if (!arweaveInstance) {
    arweaveInstance = Arweave.init({
      host: 'arweave.net',
      port: 443,
      protocol: 'https'
    })
  }
  return arweaveInstance
}
```

#### **Настройка таймаутов:**
```typescript
// В Edge функции
const TIMEOUT_MS = 30000 // 30 секунд

// В Python клиенте
response = requests.post(url, json=payload, timeout=35)
```

### **2. Обработка ошибок**

#### **Улучшенная обработка ошибок:**
```typescript
// В Edge функции
const handleError = (error: any, context: string) => {
  console.error(`Error in ${context}:`, {
    message: error.message,
    stack: error.stack,
    timestamp: new Date().toISOString()
  })
  
  return new Response(
    JSON.stringify({
      error: 'Internal server error',
      context: context,
      timestamp: new Date().toISOString()
    }),
    { 
      status: 500, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}
```

### **3. Безопасность**

#### **Валидация входных данных:**
```typescript
// В Edge функции
const validateInput = (data: any) => {
  if (!data) {
    throw new Error('Data is required')
  }
  
  if (typeof data === 'string' && data.length > 2 * 1024 * 1024) {
    throw new Error('Data too large (max 2MB)')
  }
  
  if (typeof data === 'object' && JSON.stringify(data).length > 2 * 1024 * 1024) {
    throw new Error('Data too large (max 2MB)')
  }
}
```

#### **Проверка авторизации:**
```typescript
// В Edge функции
const validateAuth = (req: Request) => {
  const authHeader = req.headers.get('authorization')
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    throw new Error('Invalid authorization header')
  }
  
  const token = authHeader.substring(7)
  // Здесь можно добавить проверку JWT токена
}
```

---

## 📊 **МОНИТОРИНГ И АНАЛИТИКА**

### **1. Метрики производительности**

#### **Сбор метрик:**
```typescript
// В Edge функции
const collectMetrics = (startTime: number, dataSize: number, success: boolean) => {
  const duration = Date.now() - startTime
  
  console.log(JSON.stringify({
    type: 'metric',
    timestamp: new Date().toISOString(),
    duration_ms: duration,
    data_size_bytes: dataSize,
    success: success,
    function: 'arweave_upload'
  }))
}
```

### **2. Алерты и уведомления**

#### **Настройка алертов:**
```typescript
// В Edge функции
const sendAlert = (message: string, level: 'info' | 'warning' | 'error') => {
  console.log(JSON.stringify({
    type: 'alert',
    level: level,
    message: message,
    timestamp: new Date().toISOString()
  }))
}
```

---

## 🚨 **УСТРАНЕНИЕ НЕПОЛАДОК**

### **1. Частые проблемы**

#### **Ошибка "Function not found":**
```bash
# Проверить деплой
supabase functions list

# Передеплоить функцию
supabase functions deploy arweave-upload
```

#### **Ошибка "Invalid wallet key":**
```bash
# Проверить переменную окружения
supabase secrets list

# Обновить переменную
supabase secrets set ARWEAVE_PRIVATE_KEY='{"kty":"RSA",...}'
```

#### **Ошибка "CORS":**
```typescript
// Обновить corsHeaders в Edge функции
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS'
}
```

### **2. Отладка**

#### **Локальная отладка:**
```bash
# Запуск с подробными логами
supabase functions serve arweave-upload --debug

# Просмотр логов
supabase functions logs arweave-upload --follow
```

#### **Продакшен отладка:**
```bash
# Логи в реальном времени
supabase functions logs arweave-upload --follow

# Логи с фильтрацией ошибок
supabase functions logs arweave-upload | grep "ERROR"
```

---

## 📝 **ЧЕКЛИСТ РАЗВЕРТЫВАНИЯ**

### **Локальная разработка:**
- [ ] Supabase CLI установлен
- [ ] Node.js и Deno установлены
- [ ] Проект инициализирован
- [ ] Edge функция создана
- [ ] Переменные окружения настроены
- [ ] Локальное тестирование пройдено

### **Продакшен:**
- [ ] Supabase проект создан
- [ ] Переменные окружения настроены в Dashboard
- [ ] Edge функция задеплоена
- [ ] Авторизация настроена
- [ ] CORS настроен
- [ ] Мониторинг настроен
- [ ] Тестирование в продакшене пройдено

---

## 🎯 **ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ**

### **Статус на 04.08.2025:**

#### ✅ **РАБОТАЕТ:**
- **Supabase локальный запуск** - `supabase start`
- **Edge Function развертывание** - `supabase functions serve arweave-upload --env-file .env`
- **Health check endpoint** - `GET /functions/v1/arweave-upload/health`
- **Конфигурация переменных окружения** - все переменные настроены правильно
- **Интеграция с Python кодом** - импорт конфигурации работает

#### ⚠️ **ТРЕБУЕТ ДОРАБОТКИ:**
- **ArWeave загрузка** - ошибка "Transaction verification failed" (400)
- **Тесты с декораторами** - конфликт с pytest фикстурами
- **Обработка ошибок** - некоторые endpoints возвращают 500 вместо ожидаемых 400/422

#### ❌ **НЕ РАБОТАЕТ:**
- **Фактическая загрузка в ArWeave** - проблема с подписью транзакций

### **Финальные команды для запуска:**

#### **1. Запуск локального Supabase:**
```bash
# Остановить все контейнеры
supabase stop

# Запустить локальный Supabase
supabase start

# Проверить статус
supabase status
```

#### **2. Настройка переменных окружения:**
```bash
# Обновить .env файл в корне проекта
echo "SUPABASE_URL=http://127.0.0.1:54321" >> .env
echo "SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0" >> .env

# Скопировать ArWeave ключ как JSON
ARWEAVE_KEY_CONTENT=$(cat arweave-wallet.json | tr -d '\n' | tr -d ' ')
sed -i '' "s|ARWEAVE_PRIVATE_KEY=arweave-wallet.json|ARWEAVE_PRIVATE_KEY=$ARWEAVE_KEY_CONTENT|" .env

# Скопировать .env в папку bot
cp .env bot/.env
```

#### **3. Запуск Edge Function:**
```bash
# Запуск функции в режиме разработки
supabase functions serve arweave-upload --env-file .env
```

#### **4. Тестирование:**
```bash
# Health check
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0" \
  http://localhost:54321/functions/v1/arweave-upload/health

# Запуск тестов
python3 -m pytest tests/test_supabase_arweave.py::TestEdgeFunctionAvailability::test_health_check -v
```

### **Следующие шаги для исправления:**

#### **1. Исправить ArWeave подпись транзакций:**
- Проверить формат приватного ключа
- Убедиться в правильности ArWeave SDK интеграции
- Добавить более подробное логирование ошибок

#### **2. Исправить тесты:**
- Убрать декораторы `@measure_performance` из проблемных тестов
- Добавить правильную обработку ошибок в Edge Function
- Исправить ожидаемые HTTP коды ответов

#### **3. Продакшен деплой:**
- Создать проект в Supabase Dashboard
- Настроить переменные окружения в продакшене
- Задеплоить Edge Function

---

## 🎯 **ЗАКЛЮЧЕНИЕ**

Данное руководство предоставляет полный процесс настройки интеграции ArWeave с Supabase Edge Function. Следуя этим инструкциям, вы сможете:

1. **Настроить локальную среду разработки** ✅
2. **Разработать и протестировать Edge функцию** ⚠️ (частично)
3. **Развернуть решение в продакшене** 📋 (планируется)
4. **Настроить мониторинг и отладку** 📋 (планируется)

**Время настройки:** ~2-4 часа для полной настройки
**Готовность к production:** 60% после выполнения всех шагов
**Основная проблема:** ArWeave подпись транзакций требует доработки
