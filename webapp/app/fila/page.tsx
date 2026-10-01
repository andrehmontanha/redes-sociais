import Link from "next/link";
import { armazenamento } from "@/lib/config";
import type { Status } from "@/lib/fila";
import { listarItens } from "@/lib/fila-servidor";
import { NOME_STATUS, NOME_TIPO, quando } from "@/lib/rotulos";

export const dynamic = "force-dynamic";

const FILTROS: { rotulo: string; status?: Status[] }[] = [
  { rotulo: "Tudo" },
  { rotulo: "Para aprovar", status: ["aguardando_aprovacao"] },
  { rotulo: "Agendados", status: ["aprovado", "publicando"] },
  { rotulo: "Publicados", status: ["publicado"] },
  { rotulo: "Com problema", status: ["erro", "rejeitado"] },
];

export default async function Fila({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const q = await searchParams;
  if (!armazenamento()) {
    return (
      <main>
        <section className="cabeca"><h1>Fila de publicação</h1></section>
        <div className="aviso erro" role="alert">
          <strong>Armazenamento não configurado.</strong> Crie um <strong>Blob</strong> e um <strong>Upstash Redis</strong> em
          Storage no painel do projeto na Vercel (as variáveis entram sozinhas) e faça um novo deploy.
        </div>
      </main>
    );
  }
  const filtro = FILTROS.find((f) => f.rotulo === q.ver) ?? FILTROS[0];
  const cliente = q.cliente || undefined;
  const itens = await listarItens({ cliente, status: filtro.status });
  const paraAprovar = (await listarItens({ cliente, status: ["aguardando_aprovacao"] })).length;

  return (
    <main>
      <section className="cabeca">
        <h1>Fila de publicação{cliente ? ` · @${cliente}` : ""}</h1>
        <p className="sub">
          O estúdio gera os criativos e manda para cá. Cada peça só vai ao ar depois de aprovada por alguém da equipe,
          no horário marcado, e nada muda depois do “ok”: se a mídia ou a legenda mudar, precisa de nova aprovação.
        </p>
      </section>
      {paraAprovar > 0 && (
        <p className="aviso"><strong>{paraAprovar}</strong> {paraAprovar === 1 ? "peça espera" : "peças esperam"} aprovação.</p>
      )}
      <nav className="filtros" aria-label="Filtrar por situação">
        {FILTROS.map((f) => (
          <Link key={f.rotulo} href={`/fila?ver=${encodeURIComponent(f.rotulo)}${cliente ? `&cliente=${cliente}` : ""}`}
            aria-current={f === filtro ? "page" : undefined}>{f.rotulo}</Link>
        ))}
      </nav>
      <section className="cartao">
        {itens.length === 0 ? (
          <p className="sub">Nada aqui. Os criativos chegam pelo estúdio (<code>enviar_webapp.py</code>).</p>
        ) : (
          <div className="rolagem">
            <table>
              <thead><tr><th /><th>Peça</th><th>Conta</th><th>Publica em</th><th>Situação</th></tr></thead>
              <tbody>
                {itens.map((i) => {
                  const capa = i.capa ?? i.midias.find((m) => !m.video);
                  return (
                    <tr key={i.id}>
                      <td>{capa ? <img className="miniatura" src={capa.url} alt="" loading="lazy" /> : <span className="miniatura" />}</td>
                      <td>
                        <Link href={`/fila/${encodeURIComponent(i.id)}`}>{NOME_TIPO[i.tipo]}{i.midias.length > 1 ? ` · ${i.midias.length} peças` : ""}</Link>
                        <div className="sub" style={{ fontSize: "0.85rem", maxWidth: "40ch", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {i.legenda.split("\n")[0] || "sem legenda"}
                        </div>
                      </td>
                      <td><Link href={`/fila?cliente=${i.cliente}`}>@{i.cliente}</Link></td>
                      <td>{quando(i.agendado_para)}</td>
                      <td><span className={`estado ${i.status}`}>{NOME_STATUS[i.status]}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
