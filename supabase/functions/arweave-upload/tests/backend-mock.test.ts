/**
 * Тесты режима мока Backend (BACKEND_USE_MOCK, per-request override).
 * Проверяют: при включённом моке putStatus/postCallback не вызывают fetch;
 * симулированный код (200/404/409) из env/заголовков; при выключенном моке — вызов fetch.
 */

import { assertEquals } from "https://deno.land/std@0.168.0/testing/asserts.ts";
import { handler } from "../index.ts";

type FetchCall = { url: string; method: string; body: string };
let fetchCalls: FetchCall[] = [];
const originalFetch = globalThis.fetch;

function mockFetch() {
  fetchCalls = [];
  globalThis.fetch = (input: string | URL | Request, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof Request ? input.url : (input as URL).href;
    const method = (init?.method ?? (input instanceof Request ? input.method : "GET")) as string;
    const body = (init?.body ?? (input instanceof Request ? input.body : undefined)) as string | undefined;
    fetchCalls.push({ url: String(url), method, body: body ?? "" });
    return Promise.resolve(new Response(null, { status: 204 }));
  };
}

function restoreFetch() {
  globalThis.fetch = originalFetch;
}

/** Перехват console.log: сохраняет аргументы в массив. Вернуть функцию восстановления. */
function captureConsole(): { logCalls: unknown[][]; restore: () => void } {
  const logCalls: unknown[][] = [];
  const originalLog = console.log;
  console.log = (...args: unknown[]) => {
    logCalls.push([...args]);
    originalLog.apply(console, args);
  };
  return {
    logCalls,
    restore: () => {
      console.log = originalLog;
    },
  };
}

/** Из перехваченного лога извлечь simulatedStatus из вызова putStatus ([mock] putStatus). */
function getPutStatusSimulatedStatus(logCalls: unknown[][]): number | undefined {
  for (const args of logCalls) {
    if (args[0] && String(args[0]).includes("[mock] putStatus") && args[1] && typeof args[1] === "object" && "simulatedStatus" in args[1]) {
      return (args[1] as { simulatedStatus: number }).simulatedStatus;
    }
  }
  return undefined;
}

function createPublishRequest(
  body: Record<string, unknown>,
  headers: Record<string, string> = {}
): Request {
  const path = "https://x/functions/v1/arweave-upload/edge/v1/publish";
  return new Request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
}

Deno.test("backend mock: BACKEND_USE_MOCK=true -> putStatus не вызывает fetch (401 token_invalid)", async () => {
  Deno.env.set("BACKEND_USE_MOCK", "true");
  mockFetch();
  try {
    const req = createPublishRequest({
      upload_token: "invalid.jwt",
      upload_id: "upload-123",
      signed_data_item: "YQ==",
      payload_size: 0,
    });
    const res = await handler(req);
    assertEquals(res.status, 401);
    const json = await res.json();
    assertEquals(json.code, "token_invalid");
    assertEquals(fetchCalls.length, 0);
  } finally {
    restoreFetch();
    Deno.env.delete("BACKEND_USE_MOCK");
  }
});

Deno.test("backend mock: override разрешён через BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE, значение из заголовка в логе", async () => {
  Deno.env.set("BACKEND_USE_MOCK", "true");
  Deno.env.set("BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE", "true");
  mockFetch();
  const { logCalls, restore: restoreLog } = captureConsole();
  try {
    const req = createPublishRequest(
      {
        upload_token: "invalid.jwt",
        upload_id: "upload-123",
        signed_data_item: "YQ==",
        payload_size: 0,
      },
      { "X-Backend-Mock-Put-Status": "409" }
    );
    const res = await handler(req);
    assertEquals(res.status, 401);
    assertEquals(fetchCalls.length, 0);
    assertEquals(getPutStatusSimulatedStatus(logCalls), 409);
  } finally {
    restoreLog();
    restoreFetch();
    Deno.env.delete("BACKEND_USE_MOCK");
    Deno.env.delete("BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE");
  }
});

Deno.test("backend mock: override разрешён через X-Backend-Mock-Secret, значение из заголовка в логе", async () => {
  Deno.env.set("BACKEND_USE_MOCK", "true");
  Deno.env.set("BACKEND_MOCK_TEST_SECRET", "test-secret-123");
  mockFetch();
  const { logCalls, restore: restoreLog } = captureConsole();
  try {
    const req = createPublishRequest(
      {
        upload_token: "invalid.jwt",
        upload_id: "upload-123",
        signed_data_item: "YQ==",
        payload_size: 0,
      },
      {
        "X-Backend-Mock-Secret": "test-secret-123",
        "X-Backend-Mock-Put-Status": "404",
      }
    );
    const res = await handler(req);
    assertEquals(res.status, 401);
    assertEquals(fetchCalls.length, 0);
    assertEquals(getPutStatusSimulatedStatus(logCalls), 404);
  } finally {
    restoreLog();
    restoreFetch();
    Deno.env.delete("BACKEND_USE_MOCK");
    Deno.env.delete("BACKEND_MOCK_TEST_SECRET");
  }
});

