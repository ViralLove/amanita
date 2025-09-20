let currentWallet = null;
let walletCreated = false;
let seedVisible = false;
// Глобальный флаг для Telegram API
let telegramAPIAvailable = false;
// Флаг для статуса инвайта
let inviteVerified = false;

// Глобальный объект для хранения текущей локализации
let localization = {};
let currentLanguage = 'ru'; // По умолчанию используем русский
const { mode, invite_verified, order_id, discount_tokens, address, language } = getParameters();


console.log("🔍 Скрипт main.js загружен");

// Функция для показа уведомления вместо стандартного alert
function showNotification(message, type = 'info', duration = 5000) {
  console.log(`🔔 [showNotification] Начало функции: ${message} (тип: ${type})`);
  logIfAvailable(`Показ уведомления: ${message} (тип: ${type})`);
  
  try {
    console.log("🔍 [showNotification] Шаг 1: Ищем контейнер для уведомлений");
  // Получаем контейнер для уведомлений
  const container = document.getElementById('notifications-container');
    console.log("🔍 [showNotification] Контейнер найден:", container ? "ДА" : "НЕТ");
    
  if (!container) {
      console.warn("⚠️ [showNotification] Контейнер не найден, используем alert");
    // Запасной вариант - показываем обычный alert
    alert(message);
      console.log("✅ [showNotification] Alert показан успешно");
    return;
  }
  
    console.log("🔍 [showNotification] Шаг 2: Создаем элемент уведомления");
  // Создаем элемент уведомления
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
    console.log("🔍 [showNotification] Элемент уведомления создан");
  
    console.log("🔍 [showNotification] Шаг 3: Определяем иконку");
  // Определяем иконку в зависимости от типа уведомления
  let icon = '';
  switch (type) {
    case 'success':
      icon = '✅';
      break;
    case 'error':
      icon = '❌';
      break;
    case 'warning':
      icon = '⚠️';
      break;
    default:
      icon = 'ℹ️';
  }
    console.log("🔍 [showNotification] Иконка определена:", icon);
  
    console.log("🔍 [showNotification] Шаг 4: Добавляем содержимое уведомления");
  // Добавляем содержимое уведомления
  notification.innerHTML = `
    <div class="notification-content">
      <div class="notification-icon">${icon}</div>
      <div class="notification-message">${message}</div>
    </div>
  `;
    console.log("🔍 [showNotification] Содержимое добавлено");
  
    console.log("🔍 [showNotification] Шаг 5: Добавляем уведомление в контейнер");
  // Добавляем уведомление в контейнер
  container.appendChild(notification);
    console.log("🔍 [showNotification] Уведомление добавлено в контейнер");
  
    console.log("🔍 [showNotification] Шаг 6: Показываем уведомление с анимацией");
  // Делаем уведомление видимым с помощью CSS-анимации
  setTimeout(() => {
    notification.classList.add('visible');
      console.log("🔍 [showNotification] Анимация показа запущена");
  }, 10);
  
    console.log("🔍 [showNotification] Шаг 7: Настраиваем автоматическое скрытие");
  // Задаем таймер для скрытия уведомления
  setTimeout(() => {
    // Добавляем класс для анимации исчезновения
    notification.classList.add('fading');
      console.log("🔍 [showNotification] Анимация скрытия запущена");
    
    // После завершения анимации удаляем элемент
    setTimeout(() => {
      notification.remove();
        console.log("🔍 [showNotification] Уведомление удалено из DOM");
    }, 500); // 500ms - продолжительность анимации fadeOut
  }, duration);
  
    console.log("✅ [showNotification] Функция выполнена успешно");
  return notification;
    
  } catch (error) {
    console.error("❌ [showNotification] Ошибка в showNotification:", error);
    console.error("🔍 [showNotification] Детали ошибки:", error.message);
    console.error("🔍 [showNotification] Стек ошибки:", error.stack);
    // Fallback - показываем alert
    alert(message);
    console.log("✅ [showNotification] Fallback alert показан");
  }
}

function getParameters() {
  const params = {};

  // Из URL
  const urlParams = new URLSearchParams(window.location.search);
  ['mode', 'language', 'invite_verified', 'order_id', 'tx_type', 'discount_tokens', 'address', 'source'].forEach(key => {
    if (urlParams.has(key)) {
      const value = urlParams.get(key);
      params[key] = (value === 'true') ? true : (value === 'false') ? false : value;
      logIfAvailable(`URL-параметр ${key} = ${params[key]}`);
    }
  });

  // Из Telegram initData
  if (window.Telegram?.WebApp?.initDataUnsafe?.start_param) {
    const startParam = window.Telegram.WebApp.initDataUnsafe.start_param;
    const pairs = startParam.split('&');
    pairs.forEach(pair => {
      const [key, value] = pair.split('=');
      if (key && value && !(key in params)) {
        params[key] = (value === 'true') ? true : (value === 'false') ? false : value;
        logIfAvailable(`start_param: ${key} = ${params[key]}`);
      }
    });
  }

  logIfAvailable("🌱 Получены параметры: " + JSON.stringify(params));

  return params;
}

// Функция для получения переменных окружения
function getEnvVar(name, defaultValue = '') {
  // Проверяем Railway переменные
  if (window.RAILWAY_ENV && window.RAILWAY_ENV[name] !== undefined) {
    return window.RAILWAY_ENV[name];
  }
  
  // Проверяем URL параметры
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has(name.toLowerCase())) {
    return urlParams.get(name.toLowerCase());
  }
  
  // Проверяем localStorage для локальной разработки
  const localValue = localStorage.getItem(`amanita_${name.toLowerCase()}`);
  if (localValue !== null) {
    return localValue;
  }
  
  return defaultValue;
}

// Глобальная переменная для управления логами
window.DEBUG_MODE = getEnvVar('DEBUG_MODE', 'false') === 'true' ||
                   window.location.hostname === 'localhost' || 
                   window.location.hostname === '127.0.0.1' ||
                   window.location.search.includes('debug=true') ||
                   localStorage.getItem('amanita_debug') === 'true';

// Дополнительная функция логирования для совместимости с индексным файлом
function logIfAvailable(message, isError = false) {
  console.log(message);
  
  // Проверяем, включен ли режим отладки
  if (!window.DEBUG_MODE) {
    return;
  }
  
  // Добавляем временную метку
  const timestamp = new Date().toLocaleTimeString();
  const formattedMessage = `[${timestamp}] ${message}`;
  
  // Логируем в debug-panel
  const logElem = document.getElementById('init-log');
  if (logElem) {
    const line = document.createElement('div');
    line.textContent = formattedMessage;
    if (isError) {
      line.style.color = '#ff6b6b';
    }
    logElem.appendChild(line);
    
    // Автоматическая прокрутка вниз
    logElem.scrollTop = logElem.scrollHeight;
  }
}

// Функция для сбора информации о состоянии Telegram API
function inspectTelegramAPI() {
  const info = {
    windowHasTelegram: typeof window.Telegram !== 'undefined',
    telegramAPIAvailable: telegramAPIAvailable,
    navigatorAppVersion: navigator.appVersion,
    userAgent: navigator.userAgent,
    windowInnerWidth: window.innerWidth,
    windowInnerHeight: window.innerHeight,
    timestamp: new Date().toISOString()
  };
  
  if (window.Telegram && Telegram.WebApp && typeof window.Telegram !== 'undefined') {
    info.hasWebApp = typeof window.Telegram.WebApp !== 'undefined';
    
    if (info.hasWebApp) {
      info.webAppVersion = window.Telegram.WebApp.version;
      info.webAppPlatform = window.Telegram.WebApp.platform;
      info.webAppColorScheme = window.Telegram.WebApp.colorScheme;
      info.hasSendData = typeof window.Telegram.WebApp.sendData === 'function';
    }
  }
  
  console.log("📊 Состояние Telegram API:", JSON.stringify(info, null, 2));
  return info;
}

window.addEventListener("DOMContentLoaded", async () => {
  console.log("🔄 DOM полностью загружен");
  logIfAvailable("🔄 DOM полностью загружен");

  // Загружаем изображения для пин-пада
  loadImages();
  logIfAvailable("🖼️ Запущена загрузка изображений для пин-пада");

  // Проверяем доступность Telegram WebApp API
  if (window.Telegram && Telegram.WebApp) {
    console.log("📱 Telegram WebApp API доступен");
    console.log("📊 WebApp данные:", {
      initData: window.Telegram.WebApp.initData,
      version: window.Telegram.WebApp.version,
      platform: window.Telegram.WebApp.platform
    });

    try {
    Telegram.WebApp.ready();
      telegramAPIAvailable = true;
      Telegram.WebApp.expand();
      logIfAvailable("✅ Telegram WebApp инициализирован");
    } catch (err) {
      console.error("❌ Ошибка при инициализации WebApp:", err);
      logIfAvailable(`❌ Ошибка при инициализации WebApp: ${err.message}`, true);
      telegramAPIAvailable = false;
    }
  } else {
    console.warn("⚠️ Telegram WebApp недоступен — запущено вне Telegram?");
    logIfAvailable("⚠️ Telegram WebApp недоступен — запущено вне Telegram?", true);
    telegramAPIAvailable = false;
  }

  logIfAvailable("🌱 Язык: " + language);

  const preferredLanguage = localStorage.getItem('preferredLanguage') || language || 'ru';
  await loadLocalization(preferredLanguage);
  updateUIWithLocalization();

  attachUIHandlers();
  handleInitialView();
});


