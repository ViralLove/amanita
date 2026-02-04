/**
 * Arweave deep-hash для верификации Data Item (ANS-104).
 * blob: sha256(sha256("blob" + len) + sha256(data))
 * list: sha256("list" + len), then acc = sha256(acc || deepHash(item)) for each item.
 */

type DeepHashChunk = Uint8Array | DeepHashChunk[];

async function sha256(data: Uint8Array): Promise<Uint8Array> {
  const h = await crypto.subtle.digest("SHA-256", data);
  return new Uint8Array(h);
}

function utf8Encode(s: string): Uint8Array {
  return new TextEncoder().encode(s);
}

export async function deepHash(chunk: DeepHashChunk): Promise<Uint8Array> {
  if (chunk instanceof Uint8Array) {
    const tag = new Uint8Array(utf8Encode("blob").length + utf8Encode(String(chunk.length)).length);
    tag.set(utf8Encode("blob"), 0);
    tag.set(utf8Encode(String(chunk.length)), utf8Encode("blob").length);
    const tagHash = await sha256(tag);
    const dataHash = await sha256(chunk);
    const combined = new Uint8Array(tagHash.length + dataHash.length);
    combined.set(tagHash, 0);
    combined.set(dataHash, tagHash.length);
    return sha256(combined);
  }
  const list = chunk as DeepHashChunk[];
  const tag = new Uint8Array(utf8Encode("list").length + utf8Encode(String(list.length)).length);
  tag.set(utf8Encode("list"), 0);
  tag.set(utf8Encode(String(list.length)), utf8Encode("list").length);
  let acc = await sha256(tag);
  for (const item of list) {
    const itemHash = await deepHash(item);
    const combined = new Uint8Array(acc.length + itemHash.length);
    combined.set(acc, 0);
    combined.set(itemHash, acc.length);
    acc = await sha256(combined);
  }
  return acc;
}
