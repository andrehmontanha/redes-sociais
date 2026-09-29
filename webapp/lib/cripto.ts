import { createCipheriv, createDecipheriv, createHash, randomBytes, timingSafeEqual } from "node:crypto";

// AES-256-GCM com chave derivada de SESSAO_SEGREDO. Usado para os cookies: o
// navegador guarda um blob opaco, e o token do Instagram nunca chega ao JavaScript
// da página (cookie httpOnly) nem aparece em texto claro em lugar nenhum.

function chave(segredo: string, finalidade: string) {
  return createHash("sha256").update(`${segredo}:${finalidade}`).digest();
}

export function selar(dados: unknown, segredo: string, finalidade: string): string {
  const iv = randomBytes(12);
  const cifra = createCipheriv("aes-256-gcm", chave(segredo, finalidade), iv);
  const corpo = Buffer.concat([cifra.update(JSON.stringify(dados), "utf8"), cifra.final()]);
  return Buffer.concat([iv, cifra.getAuthTag(), corpo]).toString("base64url");
}

export function abrir<T>(selado: string | undefined, segredo: string, finalidade: string): T | null {
  if (!selado) return null;
  try {
    const bruto = Buffer.from(selado, "base64url");
    const decifra = createDecipheriv("aes-256-gcm", chave(segredo, finalidade), bruto.subarray(0, 12));
    decifra.setAuthTag(bruto.subarray(12, 28));
    const texto = Buffer.concat([decifra.update(bruto.subarray(28)), decifra.final()]).toString("utf8");
    return JSON.parse(texto) as T;
  } catch {
    return null; // adulterado, segredo trocado ou formato antigo: trata como ausente
  }
}

export function iguais(a: string, b: string): boolean {
  const x = createHash("sha256").update(a).digest();
  const y = createHash("sha256").update(b).digest();
  return timingSafeEqual(x, y);
}
