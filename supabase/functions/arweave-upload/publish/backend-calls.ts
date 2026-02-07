/**
 * Вызовы Edge → Backend: PUT status, POST callback.
 * Authorization: Bearer EDGE_TO_BACKEND_SECRET.
 * При BACKEND_USE_MOCK=true реальный fetch не выполняется; код ответа задаётся env или per-request override.
 */

function isBackendMockEnabled(): boolean {
  const v = Deno.env.get("BACKEND_USE_MOCK");
  return v === "true" || v === "1" || (typeof v === "string" && v.toLowerCase() === "true");
}

/** Допустимые коды для мока: 200, 404, 409; иное или пусто → 200. */
export function normalizeMockStatus(value: string | number | undefined | null): 200 | 404 | 409 {
  if (value === 404 || value === 409) return value;
  if (value === 200) return 200;
  if (typeof value === "string") {
    const n = parseInt(value, 10);
    if (n === 404 || n === 409) return n;
  }
  return 200;
}

export async function putStatus(
  uploadId: string,
  status: string,
  failureCode?: string,
  requestMockPutStatus?: number
): Promise<void> {
  if (isBackendMockEnabled()) {
    const code = requestMockPutStatus !== undefined
      ? normalizeMockStatus(requestMockPutStatus)
      : normalizeMockStatus(Deno.env.get("BACKEND_MOCK_PUT_STATUS"));
    console.log("[publish] [mock] putStatus", { uploadId, status, failureCode, simulatedStatus: code });
    if (code === 404 || code === 409) {
      console.log("[publish] [mock] putStatus simulated", code);
    }
    return;
  }
  const baseUrl = Deno.env.get("BACKEND_URL");
  const secret = Deno.env.get("EDGE_TO_BACKEND_SECRET");
  if (!baseUrl || !secret) {
    console.warn("[publish] BACKEND_URL or EDGE_TO_BACKEND_SECRET not set; skipping putStatus");
    return;
  }
  const url = `${baseUrl.replace(/\/$/, "")}/v1/uploads/${uploadId}/status`;
  const body =
    status === "failed"
      ? JSON.stringify({ status, failure_code: failureCode })
      : JSON.stringify({ status });
  try {
    const res = await fetch(url, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${secret}`,
      },
      body,
    });
    if (!res.ok) {
      console.warn("[publish] putStatus failed:", res.status, await res.text());
    }
  } catch (e) {
    console.warn("[publish] putStatus network error:", e);
  }
}

export async function postCallback(
  uploadId: string,
  itemId: string | undefined,
  bundleTxId: string,
  publishedAt: string,
  requestMockCallback?: number
): Promise<void> {
  if (isBackendMockEnabled()) {
    const code = requestMockCallback !== undefined
      ? normalizeMockStatus(requestMockCallback)
      : normalizeMockStatus(Deno.env.get("BACKEND_MOCK_CALLBACK"));
    console.log("[publish] [mock] postCallback", { uploadId, itemId, bundleTxId, publishedAt, simulatedStatus: code });
    if (code === 404 || code === 409) {
      console.log("[publish] [mock] postCallback simulated", code);
    }
    return;
  }
  const baseUrl = Deno.env.get("BACKEND_URL");
  const secret = Deno.env.get("EDGE_TO_BACKEND_SECRET");
  if (!baseUrl || !secret) {
    console.warn("[publish] BACKEND_URL or EDGE_TO_BACKEND_SECRET not set; skipping postCallback");
    return;
  }
  const url = `${baseUrl.replace(/\/$/, "")}/v1/uploads/callback`;
  const body = JSON.stringify({
    upload_id: uploadId,
    item_id: itemId,
    bundle_tx_id: bundleTxId,
    published_at: publishedAt,
  });
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${secret}`,
      },
      body,
    });
    if (!res.ok) {
      console.warn("[publish] postCallback failed:", res.status, await res.text());
    }
  } catch (e) {
    console.warn("[publish] postCallback network error:", e);
  }
}
