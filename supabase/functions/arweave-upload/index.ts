/// <reference path="./deno_shim.d.ts" />
/// <reference path="./npm-arweave.d.ts" />
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import Arweave from "npm:arweave@1.15.7"
import { signTransaction } from "./arweave/compatible.ts"
import { verifyUploadToken } from "./publish/validate-token.ts"
import { putStatus, postCallback, normalizeMockStatus } from "./publish/backend-calls.ts"
import { validateDataItem } from "./publish/validate-data-item.ts"
import { bundleAndPublish } from "./publish/bundle-publish.ts"

// Инициализация ArWeave клиента с правильными параметрами
const arweave = Arweave.init({
  host: 'arweave.net',
  port: 443,
  protocol: 'https',
  timeout: 20000,
  logging: true,
})

/**
 * Загружает и подготавливает приватный ключ Arweave из файла.
 * Ожидается, что переменная окружения ARWEAVE_PRIVATE_KEY_FILE содержит путь к JSON-файлу с полным JWK.
 */
const loadArweavePrivateKey = async (): Promise<any> => {
  const privateKeyFilePath = Deno.env.get('ARWEAVE_PRIVATE_KEY_FILE')
  if (!privateKeyFilePath) {
    throw new Error('ARWEAVE_PRIVATE_KEY_FILE environment variable is required')
  }

  try {
    const rawKey = await Deno.readTextFile(privateKeyFilePath)
    const parsedKey = JSON.parse(rawKey)

    // Минимальная валидация: ключ должен содержать kty, e, n и d (для подписи)
    const requiredFields = ['kty', 'e', 'n', 'd']
    for (const field of requiredFields) {
      if (!parsedKey[field]) {
        throw new Error(`Invalid Arweave key file: missing field "${field}"`)
      }
    }

    return parsedKey
  } catch (err) {
    console.error('Failed to load Arweave private key:', err)
    throw new Error('Could not load or parse Arweave private key file')
  }
}

// Валидация входных данных
const validateTextUpload = (data: any): { data: string, contentType?: string } => {
  if (!data || typeof data.data !== 'string') {
    throw new Error('Request body must contain "data" field as string')
  }
  
  return {
    data: data.data,
    contentType: data.contentType || 'text/plain'
  }
}

// Загрузка текстовых данных
const uploadText = async (data: string, contentType: string = 'text/plain'): Promise<string> => {
  try {
    const privateKey = await loadArweavePrivateKey()
    
    // Шаг 1: Создание транзакции
    const transaction = await arweave.createTransaction({
      data: new TextEncoder().encode(data)
    }, privateKey)
    
    // Шаг 2: Добавление тегов ДО подписи (КРИТИЧЕСКИ ВАЖНО!)
    transaction.addTag('Content-Type', contentType)
    
    // Шаг 3: Подпись транзакции
    await signTransaction(arweave, transaction, privateKey)
    
    // Отладочная информация
    console.log("Transaction ID:", transaction.id)
    console.log("Signature:", transaction.signature)
    console.log("Owner:", transaction.owner)
    
    // Валидация перед отправкой
    if (!transaction.id.startsWith('ar')) {
      throw new Error('Invalid transaction ID generated')
    }
    
    if (!transaction.signature) {
      throw new Error('Transaction not signed properly')
    }
    
    // Шаг 4: Отправка транзакции
    const response = await arweave.transactions.post(transaction)
    
    if (response.status === 200 || response.status === 202) {
      return transaction.id
    } else {
      throw new Error(`ArWeave upload failed: ${response.status} ${response.statusText}`)
    }
  } catch (error) {
    console.error('Error uploading text to ArWeave:', error)
    throw error
  }
}

// Загрузка файла
const uploadFile = async (fileData: Uint8Array, contentType: string): Promise<string> => {
  try {
    const privateKey = await loadArweavePrivateKey()
    
    // Шаг 1: Создание транзакции для файла
    const transaction = await arweave.createTransaction({
      data: fileData
    }, privateKey)
    
    // Шаг 2: Добавление тегов ДО подписи (КРИТИЧЕСКИ ВАЖНО!)
    transaction.addTag('Content-Type', contentType)
    
    // Шаг 3: Подпись транзакции
    await signTransaction(arweave, transaction, privateKey)
    
    // Отладочная информация
    console.log("File Transaction ID:", transaction.id)
    console.log("File Signature:", transaction.signature)
    
    // Валидация перед отправкой
    if (!transaction.id.startsWith('ar')) {
      throw new Error('Invalid file transaction ID generated')
    }
    
    if (!transaction.signature) {
      throw new Error('File transaction not signed properly')
    }
    
    // Шаг 4: Отправка транзакции
    const response = await arweave.transactions.post(transaction)
    
    if (response.status === 200 || response.status === 202) {
      return transaction.id
    } else {
      throw new Error(`ArWeave file upload failed: ${response.status} ${response.statusText}`)
    }
  } catch (error) {
    console.error('Error uploading file to ArWeave:', error)
    throw error
  }
}

// CORS headers
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS'
}

