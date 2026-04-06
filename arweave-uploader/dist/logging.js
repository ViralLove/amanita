import crypto from "node:crypto";

/** Стартовая/детальная диагностика env: включается только при LOG_LEVEL=DEBUG (без учёта регистра). */
export function isDebugLogEnabled() {
  const v = (process.env.LOG_LEVEL || "").trim().toLowerCase();
  return v === "debug";
}

export function logDebug(event, details) {
  if (!isDebugLogEnabled()) return;
  console.log(JSON.stringify({ level: "debug", event, ...details }));
}

export function sha256Hex(value) {
    return crypto.createHash("sha256").update(value, "utf8").digest("hex");
}
export function logInfo(event, details) {
    console.log(JSON.stringify({ level: "info", event, ...details }));
}
export function logWarn(event, details) {
    console.warn(JSON.stringify({ level: "warn", event, ...details }));
}
export function logError(event, details) {
    console.error(JSON.stringify({ level: "error", event, ...details }));
}
export function errorToMessage(error) {
    if (error instanceof Error) {
        return error.message;
    }
    return String(error);
}
