import { NextResponse, type NextRequest } from "next/server";
import { protegido } from "@/lib/config";
import { ErroInstagram, quemSou } from "@/lib/instagram";
import { guardarConta } from "@/lib/sessao";

// Modo dev: o token gerado no painel da Meta (app em modo de desenvolvimento,
// conta adicionada como testadora) é colado no formulário do próprio app — nunca
// num chat. O app confere o token com a API antes de guardar.
export async function POST(req: NextRequest) {
  if (!protegido()) return NextResponse.redirect(new URL("/?config=1", req.url), 303);
  const form = await req.formData();
  const token = String(form.get("token") ?? "").trim();
  const volta = (motivo: string) =>
    NextResponse.redirect(new URL(`/modo-dev?erro=${encodeURIComponent(motivo)}`, req.url), 303);

  if (!/^[A-Za-z0-9_\-|.]{40,}$/.test(token)) return volta("isso não parece um token de acesso do Instagram");
  try {
    const eu = await quemSou(token);
    if (eu.account_type && !["BUSINESS", "MEDIA_CREATOR"].includes(eu.account_type)) {
      return volta(`@${eu.username} é conta pessoal — a API só atende contas profissionais`);
    }
    await guardarConta({
      id: String(eu.user_id ?? eu.id),
      usuario: eu.username,
      tipo: eu.account_type,
      token,
      // o painel da Meta gera token de longa duração (60 dias); a data exata não vem na resposta
      expira: new Date(Date.now() + 60 * 86400_000).toISOString(),
      origem: "dev",
      conectadoEm: new Date().toISOString(),
    });
    return NextResponse.redirect(new URL(`/conta/${encodeURIComponent(eu.username)}?conectado=1`, req.url), 303);
  } catch (e) {
    return volta(e instanceof ErroInstagram ? `o Instagram recusou o token: ${e.message}` : "não consegui validar o token");
  }
}
