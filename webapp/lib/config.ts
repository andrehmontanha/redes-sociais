// Configuração lida do ambiente (Vercel → Settings → Environment Variables).
// Nenhum segredo vai para o navegador: este módulo só roda no servidor.

export const config = {
  senha: process.env.ESTUDIO_SENHA ?? "",
  segredo: process.env.SESSAO_SEGREDO ?? "",
  igAppId: process.env.IG_APP_ID ?? "",
  igAppSecret: process.env.IG_APP_SECRET ?? "",
  graphVersao: process.env.IG_GRAPH_VERSION ?? "v23.0",
  // chave do motor (estúdio em Python) para enviar criativos à fila
  apiChave: process.env.ESTUDIO_API_CHAVE ?? "",
  // chave do agendador (cron da Vercel e GitHub Actions)
  cronSegredo: process.env.CRON_SECRET ?? "",
  redisUrl: process.env.UPSTASH_REDIS_REST_URL ?? process.env.KV_REST_API_URL ?? "",
  redisToken: process.env.UPSTASH_REDIS_REST_TOKEN ?? process.env.KV_REST_API_TOKEN ?? "",
  blobToken: process.env.BLOB_READ_WRITE_TOKEN ?? "",
};

/** URL pública do app, usada no redirect do OAuth. APP_URL vence; na Vercel cai
 *  para o domínio de produção do projeto. */
export function urlDoApp(origemDaRequisicao?: string): string {
  const explicita = process.env.APP_URL;
  if (explicita) return explicita.replace(/\/$/, "");
  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  if (vercel) return `https://${vercel}`;
  return (origemDaRequisicao ?? "http://localhost:3000").replace(/\/$/, "");
}

export const redirectOAuth = (origem?: string) => `${urlDoApp(origem)}/api/instagram/callback`;

/** O estúdio só guarda tokens com senha e segredo definidos. Sem eles o app roda
 *  apenas a demonstração — nunca um painel aberto com contas de clientes. */
export const protegido = () => config.senha.length >= 8 && config.segredo.length >= 32;
export const oauthDisponivel = () => protegido() && !!config.igAppId && !!config.igAppSecret;

/** Fila e contas no servidor: Redis (Upstash, pelo Marketplace da Vercel) para os
 *  dados e Vercel Blob para a mídia. Sem os dois, o app segue só com os cookies. */
export const armazenamento = () => protegido() && !!config.redisUrl && !!config.redisToken && !!config.blobToken;
export const motorConfigurado = () => armazenamento() && config.apiChave.length >= 32;
export const agendadorConfigurado = () => armazenamento() && config.cronSegredo.length >= 16;
