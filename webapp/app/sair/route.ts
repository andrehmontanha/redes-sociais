import { NextResponse, type NextRequest } from "next/server";
import { COOKIE_SESSAO } from "@/lib/sessao";

export async function GET(req: NextRequest) {
  const r = NextResponse.redirect(new URL("/entrar", req.url));
  r.cookies.delete(COOKIE_SESSAO);
  return r;
}
