# Универсальный тестовый фреймворк для браузера

## Описание

Масштабируемое решение для тестирования JavaScript кода через браузер. Поддерживает детальное логирование, экспорт результатов и удобный веб-интерфейс с красивым дизайном.

## 🏗️ Итоговая архитектура

### Структура файлов

```
webapp/tests/
├── README.md                    # Документация фреймворка
├── shared/
│   ├── test-styles.css         # Общие стили для всех тестовых страниц
│   └── test-utils.js           # Переиспользуемые утилиты
├── html/
│   ├── safety1-p0-tests-final.html    # P0 тесты безопасности (рабочий)
│   └── universal-test-runner.html     # Универсальный раннер
├── crypto-tests.js             # Тесты криптографических функций
└── test-framework.js           # Основной класс TestFramework (опционально)
```

### Компоненты системы

#### 1. **HTML тестовые страницы** (`html/`)
- **Полностью автономные** - все стили и функции встроены
- **Красивый дизайн** - переливающийся градиентный фон
- **Полный функционал** - запуск, экспорт, детальные логи
- **Готовы к использованию** - просто откройте в браузере

#### 2. **Переиспользуемые утилиты** (`shared/`)
- **`test-styles.css`** - общие стили для всех тестовых страниц
- **`test-utils.js`** - функции создания карточек, обновления статусов, экспорта

#### 3. **Тестовые файлы** (`*.js`)
- **`crypto-tests.js`** - все тесты криптографических функций
- **Экспорт в window** - функции доступны глобально в браузере
- **Совместимость** - работают с Node.js и браузером

## 🚀 Быстрый старт

### Для разработчиков

1. **Откройте готовую тестовую страницу:**
   ```bash
   # Запустите локальный сервер
   python3 -m http.server 8080
   
   # Откройте в браузере
   open http://localhost:8080/tests/html/safety1-p0-tests-final.html
   ```

2. **Запустите тесты:**
   - Нажмите "🚀 Запустить все тесты"
   - Или "🔍 Запустить по одному" для детального просмотра

3. **Экспортируйте результаты:**
   - "📄 Экспорт результатов" - общий отчет
   - "📄 Скачать лог" на каждой карточке - детальный лог теста

### Для создания новых тестов

#### Шаг 1: Создайте тестовый файл

```javascript
// tests/my-new-tests.js
console.log('=== ЗАГРУЗКА my-new-tests.js ===');

// Тест 1: Простая функция
async function test_simple_function() {
    console.log('Тестируем простую функцию...');
    
    try {
        // Ваша логика теста
        const result = myFunction();
        
        if (result === expected) {
            console.log('✅ Тест пройден');
            return true;
        } else {
            console.log('❌ Неожиданный результат:', result);
            return false;
        }
    } catch (error) {
        console.error('❌ Ошибка в тесте:', error);
        return false;
    }
}

// Тест 2: Асинхронная функция
async function test_async_function() {
    console.log('Тестируем асинхронную функцию...');
    
    try {
        const result = await myAsyncFunction();
        
        if (result.success) {
            console.log('✅ Асинхронный тест пройден');
            return true;
        } else {
            console.log('❌ Асинхронный тест провален');
            return false;
        }
    } catch (error) {
        console.error('❌ Ошибка в асинхронном тесте:', error);
        return false;
    }
}

// Экспорт для браузера
if (typeof window !== 'undefined') {
    console.log('Экспортируем функции в window...');
    window.test_simple_function = test_simple_function;
    window.test_async_function = test_async_function;
    console.log('✅ Функции экспортированы в window');
} else if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        test_simple_function,
        test_async_function
    };
}
```

