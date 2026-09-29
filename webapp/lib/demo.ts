import type { Bruto, Midia } from "./instagram";

// Conta fictícia e determinística para testar o painel sem app da Meta.
// Sem imagens reais: o painel desenha um marcador no lugar da miniatura.

function aleatorio(semente: number) {
  return () => {
    semente = (semente * 1664525 + 1013904223) % 4294967296;
    return semente / 4294967296;
  };
}

export const USUARIO_DEMO = "demo.resort";

export function brutoDemo(): Bruto {
  const r = aleatorio(20260929);
  const base = Date.UTC(2026, 8, 28, 21, 0);
  const temas = ["piscinas termais", "pacote de fim de semana", "recreação infantil", "café regional", "bastidores"];
  const midias: Midia[] = [];
  const insights: Bruto["insights"] = {};
  for (let i = 0; i < 30; i++) {
    const tipo = i % 3 === 0 ? "REELS" : "FEED";
    const media_type = i % 3 === 0 ? "VIDEO" : i % 3 === 1 ? "CAROUSEL_ALBUM" : "IMAGE";
    const horas = [0, 5, 10, 14][Math.floor(r() * 4)];
    const quando = new Date(base - i * 2.3 * 86400000 - horas * 3600000);
    const id = `demo${i}`;
    const tema = temas[i % temas.length];
    midias.push({
      id, media_type, media_product_type: tipo,
      caption: `${tema[0].toUpperCase()}${tema.slice(1)} ☀️ ${i % 4 === 0 ? "Legenda longa ".repeat(30) : ""}#resort #olimpia #${tema.split(" ")[0]}`,
      permalink: undefined, shortcode: `D${i}`,
      timestamp: quando.toISOString().replace(".000Z", "+0000"),
      like_count: Math.round(80 + r() * 400), comments_count: Math.round(r() * 30),
    });
    const alcance = Math.round((tipo === "REELS" ? 9000 : 4000) + r() * 18000 + (horas === 0 ? 6000 : 0));
    insights[id] = {
      reach: alcance, saved: Math.round(alcance * (0.002 + r() * 0.02)),
      shares: Math.round(alcance * (0.001 + r() * 0.012)), views: Math.round(alcance * (1.4 + r())),
      total_interactions: Math.round(alcance * 0.03), likes: midias[i].like_count ?? null, comments: midias[i].comments_count ?? null,
    };
  }
  delete insights.demo7; // um post sem insights, como acontece de verdade
  return {
    perfil: {
      username: USUARIO_DEMO, name: "Resort Demonstração", biography: "Conta fictícia para testar o painel.",
      followers_count: 48210, follows_count: 310, media_count: 912, account_type: "BUSINESS",
    },
    midias, insights,
    conta_insights: { reach: 182400, views: 621000, accounts_engaged: 9120, total_interactions: 15480 },
  };
}
