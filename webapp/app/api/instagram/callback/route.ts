import { NextResponse, type NextRequest } from "next/server";
import { config } from "@/lib/config";
import { abrir, iguais } from "@/lib/cripto";
import { ErroInstagram, quemSou, tokenLongo, trocarCodigo } from "@/lib/instagram";
import { COOKIE_STATE, guardarConta } from "@/lib/sessao";

// Volta do Instagram. Aqui o caminho encurta: o app recebe o código sozinho,
// troca pelo token de 60 dias e já abre o painel — ninguém copia URL nenhuma.
export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams;
  const falha = (motivo: string) => {
    const r = NextResponse.redirect(new URL(`/?erro=${encodeURIComponent(motivo)}`, req.url));
    r.cookies.delete(COOKIE_STATE);
    return r;
  };

  if (q.get("error")) return falha(q.get("error_description") ?? "autorização negada no Instagram");
  const salvo = abrir<{ state: string; exp: number; redirect: string }>(
    req.cookies.get(COOKIE_STATE)?.value, config.segredo, "state",
  );
  const state = q.get("state") ?? "";
  if (!salvo || salvo.exp < Date.now()) return falha("o link de autorização expirou — tente de novo");
  if (!state || !iguais(state, salvo.state)) return falha("state não confere — a autorização não começou aqui");
  const code = q.get("code");
  if (!code) return falha("o Instagram não devolveu o código");

  try {
    const curto = await trocarCodigo(code, salvo.redirect);
    const longo = await tokenLongo(curto.token);
    const eu = await quemSou(longo.token);
    await guardarConta({
      id: String(eu.user_id ?? eu.id ?? curto.userId),
      usuario: eu.username,
      tipo: eu.account_type,
      token: longo.token,
      expira: longo.expiraEm,
      origem: "oauth",
      conectadoEm: new Date().toISOString(),
    });
    const r = NextResponse.redirect(new URL(`/conta/${encodeURIComponent(eu.username)}?conectado=1`, req.url));
    r.cookies.delete(COOKIE_STATE);
    return r;
  } catch (e) {
    return falha(e instanceof ErroInstagram ? `Instagram: ${e.message}` : "falha ao trocar o código");
  }
}
