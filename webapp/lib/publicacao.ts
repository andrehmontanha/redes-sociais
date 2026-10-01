import { del } from "@vercel/blob";
import { contaDoServidor, contasDoServidor, destravar, guardarContaNoServidor, travar } from "./armazenamento";
import { config } from "./config";
import { agora, impressaoAtual, vencido, type Item } from "./fila";
import { gravarItem, lerItem, listarItens } from "./fila-servidor";
import { ErroInstagram } from "./instagram";
import type { Conta } from "./sessao";

// Publicação pela Instagram API com login do Instagram — porte do publicar.py do
// estúdio. O agendador chama `rodarAgendador` a cada poucos minutos. Cada item
// anda por etapas gravadas no Redis (filhos → container → publicado), então um
// Reel que demora a processar continua no disparo seguinte, sem publicar duas vezes.

const GRAPH = () => `https://graph.instagram.com/${config.graphVersao}`;
const LIMITE_PROCESSAMENTO_MS = 2 * 60 * 60_000;

async function chamar<T = Record<string, unknown>>(
  metodo: "GET" | "POST",
  caminho: string,
  token: string,
  params: Record<string, string> = {},
): Promise<T> {
  const corpo = new URLSearchParams({ ...params, access_token: token });
  const url = metodo === "GET" ? `${GRAPH()}/${caminho}?${corpo}` : `${GRAPH()}/${caminho}`;
  let r: Response | undefined;
  for (let tentativa = 0; tentativa < 3; tentativa++) {
    r = await fetch(url, { method: metodo, body: metodo === "POST" ? corpo : undefined, cache: "no-store" });
    if (r.status < 500 && r.status !== 429) break;
    await new Promise((ok) => setTimeout(ok, 1500 * 2 ** tentativa));
  }
  const dados = await r!.json().catch(() => ({}));
  if (!r!.ok || dados.error) {
    const e = dados.error ?? {};
    throw new ErroInstagram(`Graph API ${r!.status} em ${caminho.split("?")[0]}: ${e.message ?? "sem detalhe"}`, e.code);
  }
  return dados as T;
}

async function cota(conta: Conta) {
  const d = await chamar<{ data?: { quota_usage?: number; config?: { quota_total?: number } }[] }>(
    "GET", `${conta.id}/content_publishing_limit`, conta.token, { fields: "quota_usage,config" },
  );
  const x = d.data?.[0] ?? {};
  return { usado: x.quota_usage ?? 0, total: x.config?.quota_total ?? 100 };
}

async function statusDoContainer(id: string, token: string) {
  const d = await chamar<{ status_code?: string; status?: string }>("GET", id, token, { fields: "status_code,status" });
  return { codigo: d.status_code ?? "IN_PROGRESS", detalhe: d.status ?? "" };
}

async function criarContainer(item: Item, conta: Conta): Promise<string> {
  const criar = (p: Record<string, string>) =>
    chamar<{ id: string }>("POST", `${conta.id}/media`, conta.token, p).then((d) => d.id);
  const m = item.midias[0];
  switch (item.tipo) {
    case "feed":
      return criar({ image_url: m.url, caption: item.legenda });
    case "reel": {
      const p: Record<string, string> = { media_type: "REELS", video_url: m.url, caption: item.legenda, share_to_feed: "true" };
      if (item.capa) p.cover_url = item.capa.url;
      else if (item.thumb_offset_ms !== null) p.thumb_offset = String(item.thumb_offset_ms);
      return criar(p);
    }
    case "story":
      return criar({ media_type: "STORIES", [m.video ? "video_url" : "image_url"]: m.url });
    case "carrossel":
      return criar({ media_type: "CAROUSEL", children: (item.publicacao?.filhos ?? []).join(","), caption: item.legenda });
  }
}

type Salvar = (i: Item) => Promise<void>;

/** Um passo da publicação. Devolve true quando não há mais nada a fazer agora
 *  (publicado, erro, ou esperando o Instagram processar). */
