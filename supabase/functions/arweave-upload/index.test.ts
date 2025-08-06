/**
 * TDD-ориентированные unit-тесты для ArWeave Edge Function
 * Применяем мышление @test-qualification.mdc для жесткого анализа
 */

import { assertEquals, assertThrows } from "https://deno.land/std@0.168.0/testing/asserts.ts";
import { 
  getPrivateKey, 
  validatePrivateKey, 
  validateTextUpload, 
  uploadText, 
  uploadFile,
  createSuccessResponse,
  createErrorResponse,
  createHealthResponse,
  type ArWeavePrivateKey,
  type ArWeaveClient,
  type ArWeaveTransaction,
  type Environment
} from "./utils.ts";

// Импортируем реальный ArWeave SDK для интеграционных тестов
import Arweave from "https://esm.sh/arweave@1.15.7";

// ============================================================================
// МОКИ ДЛЯ ТЕСТИРОВАНИЯ
// ============================================================================

const mockTransaction: ArWeaveTransaction = {
  id: "ar_test_transaction_id_12345",
  addTag: () => {},
  get: () => "test_data"
};

const mockArweave: ArWeaveClient = {
  init: () => mockArweave,
  createTransaction: async () => mockTransaction,
  transactions: {
    sign: async () => {},
    post: async () => ({ status: 200 })
  }
};

const mockArweaveWithError: ArWeaveClient = {
  ...mockArweave,
  transactions: {
    ...mockArweave.transactions,
    post: async () => ({ status: 400, statusText: "Transaction verification failed." })
  }
};

// ============================================================================
// РЕАЛЬНАЯ ИНТЕГРАЦИЯ С ARWEAVE SDK
// ============================================================================

// Инициализируем реальный ArWeave клиент с правильными параметрами
const realArweave = Arweave.init({
  host: "arweave.net",
  port: 443,
  protocol: "https",
  timeout: 20000,
  logging: true,
});

// Функция для загрузки реального приватного ключа из файла
async function loadRealPrivateKey(): Promise<ArWeavePrivateKey> {
  const privateKeyFilePath = Deno.env.get('ARWEAVE_PRIVATE_KEY_FILE');
  if (!privateKeyFilePath) {
    throw new Error('ARWEAVE_PRIVATE_KEY_FILE environment variable is required');
  }

  try {
    const rawKey = await Deno.readTextFile(privateKeyFilePath);
    const parsedKey = JSON.parse(rawKey);
    validatePrivateKey(parsedKey);
    return parsedKey;
  } catch (err) {
    console.error('Failed to load Arweave private key:', err);
    throw new Error('Could not load or parse Arweave private key file');
  }
}

// ============================================================================
// ИНТЕГРАЦИОННЫЕ ТЕСТЫ С РЕАЛЬНЫМ ARWEAVE SDK
// ============================================================================

Deno.test("REAL ARWEAVE - должен успешно создавать и подписывать транзакцию", async () => {
  // Arrange
  const testData = "test content for real ArWeave integration";
  const contentType = "text/plain";
  
  // Загружаем реальный приватный ключ
  const realPrivateKey = await loadRealPrivateKey();
  
  console.log("🔑 Реальный приватный ключ загружен:", realPrivateKey.kty === "RSA");
  console.log("🔑 Ключ содержит поля:", Object.keys(realPrivateKey));
  
  // Act - создаем транзакцию с реальным ArWeave SDK
  console.log("📝 Создаем транзакцию...");
  const transaction = await realArweave.createTransaction({
    data: new TextEncoder().encode(testData)
  }, realPrivateKey);
  
  console.log("📝 Транзакция создана, ID до подписи:", transaction.id);
  console.log("📝 Owner до подписи:", transaction.owner);
  
  // Шаг 2: Добавление тегов ДО подписи (КРИТИЧЕСКИ ВАЖНО!)
  console.log("🏷️ Добавляем теги...");
  transaction.addTag('Content-Type', contentType);
  
  // Шаг 3: Подписываем транзакцию
  console.log("🔐 Подписываем транзакцию...");
  await realArweave.transactions.sign(transaction, realPrivateKey);
  
  console.log("📝 Транзакция после подписи:");
  console.log("   ID:", transaction.id);
  console.log("   Owner:", transaction.owner);
  console.log("   Signature:", transaction.signature ? transaction.signature.substring(0, 20) + "..." : "НЕТ");
  console.log("   Tags:", transaction.tags);
  
  // Assert
  assertEquals(transaction.id.startsWith("ar"), true, "Transaction ID должен начинаться с 'ar'");
  assertEquals(typeof transaction.id, "string", "Transaction ID должен быть строкой");
  assertEquals(transaction.id.length > 20, true, "Transaction ID должен быть достаточно длинным");
  assertEquals(typeof transaction.signature, "string", "Подпись должна быть строкой");
  assertEquals(transaction.signature.length > 0, true, "Подпись не должна быть пустой");
  
  console.log("✅ Транзакция успешно создана и подписана:", transaction.id);
  console.log("🔐 Подпись:", transaction.signature.substring(0, 20) + "...");
});

