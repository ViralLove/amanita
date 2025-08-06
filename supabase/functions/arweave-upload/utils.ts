/**
 * Утилиты для ArWeave Edge Function
 * Вынесены для поддержки TDD тестирования
 */

// Типы для приватного ключа
export interface ArWeavePrivateKey {
  kty: string;
  n: string;
  e: string;
  d: string;
  p: string;
  q: string;
  dp: string;
  dq: string;
  qi: string;
}

// Типы для валидации
export interface TextUploadData {
  data: string;
  contentType?: string;
}

// Интерфейс для ArWeave клиента
export interface ArWeaveClient {
  init: (config: any) => ArWeaveClient;
  createTransaction: (options: any, privateKey: any) => Promise<ArWeaveTransaction>;
  transactions: {
    sign: (transaction: ArWeaveTransaction, privateKey: any) => Promise<void>;
    post: (transaction: ArWeaveTransaction) => Promise<ArWeaveResponse>;
  };
}

// Интерфейс для транзакции
export interface ArWeaveTransaction {
  id: string;
  addTag: (key: string, value: string) => void;
  get: (key: string) => any;
}

// Интерфейс для ответа ArWeave
export interface ArWeaveResponse {
  status: number;
  statusText?: string;
}

// Интерфейс для окружения
export interface Environment {
  get: (key: string) => string | undefined;
}

// ============================================================================
// УТИЛИТЫ ДЛЯ РАБОТЫ С ПРИВАТНЫМ КЛЮЧОМ
// ============================================================================

export function getPrivateKey(env: Environment = Deno.env): ArWeavePrivateKey {
  const privateKey = env.get('ARWEAVE_PRIVATE_KEY');
  if (!privateKey) {
    throw new Error('ARWEAVE_PRIVATE_KEY environment variable is required');
  }
  
  try {
    const parsedKey = JSON.parse(privateKey);
    validatePrivateKey(parsedKey);
    return parsedKey;
  } catch (e) {
    if (e instanceof Error && e.message.includes('JSON')) {
      throw new Error('Invalid JSON format for ARWEAVE_PRIVATE_KEY');
    }
    throw e;
  }
}

export function validatePrivateKey(key: any): asserts key is ArWeavePrivateKey {
  const requiredFields = ['kty', 'n', 'e', 'd', 'p', 'q', 'dp', 'dq', 'qi'];
  
  for (const field of requiredFields) {
    if (!key[field] || typeof key[field] !== 'string') {
      throw new Error(`Invalid private key: missing or invalid field '${field}'`);
    }
  }
  
  if (key.kty !== 'RSA') {
    throw new Error('Invalid private key: must be RSA type');
  }
}

// ============================================================================
// УТИЛИТЫ ДЛЯ ВАЛИДАЦИИ ДАННЫХ
// ============================================================================

export function validateTextUpload(data: any): TextUploadData {
  if (!data || typeof data.data !== 'string') {
    throw new Error('Request body must contain "data" field as string');
  }
  
  return {
    data: data.data,
    contentType: data.contentType || 'text/plain'
  };
}

export function validateFileUpload(formData: FormData): { file: File; data: Uint8Array; contentType: string } {
  const file = formData.get('file') as File;
  
  if (!file) {
    throw new Error('No file provided');
  }
  
  return {
    file,
    data: new Uint8Array(0), // Будет заполнено позже
    contentType: file.type || 'application/octet-stream'
  };
}

// ============================================================================
// УТИЛИТЫ ДЛЯ ЗАГРУЗКИ
// ============================================================================

export async function uploadText(
  data: string, 
  contentType: string = 'text/plain',
  privateKey: ArWeavePrivateKey,
  arweave: ArWeaveClient
): Promise<string> {
  try {
    const transaction = await arweave.createTransaction({
      data: new TextEncoder().encode(data)
    }, privateKey);
    
    transaction.addTag('Content-Type', contentType);
    
    await arweave.transactions.sign(transaction, privateKey);
    const response = await arweave.transactions.post(transaction);
    
    if (response.status === 200 || response.status === 202) {
      return transaction.id;
    } else {
      throw new Error(`ArWeave upload failed: ${response.status} ${response.statusText || 'Unknown error'}`);
    }
  } catch (error) {
    // Не логируем ошибку в тестах, чтобы не засорять вывод
    if (typeof window === 'undefined' && typeof Deno !== 'undefined' && 
        error instanceof Error && !error.message?.includes('ArWeave upload failed')) {
      console.error('Error uploading text to ArWeave:', error);
    }
    throw error;
  }
}

export async function uploadFile(
  fileData: Uint8Array, 
  contentType: string,
  privateKey: ArWeavePrivateKey,
  arweave: ArWeaveClient
): Promise<string> {
  try {
    const transaction = await arweave.createTransaction({
      data: fileData
    }, privateKey);
    
    transaction.addTag('Content-Type', contentType);
    
    await arweave.transactions.sign(transaction, privateKey);
    const response = await arweave.transactions.post(transaction);
    
    if (response.status === 200 || response.status === 202) {
      return transaction.id;
    } else {
      throw new Error(`ArWeave file upload failed: ${response.status} ${response.statusText || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error uploading file to ArWeave:', error);
    throw error;
  }
}

// ============================================================================
// УТИЛИТЫ ДЛЯ HTTP ОТВЕТОВ
// ============================================================================

export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS'
};

export function createSuccessResponse(data: any): Response {
  return new Response(
    JSON.stringify(data),
    { 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  );
}

export function createErrorResponse(error: string, status: number = 500): Response {
  return new Response(
    JSON.stringify({ 
      success: false, 
      error: error
    }),
    { 
      status,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  );
}

export function createHealthResponse(): Response {
  return createSuccessResponse({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    arweave: 'connected'
  });
} 