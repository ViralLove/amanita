/**
 * Вызовы Edge → Backend: PUT status, POST callback.
 * Authorization: Bearer EDGE_TO_BACKEND_SECRET.
 */

export async function putStatus(
  uploadId: string,
  status: string,
  failureCode?: string
): Promise<void> {
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
  publishedAt: string
): Promise<void> {
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