/** Обработчик запросов (экспорт для тестов). */
export async function handler(req: Request): Promise<Response> {
  // Обработка CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const url = new URL(req.url)
    const path = url.pathname

    console.log(`[ArWeave Edge Function] ${req.method} ${path}`)

    // Health check endpoint - обрабатываем как GET запрос к корню или /health
    if ((path === '/' || path.endsWith('/health')) && req.method === 'GET') {
      return new Response(
        JSON.stringify({ 
          status: 'healthy', 
          timestamp: new Date().toISOString(),
          arweave: 'connected'
        }),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Upload text endpoint
    if (path.endsWith('/upload-text') && req.method === 'POST') {
      const body = await req.json()
      const { data, contentType } = validateTextUpload(body)
      
      const transactionId = await uploadText(data, contentType)
      
      return new Response(
        JSON.stringify({ 
          success: true, 
          transaction_id: transactionId,
          url: `https://arweave.net/${transactionId}`
        }),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Publish endpoint: signed Data Item + JWT, Backend status/callback
    if (path.endsWith("/edge/v1/publish") && req.method === "POST") {
      console.log("[publish] request received");
      let body: { upload_token?: string; upload_id?: string; signed_data_item?: string; payload_size?: number };
      try {
        body = await req.json();
      } catch {
        return new Response(
          JSON.stringify({ code: "bad_request", message: "Invalid JSON body" }),
          { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      const uploadToken = body.upload_token
      const uploadId = body.upload_id
      const signedDataItem = body.signed_data_item
      const payloadSize = body.payload_size
      if (typeof uploadToken !== "string" || !uploadToken ||
          typeof uploadId !== "string" || !uploadId ||
          typeof signedDataItem !== "string" || !signedDataItem ||
          typeof payloadSize !== "number" || payloadSize < 0) {
        return new Response(
          JSON.stringify({ code: "bad_request", message: "Missing required field" }),
          { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      const mockEnabled = (() => {
        const v = Deno.env.get("BACKEND_USE_MOCK");
        return v === "true" || v === "1" || (typeof v === "string" && v.toLowerCase() === "true");
      })();
      const allowRequestOverride = mockEnabled && (
        Deno.env.get("BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE") === "true" ||
        req.headers.get("X-Backend-Mock-Secret") === Deno.env.get("BACKEND_MOCK_TEST_SECRET")
      );
      const requestMockOverride: { putStatus?: number; callback?: number } = {};
      if (allowRequestOverride) {
        const putHeader = req.headers.get("X-Backend-Mock-Put-Status");
        const cbHeader = req.headers.get("X-Backend-Mock-Callback");
        if (putHeader !== null && putHeader !== "") requestMockOverride.putStatus = normalizeMockStatus(putHeader);
        if (cbHeader !== null && cbHeader !== "") requestMockOverride.callback = normalizeMockStatus(cbHeader);
      }
      const tokenResult = await verifyUploadToken(uploadToken, uploadId, payloadSize);
      if (!tokenResult.ok) {
        console.log("[publish] token invalid");
        await putStatus(uploadId, "failed", "token_invalid", requestMockOverride.putStatus);
        return new Response(
          JSON.stringify({ code: "token_invalid", message: "Invalid or expired token" }),
          { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      console.log("[publish] token ok");
      const dataItemResult = await validateDataItem(signedDataItem, uploadId);
      if (!dataItemResult.ok) {
        console.log("[publish] data item invalid");
        await putStatus(uploadId, "failed", "signature_invalid", requestMockOverride.putStatus);
        return new Response(
          JSON.stringify({ code: "signature_invalid", message: "Invalid Data Item or Upload-Id" }),
          { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      console.log("[publish] data item ok");
      await putStatus(uploadId, "queued_for_publish", undefined, requestMockOverride.putStatus);
      console.log("[publish] status updated");
      const itemId = dataItemResult.ok ? dataItemResult.itemId : undefined;
      const signedBytes = Uint8Array.from(
        atob(signedDataItem.replace(/-/g, "+").replace(/_/g, "/")),
        (c) => c.charCodeAt(0)
      );
      void (async () => {
        try {
          const privateKey = await loadArweavePrivateKey();
          const result = await bundleAndPublish(signedBytes, arweave, privateKey);
          if ("bundleTxId" in result) {
            await postCallback(uploadId, itemId, result.bundleTxId, new Date().toISOString(), requestMockOverride.callback);
            console.log("[publish] publish ok");
            console.log("[publish] callback sent");
          } else {
            await putStatus(uploadId, "failed", "publish_failed", requestMockOverride.putStatus);
            console.log("[publish] publish failed");
          }
        } catch (e) {
          await putStatus(uploadId, "failed", "publish_failed", requestMockOverride.putStatus);
          console.log("[publish] publish failed");
        }
      })();
      return new Response(
        JSON.stringify({ ack: true, status: "queued_for_publish" }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Upload file endpoint
    if (path.endsWith('/upload-file') && req.method === 'POST') {
      const formData = await req.formData()
      const file = formData.get('file') as File
      
      if (!file) {
        return new Response(
          JSON.stringify({ 
            success: false, 
            error: 'No file provided' 
          }),
          { 
            status: 400,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
      }

      const fileData = new Uint8Array(await file.arrayBuffer())
      const contentType = file.type || 'application/octet-stream'
      
      const transactionId = await uploadFile(fileData, contentType)
      
      return new Response(
        JSON.stringify({ 
          success: true, 
          transaction_id: transactionId,
          url: `https://arweave.net/${transactionId}`,
          filename: file.name,
          size: file.size,
          type: contentType
        }),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // 404 для неизвестных endpoints
    return new Response(
      JSON.stringify({ 
        success: false, 
        error: 'Endpoint not found' 
      }),
      { 
        status: 404,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )

  } catch (error) {
    console.error('[ArWeave Edge Function] Error:', error)
    
    // Безопасная обработка ошибки
    const errorMessage = error instanceof Error ? error.message : 'Internal server error'
    
    return new Response(
      JSON.stringify({ 
        success: false, 
        error: errorMessage
      }),
      { 
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
}

// Запуск HTTP-сервера только при прямом запуске файла (deno run / supabase functions serve).
// При импорте из тестов (deno test) index не является entry point — serve не вызывается.
const isMain = (import.meta as { main?: boolean }).main;
if (isMain && !Deno.env.get("SUPABASE_TEST")) {
  serve(handler);
}