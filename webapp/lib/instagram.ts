import { config } from "./config";

// Instagram API com login do Instagram (graph.instagram.com). Só roda no servidor.

const GRAPH = () => `https://graph.instagram.com/${config.graphVersao}`;

export const ESCOPOS = [
  "instagram_business_basic",
  "instagram_business_manage_insights",
  "instagram_business_content_publish",
];

export class ErroInstagram extends Error {
  constructor(mensagem: string, public codigo?: number) {
    super(mensagem);
  }
}

async function pedir<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { ...init, cache: "no-store" });
  const dados = await r.json().catch(() => ({}));
  if (!r.ok || dados.error) {
    const e = dados.error ?? {};
    throw new ErroInstagram(e.message ?? dados.error_message ?? `HTTP ${r.status}`, e.code);
  }
  return dados as T;
}

export function urlAutorizacao(state: string, redirect: string) {
  const q = new URLSearchParams({
    client_id: config.igAppId,
    redirect_uri: redirect,
    response_type: "code",
    scope: ESCOPOS.join(","),
    state,
    force_authentication: "1",
    enable_fb_login: "0",
  });
  return `https://www.instagram.com/oauth/authorize?${q}`;
}

export async function trocarCodigo(code: string, redirect: string) {
  const corpo = new URLSearchParams({
    client_id: config.igAppId,
    client_secret: config.igAppSecret,
    grant_type: "authorization_code",
    redirect_uri: redirect,
    code: code.replace(/#_$/, ""),
  });
  const d = await pedir<{ data?: { access_token: string; user_id: string }[]; access_token?: string; user_id?: string }>(
    "https://api.instagram.com/oauth/access_token",
    { method: "POST", body: corpo },
  );
  const item = d.data?.[0] ?? (d as { access_token: string; user_id: string });
  return { token: item.access_token, userId: String(item.user_id) };
}

export async function tokenLongo(curto: string) {
  const q = new URLSearchParams({ grant_type: "ig_exchange_token", client_secret: config.igAppSecret, access_token: curto });
  const d = await pedir<{ access_token: string; expires_in: number }>(`https://graph.instagram.com/access_token?${q}`);
  return { token: d.access_token, expiraEm: new Date(Date.now() + d.expires_in * 1000).toISOString() };
}

export type Eu = { user_id?: string; id?: string; username: string; account_type?: string };

export async function quemSou(token: string): Promise<Eu> {
  return pedir<Eu>(`${GRAPH()}/me?fields=user_id,username,account_type&access_token=${encodeURIComponent(token)}`);
}

// ---------------------------------------------------------------- leitura

export type Perfil = {
  user_id?: string;
  username: string;
  name?: string;
  biography?: string;
  website?: string;
  followers_count?: number;
  follows_count?: number;
  media_count?: number;
  profile_picture_url?: string;
  account_type?: string;
};

export type Midia = {
  id: string;
  caption?: string;
  media_type: "IMAGE" | "VIDEO" | "CAROUSEL_ALBUM";
  media_product_type?: "FEED" | "REELS" | "STORY" | "AD";
  media_url?: string;
  thumbnail_url?: string;
  permalink?: string;
  shortcode?: string;
  timestamp: string;
  like_count?: number;
  comments_count?: number;
  children?: { data: { id: string; media_type: string; media_url?: string; thumbnail_url?: string }[] };
};

export type Insights = Record<string, number | null>;

/** Mesmo formato do bruto.json do estúdio (sincronizar.py --de-arquivo). */
export type Bruto = {
  perfil: Perfil;
  midias: Midia[];
  insights: Record<string, Insights>;
  conta_insights: Record<string, number | string | null>;
};

const CAMPOS_MIDIA =
  "id,caption,media_type,media_product_type,media_url,thumbnail_url,permalink,shortcode,timestamp," +
  "like_count,comments_count,children{id,media_type,media_url,thumbnail_url}";
const METRICAS = "reach,saved,shares,views,total_interactions,likes,comments";

function valor(m: { values?: { value: number }[]; total_value?: { value: number } }) {
  return m.total_value?.value ?? m.values?.[0]?.value ?? null;
}

async function emParalelo<T, R>(itens: T[], limite: number, f: (x: T) => Promise<R>): Promise<R[]> {
  const saida: R[] = new Array(itens.length);
  let i = 0;
  const trabalhadores = Array.from({ length: Math.min(limite, itens.length) }, async () => {
    while (i < itens.length) {
      const k = i++;
      saida[k] = await f(itens[k]);
    }
  });
  await Promise.all(trabalhadores);
  return saida;
}

export async function coletar(token: string, userId: string, limite = 30): Promise<Bruto> {
  const t = encodeURIComponent(token);
  const perfil = await pedir<Perfil>(
    `${GRAPH()}/${userId}?fields=user_id,username,name,biography,website,followers_count,follows_count,` +
      `media_count,profile_picture_url,account_type&access_token=${t}`,
  );
  const midias: Midia[] = [];
  let url: string | undefined = `${GRAPH()}/${userId}/media?fields=${CAMPOS_MIDIA}&limit=${Math.min(limite, 50)}&access_token=${t}`;
  while (url && midias.length < limite) {
    const pagina: { data: Midia[]; paging?: { next?: string } } = await pedir(url);
    midias.push(...pagina.data);
    url = pagina.paging?.next;
  }
  midias.splice(limite);

  const insights: Record<string, Insights> = {};
  await emParalelo(midias, 6, async (m) => {
    try {
      const d = await pedir<{ data: { name: string; values?: { value: number }[]; total_value?: { value: number } }[] }>(
        `${GRAPH()}/${m.id}/insights?metric=${METRICAS}&access_token=${t}`,
      );
      insights[m.id] = Object.fromEntries(d.data.map((x) => [x.name, valor(x)]));
    } catch {
      // post anterior à conta profissional ou métrica indisponível: fica sem insights
    }
  });

  let conta_insights: Bruto["conta_insights"] = {};
  try {
    const fim = Math.floor(Date.now() / 1000);
    const d = await pedir<{ data: { name: string; total_value?: { value: number } }[] }>(
      `${GRAPH()}/${userId}/insights?metric=reach,views,accounts_engaged,total_interactions&period=day` +
        `&metric_type=total_value&since=${fim - 30 * 86400}&until=${fim}&access_token=${t}`,
    );
    conta_insights = Object.fromEntries(d.data.map((x) => [x.name, valor(x)]));
  } catch (e) {
    conta_insights = { erro: (e as Error).message };
  }
  return { perfil, midias, insights, conta_insights };
}
