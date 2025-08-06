import { signArweaveTransaction } from "../crypto/arweave-rsa-pss.ts";

export async function signTransaction(
  arweave: any,
  transaction: any,
  privateKey: JsonWebKey
): Promise<void> {
  console.log("🔐 Используем RSA-PSS подпись ArWeave...");
  
  const signatureData = await transaction.getSignatureData();
  console.log("   Данные для подписи размер:", signatureData.length, "байт");

  // Используем RSA-PSS реализацию
  const { signature, transactionId } = await signArweaveTransaction(privateKey, signatureData);
  const signatureB64Url = arweave.utils.bufferTob64Url(signature);

  transaction.signature = signatureB64Url;
  console.log("✅ RSA-PSS подпись установлена:", signatureB64Url.substring(0, 20) + "...");

  // Устанавливаем правильный transaction ID
  transaction.id = transactionId;
  
  console.log("✅ Transaction ID установлен:", transactionId);
  console.log("   ID начинается с 'ar':", transactionId.startsWith('ar'));
}
