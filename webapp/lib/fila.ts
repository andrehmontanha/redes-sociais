import { impressao, sha256, type CamposImpressao } from "./impressao.ts";

// Fila de publicação no servidor. O estúdio (motor em Python) gera o criativo e
// envia; aqui ele espera a aprovação humana, é publicado no horário pelo
// agendador e guarda o resultado. A trava é a mesma do estúdio: a aprovação
// grava a impressão digital, e a publicação recalcula sobre os bytes do Blob.

export type Tipo = "feed" | "carrossel" | "reel" | "story";
export type Status =
  | "aguardando_aprovacao"
  | "aprovado"
  | "publicando"
  | "publicado"
  | "rejeitado"
  | "erro";

export const LIMITES: Record<Tipo, [number, number]> = { feed: [1, 1], carrossel: [2, 10], reel: [1, 1], story: [1, 1] };

export type Midia = { url: string; pathname: string; nome: string; video: boolean; sha256: string };

export type Aprovacao = {
  por: string;
  em: string;
  impressao: string;
  origem: "painel" | "estudio";
  mensagem?: string | null;
};

export type Item = CamposImpressao & {
  id: string;
  cliente: string;
  tipo: Tipo;
  status: Status;
  criadoEm: string;
  midias: Midia[];
  capa: Midia | null;
  impressao: string;
  aprovacao: Aprovacao | null;
  rejeicao?: { por: string; em: string; motivo: string } | null;
  publicacao?: { filhos?: string[]; container?: string; iniciadoEm: string } | null;
  resultado?: { mediaId: string; permalink?: string; publicadoEm: string } | null;
  erro?: string | null;
  historico: { em: string; evento: string }[];
};

/** O que o motor manda. A mídia já está no Blob (upload direto com token curto). */
export type Envio = CamposImpressao & {
  nome: string;
  cliente: string;
  tipo: Tipo;
  midias: { url: string; pathname: string; nome: string }[];
  capa?: { url: string; pathname: string; nome: string } | null;
  aprovacao?: { por: string; em: string; impressao: string; mensagem?: string | null } | null;
};

const VIDEO = /\.(mp4|mov)$/i;
const IMAGEM = /\.(jpe?g)$/i;
const HANDLE = /^[a-z0-9._]{1,30}$/;

export const agora = () => new Date().toISOString();

export function idDoItem(cliente: string, nome: string) {
  return `${cliente}--${nome}`.replace(/[^a-z0-9._-]/gi, "_");
}

