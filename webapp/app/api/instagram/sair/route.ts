import { NextResponse, type NextRequest } from "next/server";
import { lerContas, salvarContas } from "@/lib/sessao";

// Desconecta uma conta: o token some do cookie. Para revogar do lado da Meta, o
// dono remove o app em Instagram → Configurações → Apps e sites.
export async function POST(req: NextRequest) {
  const usuario = String((await req.formData()).get("usuario") ?? "");
  const contas = await lerContas();
  await salvarContas(contas.filter((c) => c.usuario !== usuario));
  return NextResponse.redirect(new URL(`/?desconectado=${encodeURIComponent(usuario)}`, req.url), 303);
}
