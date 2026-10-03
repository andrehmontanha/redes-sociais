import { createHash } from "node:crypto";

// Impressão digital do post — a trava de aprovação. Mesmo algoritmo do
// `fila.py impressao()` do estúdio: sha256 de cada mídia (na ordem, capa por
// último) seguido de `campo=valor` com o valor formatado como o str() do Python.
// Assim a aprovação dada no estúdio confere byte a byte aqui, e qualquer mudança
// na mídia, na legenda, no tipo ou no horário exige um novo "ok".

export type CamposImpressao = {
  tipo: string;
  legenda: string;
  agendado_para: string | null;
  thumb_offset_ms: number | null;
  avatares: string[];
};

function reprPy(s: string): string {
  const aspas = s.includes("'") && !s.includes('"') ? '"' : "'";
  const corpo = s.replace(/\\/g, "\\\\").replace(new RegExp(aspas, "g"), `\\${aspas}`);
  return `${aspas}${corpo}${aspas}`;
}

/** str() do Python para os tipos que aparecem no post.json. */
export function strPy(v: unknown): string {
  if (v === null || v === undefined) return "None";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (Array.isArray(v)) return `[${v.map((x) => (typeof x === "string" ? reprPy(x) : strPy(x))).join(", ")}]`;
  return String(v);
}

export function sha256(dados: Uint8Array | string): string {
  return createHash("sha256").update(dados).digest("hex");
}

export function impressao(hashesDasMidias: string[], campos: CamposImpressao): string {
  const h = createHash("sha256");
  for (const s of hashesDasMidias) h.update(s);
  for (const campo of ["tipo", "legenda", "agendado_para", "thumb_offset_ms", "avatares"] as const) {
    h.update(`${campo}=${strPy(campos[campo])}`);
  }
  return h.digest("hex");
}
