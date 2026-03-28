#!/usr/bin/env node
/**
 * Проверка, что URL Arweave открывается в браузере (Puppeteer).
 * Использование: node scripts/verify-arweave-url-puppeteer.mjs <URL>
 * URL обычно из вывода интеграционного теста: ARWEAVE_INTEGRATION_URL=https://arweave.net/...
 * Требует: npm install puppeteer (в папке arweave-upload или корне проекта).
 */

const url = process.argv[2] || process.env.ARWEAVE_INTEGRATION_VERIFY_URL;
if (!url || !url.startsWith("https://arweave.net/")) {
  console.error("Usage: node verify-arweave-url-puppeteer.mjs <https://arweave.net/...>");
  console.error("   or: ARWEAVE_INTEGRATION_VERIFY_URL=https://arweave.net/... node verify-arweave-url-puppeteer.mjs");
  process.exit(1);
}

async function main() {
  let puppeteer;
  try {
    puppeteer = await import("puppeteer");
  } catch (e) {
    console.error("Install puppeteer: npm install puppeteer");
    process.exit(1);
  }
  const ignoreCert = process.env.IGNORE_CERT_ERRORS === "1";
  const browser = await puppeteer.default.launch({
    headless: true,
    args: ignoreCert ? ["--ignore-certificate-errors"] : [],
  });
  try {
    const page = await browser.newPage();
    if (ignoreCert) await page.setBypassCSP(true);
    const res = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });
    const status = res?.status() ?? 0;
    const ok = status >= 200 && status < 400;
    console.log(ok ? "OK" : "FAIL", url, "status", status);
    if (!ok) process.exit(1);
  } finally {
    await browser.close();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
