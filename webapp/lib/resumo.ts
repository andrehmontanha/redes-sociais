import type { Bruto, Midia } from "./instagram";

// Mesma leitura do sincronizar.py do estúdio: ranquear por ALCANCE e por
// SALVAMENTO/COMPARTILHAMENTO sobre alcance — não por curtida.

export const DIAS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"] as const;
export const JANELAS = ["00–05h", "06–11h", "12–17h", "18–23h"] as const;

export type Post = {
  id: string;
  url?: string;
  imagem?: string;
  data: string; // AAAA-MM-DD no fuso do perfil
  hora: string;
  dia: number; // 0 = domingo
  janela: number;
  formato: "reel" | "carrossel" | "imagem" | "video" | "story";
  legenda: string;
  curtidas: number | null;
  comentarios: number | null;
  alcance: number | null;
  salvamentos: number | null;
  compartilhamentos: number | null;
  views: number | null;
  taxaSalvamento: number | null;
  taxaCompartilhamento: number | null;
  hashtags: string[];
};

export function formato(m: Midia): Post["formato"] {
  if (m.media_product_type === "REELS") return "reel";
  if (m.media_type === "CAROUSEL_ALBUM") return "carrossel";
  if (m.media_product_type === "STORY") return "story";
  return m.media_type === "VIDEO" ? "video" : "imagem";
}

function partesNoFuso(iso: string, fuso: string) {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: fuso, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", weekday: "short", hourCycle: "h23",
    }).formatToParts(new Date(iso)).map((x) => [x.type, x.value]),
  );
  const dia = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(p.weekday);
  return { data: `${p.year}-${p.month}-${p.day}`, hora: `${p.hour}:${p.minute}`, h: Number(p.hour), dia };
}

const taxa = (a: number | null | undefined, b: number | null | undefined) =>
  a != null && b ? Math.round((a / b) * 10000) / 100 : null;

const ehVideo = (url?: string) => !!url && /\.(mp4|mov)(\?|$)/i.test(url);

/** Imagem desenhável do post. Vídeo e carrossel que abre com vídeo trazem o MP4
 *  em media_url — isso não vai numa <img>; usa a capa (thumbnail_url). */
export function capa(m: Midia): string | undefined {
  const filhos = m.children?.data ?? [];
  const candidatos = [
    m.thumbnail_url,
    m.media_type === "IMAGE" ? m.media_url : undefined,
    ...filhos.map((c) => c.thumbnail_url ?? (c.media_type === "IMAGE" ? c.media_url : undefined)),
    m.media_type === "CAROUSEL_ALBUM" ? m.media_url : undefined,
  ];
  return candidatos.find((u) => u && !ehVideo(u));
}

export function montarPosts(bruto: Bruto, fuso = "America/Sao_Paulo"): Post[] {
  return bruto.midias.map((m) => {
    const ins = bruto.insights[m.id] ?? {};
    const { data, hora, h, dia } = partesNoFuso(m.timestamp.replace("+0000", "Z"), fuso);
    const legenda = m.caption ?? "";
    const alcance = ins.reach ?? null;
    return {
      id: m.id, url: m.permalink,
      imagem: capa(m),
      data, hora, dia, janela: Math.floor(h / 6), formato: formato(m), legenda,
      curtidas: ins.likes ?? m.like_count ?? null,
      comentarios: ins.comments ?? m.comments_count ?? null,
      alcance, salvamentos: ins.saved ?? null, compartilhamentos: ins.shares ?? null, views: ins.views ?? null,
      taxaSalvamento: taxa(ins.saved, alcance), taxaCompartilhamento: taxa(ins.shares, alcance),
      hashtags: [...legenda.matchAll(/#([\p{L}\p{N}_]+)/gu)].map((x) => x[1].toLowerCase()),
    };
  });
}

export function mediana(v: (number | null | undefined)[]): number | null {
  const n = v.filter((x): x is number => x != null).sort((a, b) => a - b);
  if (!n.length) return null;
  const m = Math.floor(n.length / 2);
  return n.length % 2 ? n[m] : (n[m - 1] + n[m]) / 2;
}

export type Resumo = ReturnType<typeof resumir>;

export function resumir(bruto: Bruto, fuso = "America/Sao_Paulo") {
  const posts = montarPosts(bruto, fuso);
  const comAlcance = posts.filter((p) => p.alcance);
  // ranking só com valor positivo: em conta pequena a maioria dos posts tem 0
  // salvamentos, e uma lista de zeros não diz nada
  const top = (chave: keyof Post) =>
    [...comAlcance].filter((p) => ((p[chave] as number | null) ?? 0) > 0)
      .sort((a, b) => (b[chave] as number) - (a[chave] as number)).slice(0, 5);

  const porFormato = Object.entries(
    comAlcance.reduce<Record<string, Post[]>>((g, p) => ((g[p.formato] ??= []).push(p), g), {}),
  )
    .map(([f, g]) => ({
      formato: f, posts: g.length,
      alcance: mediana(g.map((p) => p.alcance)),
      salvamento: mediana(g.map((p) => p.taxaSalvamento)),
      compartilhamento: mediana(g.map((p) => p.taxaCompartilhamento)),
    }))
    .sort((a, b) => (b.alcance ?? 0) - (a.alcance ?? 0));

  // grade dia × janela: mediana de alcance, só com ≥ 3 posts (senão é anedota)
  const grade = DIAS.map((_, d) =>
    JANELAS.map((_, j) => {
      const g = comAlcance.filter((p) => p.dia === d && p.janela === j).map((p) => p.alcance);
      return { posts: g.length, alcance: g.length >= 3 ? mediana(g) : null };
    }),
  );
  const melhores = grade
    .flatMap((linha, d) => linha.map((c, j) => ({ ...c, dia: DIAS[d], janela: JANELAS[j] })))
    .filter((c) => c.alcance != null)
    .sort((a, b) => (b.alcance ?? 0) - (a.alcance ?? 0))
    .slice(0, 3);

  const datas = posts.map((p) => p.data).sort();
  const semanas = datas.length > 1 ? Math.max(1, (Date.parse(datas.at(-1)!) - Date.parse(datas[0])) / 6048e5) : 1;
  const tags = Object.entries(
    posts.flatMap((p) => p.hashtags).reduce<Record<string, number>>((c, t) => ((c[t] = (c[t] ?? 0) + 1), c), {}),
  ).sort((a, b) => b[1] - a[1]).slice(0, 10);

  return {
    perfil: bruto.perfil,
    conta: bruto.conta_insights,
    posts,
    semInsights: posts.length - comAlcance.length,
    kpis: {
      alcanceMediano: mediana(comAlcance.map((p) => p.alcance)),
      salvamentoMediano: mediana(comAlcance.map((p) => p.taxaSalvamento)),
      compartilhamentoMediano: mediana(comAlcance.map((p) => p.taxaCompartilhamento)),
      postsPorSemana: datas.length > 1 ? Math.round((datas.length / semanas) * 10) / 10 : null,
    },
    topAlcance: top("alcance"),
    topSalvamento: top("taxaSalvamento"),
    topCompartilhamento: top("taxaCompartilhamento"),
    porFormato,
    grade,
    melhores,
    legendas: {
      curtas: mediana(comAlcance.filter((p) => p.legenda.length < 300).map((p) => p.alcance)),
      longas: mediana(comAlcance.filter((p) => p.legenda.length >= 300).map((p) => p.alcance)),
    },
    hashtags: tags,
  };
}