// === Telegram WebApp Init ===
function initTelegramAPI() {
  logIfAvailable("Инициализация Telegram WebApp API");
  if (window.Telegram && Telegram.WebApp) {
    logIfAvailable("✅ Telegram WebApp API доступен");
    telegramAPIAvailable = true;
    
    try {
      logIfAvailable("Вызываем Telegram.WebApp.ready()");
    Telegram.WebApp.ready();
      logIfAvailable("Вызываем Telegram.WebApp.expand()");
    Telegram.WebApp.expand(); // optional
      
      // Проверяем наличие метода sendData
      if (typeof Telegram.WebApp.sendData === 'function') {
        logIfAvailable("✅ Метод Telegram.WebApp.sendData доступен");
      } else {
        logIfAvailable("⚠️ Метод Telegram.WebApp.sendData НЕ доступен", true);
      }
      
      // Регистрируем обработчик для mainButton если он доступен
      if (Telegram.WebApp.MainButton) {
        logIfAvailable("✅ Telegram.WebApp.MainButton доступен");
        Telegram.WebApp.MainButton.onClick(function() {
          logIfAvailable("MainButton был нажат");
        });
      } else {
        logIfAvailable("⚠️ Telegram.WebApp.MainButton НЕ доступен");
      }
    } catch (err) {
      logIfAvailable(`❌ Ошибка при инициализации Telegram WebApp API: ${err.message}`, true);
    }
  } else {
    logIfAvailable("⚠️ Telegram WebApp API не доступен, возможно тестирование вне Telegram", true);
    telegramAPIAvailable = false;
  }
}

// === Attach button handlers ===
function attachUIHandlers() {
  logIfAvailable("Привязка обработчиков событий к кнопкам");
  
  const createBtn = document.getElementById('create-btn');
  const restoreBtn = document.getElementById('restore-btn');
  const restoreConfirmBtn = document.getElementById('restore-confirm-btn');
  const revealSeedBtn = document.getElementById('reveal-seed-btn');
  const backToStartBtn = document.getElementById('back-to-start-btn');
  const clearWalletBtn = document.getElementById('clear-wallet-btn');
  const confirmWalletBtn = document.getElementById('btn_confirm_wallet');
  const copySeedBtn = document.getElementById('copy-seed-btn');
  
  if (!createBtn) logIfAvailable("❌ Кнопка create-btn не найдена!", true);
  if (!restoreBtn) logIfAvailable("❌ Кнопка restore-btn не найдена!", true);
  if (!restoreConfirmBtn) logIfAvailable("❌ Кнопка restore-confirm-btn не найдена!", true);
  if (!revealSeedBtn) logIfAvailable("❌ Кнопка reveal-seed-btn не найдена!", true);
  if (!backToStartBtn) logIfAvailable("❌ Кнопка back-to-start-btn не найдена!", true);
  if (!clearWalletBtn) logIfAvailable("❌ Кнопка clear-wallet-btn не найдена!", true);
  if (!confirmWalletBtn) logIfAvailable("❌ Кнопка btn_confirm_wallet не найдена!", true);
  if (!copySeedBtn) logIfAvailable("❌ Кнопка copy-seed-btn не найдена!", true);
  
  if (createBtn) {
    logIfAvailable("✅ Привязываем обработчик к кнопке создания кошелька");
    createBtn.onclick = function(e) {
      logIfAvailable("👆 Кнопка создания кошелька нажата");
      
      // Логируем состояние Telegram API при нажатии
      logIfAvailable("Проверка Telegram API при нажатии кнопки создания:");
      const apiState = inspectTelegramAPI();
      
      // Предварительная проверка перед вызовом
      if (typeof ethers === 'undefined') {
        logIfAvailable("❌ ethers.js не загружен при нажатии на кнопку", true);
        showNotification("Библиотека ethers.js не загружена. Обновите страницу или попробуйте позже.", "error");
        return;
      }
      handleCreateWallet();
    };
  }
  
  if (restoreBtn) restoreBtn.onclick = showRestoreScreen;
  if (restoreConfirmBtn) restoreConfirmBtn.onclick = handleRestoreWallet;
  if (revealSeedBtn) revealSeedBtn.onclick = toggleSeedVisibility;
  if (backToStartBtn) backToStartBtn.onclick = () => switchView('start-screen');
  if (copySeedBtn) copySeedBtn.onclick = copySeedPhrase;
  
  if (confirmWalletBtn) {
    confirmWalletBtn.onclick = function() {
      switchView('setup-pin-screen');
      currentPinInput = [];
      firstPinEntry = [];
      pinStep = "firstEntry";
      updatePinTexts(t('setup_pin_title'), t('setup_pin_description'));
    }
  }

  // Обработчики для новых кнопок управления кошельком
  if (clearWalletBtn) {
    clearWalletBtn.onclick = clearWallet;
  }
  
}

// === Check if wallet already exists in storage ===
function checkExistingWallet() {
  const stored = localStorage.getItem('seedEncrypted');
  if (stored) {
    logIfAvailable("💾 Обнаружен ранее сохранённый кошелёк");
    viewWallet();
  } else {
    logIfAvailable("🔍 Кошелёк не найден — продолжим инициализацию по mode");
    // handleInitialView() теперь вызывается отдельно в DOMContentLoaded
  }
}

// Функция для определения начального экрана на основе статуса инвайта
function handleInitialView() {

  logIfAvailable("🌱 Режим: " + mode);
  logIfAvailable("🌱 Инвайт: " + invite_verified);

  if (mode === 'recovery_only') {
    logIfAvailable("🌀 Вход в режим восстановления (только восстановление, recovery_only)");
    switchView('restore-screen');
    return;
  }

  if (mode === 'create_new' && invite_verified === true) {
    logIfAvailable("🧪 Начинаем генерацию нового кошелька...");
    handleCreateWallet();
    return;
  }

  if (mode === 'view_seed') {
    handleViewSeed();
    return;
  }

  if (mode === 'sign_tx') {
    handleSignTransaction();
    return;
  }

  switchView('start-screen'); // fallback
}


// Функция для очистки кошелька
function clearWallet(nextScreen) {
  logIfAvailable("🔄 Запущено удаление кошелька");
  
  try {
    // Удаляем данные из localStorage
    localStorage.removeItem('seedEncrypted');
    localStorage.removeItem('wallet_address');
    
    // Сбрасываем переменные состояния
    currentWallet = null;
    walletCreated = false;
    seedVisible = false;
    
    logIfAvailable("✅ Кошелек успешно удален");
    
    if (nextScreen) {
      switchView(nextScreen);
    }
  } catch (err) {
    logIfAvailable(`❌ Ошибка при удалении кошелька: ${err.message}`, true);
    showNotification(`Не удалось удалить кошелек: ${err.message}`, "error");
  }
}

// === Wallet Creation ===
function handleCreateWallet() {
  logIfAvailable("🧪 Начинаем генерацию нового кошелька...");

  clearWallet();
  
  try {
    switchView('loading-screen');
    document.getElementById('loading-text').textContent = t('loading_create');
    
    if (typeof ethers === 'undefined') {
      throw new Error(t('error_ethers_not_loaded'));
    }
    
    logIfAvailable("Создаем случайный кошелек через ethers.Wallet.createRandom()");
    
    // Проверяем доступность метода
    if (typeof ethers.Wallet === 'undefined') {
      throw new Error("ethers.Wallet не определен");
    }
    
    if (typeof ethers.Wallet.createRandom !== 'function') {
      throw new Error("ethers.Wallet.createRandom не является функцией");
    }
    
    logIfAvailable("Проверка API ethers успешна, создаем кошелек...");
    
    // Используем setTimeout для имитации асинхронной операции и отображения экрана загрузки
    setTimeout(() => {
      try {
        logIfAvailable("Вызываем ethers.Wallet.createRandom()");
  const wallet = ethers.Wallet.createRandom();
        logIfAvailable(`✅ Кошелек успешно создан: ${wallet.address}`);
        
        // В ethers.js v5.x mnemonic это объект с фразой в свойстве phrase
        const mnemonicPhrase = wallet.mnemonic && wallet.mnemonic.phrase ? wallet.mnemonic.phrase : "Ошибка: фраза не получена";
        
  currentWallet = {
    address: wallet.address,
          mnemonic: mnemonicPhrase,
    privateKey: wallet.privateKey,
    restored: false
  };

        // Обновляем UI с адресом и мнемоникой
        const mnemonicElem = document.getElementById('wallet-mnemonic');
        const addressElem = document.getElementById('wallet-address');
        
        if (mnemonicElem) {
        mnemonicElem.value = mnemonicPhrase;
          logIfAvailable("✅ Мнемоника установлена в поле ввода");
        } else {
          logIfAvailable("❌ Элемент wallet-mnemonic не найден!", true);
        }

        if (addressElem) {
          addressElem.textContent = wallet.address;
          logIfAvailable("✅ Адрес установлен в элемент отображения");
        } else {
          logIfAvailable("❌ Элемент wallet-address не найден!", true);
        }
      
      // Показываем элементы для работы с сид-фразой
      const revealBtn = document.getElementById('reveal-seed-btn');
        if (revealBtn) {
          revealBtn.style.display = 'block';
          logIfAvailable("✅ Кнопка показа сид-фразы активирована");
        }

        showNotification(t('account_created_success'), "success");
        logIfAvailable("✅ Процесс создания кошелька завершен успешно");
        switchView('seed-screen');
      } catch (err) {
        logIfAvailable(`❌ Ошибка при создании кошелька: ${err.message}`, true);
        showNotification(`Не удалось создать кошелек: ${err.message}`, "error");
        switchView('start-screen');
      }
    }, 500);
  } catch (err) {
    logIfAvailable(`❌ ${t('error_wallet_creation')}: ${err.message}`, true);
    showNotification(`${t('error_wallet_creation')}: ${err.message}`, "error");
    switchView('start-screen');
  }
}

