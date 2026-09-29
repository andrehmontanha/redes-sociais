import { NextResponse, type NextRequest } from "next/server";
import { brutoDemo, USUARIO_DEMO } from "@/lib/demo";
import { coletar, ErroInstagram } from "@/lib/instagram";
import { contaPorUsuario } from "@/lib/sessao";

// Exporta no formato bruto.json do estúdio. No terminal:
//   python .claude/skills/conectar-instagram/scripts/sincronizar.py --cliente <handle> --de-arquivo bruto.json
// e a análise, a identidade e os criativos seguem com os dados de dentro.
export async function GET(_req: NextRequest, ctx: { params: Promise<{ usuario: string }> }) {
  const { usuario } = await ctx.params;
  let bruto;
  if (usuario === USUARIO_DEMO) {
    bruto = brutoDemo();
  } else {
    const conta = await contaPorUsuario(usuario);
    if (!conta) return NextResponse.json({ erro: "conta não conectada" }, { status: 404 });
    try {
      bruto = await coletar(conta.token, conta.id, 60);
    } catch (e) {
      const msg = e instanceof ErroInstagram ? e.message : "falha ao ler a conta";
      return NextResponse.json({ erro: msg }, { status: 502 });
    }
  }
  const data = new Date().toISOString().slice(0, 10);
  return new NextResponse(JSON.stringify(bruto, null, 2), {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "content-disposition": `attachment; filename="bruto-${usuario}-${data}.json"`,
      "cache-control": "no-store",
    },
  });
}
