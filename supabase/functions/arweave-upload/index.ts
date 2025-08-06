import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import Arweave from "https://esm.sh/arweave@1.15.7"
import { signTransaction } from "./arweave/compatible.ts";

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

// Основной обработчик
serve(async (req) => {
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
}) 