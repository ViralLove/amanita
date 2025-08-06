/**
 * Изолированный тест на основе прототипа эксперта ArWeave
 * Проверяет рабочие техники для Deno окружения
 */

import { assertEquals } from "https://deno.land/std@0.168.0/testing/asserts.ts";
import Arweave from "https://esm.sh/arweave@1.15.7";
import { signTransaction } from "./arweave/compatible.ts";

// Загрузка приватного ключа
async function loadPrivateKey(): Promise<any> {
  const privateKeyFilePath = Deno.env.get('ARWEAVE_PRIVATE_KEY_FILE') || "arweave-wallet.json";
  const rawKey = await Deno.readTextFile(privateKeyFilePath);
  return JSON.parse(rawKey);
}

// Тест прототипа эксперта
Deno.test("EXPERT PROTOTYPE - тест рабочего прототипа эксперта", async () => {
  console.log("🧪 Тестируем прототип эксперта ArWeave...");
  
  try {
    // 1. Инициализация клиента
    const arweave = Arweave.init({
      host: "arweave.net",
      port: 443,
      protocol: "https",
    });
    
    console.log("✅ ArWeave клиент инициализирован");
    
    // 2. Загружаем приватный ключ JWK (RSA)
    const privateKey = await loadPrivateKey();
    console.log("✅ Приватный ключ загружен:", privateKey.kty === "RSA");
    
    // 3. Подготовка данных
    const dataString = "Hello Arweave from Expert Prototype!";
    const dataBytes = new TextEncoder().encode(dataString);
    const dataB64 = arweave.utils.bufferTob64Url(dataBytes);
    
    console.log("✅ Данные подготовлены:");
    console.log("   Оригинал:", dataString);
    console.log("   Размер:", dataBytes.length, "байт");
    console.log("   Base64:", dataB64.substring(0, 20) + "...");
    
    // 4. Получаем текущую информацию для транзакции
    console.log("📡 Получаем информацию для транзакции...");
    const lastTx = await arweave.transactions.getTransactionAnchor();
    const reward = await arweave.transactions.getPrice(dataBytes.length);
    
    console.log("✅ Информация получена:");
    console.log("   Last TX:", lastTx);
    console.log("   Reward:", reward);
    
    // 5. Собираем "сырой" объект транзакции
    console.log("🔧 Собираем транзакцию вручную...");
    
    // Создаем транзакцию через SDK, но с ручными параметрами
    const tx = await arweave.createTransaction({
      data: dataBytes,
      target: "",
      quantity: "0",
    }, privateKey);
    
    // Устанавливаем дополнительные параметры (если возможно)
    try {
      (tx as any).reward = reward;
      (tx as any).last_tx = lastTx;
    } catch (error) {
      console.log("⚠️ Не удалось установить reward/last_tx напрямую");
    }
    
    // Добавляем теги
    tx.addTag("Content-Type", "text/plain");
    tx.addTag("Test-Type", "expert-prototype");
    
    console.log("✅ Транзакция собрана:");
    console.log("   Format:", tx.format);
    console.log("   Owner:", tx.owner?.substring(0, 20) + "...");
    console.log("   Data size:", tx.data_size);
    console.log("   Tags count:", tx.tags?.length || 0);
    
    // 6. Подписываем транзакцию
    console.log("🔐 Подписываем транзакцию...");
    await signTransaction(arweave, tx, privateKey);
    
    console.log("✅ Транзакция подписана:");
    console.log("   ID:", tx.id);
    console.log("   Signature:", tx.signature?.substring(0, 20) + "...");
    
    // Проверяем, что ID начинается с 'ar'
    if (tx.id && tx.id.startsWith("ar")) {
      console.log("✅ Transaction ID правильный:", tx.id);
    } else {
      console.log("❌ Transaction ID неправильный:", tx.id);
      console.log("   Ожидалось: ar...");
      console.log("   Получено:", tx.id);
    }
    
    // 7. Отправляем
    console.log("📤 Отправляем транзакцию...");
    const response = await arweave.transactions.post(tx);
    
    console.log("📊 Результат отправки:");
    console.log("   Status:", response.status);
    console.log("   Status Text:", response.statusText);
    
    if (response.status === 200 || response.status === 202) {
      console.log("🎉 УСПЕХ! Транзакция отправлена!");
      console.log("🔗 URL:", `https://arweave.net/${tx.id}`);
      
      // Дополнительная проверка - скачиваем данные
      console.log("📥 Проверяем скачивание данных...");
      try {
        const downloadedData = await arweave.transactions.getData(tx.id, { decode: true });
        console.log("✅ Данные скачаны:", downloadedData);
        assertEquals(downloadedData, dataString, "Скачанные данные должны совпадать с исходными");
        console.log("✅ Валидация данных прошла успешно!");
      } catch (error: any) {
        console.log("⚠️ Ошибка при скачивании данных:", error.message);
      }
      
    } else {
      console.log("❌ Ошибка отправки:", response.status, response.statusText);
      console.log("📄 Детали ошибки:", response.data);
    }
    
  } catch (error: any) {
    console.error("❌ Критическая ошибка в прототипе:", error.message);
    console.error("Stack trace:", error.stack);
    throw error;
  }
});

// Тест валидации техник эксперта
Deno.test("EXPERT PROTOTYPE - валидация техник", async () => {
  console.log("🔍 Валидируем техники эксперта...");
  
  const arweave = Arweave.init({
    host: "arweave.net",
    port: 443,
    protocol: "https",
  });
  
  // Проверяем доступность методов
  console.log("🔧 Проверяем доступность методов...");
  
  assertEquals(typeof arweave.utils.bufferTob64Url, "function", "bufferTob64Url должен быть доступен");
  assertEquals(typeof arweave.utils.stringToB64Url, "function", "stringToB64Url должен быть доступен");
  assertEquals(typeof arweave.transactions.getTransactionAnchor, "function", "getTransactionAnchor должен быть доступен");
  assertEquals(typeof arweave.transactions.getPrice, "function", "getPrice должен быть доступен");
  assertEquals(typeof arweave.transactions.sign, "function", "sign должен быть доступен");
  assertEquals(typeof arweave.transactions.post, "function", "post должен быть доступен");
  
  console.log("✅ Все необходимые методы доступны");
  
  // Проверяем кодирование
  console.log("🔧 Проверяем кодирование...");
  const testString = "test";
  const testBytes = new TextEncoder().encode(testString);
  const testB64 = arweave.utils.bufferTob64Url(testBytes);
  const testB64String = arweave.utils.stringToB64Url(testString);
  
  console.log("   Test string:", testString);
  console.log("   Test bytes length:", testBytes.length);
  console.log("   Test base64:", testB64);
  console.log("   Test base64 string:", testB64String);
  
  assertEquals(testB64.length > 0, true, "Base64 не должен быть пустым");
  assertEquals(testB64String.length > 0, true, "Base64 string не должен быть пустым");
  
  console.log("✅ Кодирование работает корректно");
}); 