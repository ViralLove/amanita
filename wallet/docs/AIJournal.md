# AI Journal - Анализ проблем UI в Amanita Wallet

**Дата анализа**: 2024-12-19  
**Метод**: @analysis.mdc  
**Цель**: Анализ трех критических проблем UI приложения wallet

---

## 🚨 Проблема 1: Рекурсивные ошибки в handleCreateWallet() и handleRestoreWallet()

### 📋 Описание
При вызове функций `handleCreateWallet()` и `handleRestoreWallet()` возникает ошибка "Maximum call stack size exceeded", что указывает на бесконечную рекурсию.

### 🔍 Корневая причина
**Функция `logIfAvailable()`** - потенциальный источник рекурсии:

```javascript
function logIfAvailable(message, isError = false) {
  console.log(message);  // ← Возможная рекурсия через console.log
  
  if (!window.DEBUG_MODE) {
    return;
  }
  
  // Логирование в DOM может вызывать события, которые триггерят другие функции
  const logElem = document.getElementById('init-log');
  if (logElem) {
    const line = document.createElement('div');
    line.textContent = formattedMessage;
    logElem.appendChild(line);  // ← DOM манипуляции могут вызывать события
    logElem.scrollTop = logElem.scrollHeight;
  }
}
```

### 🎯 Механизм рекурсии
1. `handleCreateWallet()` → `logIfAvailable()` → DOM операции
2. DOM операции → события → обработчики событий → `handleCreateWallet()`
3. Бесконечный цикл

### 💡 Решение
- Изолировать `logIfAvailable()` от DOM операций
- Использовать `requestAnimationFrame()` для асинхронного логирования
- Добавить защиту от рекурсии через флаги

---

## 🚨 Проблема 2: Проблемы с переключением экранов

### 📋 Описание
Функция `switchView()` не переключает экраны корректно. Приложение остается на `start-screen` вместо перехода на ожидаемые экраны (`seed-screen`, `loading-screen`).

### 🔍 Корневая причина
**Несогласованность между CSS классами и inline стилями**:

```javascript
function switchView(viewId) {
  // 1. Скрывает все экраны через inline стили
  all.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.style.display = 'none';  // ← inline стиль
    }
  });
  
  // 2. Показывает нужный экран через inline стили
  const view = document.getElementById(viewId);
  if (view) {
    view.style.display = 'block';  // ← inline стиль
  }
}
```

**Проблема**: Функция не управляет CSS классом `hidden`, который используется в HTML.

### 🎯 Конфликт стилей
```html
<!-- HTML: все экраны имеют класс "hidden" -->
<div id="start-screen" class="view hidden">
<div id="success-screen" class="view">  <!-- ← НЕТ класса hidden! -->

<!-- CSS: класс .view имеет display: none -->
.view {
  display: none;
}

/* НЕТ CSS правила для .hidden! */
```

### 💡 Решение
1. Добавить CSS правило для `.hidden { display: none !important; }`
2. Синхронизировать `switchView()` с CSS классами
3. Удалить дублирование `seed-screen` в массиве `all`

---

## 🚨 Проблема 3: Проблемы с CSS классами и селектором .view:not(.hidden)

### 📋 Описание
Селектор `.view:not(.hidden)` работает некорректно из-за отсутствия CSS правила для класса `hidden`.

### 🔍 Корневая причина
**Отсутствие CSS правила для класса `hidden`**:

```css
/* styles.css - НЕТ правила для .hidden */
.view {
  display: none;
}
/* .hidden {} - ОТСУТСТВУЕТ! */
```

### 🎯 Последствия
1. Класс `hidden` не имеет CSS стилей
2. Элементы с классом `hidden` ведут себя непредсказуемо
3. Селектор `.view:not(.hidden)` находит неправильные элементы
4. `success-screen` (без класса `hidden`) всегда считается "видимым"

### 🎯 Конкретный пример проблемы
```html
<div id="start-screen" class="view hidden">     <!-- hidden=true, display=block -->
<div id="success-screen" class="view">          <!-- hidden=false, display=none -->

<!-- Селектор .view:not(.hidden) находит success-screen -->
<!-- Хотя start-screen видимый (display=block) -->
```

### 💡 Решение
```css
.hidden {
  display: none !important;
}
```

---

## 📊 Общий анализ архитектуры

### 🏗️ Проблемы архитектуры
1. **Смешение подходов**: inline стили + CSS классы
2. **Отсутствие CSS правил**: класс `hidden` не определен
3. **Несогласованность**: HTML классы не соответствуют CSS
4. **Потенциальная рекурсия**: DOM операции в функциях логирования

### 🎯 Критичность проблем
- **P0 (Критическая)**: Проблема 3 - блокирует всю навигацию
- **P1 (Высокая)**: Проблема 2 - нарушает UX
- **P1 (Высокая)**: Проблема 1 - блокирует функциональность

### 🔧 Рекомендации по исправлению
1. **Немедленно**: Добавить CSS правило для `.hidden`
2. **Короткий срок**: Исправить `switchView()` для работы с классами
3. **Средний срок**: Рефакторинг системы логирования
4. **Долгий срок**: Унификация подходов к управлению видимостью

---

## ✅ Заключение

Все три проблемы взаимосвязаны и имеют общую корневую причину - **несогласованность между HTML, CSS и JavaScript**. Основная функциональность кошелька (ethers.js интеграция) работает корректно, но UI слой имеет критические архитектурные проблемы, которые блокируют пользовательский опыт.

**Приоритет исправления**: CSS правила → switchView() → logIfAvailable()