/** Validação do que chega do motor — mesmas regras do `fila.py criar`. */
export function validarEnvio(e: Envio): string[] {
  const erros: string[] = [];
  if (!HANDLE.test(e.cliente ?? "")) erros.push("cliente inválido");
  if (!/^[\w.-]{1,80}$/.test(e.nome ?? "")) erros.push("nome do item inválido");
  if (!(e.tipo in LIMITES)) return [...erros, `tipo inválido: ${e.tipo}`];
  const [min, max] = LIMITES[e.tipo];
  const n = e.midias?.length ?? 0;
  if (n < min || n > max) erros.push(`${e.tipo}: de ${min} a ${max} mídia(s), recebi ${n}`);
  for (const m of e.midias ?? []) {
    const video = VIDEO.test(m.nome);
    if (!video && !IMAGEM.test(m.nome)) erros.push(`formato não aceito pela API: ${m.nome} (use JPEG ou MP4)`);
    if (e.tipo === "reel" && !video) erros.push(`reel precisa de vídeo: ${m.nome}`);
    if (e.tipo === "feed" && video) erros.push(`feed precisa de imagem JPEG: ${m.nome}`);
    if (!m.pathname?.startsWith(`fila/${e.cliente}/`)) erros.push(`mídia fora da pasta do cliente: ${m.pathname}`);
  }
  if (typeof e.legenda !== "string") erros.push("legenda ausente");
  else {
    if (e.legenda.length > 2200) erros.push(`legenda com ${e.legenda.length} caracteres (máx. 2200)`);
    if ((e.legenda.match(/(?<!\w)#\w+/gu) ?? []).length > 30) erros.push("mais de 30 hashtags");
    if ((e.legenda.match(/(?<!\w)@[\w.]+/gu) ?? []).length > 20) erros.push("mais de 20 menções");
    if (e.tipo === "story" && e.legenda) erros.push("story não tem legenda na API");
  }
  if (e.agendado_para !== null && (typeof e.agendado_para !== "string" || !/[+-]\d\d:\d\d$|Z$/.test(e.agendado_para) || Number.isNaN(Date.parse(e.agendado_para)))) {
    erros.push("agendado_para precisa de data com fuso, ex.: 2026-10-03T12:00:00-03:00");
  }
  if (e.thumb_offset_ms !== null && !Number.isInteger(e.thumb_offset_ms)) erros.push("thumb_offset_ms inválido");
  // Avatar exige a verificação de consentimento do estúdio na hora de publicar —
  // esses posts continuam pela fila do estúdio, não por aqui.
  if (!Array.isArray(e.avatares) || e.avatares.length) erros.push("post com avatar digital é publicado pelo estúdio, não pelo webapp");
  if (e.aprovacao && (!e.aprovacao.por || e.aprovacao.por.trim().length < 2 || !e.aprovacao.impressao)) {
    erros.push("aprovação sem nome de quem aprovou ou sem impressão digital");
  }
  return erros;
}

export function camposDe(i: CamposImpressao): CamposImpressao {
  return {
    tipo: i.tipo,
    legenda: i.legenda,
    agendado_para: i.agendado_para,
    thumb_offset_ms: i.thumb_offset_ms,
    avatares: i.avatares,
  };
}

export function impressaoDoItem(hashes: string[], i: CamposImpressao) {
  return impressao(hashes, camposDe(i));
}

/** Baixa a mídia e devolve o sha256 dos bytes — nunca confia no hash de quem enviou. */
export async function hashDaUrl(url: string): Promise<string> {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`não consegui ler a mídia (${r.status}): ${url}`);
  return sha256(new Uint8Array(await r.arrayBuffer()));
}

/** Recalcula a impressão a partir dos bytes que estão no Blob agora. */
export async function impressaoAtual(item: Item): Promise<string> {
  const todas = [...item.midias, ...(item.capa ? [item.capa] : [])];
  const hashes = await Promise.all(todas.map((m) => hashDaUrl(m.url)));
  return impressaoDoItem(hashes, item);
}

export function midiaDe(m: { url: string; pathname: string; nome: string }, hash: string): Midia {
  return { url: m.url, pathname: m.pathname, nome: m.nome, video: VIDEO.test(m.nome), sha256: hash };
}

// ------------------------------------------------------------ transições puras

export type Acao =
  | { tipo: "aprovar"; por: string; mensagem?: string }
  | { tipo: "rejeitar"; por: string; motivo: string }
  | { tipo: "desaprovar"; por: string }
  | { tipo: "tentar_de_novo"; por: string };

/** Aplica uma decisão humana. Devolve o item novo ou um erro — nunca muda o original. */
export function aplicar(item: Item, acao: Acao, em = agora()): Item | string {
  const por = acao.por.trim();
  if (por.length < 2) return "informe o nome de quem decide";
  const h = (evento: string) => [...item.historico, { em, evento }];
  switch (acao.tipo) {
    case "aprovar":
      if (item.status !== "aguardando_aprovacao") return `item em '${item.status}' — só se aprova o que aguarda aprovação`;
      return {
        ...item,
        status: "aprovado",
        aprovacao: { por, em, impressao: item.impressao, origem: "painel", mensagem: acao.mensagem ?? null },
        rejeicao: null,
        historico: h(`aprovado por ${por}`),
      };
    case "rejeitar":
      if (!["aguardando_aprovacao", "aprovado", "erro"].includes(item.status)) return `item em '${item.status}' não pode ser rejeitado`;
      if (acao.motivo.trim().length < 3) return "diga o motivo da rejeição";
      return {
        ...item,
        status: "rejeitado",
        aprovacao: null,
        rejeicao: { por, em, motivo: acao.motivo.trim() },
        historico: h(`rejeitado por ${por}: ${acao.motivo.trim()}`),
      };
    case "desaprovar":
      if (item.status !== "aprovado") return `item em '${item.status}' — só se desfaz aprovação de item aprovado`;
      return { ...item, status: "aguardando_aprovacao", aprovacao: null, historico: h(`aprovação desfeita por ${por}`) };
    case "tentar_de_novo":
      if (item.status !== "erro") return "só se tenta de novo item com erro";
      if (!item.aprovacao || item.aprovacao.impressao !== item.impressao) return "item sem aprovação válida — aprove de novo";
      return { ...item, status: "aprovado", erro: null, publicacao: null, historico: h(`nova tentativa pedida por ${por}`) };
  }
}

/** Pronto para o agendador começar a publicar? */
export function vencido(item: Item, agoraMs = Date.now()): boolean {
  if (item.status !== "aprovado" || !item.aprovacao) return false;
  return !item.agendado_para || Date.parse(item.agendado_para) <= agoraMs;
}
