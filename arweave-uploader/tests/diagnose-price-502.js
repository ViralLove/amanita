/**
 * Диагностика 502: один и тот же URL в браузере даёт 200, из Node (arweave lib) — 502.
 * Проверяем: обычный fetch из Node vs fetch с User-Agent браузера.
 * Запуск: node tests/diagnose-price-502.js
 */

const URL = "https://arweave.net/price/737";
const BROWSER_UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

async function run() {
  console.log("GET", URL);
  console.log("");

  // 1) fetch без кастомных заголовков (дефолтный Node/fetch UA)
  try {
    const r1 = await fetch(URL, { method: "GET" });
    const body1 = await r1.text();
    console.log("1) fetch() без User-Agent:");
    console.log("   Status:", r1.status, r1.statusText);
    console.log("   Body (first 80 chars):", body1.slice(0, 80));
    console.log("");
  } catch (e) {
    console.log("1) fetch() без User-Agent: ERROR", e.message);
    console.log("");
  }

  // 2) fetch с браузерным User-Agent
  try {
    const r2 = await fetch(URL, {
      method: "GET",
      headers: { "User-Agent": BROWSER_UA },
    });
    const body2 = await r2.text();
    console.log("2) fetch() с User-Agent (Chrome):");
    console.log("   Status:", r2.status, r2.statusText);
    console.log("   Body (first 80 chars):", body2.slice(0, 80));
    console.log("");
  } catch (e) {
    console.log("2) fetch() с User-Agent: ERROR", e.message);
    console.log("");
  }

  console.log("Вывод: если (1) 502 и (2) 200 — CDN77 различает по User-Agent.");
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
