# 🍄 Мухоморная клавиатура Amanita

## 📋 Обзор

Мухоморная клавиатура - это специализированный компонент ввода PIN-кода в приложении Amanita, реализованный как набор кнопок с изображениями мухоморов для каждой цифры.

## 🏗️ Архитектура

### **HTML-структура**
```html
<div id="setup-pin-screen" class="view">
  <!-- Контейнер клавиатуры -->
  <div class="mushroom-keyboard">
    <!-- Кнопки цифр 0-9 -->
    <button class="mushroom-key" data-key="1">
      <img src="assets/amanita_key_1.png" alt="1">
    </button>
    <!-- ... остальные кнопки ... -->
    
    <!-- Служебные кнопки -->
    <button class="mushroom-key" data-key="backspace">
      <img src="assets/amanita_key_back.png" alt="Backspace">
    </button>
  </div>
  
  <!-- Визуальные индикаторы ввода -->
  <div class="pin-dots">
    <div class="pin-dot"></div>
    <div class="pin-dot"></div>
    <div class="pin-dot"></div>
    <div class="pin-dot"></div>
    <div class="pin-dot"></div>
  </div>
</div>
```

### **CSS-классы**
- `.mushroom-key` - кнопки клавиатуры
- `.pin-dot` - точки-индикаторы ввода
- `.pin-dot.filled` - заполненные точки
- `#setup-pin-screen` - контейнер экрана

## ⚙️ JavaScript API

### **Глобальные переменные**
```javascript
let currentPinInput = [];        // Текущий ввод (массив цифр)
let firstPinEntry = "";          // Первый ввод для подтверждения
let pinStep = "firstEntry";      // Этап ввода
```

### **Основные функции**

#### **`handlePinInput(key)`**
```javascript
async function handlePinInput(key) {
  // Обработка ввода клавиш
  // key: "0"-"9", "backspace", "confirm"
}
```

**Параметры:**
- `key` (string) - значение клавиши из атрибута `data-key`

**Логика:**
- **Цифры 0-9:** Добавляются в `currentPinInput` (максимум 5)
- **backspace:** Удаляет последнюю цифру
- **confirm:** Зарезервировано (не используется)

#### **`processPinEntry()`**
```javascript
async function processPinEntry() {
  // Обработка завершения ввода PIN
  // Автоматически вызывается при вводе 5 цифр
}
```

## 🔄 Жизненный цикл ввода

### **1. Инициализация**
```javascript
// При загрузке DOM
window.addEventListener('DOMContentLoaded', () => {
  const setupPinScreen = document.getElementById('setup-pin-screen');
  const mushroomButtons = setupPinScreen.querySelectorAll(".mushroom-key");
  
  mushroomButtons.forEach((btn, index) => {
    const key = btn.getAttribute("data-key");
    btn.addEventListener("click", (e) => {
      if (document.getElementById('setup-pin-screen').style.display === 'block') {
        handlePinInput(key);
      }
    });
  });
});
```

### **2. Обработка ввода**
```javascript
// При нажатии клавиши
if (key === "backspace") {
  currentPinInput.pop();
} else if (currentPinInput.length < 5 && /^[0-9]$/.test(key)) {
  currentPinInput.push(key);
}

// Обновление визуального отображения
dots.forEach((dot, index) => {
  dot.classList.toggle("filled", index < currentPinInput.length);
});
```

### **3. Автоматическое подтверждение**
```javascript
// При вводе 5 цифр
if (currentPinInput.length === 5) {
  await processPinEntry();
}
```

## 🎯 Состояния клавиатуры

### **pinStep - этапы ввода**
- **"firstEntry"** - первый ввод PIN
- **"confirmEntry"** - подтверждение PIN
- **"unlockSeed"** - разблокировка для просмотра сид-фразы

### **Визуальные состояния**
- **Пустые точки** - нет ввода
- **Заполненные точки** - количество введенных цифр
- **5 заполненных точек** - готовность к подтверждению

## 🔧 API для тестирования

### **Экспортированные функции**
```javascript
// В window объекте доступны:
window.handlePinInput = handlePinInput;
window.processPinEntry = processPinEntry;
window.currentPinInput = currentPinInput;
window.firstPinEntry = firstPinEntry;
window.pinStep = pinStep;
```

### **Методы тестирования**
```javascript
// Прямой вызов обработчика
await handlePinInput("1");

// Проверка состояния
console.log(window.currentPinInput); // ["1"]

// Проверка визуального состояния
const dots = document.querySelectorAll(".pin-dot");
const filledDots = document.querySelectorAll(".pin-dot.filled");
```

## 🚀 План улучшений

### **1. Улучшение архитектуры**

#### **1.1 Модульность**
```javascript
// Создать отдельный модуль KeyboardManager
class AmanitaKeyboard {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.currentInput = [];
    this.maxLength = 5;
    this.init();
  }
  
  init() {
    this.bindEvents();
    this.updateDisplay();
  }
  
  bindEvents() {
    // Привязка обработчиков
  }
  
  handleInput(key) {
    // Обработка ввода
  }
  
  updateDisplay() {
    // Обновление визуального состояния
  }
}
```

#### **1.2 Конфигурируемость**
```javascript
const keyboardConfig = {
  maxLength: 5,
  autoSubmit: true,
  visualFeedback: true,
  soundFeedback: false,
  hapticFeedback: true
};
```

### **2. Улучшение UX**