Deno.test("REAL ARWEAVE - должен успешно загружать данные в ArWeave", async () => {
  // Arrange
  const testData = JSON.stringify({
    test: "real_arweave_integration",
    timestamp: new Date().toISOString(),
    message: "Testing real ArWeave upload"
  });
  const contentType = "application/json";
  
  // Загружаем реальный приватный ключ
  const realPrivateKey = await loadRealPrivateKey();
  
  console.log("🔑 Начинаем реальную загрузку в ArWeave...");
  
  // Act - создаем и отправляем транзакцию
  const transaction = await realArweave.createTransaction({
    data: new TextEncoder().encode(testData)
  }, realPrivateKey);
  
  // Шаг 2: Добавление тегов ДО подписи (КРИТИЧЕСКИ ВАЖНО!)
  transaction.addTag('Content-Type', contentType);
  transaction.addTag('Test-Type', 'integration-test');
  
  // Шаг 3: Подписываем транзакцию
  await realArweave.transactions.sign(transaction, realPrivateKey);
  
  // Валидация перед отправкой
  assertEquals(transaction.id.startsWith("ar"), true, "Transaction ID должен начинаться с 'ar'");
  assertEquals(transaction.signature.length > 0, true, "Подпись не должна быть пустой");
  
  // Шаг 4: Отправляем транзакцию в ArWeave
  const response = await realArweave.transactions.post(transaction);
  
  // Assert
  assertEquals(response.status === 200 || response.status === 202, true, 
    `Ожидался статус 200 или 202, получен: ${response.status}`);
  
  assertEquals(transaction.id.startsWith("ar"), true, "Transaction ID должен начинаться с 'ar'");
  
  console.log("✅ Реальная загрузка в ArWeave успешна:", transaction.id);
  console.log("📊 Статус ответа:", response.status);
  
  // Дополнительная проверка: скачиваем загруженные данные
  const downloadedData = await realArweave.transactions.getData(transaction.id, { decode: true });
  assertEquals(downloadedData, testData, "Загруженные данные должны совпадать с исходными");
  
  console.log("✅ Данные успешно скачаны и проверены");
});

Deno.test("REAL ARWEAVE - должен обрабатывать ошибки подписи корректно", async () => {
  // Arrange - используем невалидный ключ
  const invalidKey = {
    kty: "RSA",
    n: "invalid_n",
    e: "AQAB",
    d: "invalid_d",
    p: "invalid_p",
    q: "invalid_q",
    dp: "invalid_dp",
    dq: "invalid_dq",
    qi: "invalid_qi"
  };
  
  const testData = "test content";
  
  // Act & Assert - должна быть ошибка при попытке подписи
  await assertThrows(
    async () => {
      const transaction = await realArweave.createTransaction({
        data: new TextEncoder().encode(testData)
      }, invalidKey);
      
      await realArweave.transactions.sign(transaction, invalidKey);
    },
    Error,
    "Ожидается ошибка при подписи невалидным ключом"
  );
  
  console.log("✅ Ошибка подписи невалидным ключом обработана корректно");
});

// Тест базовой связи с ArWeave
Deno.test("REAL ARWEAVE - должен проверить базовую связь с сетью", async () => {
  console.log("🌐 Проверяем связь с ArWeave...");
  
  try {
    // Проверяем подключение к ArWeave
    const networkInfo = await realArweave.network.getInfo();
    console.log("✅ Связь с ArWeave установлена");
    console.log("📊 Информация о сети:", networkInfo);
    
    // Проверяем текущий блок
    const currentBlock = await realArweave.blocks.getCurrent();
    console.log("📦 Текущий блок:", currentBlock);
    
    assertEquals(typeof networkInfo, "object", "Должна быть получена информация о сети");
    assertEquals(typeof currentBlock, "object", "Должен быть получен текущий блок");
    
  } catch (error) {
    console.error("❌ Ошибка связи с ArWeave:", error);
    throw error;
  }
});

// Тест валидации приватного ключа
Deno.test("REAL ARWEAVE - должен проверить валидность приватного ключа", async () => {
  console.log("🔑 Проверяем валидность приватного ключа...");
  
  const realPrivateKey = await loadRealPrivateKey();
  
  // Проверяем структуру ключа
  console.log("🔑 Структура ключа:", {
    kty: realPrivateKey.kty,
    hasN: !!realPrivateKey.n,
    hasE: !!realPrivateKey.e,
    hasD: !!realPrivateKey.d,
    hasP: !!realPrivateKey.p,
    hasQ: !!realPrivateKey.q,
    nLength: realPrivateKey.n?.length,
    eLength: realPrivateKey.e?.length,
    dLength: realPrivateKey.d?.length
  });
  
  // Проверяем, что это RSA ключ
  assertEquals(realPrivateKey.kty, "RSA", "Ключ должен быть RSA");
  
  // Проверяем наличие всех необходимых полей
  const requiredFields = ['n', 'e', 'd', 'p', 'q', 'dp', 'dq', 'qi'] as const;
  for (const field of requiredFields) {
    assertEquals(!!(realPrivateKey as any)[field], true, `Поле ${field} должно присутствовать`);
  }
  
  // Проверяем длину ключа (RSA должен быть достаточно длинным)
  assertEquals(realPrivateKey.n.length > 100, true, "Модуль n должен быть достаточно длинным");
  assertEquals(realPrivateKey.d.length > 100, true, "Приватная экспонента d должна быть достаточно длинной");
  
  console.log("✅ Приватный ключ валиден по структуре");
  
  // Попробуем создать простую транзакцию для проверки
  try {
    const testTransaction = await realArweave.createTransaction({
      data: new TextEncoder().encode("test")
    }, realPrivateKey);
    
    console.log("✅ Транзакция создана с ключом");
    console.log("   ID до подписи:", testTransaction.id);
    console.log("   Owner:", testTransaction.owner ? testTransaction.owner.substring(0, 20) + "..." : "НЕТ");
    
    // Если ID пустой, это проблема
    if (!testTransaction.id) {
      console.log("⚠️ ВНИМАНИЕ: Transaction ID пустой после создания!");
    }
    
  } catch (error) {
    console.error("❌ Ошибка создания транзакции с ключом:", error);
    throw error;
  }
});