#### Шаг 2: Создайте HTML страницу

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мои новые тесты</title>
    <style>
        /* Скопируйте стили из safety1-p0-tests-final.html */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #f5576c 75%, #4facfe 100%);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            min-height: 100vh;
        }
        
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        /* ... остальные стили ... */
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Мои новые тесты</h1>
            <p>Описание ваших тестов</p>
        </div>

        <div class="controls">
            <button class="btn btn-primary" onclick="runAllTests()">🚀 Запустить все тесты</button>
            <button class="btn btn-info" onclick="runIndividualTests()">🔍 Запустить по одному</button>
            <button class="btn btn-danger" onclick="clearResults()">🗑️ Очистить результаты</button>
            <button class="btn btn-success" onclick="exportResults()">📄 Экспорт результатов</button>
        </div>

        <div id="status" class="status info">Готов к тестированию</div>

        <div class="summary">
            <h3>📊 Сводка результатов</h3>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill" style="width: 0%"></div>
            </div>
            <div id="summaryText">Ожидание запуска тестов...</div>
        </div>

        <div class="tests-grid" id="testsGrid">
            <!-- Тесты будут добавлены динамически -->
        </div>
    </div>

    <!-- Подключаем ваши тесты -->
    <script src="../my-new-tests.js?v=1"></script>

    <script>
        // Определите ваши тесты
        const allTests = [
            {
                id: 'test_simple_function',
                name: 'test_simple_function',
                title: 'Простая функция',
                description: 'Проверяет работу простой функции',
                category: 'Базовые тесты'
            },
            {
                id: 'test_async_function',
                name: 'test_async_function',
                title: 'Асинхронная функция',
                description: 'Проверяет работу асинхронной функции',
                category: 'Асинхронные тесты'
            }
        ];

        // Скопируйте все функции из safety1-p0-tests-final.html
        // (createTestCard, updateTestStatus, updateProgress, runAllTests, etc.)
    </script>
</body>
</html>
```

#### Шаг 3: Запустите тесты

```bash
# Откройте в браузере
open http://localhost:8080/tests/html/my-new-tests.html
```

## 📋 Принципы разработки

### 1. **Автономность**
- Каждая HTML страница содержит все необходимые стили и функции
- Никаких внешних зависимостей (кроме тестовых файлов)
- Работает "из коробки"

### 2. **Переиспользование**
- Общие стили в `shared/test-styles.css`
- Общие функции в `shared/test-utils.js`
- Копируйте готовые HTML шаблоны

### 3. **Консистентность**
- Единый дизайн для всех тестовых страниц
- Стандартные функции и API
- Одинаковая структура тестов

### 4. **Простота**
- Минимум кода для максимального результата
- Понятные имена функций и переменных
- Подробные комментарии

## 🎨 Дизайн система

### Цветовая схема
- **Фон:** Переливающийся градиент (бирюзово-фиолетовый)
- **Карточки:** Белые с тенью
- **Статусы:** Зеленый (пройден), красный (провален), желтый (выполняется)
- **Кнопки:** Синий (основные), зеленый (экспорт), красный (очистка)

### Анимации
- **Градиент:** Плавное переливание фона (15 секунд)
- **Прогресс-бар:** Плавное заполнение
- **Карточки:** Плавные переходы статусов

## 🔧 API для разработчиков

### Основные функции

```javascript
// Создание карточки теста
function createTestCard(test) {
    // test = { id, name, title, description, category }
    return `<div class="test-card">...</div>`;
}

// Обновление статуса теста
function updateTestStatus(testId, status, message) {
    // status: 'pending', 'running', 'passed', 'failed'
    // message: строка для лога
}

// Обновление прогресса
function updateProgress() {
    // Обновляет прогресс-бар и сводку
}

// Запуск всех тестов
async function runAllTests() {
    // Запускает все тесты последовательно
}