#### **2.1 Визуальная обратная связь**
- **Анимации нажатий** - масштабирование кнопок
- **Цветовая индикация** - разные цвета для разных состояний
- **Прогресс-бар** - визуальный индикатор заполнения

#### **2.2 Тактильная обратная связь**
```javascript
// Вибрация при нажатии (если поддерживается)
if (navigator.vibrate) {
  navigator.vibrate(50);
}
```

#### **2.3 Звуковая обратная связь**
```javascript
// Звуки нажатий (опционально)
const playKeySound = (key) => {
  const audio = new Audio(`sounds/key_${key}.mp3`);
  audio.play().catch(() => {}); // Игнорируем ошибки
};
```

### **3. Улучшение безопасности**

#### **3.1 Защита от брутфорса**
```javascript
class BruteForceProtection {
  constructor() {
    this.attempts = 0;
    this.maxAttempts = 3;
    this.lockoutTime = 30000; // 30 секунд
  }
  
  checkAttempt() {
    if (this.attempts >= this.maxAttempts) {
      this.lockKeyboard();
      return false;
    }
    return true;
  }
  
  lockKeyboard() {
    // Блокировка клавиатуры
  }
}
```

#### **3.2 Очистка памяти**
```javascript
// Очистка чувствительных данных
const clearSensitiveData = () => {
  currentPinInput = [];
  firstPinEntry = "";
  // Принудительная очистка памяти
  if (window.gc) window.gc();
};
```

### **4. Улучшение тестируемости**

#### **4.1 Мокирование для тестов**
```javascript
// Интерфейс для мокирования
class KeyboardTestInterface {
  constructor() {
    this.mocked = false;
    this.inputs = [];
  }
  
  mockInput(key) {
    this.inputs.push(key);
    return this.handleInput(key);
  }
  
  getInputHistory() {
    return [...this.inputs];
  }
}
```

#### **4.2 События для тестирования**
```javascript
// Кастомные события для тестирования
const keyboardEvents = {
  INPUT_CHANGED: 'keyboard:input_changed',
  PIN_COMPLETE: 'keyboard:pin_complete',
  PIN_CLEARED: 'keyboard:pin_cleared'
};

// Генерация событий
this.container.dispatchEvent(new CustomEvent(keyboardEvents.INPUT_CHANGED, {
  detail: { input: this.currentInput }
}));
```

### **5. Улучшение производительности**

#### **5.1 Дебаунсинг**
```javascript
// Предотвращение множественных быстрых нажатий
const debounce = (func, delay) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
};

const debouncedHandleInput = debounce(handlePinInput, 100);
```

#### **5.2 Виртуализация**
```javascript
// Для больших клавиатур - рендеринг только видимых кнопок
class VirtualizedKeyboard {
  constructor(container, items, itemHeight) {
    this.container = container;
    this.items = items;
    this.itemHeight = itemHeight;
    this.visibleItems = [];
    this.scrollTop = 0;
  }
  
  render() {
    // Рендеринг только видимых элементов
  }
}
```

## 📊 Метрики и мониторинг

### **Ключевые метрики**
- **Время ввода PIN** - среднее время от начала до завершения
- **Количество ошибок** - неправильные вводы
- **Успешность ввода** - процент успешных завершений
- **Время отклика** - задержка между нажатием и обновлением UI

### **Логирование**
```javascript
const keyboardLogger = {
  logInput(key, timestamp) {
    console.log(`[KEYBOARD] Input: ${key} at ${timestamp}`);
  },
  
  logError(error, context) {
    console.error(`[KEYBOARD] Error: ${error} in ${context}`);
  },
  
  logPerformance(metric, value) {
    console.log(`[KEYBOARD] ${metric}: ${value}ms`);
  }
};
```

## 🔍 Отладка и диагностика

### **Режим отладки**
```javascript
const DEBUG_MODE = localStorage.getItem('keyboard_debug') === 'true';

if (DEBUG_MODE) {
  // Дополнительное логирование
  console.log('🍄 Keyboard Debug Mode Enabled');
  
  // Визуальные индикаторы
  document.body.classList.add('keyboard-debug');
}
```

### **Инструменты разработчика**
```javascript
// Глобальные функции для консоли
window.keyboardDebug = {
  getState: () => ({
    currentInput: currentPinInput,
    firstEntry: firstPinEntry,
    pinStep: pinStep
  }),
  
  simulateInput: (key) => handlePinInput(key),
  
  clearInput: () => {
    currentPinInput = [];
    updateDisplay();
  },
  
  setStep: (step) => {
    pinStep = step;
    window.pinStep = step;
  }
};
```

## 📚 Примеры использования

### **Базовое использование**
```javascript
// Инициализация клавиатуры
const keyboard = new AmanitaKeyboard('setup-pin-screen');

// Обработка ввода
keyboard.on('input', (key) => {
  console.log(`Нажата клавиша: ${key}`);
});

// Обработка завершения
keyboard.on('complete', (pin) => {
  console.log(`PIN введен: ${pin}`);
});
```

### **Кастомизация**
```javascript
// Настройка клавиатуры
const customKeyboard = new AmanitaKeyboard('setup-pin-screen', {
  maxLength: 6,
  autoSubmit: false,
  visualFeedback: true,
  soundFeedback: true
});
```

## 🎯 Заключение

Мухоморная клавиатура - это ключевой компонент UX приложения Amanita, требующий постоянного улучшения для обеспечения безопасности, удобства использования и надежности. Предложенный план улучшений направлен на создание более модульной, тестируемой и производительной системы ввода PIN-кода.
