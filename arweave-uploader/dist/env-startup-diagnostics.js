/**
 * Стартовая сводка env при LOG_LEVEL=DEBUG: что задано и проходит ли парсинг, без значений секретов и ключей.
 */

import { isDebugLogEnabled, logDebug } from "./logging.js";
import { diagnoseJwtPublicKeyEnv } from "./publish/validate-token.js";

function isTruthyEnv(name) {
  const v = process.env[name];
  return typeof v === "string" && v.trim().length > 0;
}

function backendMockEnabled() {
  const v = process.env.BACKEND_USE_MOCK;
  return v === "true" || v === "1" || (typeof v === "string" && v.toLowerCase() === "true");
}

/**
 * Сводка по интеграции с bot (без секретов): для `server.started` и DEBUG-дампа.
 */
export function getBackendStartupSummary() {
  const backendUrlRaw = process.env.BACKEND_URL?.trim() || "";
  const backendUrlSet = backendUrlRaw.length > 0;
  const backendBaseUrl = backendUrlSet
    ? backendUrlRaw.replace(/\/$/, "")
    : null;
  const backendSecretSet = isTruthyEnv("NODE_AUTH_TOKEN");
  const backendMock = backendMockEnabled();
  return {
    BACKEND_USE_MOCK: backendMock,
    BACKEND_URL_set: backendUrlSet,
    ...(backendBaseUrl ? { BACKEND_URL: backendBaseUrl } : {}),
    NODE_AUTH_TOKEN_set: backendSecretSet,
    backendCallbacksConfigured: backendMock || (backendUrlSet && backendSecretSet),
  };
}

/**
 * @param {object} config — результат `loadConfig()` (port, jwk, arweave*, relayAuthToken)
 */
export function logStartupEnvDiagnostics(config) {
  if (!isDebugLogEnabled()) return;

  const useRealArweave =
    process.env.USE_REAL_ARWEAVE === "true" || process.env.USE_REAL_ARWEAVE === "1";

  const arweaveKeySource = process.env.ARWEAVE_PRIVATE_KEY?.trim()
    ? "ARWEAVE_PRIVATE_KEY"
    : "ARWEAVE_PRIVATE_KEY_FILE";

  const jwt = diagnoseJwtPublicKeyEnv();
  const jwtHasInline = !!(process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY?.trim());
  const jwtHasFile = !!(process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE?.trim());

  const backend = getBackendStartupSummary();
  const backendUrlSet = backend.BACKEND_URL_set;
  const backendSecretSet = backend.NODE_AUTH_TOKEN_set;
  const backendMock = backend.BACKEND_USE_MOCK;

  const issues = [];
  if (!jwtHasInline && !jwtHasFile) {
    issues.push(
      "UPLOAD_TOKEN_JWT_PUBLIC_KEY / _FILE not set — POST /v1/crystalize will return token_invalid until a public key is configured"
    );
  } else if (jwtHasFile && !jwtHasInline && jwt.configured && !jwt.rawLoaded) {
    issues.push(
      "UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE: file missing or unreadable — crystalize will fail (token_invalid)"
    );
  } else if (jwt.rawLoaded && !jwt.parseOk) {
    issues.push(
      "UPLOAD_TOKEN_JWT_PUBLIC_KEY: PEM/JWK parse failed — crystalize will return token_invalid"
    );
  }
  if (!backendMock && backendUrlSet && !backendSecretSet) {
    issues.push(
      "BACKEND_URL set but NODE_AUTH_TOKEN is empty — putStatus/postCallback will be skipped (publish.backend.skip)"
    );
  }
  if (!backendMock && !backendUrlSet && backendSecretSet) {
    issues.push(
      "NODE_AUTH_TOKEN set but BACKEND_URL is empty — putStatus/postCallback will be skipped"
    );
  }

  logDebug("server.env.snapshot", {
    LOG_LEVEL: process.env.LOG_LEVEL ?? "(unset)",
    PORT: config.port,
    USE_REAL_ARWEAVE: useRealArweave,
    ARWEAVE_PROTOCOL: config.arweaveProtocol,
    ARWEAVE_HOST: config.arweaveHost,
    ARWEAVE_PORT: config.arweavePort,
    arweavePrivateKeySource: arweaveKeySource,
    arweaveJwkKty: config.jwk?.kty ?? "unknown",
    RELAY_AUTH_TOKEN_set: !!config.relayAuthToken,
    uploadTokenJwt: {
      source: jwt.source,
      configured: jwt.configured,
      rawLoaded: jwt.rawLoaded,
      parseOk: jwt.parseOk,
      ...(jwt.asymmetricKeyType ? { asymmetricKeyType: jwt.asymmetricKeyType } : {}),
    },
    backend: {
      ...backend,
      BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE: isTruthyEnv("BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE"),
      BACKEND_MOCK_TEST_SECRET_set: isTruthyEnv("BACKEND_MOCK_TEST_SECRET"),
    },
    issues,
  });
}
