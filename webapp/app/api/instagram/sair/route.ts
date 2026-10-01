import { NextResponse, type NextRequest } from "next/server";
import { removerContaDoServidor } from "@/lib/armazenamento";
import { armazenamento } from "@/lib/config";
import { esquecerNoNavegador } from "@/lib/sessao";

// Desconecta uma conta: o token some do cookie e do servidor (a fila daquela conta
// deixa de publicar até reconectar). Para revogar do lado da Meta, o dono remove o
// app em Instagram → Configurações → Apps e sites.
export async function POST(req: NextRequest) {
  const usuario = String((await req.formData()).get("usuario") ?? "");
  await esquecerNoNavegador(usuario);
  if (armazenamento()) await removerContaDoServidor(usuario);
  return NextResponse.redirect(new URL(`/?desconectado=${encodeURIComponent(usuario)}`, req.url), 303);
}
