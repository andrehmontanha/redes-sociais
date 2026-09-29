import { randomBytes } from "node:crypto";
import { NextResponse, type NextRequest } from "next/server";
import { config, oauthDisponivel, redirectOAuth } from "@/lib/config";
import { selar } from "@/lib/cripto";
import { urlAutorizacao } from "@/lib/instagram";
import { COOKIE_STATE, opcoesCookie } from "@/lib/sessao";

// Início do "Entrar com Instagram": gera o state anti-CSRF, guarda selado num
// cookie de 15 minutos e manda o navegador para a tela oficial do Instagram.
export async function GET(req: NextRequest) {
  if (!oauthDisponivel()) return NextResponse.redirect(new URL("/modo-dev?faltando=app", req.url));
  const state = randomBytes(24).toString("base64url");
  const redirect = redirectOAuth(req.nextUrl.origin);
  const r = NextResponse.redirect(urlAutorizacao(state, redirect));
  r.cookies.set(COOKIE_STATE, selar({ state, exp: Date.now() + 15 * 60_000, redirect }, config.segredo, "state"), {
    ...opcoesCookie,
    maxAge: 15 * 60,
  });
  return r;
}