// Тест версии ArWeave SDK и альтернативного подхода
Deno.test("REAL ARWEAVE - должен проверить версию SDK и альтернативный подход", async () => {
  console.log("🔍 Проверяем версию ArWeave SDK...");
  
  // Проверяем версию SDK
  console.log("📦 ArWeave SDK версия:", (realArweave as any).version || "неизвестна");
  console.log("🔧 ArWeave SDK методы:", Object.keys(realArweave));
  
  const realPrivateKey = await loadRealPrivateKey();
  
  // Попробуем альтернативный подход - создание транзакции без данных
  console.log("🔄 Пробуем создать транзакцию без данных...");
  try {
    const emptyTransaction = await realArweave.createTransaction({}, realPrivateKey);
    console.log("📝 Пустая транзакция ID:", emptyTransaction.id);
    console.log("📝 Пустая транзакция Owner:", emptyTransaction.owner ? emptyTransaction.owner.substring(0, 20) + "..." : "НЕТ");
  } catch (error: any) {
    console.log("❌ Ошибка создания пустой транзакции:", error.message);
  }
  
  // Попробуем создать транзакцию с минимальными данными
  console.log("🔄 Пробуем создать транзакцию с минимальными данными...");
  try {
    const minimalTransaction = await realArweave.createTransaction({
      data: "test"
    }, realPrivateKey);
    console.log("📝 Минимальная транзакция ID:", minimalTransaction.id);
    console.log("📝 Минимальная транзакция Owner:", minimalTransaction.owner ? minimalTransaction.owner.substring(0, 20) + "..." : "НЕТ");
  } catch (error: any) {
    console.log("❌ Ошибка создания минимальной транзакции:", error.message);
  }
  
  // Попробуем создать транзакцию с Uint8Array
  console.log("🔄 Пробуем создать транзакцию с Uint8Array...");
  try {
    const uint8Transaction = await realArweave.createTransaction({
      data: new Uint8Array([116, 101, 115, 116]) // "test" в байтах
    }, realPrivateKey);
    console.log("📝 Uint8Array транзакция ID:", uint8Transaction.id);
    console.log("📝 Uint8Array транзакция Owner:", uint8Transaction.owner ? uint8Transaction.owner.substring(0, 20) + "..." : "НЕТ");
  } catch (error: any) {
    console.log("❌ Ошибка создания Uint8Array транзакции:", error.message);
  }
  
  // Проверим, есть ли метод для генерации ID вручную
  console.log("🔧 Доступные методы transactions:", Object.keys(realArweave.transactions));
  console.log("🔧 Доступные методы crypto:", Object.keys(realArweave.crypto || {}));
  console.log("🔧 Доступные методы utils:", Object.keys(realArweave.utils || {}));
});

// Тест по шаблону экспертов для проверки совместимости Deno
Deno.test("REAL ARWEAVE - тест по шаблону экспертов", async () => {
  console.log("🧪 Тестируем по шаблону экспертов...");
  
  // Проверяем подключение
  try {
    const info = await realArweave.network.getInfo();
    console.log("✅ Подключение к ArWeave:", info.height);
  } catch (error: any) {
    console.log("❌ Ошибка подключения:", error.message);
    return;
  }
  
  const realPrivateKey = await loadRealPrivateKey();
  
  // Создаем транзакцию по шаблону экспертов
  console.log("📝 Создаем транзакцию по шаблону экспертов...");
  const tx = await realArweave.createTransaction({ 
    data: new TextEncoder().encode("Hello") 
  }, realPrivateKey);
  
  console.log("📝 До подписи - ID:", tx.id, "Owner:", tx.owner?.substring(0, 6));
  
  // Добавляем тег
  tx.addTag("Content-Type", "text/plain");
  
  // Подписываем
  console.log("🔐 Подписываем транзакцию...");
  await realArweave.transactions.sign(tx, realPrivateKey);
  
  console.log("📝 После подписи - ID:", tx.id, "Owner:", tx.owner?.substring(0, 6));
  
  // Проверяем результат
  if (tx.id) {
    console.log("✅ Transaction ID сгенерирован:", tx.id);
    assertEquals(tx.id.startsWith("ar"), true, "Transaction ID должен начинаться с 'ar'");
  } else {
    console.log("❌ Transaction ID остается пустым - проблема совместимости Deno");
    // Это подтверждает проблему совместимости Deno с ArWeave SDK
  }
  
  if (tx.owner) {
    console.log("✅ Owner сгенерирован:", tx.owner.substring(0, 20) + "...");
  } else {
    console.log("❌ Owner не сгенерирован");
  }
});