// === Wallet Restoration (с обязательной установкой PIN) ===
function handleRestoreWallet() {
  logIfAvailable("🔄 Запущено восстановление мухоморного аккаунта");
  const mnemonic = document.getElementById('mnemonic-input').value.trim();
  const error = document.getElementById('restore-error');
  error.textContent = "";
  error.classList.add('hidden');

  if (!mnemonic) {
    logIfAvailable("⚠️ Пустая сид-фраза (мухоморный пароль)", true);
    error.textContent = t("restore_missing_seed");
    error.classList.remove('hidden');
    return;
  }

  try {
    switchView('loading-screen');
    document.getElementById('loading-text').textContent = t('loading_restore');

    if (typeof ethers === 'undefined') {
      throw new Error(t('error_no_ethers'));
    }

    logIfAvailable("🌱 Восстанавливаем аккаунт из сид-фразы...");

    setTimeout(() => {
      try {
        const wallet = ethers.Wallet.fromMnemonic(mnemonic);
        logIfAvailable(`✅ Аккаунт успешно восстановлен: ${wallet.address.substring(0, 10)}...`);

    currentWallet = {
      address: wallet.address,
          mnemonic: mnemonic, // Используем оригинальную введенную мнемонику
          privateKey: wallet.privateKey,
          restored: true     // Указываем, что кошелек восстановлен
        };

        // После успешного восстановления из сид-фразы, переходим к установке PIN
        logIfAvailable("✅ Восстановление кошелька из сид-фразы успешно, переход к установке PIN.");
        switchView('setup-pin-screen');
        currentPinInput = [];
        firstPinEntry = [];
        pinStep = "firstEntry";
        // Обновляем глобальные переменные
        window.currentPinInput = currentPinInput;
        window.firstPinEntry = [...firstPinEntry];
        window.pinStep = pinStep;
        updatePinTexts(t('setup_pin_title'), t('setup_pin_description'));

      } catch (err) {
        logIfAvailable(`❌ Ошибка при парсинге сид-фразы или создании кошелька: ${err.message}`, true);
        const restoreErrorElem = document.getElementById('restore-error');
        if(restoreErrorElem){
            restoreErrorElem.textContent = t("restore_invalid_seed") + " (" + err.message + ")";
            restoreErrorElem.classList.remove('hidden');
        }
        switchView('restore-screen');
      }
    }, 500);

  } catch (err) {
    logIfAvailable(`❌ Критическая ошибка при попытке восстановления (возможно, ethers не загружен): ${err.message}`, true);
    const restoreErrorElem = document.getElementById('restore-error'); 
    if(restoreErrorElem) {
        restoreErrorElem.textContent = t("restore_general_error") + " (" + err.message + ")"; 
        restoreErrorElem.classList.remove('hidden');
    }
    switchView('restore-screen');
  }
}

// === Show wallet info UI ===
function viewWallet() {
  logIfAvailable("Отображение информации о кошельке");
  try {
    const addressElem = document.getElementById('wallet-address');
    const mnemonicElem = document.getElementById('wallet-mnemonic');
    
    if (!addressElem) {
      logIfAvailable("Элемент wallet-address не найден", true);
      return;
    }
    if (!mnemonicElem) {
      logIfAvailable("Элемент wallet-mnemonic не найден", true);
      return;
    }
    
    if (!currentWallet) {
      logIfAvailable("Ошибка: currentWallet не определен", true);
      return;
    }
    
    // Проверяем наличие всех необходимых данных
    if (!currentWallet.address) {
      logIfAvailable("Ошибка: currentWallet.address не определен", true);
      return;
    }
    
    addressElem.textContent = currentWallet.address;
    
    // Проверяем, есть ли доступ к мнемонической фразе
    if (currentWallet.mnemonic) {
      mnemonicElem.value = seedVisible
    ? currentWallet.mnemonic
    : "******** ******** ******** ******** ******** ********";

      // Показываем элементы для работы с сид-фразой
      const revealBtn = document.getElementById('reveal-seed-btn');
      if (revealBtn) revealBtn.style.display = 'block';
    } else {
      // Если сид-фраза недоступна, показываем соответствующее сообщение
      mnemonicElem.value = t("error_seed_unavailable");
      mnemonicElem.classList.add('error');
      
      // Скрываем кнопку показа/скрытия сид-фразы
      const revealBtn = document.getElementById('reveal-seed-btn');
      if (revealBtn) revealBtn.style.display = 'none';
    }

    switchView('seed-screen');
    logIfAvailable("✅ Информация о кошельке успешно отображена");
  } catch (err) {
    logIfAvailable(`❌ Ошибка при отображении информации о кошельке: ${err.message}`, true);
  }
}

// === Toggle mnemonic visibility ===
function toggleSeedVisibility() {
  logIfAvailable("Переключение видимости сид-фразы");
  seedVisible = !seedVisible;
  const seedElem = document.getElementById('wallet-mnemonic');
  
  if (!currentWallet || !currentWallet.mnemonic) {
    logIfAvailable("⚠️ Невозможно показать сид-фразу - данные недоступны", true);
    showNotification(t("error_seed_unavailable"), "warning");
    if (seedElem) seedElem.value = t("error_seed_unavailable"); 
    return;
  }
  
  if (seedElem) { 
    seedElem.value = seedVisible
    ? currentWallet.mnemonic
    : "******** ******** ******** ******** ******** ********";
      
    if (seedVisible) {
      logIfAvailable("⚠️ Сид-фраза отображается в открытом виде - убедитесь, что никто не подсматривает", true);
      showNotification(t("seed_visible_warning"), "warning");
    } else {
      showNotification(t("seed_hidden"), "success");
    }
  } else {
    logIfAvailable("Error: wallet-mnemonic element not found during toggleSeedVisibility", true);
  }
}

// === Копировать мухоморный пароль в буфер обмена ===
function copySeedPhrase() {
  logIfAvailable("Копирование мухоморного пароля в буфер обмена");
  const seedElem = document.getElementById('wallet-mnemonic');
  
  if (!currentWallet || !currentWallet.mnemonic) {
    logIfAvailable("⚠️ Невозможно скопировать мухоморный пароль - данные недоступны", true);
    showNotification(t("error_seed_unavailable"), "error");
    return;
  }
  
  if (!seedElem) {
    logIfAvailable("Error: wallet-mnemonic element not found during copySeedPhrase", true);
    showNotification(t("error_internal_ui"), "error"); // Общая ошибка UI
    return;
  }

  try {
    const wasSeedVisible = seedVisible;
    
    if (!wasSeedVisible) {
      if (seedElem) seedElem.value = currentWallet.mnemonic;
    }
    
    navigator.clipboard.writeText(currentWallet.mnemonic)
      .then(() => {
        logIfAvailable("✅ Мухоморный пароль скопирован в буфер обмена");
        showNotification(t("copy_seed_success"), "success");
        
        if (!wasSeedVisible) {
          if (seedElem) seedElem.value = 
            "******** ******** ******** ******** ******** ********";
        }
      })
      .catch(err => {
        logIfAvailable(`❌ Ошибка при копировании в буфер обмена: ${err.message}`, true);
        showNotification(t("copy_seed_error") + ": " + err.message, "error");
      });
  } catch (err) {
    logIfAvailable(`❌ Ошибка при копировании мухоморного пароля: ${err.message}`, true);
    showNotification(t("copy_seed_error") + ": " + err.message, "error");
  }
}

// === View seed ===
function handleViewSeed() {
  logIfAvailable("🌱 Запрос на просмотр сид-фразы, переключаемся на ввод PIN");
  switchView("setup-pin-screen");
  updatePinTexts(t("pin_enter_to_view_seed"), t("pin_enter_to_view_seed_description")); 
  currentPinInput = [];
  firstPinEntry = []; 
  pinStep = "unlockSeed"; 
  logIfAvailable(`🔄 Установлен pinStep = "unlockSeed"`);
}

// === Sign transaction ===
function handleSignTransaction() {
  const urlParams = new URLSearchParams(window.location.search);
  const orderId = urlParams.get("order_id") || "ORDER";
  const txType = urlParams.get("tx_type") || "generic";
  const amount = urlParams.get("discount_tokens") || "0";
  const address = urlParams.get("address") || "";

  document.getElementById("tx-order-id").textContent = orderId;
  document.getElementById("tx-token-amount").textContent = amount;
  document.getElementById("sign-submit-btn").addEventListener("click", async () => {
    const pin = document.getElementById("sign-pin-input").value;
    const encrypted = localStorage.getItem("seedEncrypted");

    if (!encrypted) {
      showNotification(t("error_local_access"), "warning");
      return;
    }
    try {
      // Расшифровка с использованием AES-GCM
      const phrase = await decryptWithAES(encrypted, pin);
      const wallet = ethers.Wallet.fromMnemonic(phrase);
      const message = `SIGN_AMANITA_ORDER:${orderId}:${amount}`;
      wallet.signMessage(message).then(signature => {
        const payload = JSON.stringify({
          event: "tx_signed",
          signature,
          address: wallet.address,
          order_id: orderId,
          tx_type: txType
        });
        window.Telegram.WebApp.sendData(payload);
      }).catch(err => {
        console.error("Ошибка при подписании:", err);
        showNotification(t("sign_error_signing"), "error");
      });
    } catch (e) {
      console.error("Ошибка восстановления кошелька:", e);
      
      // Определяем тип ошибки для более точного сообщения
      if (e.message.includes("Не удалось расшифровать данные")) {
        showNotification(t("error_wrong_pin"), "error"); // "❌ Неверный PIN-код."
      } else {
        showNotification(t("error_verify_format"), "error"); // "Ошибка доступа к мухоморному паролю. Проверьте формат."
      }
    }
  });
  switchView("sign-screen");
}