export async function avancar(item: Item, conta: Conta, salvar: Salvar): Promise<boolean> {
  const evento = (texto: string) => item.historico.push({ em: agora(), evento: texto });

  if (item.status === "aprovado") {
    if (!item.aprovacao || item.aprovacao.impressao !== item.impressao || (await impressaoAtual(item)) !== item.aprovacao.impressao) {
      throw new Error("mídia, legenda ou horário mudaram depois da aprovação — precisa de nova aprovação");
    }
    const { usado, total } = await cota(conta);
    if (usado >= total) throw new Error(`cota de publicação esgotada (${usado}/${total} nas últimas 24 h)`);
    item.status = "publicando";
    item.publicacao = { iniciadoEm: agora() };
    evento(`publicação iniciada · cota ${usado}/${total}`);
    await salvar(item);
    return false;
  }
  if (item.status !== "publicando" || !item.publicacao) return true;

  const pub = item.publicacao;
  if (Date.now() - Date.parse(pub.iniciadoEm) > LIMITE_PROCESSAMENTO_MS) {
    throw new Error("o Instagram não terminou de processar a mídia em 2 horas");
  }

  if (item.tipo === "carrossel" && !pub.filhos) {
    pub.filhos = [];
    for (const m of item.midias) {
      const p: Record<string, string> = m.video
        ? { is_carousel_item: "true", media_type: "VIDEO", video_url: m.url }
        : { is_carousel_item: "true", image_url: m.url };
      pub.filhos.push((await chamar<{ id: string }>("POST", `${conta.id}/media`, conta.token, p)).id);
    }
    evento(`${pub.filhos.length} peças do carrossel enviadas`);
    await salvar(item);
    return false;
  }

  if (item.tipo === "carrossel" && !pub.container) {
    const estados = await Promise.all(pub.filhos!.map((f) => statusDoContainer(f, conta.token)));
    const ruim = estados.find((e) => e.codigo === "ERROR" || e.codigo === "EXPIRED");
    if (ruim) throw new Error(`uma peça do carrossel falhou no Instagram: ${ruim.codigo} ${ruim.detalhe}`);
    if (estados.some((e) => e.codigo !== "FINISHED")) return true;
  }

  if (!pub.container) {
    pub.container = await criarContainer(item, conta);
    evento("container criado no Instagram");
    await salvar(item);
    return false;
  }

  const estado = await statusDoContainer(pub.container, conta.token);
  if (estado.codigo === "ERROR" || estado.codigo === "EXPIRED") {
    throw new Error(`o Instagram recusou a mídia: ${estado.codigo} ${estado.detalhe}`);
  }
  if (estado.codigo !== "FINISHED") return true;

  const { id: mediaId } = await chamar<{ id: string }>("POST", `${conta.id}/media_publish`, conta.token, { creation_id: pub.container });
  let permalink: string | undefined;
  let publicadoEm = agora();
  try {
    const info = await chamar<{ permalink?: string; timestamp?: string }>("GET", mediaId, conta.token, { fields: "permalink,timestamp" });
    permalink = info.permalink;
    publicadoEm = info.timestamp ?? publicadoEm;
  } catch {
    // publicado; só o link não veio — fica o id
  }
  item.status = "publicado";
  item.resultado = { mediaId, permalink, publicadoEm };
  evento("publicado");
  await salvar(item);
  // vídeo pesa no armazenamento; depois de publicado o Instagram já tem a cópia dele
  const videos = item.midias.filter((m) => m.video).map((m) => m.url);
  if (videos.length) await del(videos, { token: config.blobToken }).catch(() => undefined);
  return true;
}

/** Leva um item adiante até terminar ou o prazo do disparo acabar. */
export async function publicarItem(id: string, prazo: number, ignorarHorario = false): Promise<Item | null> {
  if (!(await travar(id, 300))) return null; // outro disparo está cuidando dele
  try {
    let item = await lerItem(id);
    if (!item) return null;
    if (item.status === "aprovado" && !ignorarHorario && !vencido(item)) return item;
    const conta = await contaDoServidor(item.cliente);
    try {
      if (!conta) throw new Error(`@${item.cliente} não está conectado no webapp — entre com o Instagram dessa conta`);
      while (Date.now() < prazo) {
        if (await avancar(item, conta, gravarItem)) break;
        await new Promise((ok) => setTimeout(ok, 2000));
        item = (await lerItem(id)) ?? item;
      }
    } catch (e) {
      item.status = "erro";
      item.erro = e instanceof Error ? e.message : String(e);
      item.historico.push({ em: agora(), evento: `erro: ${item.erro}` });
      await gravarItem(item);
    }
    return item;
  } finally {
    await destravar(id);
  }
}

/** Renova tokens a menos de 20 dias de vencer (o do Instagram dura 60 e renova por mais 60). */
export async function renovarTokens(): Promise<string[]> {
  const renovadas: string[] = [];
  for (const c of await contasDoServidor()) {
    const faltam = Date.parse(c.expira) - Date.now();
    const desde = Date.now() - Date.parse(c.conectadoEm);
    if (faltam > 20 * 86400_000 || faltam <= 0 || desde < 86400_000) continue;
    try {
      const q = new URLSearchParams({ grant_type: "ig_refresh_token", access_token: c.token });
      const r = await fetch(`https://graph.instagram.com/refresh_access_token?${q}`, { cache: "no-store" });
      const d = await r.json();
      if (!r.ok || !d.access_token) continue;
      await guardarContaNoServidor({
        ...c,
        token: d.access_token,
        expira: new Date(Date.now() + d.expires_in * 1000).toISOString(),
        conectadoEm: new Date().toISOString(),
      });
      renovadas.push(c.usuario);
    } catch {
      // tenta de novo no próximo disparo
    }
  }
  return renovadas;
}

/** Um disparo do agendador: continua o que está publicando e começa o que venceu. */
export async function rodarAgendador(duracaoMs = 50_000) {
  const prazo = Date.now() + duracaoMs;
  const itens = await listarItens({ status: ["aprovado", "publicando"] });
  const fila = itens.filter((i) => i.status === "publicando" || vencido(i));
  const resultado: { id: string; status: string; erro?: string | null }[] = [];
  for (const i of fila) {
    if (Date.now() >= prazo) break;
    const depois = await publicarItem(i.id, prazo);
    if (depois) resultado.push({ id: depois.id, status: depois.status, erro: depois.erro });
  }
  const renovadas = await renovarTokens();
  return { processados: resultado, aguardando: itens.length - fila.length, renovadas };
}
