/**
 * Интеграционный тест: реальное соединение с Arweave, реальный ключ, минимальный контент.
 * Production-путь: signTransaction (RSA-PSS из arweave/compatible.ts), ключ из ARWEAVE_PRIVATE_KEY_FILE.
 *
 * Запуск из папки arweave-upload:
 *   deno task test:integration:real   — подхватит ARWEAVE_PRIVATE_KEY_FILE из .env в корне arweave-upload
 *   или: ARWEAVE_PRIVATE_KEY_FILE=./arweave-wallet.json deno test tests/integration-arweave-real.test.ts --allow-env --allow-read --allow-net --no-check --unsafely-ignore-certificate-errors
 *
 * Результат: печатает ARWEAVE_INTEGRATION_URL=https://arweave.net/{id}.
 * Верификация: ARWEAVE_INTEGRATION_VERIFY_URL=https://arweave.net/{id} deno task test:integration:verify
 */
/// <reference path="../deno_shim.d.ts" />
import { assertEquals } from "https://deno.land/std@0.168.0/testing/asserts.ts";
import Arweave from "npm:arweave@1.15.7";
import { signTransaction } from "../arweave/compatible.ts";

const MINIMAL_CONTENT = "888";

/** Подгрузить .env из корня arweave-upload (../.env относительно этого файла), если переменная ещё не задана. */
async function loadEnvIfNeeded(): Promise<void> {
  if (Deno.env.get("ARWEAVE_PRIVATE_KEY_FILE")) return;
  const envUrl = new URL("../.env", import.meta.url);
  try {
    const content = await Deno.readTextFile(envUrl);
    for (const line of content.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eq = trimmed.indexOf("=");
      if (eq <= 0) continue;
      const key = trimmed.slice(0, eq).trim();
      let value = trimmed.slice(eq + 1).trim();
      if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'")))
        value = value.slice(1, -1);
      if (key) Deno.env.set(key, value);
    }
  } catch {
    // .env не найден или не читается — оставляем как есть
  }
}

await loadEnvIfNeeded();

function getKeyFilePath(): string | undefined {
  return Deno.env.get("ARWEAVE_PRIVATE_KEY_FILE");
}

async function loadPrivateKey(): Promise<JsonWebKey> {
  let path = getKeyFilePath();
  if (!path) {
    throw new Error(
      "ARWEAVE_PRIVATE_KEY_FILE required. Задайте в .env в корне arweave-upload или в окружении."
    );
  }
  // Относительный путь — от корня arweave-upload (где лежит .env)
  const keyUrl =
    path.startsWith("/") || /^[A-Za-z]:/.test(path)
      ? path
      : new URL(path.replace(/^\.\//, ""), new URL("..", import.meta.url));
  const raw = await Deno.readTextFile(keyUrl);
  const parsed = JSON.parse(raw) as JsonWebKey;
  const required = ["kty", "e", "n", "d"];
  for (const f of required) {
    if (!(f in parsed) || !parsed[f as keyof JsonWebKey]) {
      throw new Error(`Invalid key: missing ${f}`);
    }
  }
  return parsed;
}

Deno.test({
  name: "integration: real Arweave upload with real key, minimal content",
  ignore: !getKeyFilePath(),
  fn: async () => {
    const privateKey = await loadPrivateKey();
    const arweave = Arweave.init({
      host: "arweave.net",
      port: 443,
      protocol: "https",
      timeout: 20000,
      logging: false,
    });

    const transaction = await arweave.createTransaction(
      { data: new TextEncoder().encode(MINIMAL_CONTENT) },
      privateKey as any
    );
    transaction.addTag("Content-Type", "text/plain");
    transaction.addTag("X-Integration-Test", "arweave-upload");

    await signTransaction(arweave, transaction, privateKey);

    assertEquals(transaction.id.startsWith("ar"), true);
    assertEquals(typeof transaction.signature, "string");
    assertEquals(transaction.signature.length > 0, true);

    const response = await arweave.transactions.post(transaction);
    assertEquals(
      response.status === 200 || response.status === 202,
      true,
      `post failed: ${response.status} ${response.statusText}`
    );

    const url = `https://arweave.net/${transaction.id}`;
    console.log("ARWEAVE_INTEGRATION_URL=" + url);
    console.log("ARWEAVE_INTEGRATION_TX_ID=" + transaction.id);

    assertEquals(transaction.id.startsWith("ar"), true);
  },
  sanitizeOps: false,
  sanitizeResources: false,
});

/** Верификация: по URL проверяем, что страница Arweave отвечает (для проверки в браузере / Puppeteer). */
Deno.test({
  name: "integration: verify Arweave URL is reachable (fetch)",
  ignore: !Deno.env.get("ARWEAVE_INTEGRATION_VERIFY_URL"),
  fn: async () => {
    const url = Deno.env.get("ARWEAVE_INTEGRATION_VERIFY_URL")!;
    assertEquals(url.startsWith("https://arweave.net/"), true);
    const res = await fetch(url, { redirect: "follow" });
    const ok = res.status >= 200 && res.status < 400;
    assertEquals(ok, true, `URL must respond: ${res.status} ${res.statusText}`);
    const text = await res.text();
    assertEquals(text.length > 0, true);
    console.log("ARWEAVE_VERIFY_OK=" + url + " status=" + res.status);
  },
  sanitizeOps: false,
  sanitizeResources: false,
});