// ===== Сохранение данных кошелька после установки PIN =====
async function saveWalletWithPin(mnemonic, pin, nextScreen) {
  console.log(`🔐 Вызов saveWalletWithPin, PIN: ${pin.replace(/./g, '*')}, экран: ${nextScreen}`);
  try {
    // Шифруем сид-фразу с использованием AES-GCM + PBKDF2
    console.log(`🔑 Начало AES-GCM шифрования сид-фразы`);
    logIfAvailable("🔐 Начало безопасного шифрования сид-фразы с AES-GCM");
    
    const encrypted = await encryptWithAES(mnemonic, pin);
    console.log(`💾 Запись в localStorage, длина зашифрованных данных: ${encrypted.length}`);
    localStorage.setItem("seedEncrypted", encrypted);
    logIfAvailable("✅ Сохраняем данные кошелька в localStorage с AES-GCM шифрованием");

    // Для простоты (и совместимости с другими частями) сохраняем адрес кошелька
    if (currentWallet && currentWallet.address) {
      console.log(`📝 Сохранение адреса кошелька: ${currentWallet.address.substring(0, 8)}...`);
      localStorage.setItem("wallet_address", currentWallet.address);
    } else {
      console.warn(`⚠️ Не найден адрес кошелька для сохранения`);
    }

    console.log(`🏁 Установка флага walletCreated = true`);
    walletCreated = true;

    // Отправляем адрес в бот ПОСЛЕ сохранения данных
    if (walletCreated) {
      const sent = sendAddressToBot();
      if (!sent) {
        logIfAvailable("⚠️ Не удалось отправить адрес в бот, но продолжаем...");
      }
    }

    // Проверяем, существует ли экран для перехода
    const targetScreen = document.getElementById(nextScreen);
    if (targetScreen) {
      console.log(`✅ Экран ${nextScreen} найден, переходим`);
      // Переходим на следующий экран
      console.log(`🔀 Переход на экран: ${nextScreen}`);
      switchView(nextScreen);
      logIfAvailable("🌱 Установка PIN завершена, переход на экран: " + nextScreen);
    } else {
      console.error(`❌ Экран ${nextScreen} не найден в DOM!`);
      console.error(`Доступные экраны: ${Array.from(document.querySelectorAll('.view')).map(el => el.id).join(', ')}`);
      showNotification("Внутренняя ошибка: экран не найден", "error");
      // Запасной вариант - возвращаемся на стартовый экран
      switchView('start-screen');
    }
  } catch (e) {
    console.error(`❌ Ошибка при сохранении PIN: ${e.message}`);
    logIfAvailable(`❌ Ошибка при установке PIN: ${e.message}`, true);
    showNotification("Ошибка при сохранении PIN. Попробуйте снова.", "error");
  }
}

// ===== PIN-Клавиатура: логика ввода =====
let currentPinInput = [];
let firstPinEntry = []; // Изменено на массив для тестирования
let pinStep = "firstEntry"; // либо "firstEntry" либо "confirmEntry"

// Экспортируем переменные в window для тестирования
window.currentPinInput = currentPinInput;
  window.firstPinEntry = [...firstPinEntry];
window.pinStep = pinStep;

// Навешиваем обработчики на кнопки
window.addEventListener('DOMContentLoaded', () => {
  console.log(`🔄 Инициализация обработчиков для мухоморных кнопок`);
  const setupPinScreen = document.getElementById('setup-pin-screen');
  if (setupPinScreen) {
    const mushroomButtons = setupPinScreen.querySelectorAll(".mushroom-key");
    console.log(`🔍 Найдено ${mushroomButtons.length} мухоморных кнопок на экране установки PIN`);

    mushroomButtons.forEach((btn, index) => {
      const key = btn.getAttribute("data-key");
      console.log(`🔄 Кнопка #${index + 1} на экране установки PIN: data-key="${key}"`);
      
      btn.addEventListener("click", (e) => {
        console.log(`👆 Клик по мухоморной кнопке с ключом: ${key} (экран установки PIN)`);
        // Убедимся, что мы на правильном экране, прежде чем обрабатывать ввод
        if (document.getElementById('setup-pin-screen').style.display === 'block') {
          handlePinInput(key);
        } else {
          console.warn("⚠️ Попытка обработать PIN-ввод с клавиатуры, когда экран setup-pin-screen не активен.");
        }
      });
    });
  } else {
    console.error('❌ Экран setup-pin-screen не найден при инициализации обработчиков клавиатуры PIN');
  }
});

// Универсальный обработчик нажатий на мухоморные кнопки
async function handlePinInput(key) {
  console.log(`🔑 Нажата кнопка с key=${key}, текущий ввод: [${currentPinInput.join(',')}]`);
  const activeSetupPinScreen = document.getElementById('setup-pin-screen');
  
  // Обрабатываем ввод только если экран установки PIN видим
  if (activeSetupPinScreen && activeSetupPinScreen.style.display === 'block') {
    const dots = activeSetupPinScreen.querySelectorAll(".pin-dot");

    if (!dots || dots.length === 0) {
      console.error("❌ Элементы .pin-dot не найдены на экране setup-pin-screen.");
      return;
    }

    if (key === "backspace") {
      console.log("🔙 Удаление последней цифры PIN");
      currentPinInput.pop();
      // Синхронизируем с глобальной переменной для тестирования
      window.currentPinInput = [...currentPinInput];
    } else if (key === "confirm") { // Эта логика здесь больше не нужна, т.к. есть отдельная кнопка submit
      // console.log(`🔐 Нажата кнопка подтверждения, длина PIN: ${currentPinInput.length}`);
      // if (currentPinInput.length === 5) {
      //   console.log("✅ Длина PIN = 5, вызываем processPinEntry()");
      //   processPinEntry();
      // } else {
      //   console.log(`⚠️ Неверная длина PIN: ${currentPinInput.length}, требуется 5 цифр`);
      //   showNotification(t("error_pin_length_generic") || "Введите 5 цифр PIN-кода", "warning");
      // }
      console.log("⚠️ Кнопка 'confirm' на клавиатуре была нажата, но теперь используется выделенная кнопка 'Подтвердить'");
    } else if (currentPinInput.length < 5 && /^[0-9]$/.test(key)) {
      console.log(`➕ Добавлена цифра ${key}, новая длина: ${currentPinInput.length + 1}`);
      currentPinInput.push(key);
      // Синхронизируем с глобальной переменной для тестирования
      try {
        console.log(`🔧 Синхронизация: currentPinInput = [${currentPinInput.join(',')}]`);
        window.currentPinInput = [...currentPinInput];
        console.log(`🔧 Синхронизация: window.currentPinInput = [${window.currentPinInput.join(',')}]`);
      } catch (error) {
        console.error("❌ Ошибка синхронизации:", error);
      }
    }

    // Обновляем отображение точек
    dots.forEach((dot, index) => {
      dot.classList.toggle("filled", index < currentPinInput.length);
    });
    console.log(`🔵 Обновлены точки PIN (${currentPinInput.length}/5)`);

    // Если введено 5 цифр, автоматически вызываем processPinEntry
    if (currentPinInput.length === 5) {
      console.log("✅ Введено 5 цифр PIN, автоматически вызываем processPinEntry()");
      try {
        await processPinEntry();
      } catch (err) {
        console.error(`❌ Ошибка при обработке PIN: ${err.message}`);
        logIfAvailable(`❌ Ошибка при обработке PIN: ${err.message}`, true);
        showNotification("Ошибка при обработке PIN. Попробуйте снова.", "error");
      }
    }
  } else {
    console.warn("⚠️ Попытка обработать PIN-ввод, когда экран setup-pin-screen не активен или не найден.");
  }
}

