import fs from "node:fs";
function parsePort(value, fallback) {
    const n = Number(value ?? fallback);
    if (!Number.isInteger(n) || n <= 0) {
        throw new Error("Invalid PORT value");
    }
    return n;
}
function parseJwkFromEnv() {
    const keyJson = process.env.ARWEAVE_PRIVATE_KEY;
    if (!keyJson) {
        return null;
    }
    try {
        const parsed = JSON.parse(keyJson);
        return parsed;
    }
    catch (error) {
        throw new Error(`Failed to parse ARWEAVE_PRIVATE_KEY: ${error.message}`);
    }
}
function parseJwkFromFile() {
    const filePath = process.env.ARWEAVE_PRIVATE_KEY_FILE;
    if (!filePath) {
        return null;
    }
    try {
        const content = fs.readFileSync(filePath, "utf8");
        const parsed = JSON.parse(content);
        return parsed;
    }
    catch (error) {
        throw new Error(`Failed to read ARWEAVE_PRIVATE_KEY_FILE: ${error.message}`);
    }
}
function loadJwk() {
    const fromEnv = parseJwkFromEnv();
    if (fromEnv) {
        return fromEnv;
    }
    const fromFile = parseJwkFromFile();
    if (fromFile) {
        return fromFile;
    }
    throw new Error("Missing Arweave key: set ARWEAVE_PRIVATE_KEY or ARWEAVE_PRIVATE_KEY_FILE");
}
export function loadConfig() {
    const protocolRaw = (process.env.ARWEAVE_PROTOCOL ?? "https").toLowerCase();
    if (protocolRaw !== "http" && protocolRaw !== "https") {
        throw new Error("ARWEAVE_PROTOCOL must be http or https");
    }
    const host = process.env.ARWEAVE_HOST ?? "arweave.net";
    const port = parsePort(process.env.PORT, 3000);
    const arPort = parsePort(process.env.ARWEAVE_PORT, protocolRaw === "https" ? 443 : 80);
    return {
        port,
        relayAuthToken: process.env.RELAY_AUTH_TOKEN,
        arweaveProtocol: protocolRaw,
        arweaveHost: host,
        arweavePort: arPort,
        jwk: loadJwk(),
    };
}