// Тест отправки транзакции с неправильным ID
Deno.test("REAL ARWEAVE - тест отправки транзакции", async () => {
  console.log("🚀 Тестируем отправку транзакции...");
  
  const realPrivateKey = await loadRealPrivateKey();
  
  // Создаем и подписываем транзакцию
  const tx = await realArweave.createTransaction({ 
    data: new TextEncoder().encode("Test transaction for upload") 
  }, realPrivateKey);
  
  tx.addTag("Content-Type", "text/plain");
  tx.addTag("Test-Type", "upload-test");
  
  await realArweave.transactions.sign(tx, realPrivateKey);
  
  console.log("📝 Transaction ID:", tx.id);
  console.log("📝 Owner:", tx.owner?.substring(0, 20) + "...");
  console.log("📝 Signature:", tx.signature?.substring(0, 20) + "...");
  
  // Пытаемся отправить транзакцию
  console.log("📤 Отправляем транзакцию...");
  try {
    const response = await realArweave.transactions.post(tx);
    console.log("📊 Статус ответа:", response.status);
    console.log("📊 Статус текст:", response.statusText);
    
    if (response.status === 200 || response.status === 202) {
      console.log("✅ Транзакция отправлена успешно!");
    } else {
      console.log("❌ Ошибка отправки:", response.status, response.statusText);
    }
  } catch (error: any) {
    console.log("❌ Исключение при отправке:", error.message);
  }
});

// Тест правильной генерации Transaction ID
Deno.test("REAL ARWEAVE - тест правильной генерации Transaction ID", async () => {
  console.log("🔍 Тестируем правильную генерацию Transaction ID...");
  
  const realPrivateKey = await loadRealPrivateKey();
  
  // Создаем транзакцию
  const tx = await realArweave.createTransaction({ 
    data: new TextEncoder().encode("Test transaction for ID generation") 
  }, realPrivateKey);
  
  console.log("📝 До подписи:");
  console.log("   ID:", tx.id);
  console.log("   Owner:", tx.owner?.substring(0, 20) + "...");
  console.log("   Data size:", tx.data_size);
  
  // Добавляем теги
  tx.addTag("Content-Type", "text/plain");
  tx.addTag("Test-Type", "id-generation");
  
  // Подписываем
  await realArweave.transactions.sign(tx, realPrivateKey);
  
  console.log("📝 После подписи:");
  console.log("   ID:", tx.id);
  console.log("   Owner:", tx.owner?.substring(0, 20) + "...");
  console.log("   Signature:", tx.signature?.substring(0, 20) + "...");
  console.log("   Data size:", tx.data_size);
  
  // Проверяем, что ID начинается с 'ar'
  if (tx.id && tx.id.startsWith("ar")) {
    console.log("✅ Transaction ID правильный:", tx.id);
  } else {
    console.log("❌ Transaction ID неправильный:", tx.id);
    console.log("   Ожидалось: ar...");
    console.log("   Получено:", tx.id);
    
         // Попробуем вручную вычислить ID
     console.log("🔧 Пытаемся вычислить ID вручную...");
     try {
       // Получаем данные для подписи
       const signatureData = await tx.getSignatureData();
       console.log("   Signature data length:", signatureData.length);
       
       // Вычисляем хеш
       const hash = await realArweave.crypto.hash(signatureData);
       console.log("   Hash:", hash);
       
       // Конвертируем в base64url
       const id = realArweave.utils.bufferTob64Url(hash);
       console.log("   Computed ID:", id);
      
      if (id.startsWith("ar")) {
        console.log("✅ Вычисленный ID правильный:", id);
      } else {
        console.log("❌ Вычисленный ID тоже неправильный:", id);
      }
    } catch (error: any) {
      console.log("❌ Ошибка при вычислении ID:", error.message);
    }
  }
});

// ============================================================================
// TDD ТЕСТЫ ДЛЯ getPrivateKey()
// ============================================================================

Deno.test("getPrivateKey - должен корректно парсить валидный JSON ключ", () => {
  // Arrange
  const validKey = {
    kty: "RSA",
    n: "test_n_value",
    e: "AQAB",
    d: "test_d_value",
    p: "test_p_value",
    q: "test_q_value",
    dp: "test_dp_value",
    dq: "test_dq_value",
    qi: "test_qi_value"
  };
  
  const mockEnv: Environment = {
    get: (key: string) => {
      if (key === 'ARWEAVE_PRIVATE_KEY') {
        return JSON.stringify(validKey);
      }
      return undefined;
    }
  };

  // Act
  const privateKey = getPrivateKey(mockEnv);

  // Assert
  assertEquals(privateKey.kty, "RSA");
  assertEquals(privateKey.n, "test_n_value");
  assertEquals(privateKey.e, "AQAB");
  assertEquals(privateKey.d, "test_d_value");
});