Deno.test("backend mock: без override секрет не совпадает -> заголовки игнорируются, используется env (simulatedStatus из env)", async () => {
  Deno.env.set("BACKEND_USE_MOCK", "true");
  Deno.env.set("BACKEND_MOCK_TEST_SECRET", "right-secret");
  Deno.env.set("BACKEND_MOCK_PUT_STATUS", "404");
  mockFetch();
  const { logCalls, restore: restoreLog } = captureConsole();
  try {
    const req = createPublishRequest(
      {
        upload_token: "invalid.jwt",
        upload_id: "upload-123",
        signed_data_item: "YQ==",
        payload_size: 0,
      },
      { "X-Backend-Mock-Secret": "wrong-secret", "X-Backend-Mock-Put-Status": "409" }
    );
    const res = await handler(req);
    assertEquals(res.status, 401);
    assertEquals(fetchCalls.length, 0);
    const status = getPutStatusSimulatedStatus(logCalls);
    assertEquals(status, 404);
  } finally {
    restoreLog();
    restoreFetch();
    Deno.env.delete("BACKEND_USE_MOCK");
    Deno.env.delete("BACKEND_MOCK_TEST_SECRET");
    Deno.env.delete("BACKEND_MOCK_PUT_STATUS");
  }
});

Deno.test("backend mock: мок выключен -> putStatus вызывает fetch к Backend", async () => {
  Deno.env.delete("BACKEND_USE_MOCK");
  Deno.env.set("BACKEND_URL", "https://backend.test");
  Deno.env.set("EDGE_TO_BACKEND_SECRET", "test-secret");
  mockFetch();
  try {
    const req = createPublishRequest({
      upload_token: "invalid.jwt",
      upload_id: "upload-123",
      signed_data_item: "YQ==",
      payload_size: 0,
    });
    const res = await handler(req);
    assertEquals(res.status, 401);
    assertEquals(fetchCalls.length, 1);
    const putCall = fetchCalls.find((c) => c.method === "PUT" && c.body.includes("token_invalid"));
    assertEquals(!!putCall, true);
    assertEquals(putCall!.url.includes("/uploads/") && putCall!.url.includes("status"), true);
  } finally {
    restoreFetch();
    Deno.env.delete("BACKEND_URL");
    Deno.env.delete("EDGE_TO_BACKEND_SECRET");
  }
});

Deno.test("backend mock: мок 200 по умолчанию (без override)", async () => {
  Deno.env.set("BACKEND_USE_MOCK", "true");
  mockFetch();
  const { logCalls, restore: restoreLog } = captureConsole();
  try {
    const req = createPublishRequest({
      upload_token: "invalid.jwt",
      upload_id: "upload-123",
      signed_data_item: "YQ==",
      payload_size: 0,
    });
    const res = await handler(req);
    assertEquals(res.status, 401);
    assertEquals(fetchCalls.length, 0);
    const status = getPutStatusSimulatedStatus(logCalls);
    assertEquals(status, 200);
  } finally {
    restoreLog();
    restoreFetch();
    Deno.env.delete("BACKEND_USE_MOCK");
  }
});

Deno.test("backend mock: мок 404 из env (BACKEND_MOCK_PUT_STATUS=404)", async () => {
  Deno.env.set("BACKEND_USE_MOCK", "true");
  Deno.env.set("BACKEND_MOCK_PUT_STATUS", "404");
  mockFetch();
  const { logCalls, restore: restoreLog } = captureConsole();
  try {
    const req = createPublishRequest({
      upload_token: "invalid.jwt",
      upload_id: "upload-123",
      signed_data_item: "YQ==",
      payload_size: 0,
    });
    const res = await handler(req);
    assertEquals(res.status, 401);
    assertEquals(fetchCalls.length, 0);
    const status = getPutStatusSimulatedStatus(logCalls);
    assertEquals(status, 404);
  } finally {
    restoreLog();
    restoreFetch();
    Deno.env.delete("BACKEND_USE_MOCK");
    Deno.env.delete("BACKEND_MOCK_PUT_STATUS");
  }
});

Deno.test("backend mock: мок 409 из заголовка (override разрешён)", async () => {
  Deno.env.set("BACKEND_USE_MOCK", "true");
  Deno.env.set("BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE", "true");
  mockFetch();
  const { logCalls, restore: restoreLog } = captureConsole();
  try {
    const req = createPublishRequest(
      {
        upload_token: "invalid.jwt",
        upload_id: "upload-123",
        signed_data_item: "YQ==",
        payload_size: 0,
      },
      { "X-Backend-Mock-Put-Status": "409" }
    );
    const res = await handler(req);
    assertEquals(res.status, 401);
    assertEquals(fetchCalls.length, 0);
    const status = getPutStatusSimulatedStatus(logCalls);
    assertEquals(status, 409);
  } finally {
    restoreLog();
    restoreFetch();
    Deno.env.delete("BACKEND_USE_MOCK");
    Deno.env.delete("BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE");
  }
});
