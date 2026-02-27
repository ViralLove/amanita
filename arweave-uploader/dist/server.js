import Fastify from "fastify";
import { randomUUID } from "node:crypto";
import { pathToFileURL } from "node:url";
import { ArweaveClient } from "./arweave-client.js";
import { isAuthorized } from "./auth.js";
import { loadConfig } from "./config.js";
import { errorToMessage, logError, logInfo, logWarn, sha256Hex } from "./logging.js";
import { putStatus, postCallback, normalizeMockStatus } from "./publish/backend-calls.js";
import { validateUploadBody } from "./validation.js";

function isBackendMockEnabled() {
  const v = process.env.BACKEND_USE_MOCK;
  return v === "true" || v === "1" || (typeof v === "string" && v.toLowerCase() === "true");
}

function computeRequestMockOverride(request) {
  if (!isBackendMockEnabled()) return null;
  const allowOverride = process.env.BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE === "true" || process.env.BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE === "1";
  const secretHeader = request.headers["x-backend-mock-secret"];
  const secretEnv = process.env.BACKEND_MOCK_TEST_SECRET;
  const allowed = allowOverride || (secretEnv && secretHeader === secretEnv);
  if (!allowed) return null;
  const putStatusRaw = request.headers["x-backend-mock-put-status"];
  const callbackRaw = request.headers["x-backend-mock-callback"];
  return {
    putStatus: putStatusRaw !== undefined ? normalizeMockStatus(putStatusRaw) : undefined,
    callback: callbackRaw !== undefined ? normalizeMockStatus(callbackRaw) : undefined,
  };
}
export function buildApp({ config, arweaveClient }) {
    const app = Fastify({ logger: false });
    if (!config.relayAuthToken) {
        logWarn("relay.auth.disabled", {
            message: "RELAY_AUTH_TOKEN is not set, endpoint is open",
        });
    }
    app.get("/health", async () => {
        return {
            ok: true,
            service: "arweave-uploader",
            version: "0.1.0",
        };
    });
    app.post("/upload-canonical-issue", async (request, reply) => {
        const requestId = randomUUID();
        const started = Date.now();
        if (!isAuthorized(request, reply, config.relayAuthToken)) {
            return;
        }
        try {
            const payload = validateUploadBody(request.body);
            const payloadLength = payload.data.length;
            const payloadSha256 = sha256Hex(payload.data);
            logInfo("upload.request.received", {
                requestId,
                path: "/upload-canonical-issue",
                payloadLength,
                payloadSha256,
            });
            const result = await arweaveClient.uploadCanonicalIssue(payload);
            const durationMs = Date.now() - started;
            logInfo("upload.arweave.response", {
                requestId,
                txId: result.transactionId,
                arweaveStatus: result.status,
                arweaveStatusText: result.statusText,
                durationMs,
            });
            if (result.status >= 400) {
                const response = {
                    success: false,
                    code: "ARWEAVE_POST_FAILED",
                    message: "Arweave rejected transaction",
                };
                reply.code(502).send(response);
                return;
            }
            const success = {
                success: true,
                transaction_id: result.transactionId,
                url: `https://arweave.net/${result.transactionId}`,
            };
            reply.code(200).send(success);
        }
        catch (error) {
            const message = errorToMessage(error);
            logError("upload.failed", {
                requestId,
                error: message,
            });
            const isValidationError = message.startsWith("Invalid request body");
            reply.code(isValidationError ? 400 : 500).send({
                success: false,
                code: isValidationError ? "VALIDATION_ERROR" : "INTERNAL_ERROR",
                message: isValidationError ? message : "Internal server error",
            });
        }
    });
    app.post("/edge/v1/publish", async (request, reply) => {
        const requestMockOverride = computeRequestMockOverride(request);
        let body;
        try {
            body = typeof request.body === "object" ? request.body : JSON.parse(request.body || "{}");
        } catch {
            reply.code(400).send({ code: "invalid_body", message: "Invalid JSON body" });
            return;
        }
        const uploadId = body.upload_id;
        if (!uploadId || typeof uploadId !== "string") {
            reply.code(400).send({ code: "missing_upload_id", message: "upload_id is required" });
            return;
        }
        await putStatus(uploadId, "queued_for_publish", undefined, requestMockOverride?.putStatus);
        const publishedAt = new Date().toISOString();
        await postCallback(uploadId, body.item_id, body.bundle_tx_id ?? "dummy-tx-id", publishedAt, requestMockOverride?.callback);
        reply.code(200).send({ ack: true, status: "queued_for_publish" });
    });
    return app;
}
export async function startServer() {
    const config = loadConfig();
    const arweaveClient = new ArweaveClient(config);
    const app = buildApp({ config, arweaveClient });
    await app.listen({ host: "0.0.0.0", port: config.port });
    logInfo("server.started", {
        port: config.port,
        arweaveHost: config.arweaveHost,
        arweaveProtocol: config.arweaveProtocol,
        arweavePort: config.arweavePort,
    });
}
const isEntrypoint = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isEntrypoint) {
    startServer().catch((error) => {
        logError("server.start.failed", { error: errorToMessage(error) });
        process.exit(1);
    });
}