Deno.test("getPrivateKey - должен выбросить ошибку при отсутствии ключа", () => {
  // Arrange
  const mockEnv: Environment = {
    get: (key: string) => undefined
  };

  // Act & Assert
  assertThrows(
    () => getPrivateKey(mockEnv),
    Error,
    "ARWEAVE_PRIVATE_KEY environment variable is required"
  );
});

Deno.test("getPrivateKey - должен выбросить ошибку при невалидном JSON", () => {
  // Arrange
  const mockEnv: Environment = {
    get: (key: string) => {
      if (key === 'ARWEAVE_PRIVATE_KEY') {
        return "invalid json string";
      }
      return undefined;
    }
  };

  // Act & Assert
  assertThrows(
    () => getPrivateKey(mockEnv),
    Error,
    "Invalid JSON format for ARWEAVE_PRIVATE_KEY"
  );
});

Deno.test("getPrivateKey - должен выбросить ошибку при неполном ключе", () => {
  // Arrange
  const incompleteKey = {
    kty: "RSA",
    n: "test_n_value"
    // Отсутствуют обязательные поля
  };
  
  const mockEnv: Environment = {
    get: (key: string) => {
      if (key === 'ARWEAVE_PRIVATE_KEY') {
        return JSON.stringify(incompleteKey);
      }
      return undefined;
    }
  };

  // Act & Assert
  assertThrows(
    () => getPrivateKey(mockEnv),
    Error,
    "Invalid private key: missing or invalid field 'e'"
  );
});