// Обработка ввода PIN при нажатии кнопки "OK"
async function processPinEntry() {
  console.log("🔍 [processPinEntry] НАЧАЛО ФУНКЦИИ");
  
  // Читаем из глобальных переменных для тестирования
  console.log(`🔍 [processPinEntry] ДО синхронизации: window.currentPinInput = [${window.currentPinInput.join(',')}]`);
  console.log(`🔍 [processPinEntry] ДО синхронизации: currentPinInput (локальная) = [${currentPinInput.join(',')}]`);
  
  // ПРИНУДИТЕЛЬНАЯ синхронизация - используем window.currentPinInput если он есть
  if (window.currentPinInput && window.currentPinInput.length > 0) {
    currentPinInput = [...window.currentPinInput];
    console.log(`🔧 ПРИНУДИТЕЛЬНАЯ синхронизация: currentPinInput = [${currentPinInput.join(',')}]`);
  }
  
  pinStep = window.pinStep || pinStep;
  firstPinEntry = window.firstPinEntry || firstPinEntry;
  // Убеждаемся, что firstPinEntry - массив
  if (!Array.isArray(firstPinEntry)) {
    firstPinEntry = [];
  }
  
  // Синхронизируем обратно для тестирования
  window.currentPinInput = [...currentPinInput];
  window.pinStep = pinStep;
  window.firstPinEntry = [...firstPinEntry];
  console.log(`🔍 [processPinEntry] ПОСЛЕ синхронизации: currentPinInput = [${currentPinInput.join(',')}]`);
  console.log(`🔍 [processPinEntry] ПОСЛЕ синхронизации: window.currentPinInput = [${window.currentPinInput.join(',')}]`);
  
  console.log("🔍 [processPinEntry] currentPinInput:", currentPinInput);
  console.log("🔍 [processPinEntry] pinStep:", pinStep);
  console.log("🔍 [processPinEntry] window.pinStep:", window.pinStep);
  
  const enteredPin = currentPinInput.join("");
  console.log("🔍 [processPinEntry] enteredPin:", enteredPin.replace(/./g, '*'));
  
  logIfAvailable(`🔄 [PIN] Запущена функция processPinEntry(), этап: ${pinStep}`);

  if (pinStep === "firstEntry") {
    console.log("🔍 [processPinEntry] ВХОДИМ В БЛОК firstEntry");
    logIfAvailable("🥇 [PIN] Первый ввод PIN сохранён, переход ко второму вводу");
    // Сохраняем PIN как массив для тестирования
    firstPinEntry = [...currentPinInput];
    currentPinInput = [];
    pinStep = "confirmEntry";
    // Обновляем глобальные переменные
    window.firstPinEntry = [...firstPinEntry];
    window.currentPinInput = [...currentPinInput];
    window.pinStep = pinStep;
    updatePinTitle(t("pin_confirm_title"));
  } else if (pinStep === "confirmEntry") {
    console.log("🔍 [processPinEntry] ВХОДИМ В БЛОК confirmEntry");
    logIfAvailable("🔍 [PIN] Начинаем проверку совпадения PIN-кодов");
    // Сравниваем строку с массивом
    const firstPinString = Array.isArray(firstPinEntry) ? firstPinEntry.join("") : firstPinEntry;
    if (enteredPin === firstPinString) {
      logIfAvailable("✅ [PIN] PIN-коды совпадают, начинаем процесс сохранения");
      
      if (currentWallet && currentWallet.mnemonic) {
        logIfAvailable("💼 [WALLET] Кошелёк найден, начинаем процесс сохранения");
        
        // 1. Сохраняем кошелек локально с AES-GCM шифрованием
        logIfAvailable("💾 [STEP 1/4] Сохраняем кошелек локально с AES-GCM шифрованием");
        await saveWalletWithPin(currentWallet.mnemonic, enteredPin, "success-screen");
        
        // 2. Показываем success screen
        logIfAvailable("🎉 [STEP 2/4] Переключаемся на success screen");
        switchView("success-screen");
        
        // 3. Показываем уведомление об успехе
        logIfAvailable("✨ [STEP 3/4] Показываем уведомление об успехе");
        showNotification(t("pin_set_success"), "success");

        // 4. Логируем готовность к отправке данных
        logIfAvailable("📤 [STEP 4/4] Готовы к отправке данных при нажатии на кнопку");
        logIfAvailable(`🔐 [DEBUG] walletCreated = ${walletCreated}`);
        logIfAvailable(`🔐 [DEBUG] dataWasSent = ${window.dataWasSent}`);

      } else {
        logIfAvailable("❌ [ERROR] Ошибка: объект currentWallet не существует или не содержит mnemonic", true);
        showNotification(t("error_wallet_data_unavailable_on_pin_confirm"), "error");
      }
    } else {
      logIfAvailable("⚠️ [PIN] PIN-коды не совпадают, возврат к первому вводу");
      showNotification(t("error_pin_mismatch"), "error");
      currentPinInput = [];
      firstPinEntry = [];
      pinStep = "firstEntry";
      // Синхронизируем глобальные переменные
      window.currentPinInput = [...currentPinInput];
      window.firstPinEntry = [...firstPinEntry];
      window.pinStep = pinStep;
      updatePinTexts(t('setup_pin_title'), t('setup_pin_description')); 
    }
  } else if (pinStep === "unlockSeed") {
    console.log("🔍 [processPinEntry] ВХОДИМ В БЛОК unlockSeed");
    console.log(`🔑 Попытка разблокировать сид-фразу с PIN: ${enteredPin.replace(/./g, '*')}`);
    
    // Получаем seedEncrypted из localStorage в области видимости блока unlockSeed
    console.log("🔍 [unlockSeed] Шаг 1: Получаем seedEncrypted из localStorage");
    const encrypted = localStorage.getItem("seedEncrypted");
    console.log("🔍 [unlockSeed] seedEncrypted:", encrypted ? "найден" : "НЕ НАЙДЕН");

    if (!encrypted) {
        console.log("🔍 [unlockSeed] Шаг 2: seedEncrypted отсутствует, начинаем обработку ошибки");
      console.error("❌ Зашифрованные данные не найдены в localStorage для unlockSeed");
        
        console.log("🔍 [unlockSeed] Шаг 3: Вызываем showNotification");
        try {
          showNotification(t("error_no_wallet_for_pin_unlock"), "error");
          console.log("✅ [unlockSeed] showNotification выполнен успешно");
        } catch (error) {
          console.error("❌ [unlockSeed] Ошибка в showNotification:", error);
          // Продолжаем выполнение даже при ошибке в showNotification
        }
        
        console.log("🔍 [unlockSeed] Шаг 4: Сбрасываем pinStep на firstEntry");
        pinStep = "firstEntry";
        // Обновляем глобальную переменную
        window.pinStep = pinStep;
        console.log("🔍 [unlockSeed] pinStep после сброса:", pinStep);
        
        console.log("🔍 [unlockSeed] Шаг 5: Вызываем updatePinTexts");
        try {
      updatePinTexts(t('setup_pin_title'), t('setup_pin_description'));
          console.log("✅ [unlockSeed] updatePinTexts выполнен успешно");
        } catch (error) {
          console.error("❌ [unlockSeed] Ошибка в updatePinTexts:", error);
          // Продолжаем выполнение даже при ошибке в updatePinTexts
        }
        
        console.log("🔍 [unlockSeed] Шаг 6: Очищаем currentPinInput");
        currentPinInput = [];
        // Обновляем глобальную переменную
        window.currentPinInput = currentPinInput;
        console.log("🔍 [unlockSeed] currentPinInput после очистки:", currentPinInput);
        
        console.log("🔍 [unlockSeed] Шаг 7: Возвращаемся из функции");
        return;
    }
    
    try {
      // Расшифровка с использованием AES-GCM
      logIfAvailable("🔐 Расшифровка с использованием AES-GCM");
      console.log("🔍 [unlockSeed] ДИАГНОСТИКА ПЕРЕД РАСШИФРОВКОЙ:");
      console.log("  - encrypted:", encrypted);
      console.log("  - typeof encrypted:", typeof encrypted);
      console.log("  - encrypted.length:", encrypted ? encrypted.length : 'undefined');
      console.log("  - enteredPin:", enteredPin.replace(/./g, '*'));
      console.log("  - enteredPin.length:", enteredPin.length);
      
      const phrase = await decryptWithAES(encrypted, enteredPin);
      logIfAvailable("✅ AES-GCM расшифровка успешна");

      // PIN верный, показываем сид-фразу
        console.log("✅ PIN верный, показываем сид-фразу на экране #seed-screen");
        
        const storedAddress = localStorage.getItem("wallet_address");
        currentWallet = { 
            mnemonic: phrase, 
            address: storedAddress || "" 
        };
        seedVisible = true; 

        const seedScreenMnemonicElem = document.getElementById('wallet-mnemonic');
        const seedScreenAddressElem = document.getElementById('wallet-address');
        const btnConfirmWallet = document.getElementById('btn_confirm_wallet');
        const revealSeedBtn = document.getElementById('reveal-seed-btn');
        const copySeedBtn = document.getElementById('copy-seed-btn');

        if (seedScreenMnemonicElem) {
          seedScreenMnemonicElem.value = phrase; 
        } else {
          console.error("❌ Элемент #wallet-mnemonic не найден на seed-screen!");
        }
        
        if (seedScreenAddressElem && currentWallet.address) {
          seedScreenAddressElem.textContent = currentWallet.address; 
        }

        if (btnConfirmWallet) btnConfirmWallet.style.display = 'none'; 
        if (revealSeedBtn) revealSeedBtn.style.display = 'inline-block'; 
        if (copySeedBtn) copySeedBtn.style.display = 'inline-block';   

        switchView("seed-screen"); 
        logIfAvailable("👀 Сид-фраза отображена на 20 секунд на экране #seed-screen");
        
        setTimeout(() => {
          // Проверяем, активен ли еще экран просмотра сид-фразы, чтобы избежать действий, если пользователь уже переключился
          const currentVisibleSeedScreen = document.getElementById('seed-screen');
          if (currentVisibleSeedScreen && currentVisibleSeedScreen.style.display === 'block') { 
            if (seedScreenMnemonicElem) seedScreenMnemonicElem.value = ""; 
            if (seedScreenAddressElem) seedScreenAddressElem.textContent = ""; 
            
            currentWallet = null; 
            seedVisible = false;
            
            // Восстанавливаем кнопку "Я записал(а)", если она существует, для будущих циклов
            const btnConfirmWalletForRestore = document.getElementById('btn_confirm_wallet');
            if (btnConfirmWalletForRestore) btnConfirmWalletForRestore.style.display = 'block'; 

            logIfAvailable("🙈 Сид-фраза автоматически скрыта, закрываем окно...");
            if (window.Telegram && Telegram.WebApp && typeof Telegram.WebApp.close === 'function') {
              Telegram.WebApp.close();
            } else {
              console.log("Попытка закрыть окно браузера после отображения сид-фразы. Если не сработало, закройте вкладку вручную.");
              window.close(); // Попытка закрыть вкладку браузера
            }
          } else {
            logIfAvailable("Окно просмотра сид-фразы уже неактивно, отмена автоматического закрытия.");
          }
        }, 20000);
    } catch (e) {
      console.error("❌ Ошибка при расшифровке сид-фразы для unlockSeed:", e);
        
      // Определяем тип ошибки для более точного сообщения
      if (e.message.includes("Не удалось расшифровать данные")) {
        showNotification(t("error_wrong_pin_for_view"), "error"); // "❌ Неверный PIN-код."
      } else {
        showNotification(t("error_decryption_failed_view_seed"), "error"); // "Ошибка расшифровки данных при просмотре сид-фразы."
      }
      
        currentPinInput = []; 
        // Явно обновляем точки
        const activeSetupPinScreen = document.getElementById('setup-pin-screen');
        if (activeSetupPinScreen && activeSetupPinScreen.style.display === 'block') {
            const dots = activeSetupPinScreen.querySelectorAll(".pin-dot");
            if (dots && dots.length > 0) {
                dots.forEach(dot => dot.classList.remove("filled"));
            }
        }
        updatePinTexts(t("pin_enter_to_view_seed_retry"), t("pin_enter_to_view_seed_description")); 
    }
  }

  // Сброс отображения точек
  const setupPinScreenDots = document.querySelectorAll("#setup-pin-screen .pin-dot");
  if (pinStep === "unlockSeed") {
    // Если это этап unlockSeed и PIN был неверным, точки уже очищены выше.
    // Если PIN был верным, то происходит переход на другой экран, и состояние точек на setup-pin-screen уже не важно.
    // Поэтому в этом случае дополнительно ничего не делаем с точками здесь.
    // Сравниваем строку с массивом
    const firstPinString = Array.isArray(firstPinEntry) ? firstPinEntry.join("") : firstPinEntry;
    if (enteredPin === firstPinString) { // Это условие неверно для unlockSeed, должно быть savedPin === enteredPin
        // Если PIN верный (идет переход), то можно и очистить, на всякий случай
        if (setupPinScreenDots.length > 0) {
            setupPinScreenDots.forEach(dot => dot.classList.remove("filled"));
            console.log("🔄 Точки PIN сброшены после успешного unlockSeed (на всякий случай).");
        }
    }
  } else {
    console.log("🔍 [processPinEntry] ВХОДИМ В БЛОК else - неизвестный pinStep:", pinStep);
    // Для этапов firstEntry и confirmEntry (после успешного первого ввода или после несовпадения PIN-кодов)
    if (setupPinScreenDots.length > 0) {
        setupPinScreenDots.forEach(dot => dot.classList.remove("filled"));
        console.log("🔄 Точки PIN сброшены для этапов firstEntry/confirmEntry.");
    } else {
        console.warn("⚠️ Элементы .pin-dot не найдены на экране setup-pin-screen при общем сбросе точек.");
    }
  }
  
  console.log("🔍 [processPinEntry] КОНЕЦ ФУНКЦИИ");
}

