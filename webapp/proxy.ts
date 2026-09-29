import { NextResponse, type NextRequest } from "next/server";
import { protegido } from "./lib/config";
import { COOKIE_SESSAO, sessaoValida } from "./lib/sessao";

// Trava de acesso do estúdio. Com senha configurada, tudo exige sessão, menos a
// tela de entrada e a demonstração (que não tem dado de cliente). Sem senha
// configurada, só a demonstração funciona: nada de contas reais num app aberto.

const PUBLICO = ["/entrar", "/demo", "/conta/demo.resort", "/api/conta/demo.resort/bruto"];

export function proxy(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (PUBLICO.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return NextResponse.next();

  if (!protegido()) {
    if (pathname === "/") return NextResponse.next();
    return NextResponse.redirect(new URL("/?config=1", req.url));
  }
  if (sessaoValida(req.cookies.get(COOKIE_SESSAO)?.value)) return NextResponse.next();
  if (pathname.startsWith("/api/")) return NextResponse.json({ erro: "sessão expirada" }, { status: 401 });
  const entrar = new URL("/entrar", req.url);
  entrar.searchParams.set("volta", pathname + search);
  return NextResponse.redirect(entrar);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg).*)"],
};
