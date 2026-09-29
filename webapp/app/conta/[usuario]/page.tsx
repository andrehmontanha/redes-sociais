import Link from "next/link";
import { notFound } from "next/navigation";
import Painel from "@/components/Painel";
import { brutoDemo, USUARIO_DEMO } from "@/lib/demo";
import { coletar, ErroInstagram } from "@/lib/instagram";
import { resumir } from "@/lib/resumo";
import { contaPorUsuario } from "@/lib/sessao";

export const dynamic = "force-dynamic";
export const maxDuration = 60; // leitura de 30 posts + insights cabe com folga

export default async function Conta({
  params, searchParams,
}: { params: Promise<{ usuario: string }>; searchParams: Promise<Record<string, string>> }) {
  const { usuario } = await params;
  const q = await searchParams;
  const nome = decodeURIComponent(usuario);
  const demo = nome === USUARIO_DEMO;

  let bruto;
  let erro: string | null = null;
  if (demo) {
    bruto = brutoDemo();
  } else {
    const conta = await contaPorUsuario(nome);
    if (!conta) notFound();
    try {
      bruto = await coletar(conta.token, conta.id, 30);
    } catch (e) {
      erro = e instanceof ErroInstagram
        ? e.codigo === 190 ? "o token venceu ou foi revogado — conecte a conta de novo" : e.message
        : "falha ao ler a conta";
    }
  }

  return (
    <main>
      {q.conectado && <p className="aviso ok">@{nome} conectado. As métricas abaixo vêm de dentro da conta.</p>}
      {demo && (
        <p className="aviso"><strong>Demonstração.</strong> Conta e números fictícios, gerados para mostrar o painel.</p>
      )}
      {erro ? (
        <div className="aviso erro" role="alert">
          <strong>Não consegui ler @{nome}:</strong> {erro}. <Link href="/">Voltar às contas</Link>
        </div>
      ) : (
        <Painel resumo={resumir(bruto!)} usuario={nome} demo={demo} />
      )}
    </main>
  );
}