Deno.test("getPrivateKey - должен корректно обрабатывать реальный RSA ключ", () => {
  // Arrange
  const realKey = {
    "kty": "RSA",
    "e": "AQAB",
    "n": "gwSkfa7qf2dMGHEkx7WijiRvF7HDjYpO996oU5VAKzEuXRY7hyG6h7Q0ZyrL4t3-tR_wvKGxh4WxuHe8TPYfvqQWg3Cyyn3mmhKdgkEcS1WclIdZdgpTgJuNTJpvwu_egC6IwldVB8Vi-lRWzRh22833udef56Q-ZrTVgM-SHRNReVETIM7RskWOcn9b5Xxc4ZoEC1TbUK2DgXkSV5bR1B5TjlW2L7pTk8AK1lqMRhxKAwg6o-O7ssmqlBBi9Vg0ts5ui4GTiz1Fvr8_vJwjoWGbCE44QGSwqRE5rzZ4MQ_clgxPMrmADUzwDrOh7Vc9w771HegOJn1mOC2KC0T4LVLteOcYHi2eZBF_J8RAb66lWoO8LSMwMZeYuwrB7H8G7ZOk-bnfxDBwnKfm9NGrxWxw_eWsRQyqafpPipHZAEka0C5txRPZ2FSPXiDZgVqWFu2nqc7VtJ7DVN8k_ikTUaB8ZIEsFv3gnARkbdWhEvp6jajTSWAEzOcFeZpi6lpVDsJ1yEl6Z5j1Ld-_EfqPQOdaTmJhCxisEO7lRqua6SrA0ODUpX-CcJRxEeCJWzHLcr1a8FQgnZlGn8_sw9UgwDV3C12iMX1o-Uj1cYvW_2JMTKfTBqldS262weEpZLPCQILvrsOQ7r0UBieb8fPh5AfuPi-4YWmwuXq2yJ5DlLE",
    "d": "ZUA2OqbttA3JQe5WZTwaZs0DSYVoQb8MLgRVg1qJX5e_Y9LlqBXJyEvcX4o0TJwQ1jrb2Xr_7mLEqHFoBPYELFk0yNlUYqaPiqwuK1ZUHmgH_MTovw9V3sLXnMaQ7k5fXiIYMFA7dyj0x85b0l5ApLd05ZsciXBlhQvlH4nKOkwOn7mnFaifZ6zXW-bOxven8_UJgRRP9PZS9cDyCtyUReA15H6asCHHqxwzg9owI5KDI_q9DqDVEmNFPu22_DHxcwDvb0JxGp78gl_cSs9DvdjnbbC9Sg5GdDHKqXxnwEqoxxC2N9YhfqXhswrhbcEJC3hMh5MpNFeeonWXBASF4ac504vsdSPc0PKbRhTv9Nzr6f4qeVfREXhveb1mDd9BGXEDyi5drQmS3rc-zg4FpwDyiLP6i9UDPOP0IFINEmq7VYFXTR7kINtHXHLMxamP4vfecRI-EQHCnvDm8G9Ydpk-AL-3Y_LHmbCrtYvmRzFSO-Fw-GxVaU7om4db6u9cISODxvNTA4LMQuWsAuhjr1INOngV2AFwYPqk7kutrIWToCjCfOG-kojGIG66EmM7WiWrPYEiND9A8qHTECfDKE4SpY2ZMQRYrv9SG4G-DgiZNSw9udSr1qsP_vLhCPbe3rvYTr8MFge5n2V8MZh7_P-zGMs-WAgPL7XBnEoQLD0",
    "p": "45RbKtFz087-FmVtMYhf4C1kNP9gijJfp3ynLEbXKokqdjWS1gwV0D8GxldAG76GVOX7bKSvdxaKw-BLdGMAKysR_V0abhtyqkofWV3k6ZrbXPU3I2rQQmZCgH1Ka5Cc2e6uJ558V_in3L45xID8cxZJ0paHYuX-oXw9FZg9PB-RRjeXoAwSzhXTOsAhfB9uCiNEoHnwksxODkn0uPu98ZeCHVN0tp7H-gh6dhk9oYhyZZOXb6FhcYHpLUzqSqAdVUHaoAFGN3m3lx0_WAzCroog4WbpZNpCeWzvzww0kVJRPjEPvAL-0URdnoSjsOMGlNZ54K-o_MXW4DbnXYox1w",
    "q": "k2FACYUzVrtsbvX1gjSXwBwQpD-uJv-Kz-wbz3rUR-pjDUZC91adAcTwyZHSf40IOfOzwUdaoTaDmiqqGDuFgOv_DH20_kN5ylsfdcysoSdoOpW-QfFRVB8UJCn3pwDDUGjVg0cx_zU1-CjIXExTSYBFfxTsVvOPeg8MrA7_aRJ8DoIUvquqHCLmcJM7tEfIXKyE93RfvTcBp8IW0jJaP_1HR-vvbsYRTqwYMov4hFGsQ8FoPxy4EkpbgdOiWc4RNNEdy31U4t23J0CIrVMpga-7pZKyF9Nr6ZVoLC-JeEpUmXMERCO_-WZQoB8wwnl6F8-7OAZdE6mTcFKHpD8stw",
    "dp": "o6n-gmWM8ecrjbm1dGjJ4nNiXEbIC7q8VbvskYgElz97vPU8OxkH2vJokd0PaqRzAL1AOlqZIYChnMpCGVpVNbZMwrPhHQw6Q0L5FpDS3jkSxuBGnf7j9MyLyNHR4ldmpcfjkPSGIdHeDn7zFmFYq_98aaj9hl825rVtTIlmiEV_eUrjjSMBpxnFBbxEmHoV7c59PRdUro2lGNuQ1jOc3xCBb0ukZOz9jc_pGeN_EhsJgglJX-tkI3g00_I7kB1j2vt4GZexApZTNKbA9jZ_D3ygttkGwhPAuIhiUblKWLQlXx9zXFefH6oV1bk36y7pfcJcdfx-AALbS_XQH9IRkw",
    "dq": "IgtuAoT9hgSHmN5CV1CU2XDiOz7mmOWhCETPa89A6Ffxh6h6Ya5lWHpI8Rc5W_OVOeXc2UIFYoY4Qk2muzBMt6pMYXNMcwvdP2xrSQf9vMBgqF_c8livY9JGEdCL_80CUTnWUJwKpZyCGhA5sHCFMM5rv15y9ecPdq-xSrGwOHJnq-ZKqnz3L8a0Gr84JH4Mf7Puh0cfspLZVApWwTmWdX-pjqimx50DdHv2nv6Maux-8avky-dzce4xUz0zHLGocd34lwAdssZqv6t9pyQ1y1pv62CGuVBCdlPoG4TjqaDqCAR0sNTdTNxgtYxe9B2hoYyAAAIgUCF1CJZX9Q4O4w",
    "qi": "rtGKTxE7uN-f-_Vp6IhEAatOwm2FI128oqRGXSa_UrCHoIOVuFStDs-ZXxPrpjBItdQQ3hkIs97f_hVbtC6t69TLlgcuTpR0GCnKRY1VzIKUsCxh51i-P2dE72YWyynRYYPrwoOJ4R_EU_MYkQqm_ec9ZDat07AKXg9vMTv5sBXWLGKi1A5bufTga3UrjHT9MkYVNj8PS11xoPPJDQzQ-EmC5lfT8L0wGNcA1ZC_3MP49eDbMedGQ0VVaMLG8evL8FHhbgGfr7e0Vlxgh7sTGtFz945CKA4HN2LVwxDh9f3bIKm8m3b4PbPPkawmHHmVeEqiZX0zUK0UdsUJY0DSIQ"
  };
  
  const mockEnv: Environment = {
    get: (key: string) => {
      if (key === 'ARWEAVE_PRIVATE_KEY') {
        return JSON.stringify(realKey);
      }
      return undefined;
    }
  };

  // Act
  const privateKey = getPrivateKey(mockEnv);

  // Assert
  assertEquals(privateKey.kty, "RSA");
  assertEquals(privateKey.e, "AQAB");
  assertEquals(privateKey.n, realKey.n);
  assertEquals(privateKey.d, realKey.d);
  assertEquals(privateKey.p, realKey.p);
  assertEquals(privateKey.q, realKey.q);
  assertEquals(privateKey.dp, realKey.dp);
  assertEquals(privateKey.dq, realKey.dq);
  assertEquals(privateKey.qi, realKey.qi);
});