// Функция обновления заголовка
function updatePinTitle(text) {
  console.log(`🔤 Вызов updatePinTitle с текстом: "${text}"`);
  const title = document.getElementById("pin-entry-title");
  if (title) {
    title.textContent = text;
    console.log(`✅ Заголовок успешно обновлен на: "${text}"`);
  } else {
    console.warn(`⚠️ Элемент с ID "pin-entry-title" не найден (тестовая среда)`);
  }
}

// Вспомогательная функция для обновления заголовка и описания экрана PIN
function updatePinTexts(titleText, descriptionText) {
  console.log(`🔤 Вызов updatePinTexts: Заголовок="${titleText}", Описание="${descriptionText}"`);
  const titleEl = document.getElementById("pin-entry-title");
  const descriptionEl = document.getElementById("pin-setup-description");

  if (titleEl) {
    titleEl.textContent = titleText;
    console.log(`✅ Заголовок обновлен на: "${titleText}"`);
  } else {
    console.warn(`⚠️ Элемент с ID "pin-entry-title" не найден (тестовая среда)`);
  }

  if (descriptionEl) {
    descriptionEl.textContent = descriptionText;
    console.log(`✅ Описание PIN обновлено на: "${descriptionText}"`);
  } else {
    console.warn(`⚠️ Элемент с ID "pin-setup-description" не найден (тестовая среда)`);
  }
}

// === Send address to Telegram Bot ===
function sendAddressToBot() {
  logIfAvailable("📤 [SEND] Начинаем процесс отправки адреса в бот");
  try {
    if (!currentWallet || !currentWallet.address) {
      logIfAvailable("❌ [SEND] Ошибка: адрес кошелька недоступен", true);
      throw new Error("Адрес кошелька недоступен");
    }
    
    if (!window.Telegram?.WebApp) {
      logIfAvailable("❌ [SEND] Ошибка: Telegram WebApp API недоступен", true);
      throw new Error("Telegram WebApp API недоступен");
    }

    const webAppQueryId = window.Telegram.WebApp.initDataUnsafe?.query_id;
    if (!webAppQueryId) {
      logIfAvailable("ℹ️ [SEND] query_id недоступен, используем обычный sendData");
      const payload = {
          event: walletCreated && currentWallet?.restored ? "restored_access" : "created_access",
          address: currentWallet.address
      };
      logIfAvailable(`📤 [SEND] Отправляем данные: ${JSON.stringify(payload)}`);
      window.Telegram.WebApp.sendData(JSON.stringify(payload));
      logIfAvailable("✅ [SEND] Данные успешно отправлены через sendData");
      } else {
      logIfAvailable(`ℹ️ [SEND] Найден query_id: ${webAppQueryId}, используем его`);
      const payload = {
        event: walletCreated && currentWallet?.restored ? "restored_access" : "created_access",
        address: currentWallet.address,
        query_id: webAppQueryId
      };
      logIfAvailable(`📤 [SEND] Отправляем данные: ${JSON.stringify(payload)}`);
      window.Telegram.WebApp.sendData(JSON.stringify(payload));
      logIfAvailable("✅ [SEND] Данные успешно отправлены с query_id");
    }

    logIfAvailable(`📊 [DEBUG] WebApp initData: ${window.Telegram.WebApp.initData}`);
    logIfAvailable(`📊 [DEBUG] WebApp version: ${window.Telegram.WebApp.version}`);
    
    return true;
  } catch (err) {
    logIfAvailable(`❌ [SEND] Ошибка при отправке: ${err.message}`, true);
    showNotification(`Ошибка при отправке данных в бот: ${err.message}`, "error");
    return false;
  }
}

// === UI routing ===
function showRestoreScreen() {
  console.log("Переход к экрану восстановления");
  switchView('restore-screen');
}

// === Utility: view switcher ===
function switchView(viewId) {
  console.log(`🔄 Вызвана функция switchView с ID: "${viewId}"`);
  
  const all = [
    'start-screen',
    'seed-screen',
    'restore-screen',
    'loading-screen',
    'unlock-screen',
    'view-screen',
    'sign-screen',
    'seed-screen',
    'setup-pin-screen',
    'success-screen'
  ];

  console.log(`📋 Скрываем все экраны: ${all.join(', ')}`);
  all.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.style.display = 'none';
      console.log(`🙈 Скрыт экран: ${id}`);
    } else {
      console.warn(`⚠️ Элемент с ID "${id}" не найден в DOM при попытке скрыть`);
    }
  });

  // Предохранитель для режима recovery
  console.log(`🔍 Текущий режим (в switchView): ${mode || 'не установлен'}`);
  if (viewId === 'start-screen' && (mode === 'recovery' || mode === 'recovery_only')) {
    console.warn(`❌ Стартовый экран заблокирован в режиме ${mode}`);
    logIfAvailable(`❌ Стартовый экран заблокирован в режиме ${mode}`);
    // Если мы в режиме recovery/recovery_only и пытаемся показать start-screen, 
    // показываем restore-screen вместо этого, если он существует.
    const fallbackView = document.getElementById('restore-screen');
    if (fallbackView) {
        fallbackView.style.display = 'block';
        logIfAvailable(`🔁 Автоматически показан экран: restore-screen вместо start-screen в режиме ${mode}`);
    }
    return; // Важно завершить выполнение, чтобы не пытаться показать viewId, который был start-screen
  }

  const view = document.getElementById(viewId);
  if (view) {
    console.log(`👁️ Показываем экран: ${viewId}`);
    view.style.display = 'block';
    logIfAvailable(`🔁 Показан экран: ${viewId}`);
  } else {
    console.error(`❌ Элемент с ID "${viewId}" не найден в DOM при попытке показать`);
    console.warn(`[WebApp] ⚠️ Элемент view ${viewId} не найден`);
  }
}

// === Новая функция: проверка целостности данных кошелька ===
function verifyWalletDataIntegrity() {
  logIfAvailable("🔍 Проверка целостности данных кошелька");
  try {
    if (!currentWallet) {
      logIfAvailable("❌ Объект currentWallet не существует", true);
      showNotification(t('wallet_data_not_found'), "error");
      return false;
    }
    
    if (!currentWallet.address) {
      logIfAvailable("❌ Отсутствует адрес кошелька", true);
      showNotification(t('wallet_no_address'), "error");
      return false;
    }
    
    // Проверяем формат адреса (должен начинаться с 0x и иметь длину 42 символа)
    if (!currentWallet.address.startsWith('0x') || currentWallet.address.length !== 42) {
      logIfAvailable("❌ Некорректный формат адреса кошелька", true);
      showNotification(t('wallet_invalid_address'), "warning");
      return false;
    }
    
    // Если есть приватный ключ, проверяем его формат
    if (currentWallet.privateKey) {
      if (!currentWallet.privateKey.startsWith('0x') || currentWallet.privateKey.length !== 66) {
        logIfAvailable("❌ Некорректный формат приватного ключа", true);
        showNotification(t('wallet_invalid_key'), "warning");
        return false;
      }
    }
    
    // Если есть мнемоническая фраза, проверяем количество слов (должно быть 12 или 24)
    if (currentWallet.mnemonic) {
      const wordCount = currentWallet.mnemonic.trim().split(/\s+/).length;
      if (wordCount !== 12 && wordCount !== 24) {
        logIfAvailable(`❌ Некорректное количество слов в мнемонической фразе: ${wordCount}`, true);
        showNotification(t('wallet_invalid_mnemonic'), "warning");
        return false;
      }
    }
    
    logIfAvailable("✅ Данные кошелька прошли проверку целостности");
    return true;
  } catch (err) {
    logIfAvailable(`❌ Ошибка при проверке целостности данных кошелька: ${err.message}`, true);
    showNotification(t('wallet_verify_error'), "error");
    return false;
  }
}