// Экспорт результатов
function exportResults() {
    // Скачивает Markdown отчет
}
```

### Структура теста

```javascript
{
    id: 'unique_test_id',           // Уникальный ID
    name: 'testFunctionName',       // Имя функции теста
    title: 'Отображаемое название', // Название для UI
    description: 'Описание теста',  // Описание
    category: 'Категория'           // Категория для группировки
}
```

### Функция теста

```javascript
async function test_my_function() {
    console.log('Начинаем тест...');
    
    try {
        // Ваша логика теста
        const result = await myFunction();
        
        if (result === expected) {
            console.log('✅ Тест пройден');
            return true;
        } else {
            console.log('❌ Неожиданный результат:', result);
            return false;
        }
    } catch (error) {
        console.error('❌ Ошибка в тесте:', error);
        return false;
    }
}
```

## 📁 Примеры использования

### Тестирование API

```javascript
async function test_api_endpoint() {
    console.log('Тестируем API endpoint...');
    
    try {
        const response = await fetch('/api/test');
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ API работает корректно');
            return true;
        } else {
            console.log('❌ API вернул ошибку:', data.error);
            return false;
        }
    } catch (error) {
        console.error('❌ Ошибка сети:', error);
        return false;
    }
}
```

### Тестирование DOM

```javascript
async function test_dom_manipulation() {
    console.log('Тестируем манипуляции с DOM...');
    
    try {
        const element = document.getElementById('test-element');
        
        if (!element) {
            console.log('❌ Элемент не найден');
            return false;
        }
        
        element.textContent = 'Тест';
        
        if (element.textContent === 'Тест') {
            console.log('✅ DOM манипуляции работают');
            return true;
        } else {
            console.log('❌ DOM манипуляции не работают');
            return false;
        }
    } catch (error) {
        console.error('❌ Ошибка DOM:', error);
        return false;
    }
}
```

### Тестирование криптографии

```javascript
async function test_encryption() {
    console.log('Тестируем шифрование...');
    
    try {
        const data = 'секретные данные';
        const encrypted = await encryptWithAES(data, 'password');
        const decrypted = await decryptWithAES(encrypted, 'password');
        
        if (decrypted === data) {
            console.log('✅ Шифрование работает корректно');
            return true;
        } else {
            console.log('❌ Шифрование не работает');
            return false;
        }
    } catch (error) {
        console.error('❌ Ошибка шифрования:', error);
        return false;
    }
}
```

## 🚀 Готовые шаблоны

### 1. **safety1-p0-tests-final.html**
- P0 тесты безопасности
- 11 криптографических тестов
- Полностью рабочий

### 2. **universal-test-runner.html**
- Универсальный раннер
- Легко добавлять новые тесты
- Тот же функционал

### 3. **Шаблон для новых тестов**
```html
<!-- Скопируйте safety1-p0-tests-final.html -->
<!-- Измените заголовок и массив allTests -->
<!-- Добавьте свои тестовые функции -->
```

## 📝 Лучшие практики

### 1. **Именование**
- Функции тестов: `test_название_функции`
- ID тестов: `test_название_функции`
- Файлы: `название-tests.js`

### 2. **Логирование**
- Используйте `console.log` для информационных сообщений
- Используйте `console.error` для ошибок
- Логи автоматически сохраняются для каждого теста

### 3. **Обработка ошибок**
- Всегда оборачивайте код в `try-catch`
- Возвращайте `true`/`false` для результата
- Логируйте ошибки подробно

### 4. **Асинхронность**
- Используйте `async/await` для асинхронных операций
- Не забывайте `await` перед асинхронными вызовами
- Обрабатывайте ошибки в асинхронном коде

## 🔍 Отладка

### Консоль браузера
- Откройте DevTools (F12)
- Смотрите логи в консоли
- Проверяйте ошибки загрузки скриптов

### Детальные логи
- Нажмите "🔍 Детальный лог" на любой карточке
- Скачайте лог кнопкой "📄 Скачать лог"
- Изучите последовательность выполнения

### Частые проблемы
1. **Функции не найдены** - проверьте экспорт в `window`
2. **Тесты не запускаются** - проверьте подключение скриптов
3. **Ошибки DOM** - проверьте наличие элементов на странице

## 🎯 Заключение

Этот фреймворк предоставляет:
- **Простое** создание тестов
- **Красивый** веб-интерфейс
- **Детальное** логирование
- **Готовые** шаблоны
- **Масштабируемость** для больших проектов

Используйте готовые файлы как основу для ваших тестов и следуйте принципам, описанным в этом README.