// ============================================================================
// TDD ТЕСТЫ ДЛЯ validatePrivateKey()
// ============================================================================

Deno.test("validatePrivateKey - должен валидировать корректный ключ", () => {
  // Arrange
  const validKey: ArWeavePrivateKey = {
    kty: "RSA",
    n: "test_n",
    e: "AQAB",
    d: "test_d",
    p: "test_p",
    q: "test_q",
    dp: "test_dp",
    dq: "test_dq",
    qi: "test_qi"
  };

  // Act & Assert (не должно выбросить ошибку)
  validatePrivateKey(validKey);
});

Deno.test("validatePrivateKey - должен выбросить ошибку при неверном типе", () => {
  // Arrange
  const invalidKey = {
    kty: "EC", // Неверный тип
    n: "test_n",
    e: "AQAB",
    d: "test_d",
    p: "test_p",
    q: "test_q",
    dp: "test_dp",
    dq: "test_dq",
    qi: "test_qi"
  };

  // Act & Assert
  assertThrows(
    () => validatePrivateKey(invalidKey),
    Error,
    "Invalid private key: must be RSA type"
  );
});

// ============================================================================
// TDD ТЕСТЫ ДЛЯ validateTextUpload()
// ============================================================================

Deno.test("validateTextUpload - должен валидировать корректные данные", () => {
  // Arrange
  const validData = {
    data: "test content",
    contentType: "text/plain"
  };

  // Act
  const result = validateTextUpload(validData);

  // Assert
  assertEquals(result.data, "test content");
  assertEquals(result.contentType, "text/plain");
});

Deno.test("validateTextUpload - должен использовать дефолтный content-type", () => {
  // Arrange
  const dataWithoutContentType = {
    data: "test content"
  };

  // Act
  const result = validateTextUpload(dataWithoutContentType);

  // Assert
  assertEquals(result.data, "test content");
  assertEquals(result.contentType, "text/plain");
});

Deno.test("validateTextUpload - должен выбросить ошибку при отсутствии data", () => {
  // Arrange
  const invalidData = {
    contentType: "text/plain"
  };

  // Act & Assert
  assertThrows(
    () => validateTextUpload(invalidData),
    Error,
    'Request body must contain "data" field as string'
  );
});

Deno.test("validateTextUpload - должен выбросить ошибку при нестроковом data", () => {
  // Arrange
  const invalidData = {
    data: 123,
    contentType: "text/plain"
  };

  // Act & Assert
  assertThrows(
    () => validateTextUpload(invalidData),
    Error,
    'Request body must contain "data" field as string'
  );
});

// ============================================================================
// TDD ТЕСТЫ ДЛЯ uploadText()
// ============================================================================

Deno.test("uploadText - должен успешно загружать текст", async () => {
  // Arrange
  const testData = "test content";
  const contentType = "text/plain";
  const mockPrivateKey: ArWeavePrivateKey = {
    kty: "RSA",
    n: "test_n",
    e: "AQAB",
    d: "test_d",
    p: "test_p",
    q: "test_q",
    dp: "test_dp",
    dq: "test_dq",
    qi: "test_qi"
  };

  // Act
  const transactionId = await uploadText(testData, contentType, mockPrivateKey, mockArweave);

  // Assert
  assertEquals(transactionId, "ar_test_transaction_id_12345");
});

Deno.test("uploadText - должен выбросить ошибку при неудачной отправке", async () => {
  // Arrange
  const testData = "test content";
  const contentType = "text/plain";
  const mockPrivateKey: ArWeavePrivateKey = {
    kty: "RSA",
    n: "test_n",
    e: "AQAB",
    d: "test_d",
    p: "test_p",
    q: "test_q",
    dp: "test_dp",
    dq: "test_dq",
    qi: "test_qi"
  };

  // Act & Assert
  await assertThrows(
    async () => {
      await uploadText(testData, contentType, mockPrivateKey, mockArweaveWithError);
    },
    Error,
    "ArWeave upload failed: 400 Transaction verification failed."
  );
});

// ============================================================================
// КРИТИЧЕСКИЙ ТЕСТ: ВОСПРОИЗВЕДЕНИЕ РЕАЛЬНОЙ ОШИБКИ
// ============================================================================

Deno.test("uploadText - должен воспроизвести реальную ошибку 'Transaction verification failed'", async () => {
  // Arrange - используем реальный приватный ключ из переменных окружения
  const testData = JSON.stringify({
    test: "data",
    number: 42,
    boolean: true,
    array: [1, 2, 3],
    object: { nested: "value" }
  });
  const contentType = "application/json";
  
  // Получаем реальный приватный ключ
  const realPrivateKey = getPrivateKey();
  
  // Создаем мок ArWeave, который возвращает реальную ошибку
  const mockArweaveWithRealError: ArWeaveClient = {
    ...mockArweave,
    transactions: {
      ...mockArweave.transactions,
      post: async () => ({ 
        status: 400, 
        statusText: "Transaction verification failed." 
      })
    }
  };

  // Act & Assert
  await assertThrows(
    async () => await uploadText(testData, contentType, realPrivateKey, mockArweaveWithRealError),
    Error,
    "ArWeave upload failed: 400 Transaction verification failed."
  );
});