// ===== КРИПТОГРАФИЧЕСКИЕ УТИЛИТЫ ДЛЯ БЕЗОПАСНОГО ШИФРОВАНИЯ =====

/**
 * Генерирует криптографически стойкую соль для PBKDF2
 * @returns {Uint8Array} Массив из 16 байт случайных данных
 */
function generateSalt() {
  try {
    logIfAvailable("🔐 Генерация криптографически стойкой соли");
    
    // Генерируем 16 байт (128 бит) криптографически стойкой соли
    const salt = new Uint8Array(16);
    crypto.getRandomValues(salt);
    
    logIfAvailable(`✅ Соль успешно сгенерирована (${salt.length} байт)`);
    return salt;
  } catch (err) {
    logIfAvailable(`❌ Ошибка при генерации соли: ${err.message}`, true);
    throw new Error(`Не удалось сгенерировать соль: ${err.message}`);
  }
}

/**
 * Генерирует случайный вектор инициализации (IV) для AES-GCM
 * @returns {Uint8Array} Массив из 12 байт случайных данных
 */
function generateIV() {
  try {
    logIfAvailable("🔐 Генерация вектора инициализации (IV)");
    
    // Генерируем 12 байт (96 бит) для AES-GCM IV
    const iv = new Uint8Array(12);
    crypto.getRandomValues(iv);
    
    logIfAvailable(`✅ IV успешно сгенерирован (${iv.length} байт)`);
    return iv;
  } catch (err) {
    logIfAvailable(`❌ Ошибка при генерации IV: ${err.message}`, true);
    throw new Error(`Не удалось сгенерировать IV: ${err.message}`);
  }
}

/**
 * Шифрует данные с использованием AES-GCM и PBKDF2
 * @param {string} data - Данные для шифрования
 * @param {string} password - Пароль (PIN) для деривации ключа
 * @returns {Promise<string>} Base64 строка с версионированием: "v2::salt::iv::encryptedData"
 */
async function encryptWithAES(data, password) {
  try {
    logIfAvailable("🔐 Начало AES-GCM шифрования");
    
    // Генерируем соль и IV
    const salt = generateSalt();
    const iv = generateIV();
    
    logIfAvailable("🔑 Деривация ключа через PBKDF2");
    
    // Импортируем пароль как ключ для PBKDF2
    const passwordKey = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(password),
      'PBKDF2',
      false,
      ['deriveBits', 'deriveKey']
    );
    
    // Деривируем ключ через PBKDF2 (100,000 итераций для безопасности)
    const key = await crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: salt,
        iterations: 100000,
        hash: 'SHA-256'
      },
      passwordKey,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt']
    );
    
    logIfAvailable("🔒 Шифрование данных через AES-GCM");
    
    // Шифруем данные
    const encryptedData = await crypto.subtle.encrypt(
      {
        name: 'AES-GCM',
        iv: iv
      },
      key,
      new TextEncoder().encode(data)
    );
    
    // Формируем результат: версия::соль::IV::зашифрованные_данные
    const result = [
      'v2',
      btoa(String.fromCharCode(...salt)),
      btoa(String.fromCharCode(...iv)),
      btoa(String.fromCharCode(...new Uint8Array(encryptedData)))
    ].join('::');
    
    logIfAvailable(`✅ AES-GCM шифрование завершено (${result.length} символов)`);
    return result;
    
  } catch (err) {
    logIfAvailable(`❌ Ошибка при AES-GCM шифровании: ${err.message}`, true);
    throw new Error(`Не удалось зашифровать данные: ${err.message}`);
  }
}

/**
 * Расшифровывает данные, зашифрованные с помощью encryptWithAES
 * @param {string} encryptedData - Base64 строка в формате "v2::salt::iv::encryptedData"
 * @param {string} password - Пароль (PIN) для деривации ключа
 * @returns {Promise<string>} Расшифрованные данные
 */
async function decryptWithAES(encryptedData, password) {
  try {
    logIfAvailable("🔐 Начало AES-GCM расшифровки");
    
    // Парсим формат: версия::соль::IV::зашифрованные_данные
    const parts = encryptedData.split('::');
    if (parts.length !== 4 || parts[0] !== 'v2') {
      throw new Error('Неверный формат зашифрованных данных');
    }
    
    const [, saltB64, ivB64, dataB64] = parts;
    
    // Декодируем Base64 компоненты
    const salt = new Uint8Array(atob(saltB64).split('').map(c => c.charCodeAt(0)));
    const iv = new Uint8Array(atob(ivB64).split('').map(c => c.charCodeAt(0)));
    const encrypted = new Uint8Array(atob(dataB64).split('').map(c => c.charCodeAt(0)));
    
    logIfAvailable("🔑 Деривация ключа через PBKDF2");
    
    // Импортируем пароль как ключ для PBKDF2
    const passwordKey = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(password),
      'PBKDF2',
      false,
      ['deriveBits', 'deriveKey']
    );
    
    // Деривируем ключ через PBKDF2 (те же параметры, что при шифровании)
    const key = await crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: salt,
        iterations: 100000,
        hash: 'SHA-256'
      },
      passwordKey,
      { name: 'AES-GCM', length: 256 },
      false,
      ['decrypt']
    );
    
    logIfAvailable("🔓 Расшифровка данных через AES-GCM");
    
    // Расшифровываем данные
    const decryptedData = await crypto.subtle.decrypt(
      {
        name: 'AES-GCM',
        iv: iv
      },
      key,
      encrypted
    );
    
    // Преобразуем в строку
    const result = new TextDecoder().decode(decryptedData);
    
    logIfAvailable(`✅ AES-GCM расшифровка завершена (${result.length} символов)`);
    return result;
    
  } catch (err) {
    logIfAvailable(`❌ Ошибка при AES-GCM расшифровке: ${err.message}`, true);
    throw new Error(`Не удалось расшифровать данные: ${err.message}`);
  }
}

/**
 * Определяет версию шифрования зашифрованных данных
 * @param {string} encryptedData - Зашифрованные данные
 * @returns {string|null} Версия шифрования ('v1', 'v2') или null если неопределена
 */
function getEncryptionVersion(encryptedData) {
  try {
    if (!encryptedData || typeof encryptedData !== 'string') {
      return null;
    }
    
    // Проверяем формат v2: "v2::salt::iv::encryptedData"
    if (encryptedData.startsWith('v2::')) {
      const parts = encryptedData.split('::');
      if (parts.length === 4) {
        logIfAvailable("🔍 Обнаружена версия шифрования: v2 (AES-GCM)");
        return 'v2';
      }
    }
    
    // Проверяем формат v1: Base64 строка без версионирования
    // Пытаемся декодировать как Base64 и проверить наличие "::"
    try {
      const decoded = atob(encryptedData);
      if (decoded.includes('::')) {
        logIfAvailable("🔍 Обнаружена версия шифрования: v1 (Base64)");
        return 'v1';
      }
    } catch (e) {
      // Не Base64 или не содержит "::"
    }
    
    logIfAvailable("⚠️ Неопределенная версия шифрования", true);
    return null;
    
  } catch (err) {
    logIfAvailable(`❌ Ошибка при определении версии шифрования: ${err.message}`, true);
    return null;
  }
}

// Добавляем функции для безопасного хранения (УСТАРЕВШИЕ - НЕ ИСПОЛЬЗОВАТЬ)
function encryptData(data, password) {
  try {
    // Простое шифрование для MVP - не используйте в production без улучшения
    const dataString = JSON.stringify(data);
    // XOR шифрование с паролем для базовой защиты
    let encrypted = '';
    for (let i = 0; i < dataString.length; i++) {
      encrypted += String.fromCharCode(dataString.charCodeAt(i) ^ password.charCodeAt(i % password.length));
    }
    return btoa(encrypted); // Base64 для безопасного хранения
  } catch (err) {
    logIfAvailable(`❌ Ошибка при шифровании данных: ${err.message}`, true);
    return null;
  }
}

function decryptData(encryptedData, password) {
  try {
    // Расшифровка данных
    const encryptedString = atob(encryptedData); // Из Base64
    let decrypted = '';
    for (let i = 0; i < encryptedString.length; i++) {
      decrypted += String.fromCharCode(encryptedString.charCodeAt(i) ^ password.charCodeAt(i % password.length));
    }
    return JSON.parse(decrypted);
  } catch (err) {
    logIfAvailable(`❌ Ошибка при расшифровке данных: ${err.message}`, true);
    return null;
  }
}

// Функция загрузки локализации
async function loadLocalization(language = 'ru') {
  try {
    const response = await fetch(`localization/${language}.json`);
    if (!response.ok) throw new Error(`Не удалось загрузить локализацию: ${response.status}`);
    localization = await response.json();
    currentLanguage = language;
    console.log(`✅ Локализация загружена: ${language}`);
    return true;
  } catch (error) {
    console.error(`❌ Ошибка при загрузке локализации: ${error.message}`);
    return false;
  }
}

// === Функция для загрузки изображений ===
function loadImages() {
  const images = [
    'amanita_key_1.png',
    'amanita_key_2.png',
    'amanita_key_3.png',
    'amanita_key_4.png',
    'amanita_key_5.png',
    'amanita_key_6.png',
    'amanita_key_7.png',
    'amanita_key_8.png',
    'amanita_key_9.png',
    'amanita_key_0.png',
    'amanita_key_back.png',
    'star.png'
  ];

  images.forEach(image => {
    const img = new Image();
    img.src = `assets/${image}`;
    img.onload = () => logIfAvailable(`✅ Загружено изображение: ${image}`);
    img.onerror = () => logIfAvailable(`❌ Ошибка загрузки изображения: ${image}`, true);
  });
}

