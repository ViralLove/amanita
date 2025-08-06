/**
 * Тест с использованием arweave-deno библиотеки
 * Проверяем альтернативную реализацию для Deno
 */

import { assertEquals } from "https://deno.land/std@0.168.0/testing/asserts.ts";

// Загрузка приватного ключа
async function loadPrivateKey(): Promise<any> {
  const privateKeyFilePath = Deno.env.get('ARWEAVE_PRIVATE_KEY_FILE') || "arweave-wallet.json";
  const rawKey = await Deno.readTextFile(privateKeyFilePath);
  return JSON.parse(rawKey);
}

// Тест с arweave-deno
Deno.test("ARWEAVE-DENO - тест альтернативной библиотеки", async () => {
  console.log("🧪 Тестируем arweave-deno библиотеку...");
  
  try {
    // Пробуем импортировать arweave-deno
    console.log("📦 Импортируем arweave-deno...");
    
    // Попробуем разные варианты импорта
    let Arweave: any;
    try {
      Arweave = await import("https://deno.land/x/arweave@1.14.0/mod.ts");
      console.log("✅ arweave-deno импортирован успешно");
    } catch (error) {
      console.log("❌ arweave-deno не найден, пробуем альтернативы...");
      
      try {
        Arweave = await import("https://esm.sh/arweave-deno@latest");
        console.log("✅ arweave-deno через esm.sh импортирован");
      } catch (error2) {
        console.log("❌ arweave-deno недоступен");
        console.log("🔍 Проверим доступные версии...");
        
        // Проверим доступные версии
        const response = await fetch("https://deno.land/x/arweave");
        if (response.ok) {
          const text = await response.text();
          console.log("📋 Доступные версии arweave:", text.substring(0, 200));
        }
        
        throw new Error("arweave-deno библиотека недоступна");
      }
    }
    
    // Инициализация клиента
    const arweave = Arweave.default.init({
      host: "arweave.net",
      port: 443,
      protocol: "https",
    });
    
    console.log("✅ Arweave клиент инициализирован");
    
    // Загружаем приватный ключ
    const privateKey = await loadPrivateKey();
    console.log("✅ Приватный ключ загружен:", privateKey.kty === "RSA");
    
    // Подготовка данных
    const dataString = "Hello Arweave from Deno!";
    const dataBytes = new TextEncoder().encode(dataString);
    
    console.log("✅ Данные подготовлены:", dataString);
    
    // Создаем транзакцию
    const transaction = await arweave.createTransaction({
      data: dataBytes
    }, privateKey);
    
    transaction.addTag("Content-Type", "text/plain");
    transaction.addTag("Test-Type", "arweave-deno");
    
    console.log("✅ Транзакция создана");
    console.log("   Owner:", transaction.owner?.substring(0, 20) + "...");
    console.log("   Data size:", transaction.data_size);
    
    // Подписываем
    await arweave.transactions.sign(transaction, privateKey);
    
    console.log("✅ Транзакция подписана");
    console.log("   ID:", transaction.id);
    console.log("   Signature:", transaction.signature?.substring(0, 20) + "...");
    
    // Проверяем ID
    if (transaction.id && transaction.id.startsWith("ar")) {
      console.log("🎉 Transaction ID правильный:", transaction.id);
      
      // Отправляем
      const response = await arweave.transactions.post(transaction);
      console.log("📊 Статус отправки:", response.status);
      
      if (response.status === 200 || response.status === 202) {
        console.log("🎉 УСПЕХ! Транзакция отправлена!");
        console.log("🔗 URL:", `https://arweave.net/${transaction.id}`);
      } else {
        console.log("❌ Ошибка отправки:", response.status, response.statusText);
      }
    } else {
      console.log("❌ Transaction ID неправильный:", transaction.id);
    }
    
  } catch (error: any) {
    console.error("❌ Ошибка в arweave-deno тесте:", error.message);
    console.error("Stack trace:", error.stack);
    throw error;
  }
}); 