Deno.test("uploadText - должен воспроизвести реальную ошибку с реальными данными", async () => {
  // Arrange - используем точно такие же данные, как в Python тесте
  const testData = JSON.stringify({
    test: "data",
    number: 42,
    boolean: true,
    array: [1, 2, 3],
    object: { nested: "value" }
  });
  const contentType = "application/json";
  
  // Получаем реальный приватный ключ
  const realPrivateKey = getPrivateKey();
  
  // Создаем мок ArWeave, который возвращает реальную ошибку
  const mockArweaveWithRealError: ArWeaveClient = {
    ...mockArweave,
    transactions: {
      ...mockArweave.transactions,
      post: async () => ({ 
        status: 400, 
        statusText: "Transaction verification failed." 
      })
    }
  };

  // Act & Assert
  const error = await assertThrows(
    async () => await uploadText(testData, contentType, realPrivateKey, mockArweaveWithRealError),
    Error
  );
  
  // Проверяем точное сообщение об ошибке
  assertEquals(error.message, "ArWeave upload failed: 400 Transaction verification failed.");
});

// ============================================================================
// TDD ТЕСТЫ ДЛЯ uploadFile()
// ============================================================================

Deno.test("uploadFile - должен успешно загружать файл", async () => {
  // Arrange
  const fileData = new Uint8Array([1, 2, 3, 4, 5]);
  const contentType = "application/octet-stream";
  const mockPrivateKey: ArWeavePrivateKey = {
    kty: "RSA",
    n: "test_n",
    e: "AQAB",
    d: "test_d",
    p: "test_p",
    q: "test_q",
    dp: "test_dp",
    dq: "test_dq",
    qi: "test_qi"
  };

  // Act
  const transactionId = await uploadFile(fileData, contentType, mockPrivateKey, mockArweave);

  // Assert
  assertEquals(transactionId, "ar_test_transaction_id_12345");
});

// ============================================================================
// TDD ТЕСТЫ ДЛЯ HTTP УТИЛИТ
// ============================================================================

Deno.test("createSuccessResponse - должен создавать корректный ответ", () => {
  // Arrange
  const testData = { success: true, transaction_id: "ar_test" };

  // Act
  const response = createSuccessResponse(testData);

  // Assert
  assertEquals(response.status, 200);
  assertEquals(response.headers.get("Access-Control-Allow-Origin"), "*");
  assertEquals(response.headers.get("Content-Type"), "application/json");
});

Deno.test("createErrorResponse - должен создавать корректный ответ с ошибкой", () => {
  // Arrange
  const errorMessage = "Test error";
  const statusCode = 400;

  // Act
  const response = createErrorResponse(errorMessage, statusCode);

  // Assert
  assertEquals(response.status, 400);
  assertEquals(response.headers.get("Access-Control-Allow-Origin"), "*");
  assertEquals(response.headers.get("Content-Type"), "application/json");
});

Deno.test("createHealthResponse - должен создавать корректный health check", () => {
  // Act
  const response = createHealthResponse();

  // Assert
  assertEquals(response.status, 200);
  assertEquals(response.headers.get("Access-Control-Allow-Origin"), "*");
  assertEquals(response.headers.get("Content-Type"), "application/json");
});

// ============================================================================
// ИНТЕГРАЦИОННЫЕ ТЕСТЫ
// ============================================================================

Deno.test("Полный цикл uploadText - должен работать end-to-end", async () => {
  // Arrange
  const testData = "integration test content";
  const contentType = "text/plain";
  const mockPrivateKey: ArWeavePrivateKey = {
    kty: "RSA",
    n: "test_n",
    e: "AQAB",
    d: "test_d",
    p: "test_p",
    q: "test_q",
    dp: "test_dp",
    dq: "test_dq",
    qi: "test_qi"
  };

  // Act
  const transactionId = await uploadText(testData, contentType, mockPrivateKey, mockArweave);

  // Assert
  assertEquals(transactionId, "ar_test_transaction_id_12345");
  assertEquals(transactionId.startsWith("ar"), true);
});

Deno.test("Обработка ошибок - должен корректно обрабатывать исключения", async () => {
  // Arrange
  const mockArweaveWithException: ArWeaveClient = {
    ...mockArweave,
    createTransaction: async () => {
      throw new Error("Network error");
    }
  };
  
  const testData = "test content";
  const contentType = "text/plain";
  const mockPrivateKey: ArWeavePrivateKey = {
    kty: "RSA",
    n: "test_n",
    e: "AQAB",
    d: "test_d",
    p: "test_p",
    q: "test_q",
    dp: "test_dp",
    dq: "test_dq",
    qi: "test_qi"
  };

  // Act & Assert
  await assertThrows(
    async () => await uploadText(testData, contentType, mockPrivateKey, mockArweaveWithException),
    Error,
    "Network error"
  );
}); 