// Функция получения локализованной строки (аналог loc.t из бота)
function t(key, ...params) {
  // Получаем строку из объекта локализации
  const text = localization[key] || key;
  
  // Если параметры не переданы, возвращаем строку как есть
  if (!params || params.length === 0) return text;
  
  // Заменяем {0}, {1}, {2}... на соответствующие параметры
  return text.replace(/\{(\d+)\}/g, (match, index) => {
    const paramIndex = parseInt(index);
    return params[paramIndex] !== undefined ? params[paramIndex] : match;
  });
}

// Функция для обновления placeholder в текстовых полях
function updatePlaceholders() {
  // Обновляем placeholder для полей ввода с атрибутом data-l10n-placeholder
  document.querySelectorAll('[data-l10n-placeholder]').forEach(element => {
    const key = element.getAttribute('data-l10n-placeholder');
    if (key) {
      element.placeholder = t(key);
    }
  });
  
  // Дополнительные обновления placeholder для обратной совместимости
  const signPinInput = document.getElementById('sign-pin-input');
  if (signPinInput && !signPinInput.hasAttribute('data-l10n-placeholder')) {
    signPinInput.placeholder = t('sign_pin_placeholder');
  }
  
  // Убрали unlockPinInput, т.к. экран unlock-screen был удален/заменен на setup-pin-screen для просмотра сида
}

// Обновляем функцию updateUIWithLocalization, чтобы вызывать все обновления
function updateUIWithLocalization() {
  // Находим все элементы с атрибутом data-l10n
  document.querySelectorAll('[data-l10n]').forEach(element => {
    const key = element.getAttribute('data-l10n');
    if (key) {
      // Для обычных элементов просто меняем textContent
      // Для кнопок логика сложнее из-за иконок и обрабатывается в updateButtonTexts
      if (element.tagName !== 'BUTTON' && !element.classList.contains('shaman-button') && !element.classList.contains('button-secondary')) {
         // Проверяем, что это не input и не textarea, чтобы не затереть placeholder
        if (element.tagName !== 'INPUT' && element.tagName !== 'TEXTAREA') {
            element.textContent = t(key);
        }
      }
    }
  });
  
  // Обновляем тексты в кнопках
  updateButtonTexts();
  
  // Обновляем placeholder в полях ввода
  updatePlaceholders();

  // После обновления локализации, если текущий экран - это экран установки PIN,
  // нужно обновить тексты заголовка и описания в соответствии с текущим шагом (pinStep)
  const setupPinScreen = document.getElementById('setup-pin-screen');
  if (setupPinScreen && setupPinScreen.style.display === 'block') {
    if (pinStep === 'firstEntry') {
      updatePinTexts(t('setup_pin_title'), t('setup_pin_description'));
    } else if (pinStep === 'confirmEntry') {
      updatePinTexts(t('pin_confirm_title'), t('setup_pin_description')); // Описание остается "придумайте", но заголовок "повторите"
    } else if (pinStep === 'unlockSeed') {
      // Если была ошибка и в заголовке "попробуйте снова"
      const currentTitle = document.getElementById('pin-entry-title').textContent;
      if (currentTitle === t('pin_enter_to_view_seed_retry')) {
         updatePinTexts(t('pin_enter_to_view_seed_retry'), t('pin_enter_to_view_seed_description'));
      } else {
         updatePinTexts(t('pin_enter_to_view_seed'), t('pin_enter_to_view_seed_description'));
      }
    }
  }
}

function updateButtonTexts() {
  // Обновляем тексты в кнопках с сохранением иконок
  const buttonUpdates = [
    { id: 'create-btn', key: 'btn_create_wallet', icon: '🆕' },
    { id: 'restore-btn', key: 'btn_restore_wallet', icon: '🔄' },
    { id: 'reveal-seed-btn', key: 'btn_reveal_seed', icon: '👁️' },
    { id: 'copy-seed-btn', key: 'btn_copy_seed', icon: '📋' },
    { id: 'btn_confirm_wallet', key: 'btn_confirm_wallet', icon: '✅' },
    { id: 'restore-confirm-btn', key: 'btn_restore_wallet', icon: '✅' }, // Использует тот же ключ, что и restore-btn
    { id: 'back-to-start-btn', key: 'btn_back', icon: '⬅️' },
    // { id: 'clear-wallet-btn', key: 'btn_delete_wallet', icon: '🗑️' }, // такой кнопки нет в HTML сейчас
    { id: 'setup-pin-submit-btn', key: 'setup_pin_submit_btn', icon: '🔐'},
    { id: 'sign-submit-btn', key: 'btn_sign_submit', icon: '✍️' },
    // { id: 'unlock-submit-btn', key: 'unlock_btn', icon: '🔓' }, // такой кнопки нет в HTML сейчас
    // { id: 'change-lang-btn', key: 'btn_change_lang', icon: '🌐' }, // такой кнопки нет в HTML сейчас
    { id: 'finish-btn', key: 'success_btn', icon: '✅' }
  ];

  buttonUpdates.forEach(update => {
    const button = document.getElementById(update.id);
    if (!button) return;
    
    let iconSpan = button.querySelector('.icon');
    if (!iconSpan && update.icon) { // Добавляем иконку только если она указана
      iconSpan = document.createElement('span');
      iconSpan.className = 'icon';
      button.prepend(iconSpan); // Вставляем иконку в начало кнопки
    }
    
    if (iconSpan && update.icon) {
      iconSpan.textContent = update.icon + ' '; // Добавляем пробел после иконки
    } else if (iconSpan && !update.icon) { // Если иконка не нужна, но span есть, удаляем его
        iconSpan.remove();
    }
    
    // Удаляем старые текстовые узлы, которые не являются элементом .icon
    Array.from(button.childNodes).forEach(node => {
        if (node.nodeType === Node.TEXT_NODE || (node.nodeType === Node.ELEMENT_NODE && !node.classList.contains('icon'))) {
            button.removeChild(node);
        }
    });
    
    // Добавляем новый текст после иконки (если она есть) или просто текст
    const textNode = document.createTextNode(t(update.key));
    if (iconSpan && update.icon) { // Если есть иконка, добавляем текст после нее
        button.appendChild(textNode);
    } else { // Если иконки нет, добавляем текст в начало (или после удаленной иконки)
        button.prepend(textNode);
    }
  });
}

async function changeLanguage(language) {
  if (await loadLocalization(language)) {
    updateUIWithLocalization();
    // Сохраняем выбранный язык, чтобы использовать его при следующей загрузке
    localStorage.setItem('preferredLanguage', language);
    return true;
  }
  return false;
}

// Использование (например, при клике на кнопку смены языка, если она будет добавлена)
// document.getElementById('change-lang-btn').addEventListener('click', () => {
//   const newLang = currentLanguage === 'ru' ? 'en' : 'ru';
//   changeLanguage(newLang);
// });

// Обработчик для кнопки Завершить/Перейти в каталог
const finishBtn = document.getElementById('finish-btn');
if (finishBtn) {
    finishBtn.addEventListener('click', async () => {
      try {
        logIfAvailable("🔄 [FINISH] Нажата кнопка 'Перейти в каталог'");
        
        // Проверяем состояние Telegram WebApp
        const webAppState = {
          available: !!window.Telegram?.WebApp,
          version: window.Telegram?.WebApp?.version,
          initDataUnsafe: window.Telegram?.WebApp?.initDataUnsafe,
          hasMainButton: !!window.Telegram?.WebApp?.MainButton,
          hasSendData: typeof window.Telegram?.WebApp?.sendData === 'function'
        };
        logIfAvailable(`📊 [FINISH] Состояние WebApp: ${JSON.stringify(webAppState)}`);

        // Отправляем данные в бот только если они еще не были отправлены
        if (walletCreated && !window.dataWasSent) {
          logIfAvailable("📤 [FINISH] Отправляем данные в бот (они еще не были отправлены)");
          const sent = sendAddressToBot();
          if (sent) {
            window.dataWasSent = true;
            logIfAvailable("✅ [FINISH] Данные успешно отправлены");
      } else {
            logIfAvailable("❌ [FINISH] Не удалось отправить данные", true);
            throw new Error("Не удалось отправить адрес в бот");
          }
        } else {
          logIfAvailable(`ℹ️ [FINISH] Пропускаем отправку данных: walletCreated=${walletCreated}, dataWasSent=${window.dataWasSent}`);
        }

        // Небольшая пауза
        logIfAvailable("⏳ [FINISH] Ждем 300мс");
        await new Promise(resolve => setTimeout(resolve, 300));
        
        // ВРЕМЕННО ОТКЛЮЧЕНО: Закрытие окна отключено для отладки
        // TODO: ВОССТАНОВИТЬ ПЕРЕД РЕЛИЗОМ - раскомментировать нужный блок кода:
        /*
        if (window.Telegram?.WebApp?.close) {
          window.Telegram.WebApp.close();
        } else {
          window.close();
        }
        */
        logIfAvailable("🚫 [FINISH] Закрытие окна временно отключено для отладки");
        showNotification("Закрытие окна отключено для отладки", "info");
        logIfAvailable("✅ [FINISH] Процесс завершения успешно выполнен");
      } catch (err) {
        logIfAvailable(`❌ [FINISH] Ошибка при завершении: ${err.message}`, true);
        showNotification("Ошибка при отправке данных. Попробуйте еще раз.", "error");
      }
    });
}

// Экспорт функций для тестирования
if (typeof window !== 'undefined') {
    console.log('🔧 Экспортируем функции для тестирования...');
    window.processPinEntry = processPinEntry;
    window.saveWalletWithPin = saveWalletWithPin;
    window.generateSalt = generateSalt;
    window.generateIV = generateIV;
    window.encryptWithAES = encryptWithAES;
    window.decryptWithAES = decryptWithAES;
    console.log('✅ Функции экспортированы в window для тестирования');
}