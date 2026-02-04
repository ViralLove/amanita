import { assertEquals } from "https://deno.land/std@0.168.0/testing/asserts.ts";
import { signArweaveTransaction } from "../crypto/arweave-rsa-pss.ts";

Deno.test("signArweaveTransaction returns signature and transactionId starting with ar", async () => {
  const keyPair = await crypto.subtle.generateKey(
    {
      name: "RSA-PSS",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true,
    ["sign"]
  );

  const jwk = await crypto.subtle.exportKey("jwk", keyPair.privateKey);
  const privateKey: JsonWebKey = {
    kty: jwk.kty!,
    n: jwk.n!,
    e: jwk.e!,
    d: jwk.d!,
    p: jwk.p,
    q: jwk.q,
    dp: jwk.dp,
    dq: jwk.dq,
    qi: jwk.qi,
  };

  const signatureData = new TextEncoder().encode("test signature data");
  const { signature, transactionId } = await signArweaveTransaction(
    privateKey,
    signatureData
  );

  assertEquals(signature instanceof Uint8Array, true);
  assertEquals(signature.length, 256);
  assertEquals(transactionId.startsWith("ar"), true);
});
