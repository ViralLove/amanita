/**
 * Демонстрация воспроизведения реальной ошибки "Transaction verification failed"
 * Этот файл показывает, как воспроизвести ошибку, которую мы видим в Python тестах
 */

import { getPrivateKey, uploadText } from "./utils.ts";

// Мок ArWeave клиента, который возвращает реальную ошибку
const mockArweaveWithRealError = {
  init: () => mockArweaveWithRealError,
  createTransaction: async () => ({
    id: "ar_test_transaction_id_12345",
    addTag: () => {},
    get: () => "test_data"
  }),
  transactions: {
    sign: async () => {},
    post: async () => ({ 
      status: 400, 
      statusText: "Transaction verification failed." 
    })
  }
};

// Демонстрация воспроизведения ошибки
async function demonstrateRealError() {
  try {
    console.log("🔍 Демонстрация воспроизведения реальной ошибки...");
    
    // Используем точно такие же данные, как в Python тесте
    const testData = JSON.stringify({
      test: "data",
      number: 42,
      boolean: true,
      array: [1, 2, 3],
      object: { nested: "value" }
    });
    
    // Получаем реальный приватный ключ
    const realPrivateKey = getPrivateKey();
    
    console.log("📝 Тестовые данные:", testData.substring(0, 100) + "...");
    console.log("🔑 Приватный ключ получен:", realPrivateKey.kty === "RSA");
    
    // Пытаемся загрузить данные (это вызовет ошибку)
    const transactionId = await uploadText(
      testData, 
      "application/json", 
      realPrivateKey, 
      mockArweaveWithRealError
    );
    
    console.log("✅ Успешная загрузка:", transactionId);
    
  } catch (error) {
    console.log("❌ ОШИБКА ВОСПРОИЗВЕДЕНА:");
    console.log("   Сообщение:", error.message);
    console.log("   Тип ошибки:", error.constructor.name);
    
    // Проверяем, что это именно та ошибка, которую мы видим в Python тестах
    if (error.message.includes("Transaction verification failed")) {
      console.log("✅ Ошибка 'Transaction verification failed' успешно воспроизведена!");
    } else {
      console.log("❌ Неожиданная ошибка:", error.message);
    }
  }
}

// Запускаем демонстрацию
if (import.meta.main) {
  await demonstrateRealError();
}

export { demonstrateRealError }; 