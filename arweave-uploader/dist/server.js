import Fastify from "fastify";
import { randomUUID } from "node:crypto";
import { pathToFileURL } from "node:url";
import { ArweaveClient } from "./arweave-client.js";
import { isAuthorized } from "./auth.js";
import { loadConfig } from "./config.js";
import { errorToMessage, logError, logInfo, logWarn, sha256Hex } from "./logging.js";
import { putStatus, postCallback, normalizeMockStatus } from "./publish/backend-calls.js";
import { bundleAndPublish } from "./publish/bundle-publish.js";
import { validateDataItem } from "./publish/validate-data-item.js";
import { verifyUploadToken } from "./publish/validate-token.js";
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
            version: "0.2.0",
        };
    });
    app.post("/v1/crystalize", async (request, reply) => {
        const requestMockOverride = computeRequestMockOverride(request);
        let body;
        try {
            body = typeof request.body === "object" ? request.body : JSON.parse(request.body || "{}");
        } catch {
            reply.code(400).send({ code: "invalid_body", message: "Invalid JSON body" });
            return;
        }
        const uploadId = body.upload_id;
        const uploadToken = body.upload_token;
        const signedDataItem = body.signed_data_item;
        const payloadSize = body.payload_size;

        logInfo("publish.request.received", { uploadId });

        if (!uploadId || typeof uploadId !== "string") {
            reply.code(400).send({ code: "missing_field", message: "upload_id is required" });
            return;
        }
        if (!uploadToken || typeof uploadToken !== "string") {
            reply.code(400).send({ code: "missing_field", message: "upload_token is required" });
            return;
        }
        if (!signedDataItem || typeof signedDataItem !== "string") {
            reply.code(400).send({ code: "missing_field", message: "signed_data_item is required" });
            return;
        }
        if (payloadSize === undefined || payloadSize === null || typeof payloadSize !== "number" || payloadSize < 0) {
            reply.code(400).send({ code: "missing_field", message: "payload_size is required and must be a non-negative number" });
            return;
        }

        const tokenResult = await verifyUploadToken(uploadToken, uploadId, payloadSize);
        if (!tokenResult.ok) {
            logInfo("publish.token_invalid", { uploadId });
            await putStatus(uploadId, "failed", "token_invalid", requestMockOverride?.putStatus);
            reply.code(401).send({ code: "token_invalid", message: "Invalid or expired upload token" });
            return;
        }

        const dataItemResult = await validateDataItem(signedDataItem, uploadId);
        if (!dataItemResult.ok) {
            logInfo("publish.data_item_invalid", { uploadId });
            await putStatus(uploadId, "failed", "signature_invalid", requestMockOverride?.putStatus);
            reply.code(400).send({ code: "signature_invalid", message: "Data item signature or Upload-Id tag invalid" });
            return;
        }

        const itemId = dataItemResult.itemId;
        await putStatus(uploadId, "queued_for_publish", undefined, requestMockOverride?.putStatus);

        const signedDataItemBytes = Buffer.from(
            signedDataItem.replace(/-/g, "+").replace(/_/g, "/"),
            "base64"
        );
        const bundleResult = await bundleAndPublish(signedDataItemBytes, arweaveClient);
        if (bundleResult.error) {
            logWarn("publish.bundle_failed", { uploadId, error: bundleResult.error });
            await putStatus(uploadId, "failed", "publish_failed", requestMockOverride?.putStatus);
            reply.code(502).send({ code: "publish_failed", message: "Bundle publish to Arweave failed" });
            return;
        }

        logInfo("publish.bundle_success", { uploadId, bundleTxId: bundleResult.bundleTxId });
        const publishedAt = new Date().toISOString();
        await postCallback(uploadId, itemId, bundleResult.bundleTxId, publishedAt, requestMockOverride?.callback);
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
