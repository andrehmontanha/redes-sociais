import type { Post, Resumo } from "@/lib/resumo";
import { DIAS, JANELAS } from "@/lib/resumo";

const num = (n: number | null | undefined, casas = 0) =>
  n == null ? "—" : n.toLocaleString("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: casas });
const pct = (n: number | null | undefined) => (n == null ? "—" : `${num(n, 2)}%`);
const compacto = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("pt-BR", { notation: "compact", maximumFractionDigits: 1 });
const FORMATOS: Record<string, string> = { reel: "Reel", carrossel: "Carrossel", imagem: "Imagem", video: "Vídeo", story: "Story" };

function Miniatura({ p }: { p: Post }) {
  // eslint-disable-next-line @next/next/no-img-element
  return p.imagem ? <img className="mini" src={p.imagem} alt="" loading="lazy" /> : <span className="mini">{FORMATOS[p.formato]}</span>;
}

function Top({ titulo, explica, posts, valor }: {
  titulo: string; explica: string; posts: Post[]; valor: (p: Post) => string;
}) {
  return (
    <section className="cartao">
      <div><h2>{titulo}</h2><p className="sub" style={{ fontSize: "0.85rem" }}>{explica}</p></div>
      {posts.length === 0 && <p className="sub">Nenhum post com valor acima de zero nesta amostra.</p>}
      <ol className="tops" style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {posts.map((p) => (
          <li key={p.id} className="top">
            <Miniatura p={p} />
            <div className="txt">
              <div className="leg">{p.url ? <a href={p.url} target="_blank" rel="noreferrer">{p.legenda || "(sem legenda)"}</a> : p.legenda || "(sem legenda)"}</div>
              <div className="meta">{FORMATOS[p.formato]} · {p.data.split("-").reverse().join("/")} {p.hora} · alcance {compacto(p.alcance)}</div>
            </div>
            <span className="num">{valor(p)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function nivel(v: number | null, max: number) {
  if (v == null || !max) return "var(--seq-vazio)";
  const passo = Math.min(6, Math.max(1, Math.ceil((v / max) * 6)));
  return `var(--seq-${passo})`;
}

export default function Painel({ resumo, usuario, demo }: { resumo: Resumo; usuario: string; demo: boolean }) {
  const { perfil, conta, kpis } = resumo;
  const maxFormato = Math.max(...resumo.porFormato.map((f) => f.alcance ?? 0), 1);
  const maxCelula = Math.max(...resumo.grade.flat().map((c) => c.alcance ?? 0), 0);
  const temConta = conta && !("erro" in conta);

  return (
    <>
      <section className="cabeca">
        <div style={{ display: "flex", gap: 12, alignItems: "baseline", flexWrap: "wrap" }}>
          <h1>@{perfil.username}</h1>
          {perfil.name && <span className="sub">{perfil.name}</span>}
        </div>
        <p className="sub">
          {num(perfil.followers_count)} seguidores · {resumo.posts.length} posts analisados
          {resumo.semInsights > 0 && ` (${resumo.semInsights} sem métricas internas)`}
        </p>
        <div className="acoes">
          <a className="botao" href={`/api/conta/${encodeURIComponent(usuario)}/bruto`}>Baixar dados para o estúdio</a>
          {!demo && <a className="botao" href={`https://www.instagram.com/${perfil.username}/`} target="_blank" rel="noreferrer">Abrir no Instagram</a>}
        </div>
      </section>

      <section className="kpis" aria-label="Números-chave">
        <div className="kpi"><div className="rotulo">Alcance mediano por post</div><div className="valor">{compacto(kpis.alcanceMediano)}</div><div className="nota">contas únicas que viram</div></div>
        <div className="kpi"><div className="rotulo">Salvamento / alcance</div><div className="valor">{pct(kpis.salvamentoMediano)}</div><div className="nota">mediana — quem quis guardar</div></div>
        <div className="kpi"><div className="rotulo">Compartilhamento / alcance</div><div className="valor">{pct(kpis.compartilhamentoMediano)}</div><div className="nota">mediana — quem levou adiante</div></div>
        <div className="kpi"><div className="rotulo">Cadência</div><div className="valor">{num(kpis.postsPorSemana, 1)}</div><div className="nota">posts por semana</div></div>
        {temConta && (
          <div className="kpi"><div className="rotulo">Alcance da conta, 30 dias</div><div className="valor">{compacto(conta.reach as number)}</div><div className="nota">{compacto(conta.accounts_engaged as number)} contas engajadas</div></div>
        )}
      </section>

      <div className="grade-2">
        <section className="cartao" aria-labelledby="t-formato">
          <div>
            <h2 id="t-formato">Alcance mediano por formato</h2>
            <p className="sub" style={{ fontSize: "0.85rem" }}>Contas únicas alcançadas, mediana dos posts de cada formato.</p>
          </div>
          <div className="barras">
            {resumo.porFormato.map((f) => (
              <div className="barra" key={f.formato} tabIndex={0}
                data-dica={`${FORMATOS[f.formato]}: ${num(f.alcance)} de alcance · ${pct(f.salvamento)} salvam · ${f.posts} posts`}>
                <span className="nome">{FORMATOS[f.formato]}</span>
                <div className="trilho"><div className="preenchido" style={{ width: `${((f.alcance ?? 0) / maxFormato) * 100}%` }} /></div>
                <span className="num">{compacto(f.alcance)}</span>
              </div>
            ))}
          </div>
          <details>
            <summary>Ver tabela</summary>
            <table>
              <thead><tr><th>Formato</th><th className="n">Posts</th><th className="n">Alcance</th><th className="n">Salv./alc.</th><th className="n">Compart./alc.</th></tr></thead>
              <tbody>{resumo.porFormato.map((f) => (
                <tr key={f.formato}><td>{FORMATOS[f.formato]}</td><td className="n">{f.posts}</td><td className="n">{num(f.alcance)}</td><td className="n">{pct(f.salvamento)}</td><td className="n">{pct(f.compartilhamento)}</td></tr>
              ))}</tbody>
            </table>
          </details>
        </section>

        <section className="cartao" aria-labelledby="t-quando">
          <div>
            <h2 id="t-quando">Quando publicar</h2>
            <p className="sub" style={{ fontSize: "0.85rem" }}>
              Alcance mediano por dia e horário (Brasília). Só janelas com 3 posts ou mais; as demais ficam neutras.
            </p>
          </div>
          <div className="calor" role="img" aria-label="Mapa de alcance por dia da semana e faixa de horário">
            <span />
            {JANELAS.map((j) => <span key={j} className="cab">{j}</span>)}
            {resumo.grade.map((linha, d) => (
              <FragmentoDia key={d} dia={DIAS[d]} linha={linha} max={maxCelula} />
            ))}
          </div>
          {resumo.melhores.length ? (
            <p className="sub">Melhores janelas: {resumo.melhores.map((m) => `${m.dia} ${m.janela} (${compacto(m.alcance)})`).join(" · ")}</p>
          ) : (
            <p className="sub">Amostra pequena por janela — publique em horários variados para o painel aprender.</p>
          )}
        </section>
      </div>

      <div className="grade-3">
        <Top titulo="Maior alcance" explica="Quem mais chegou em gente nova." posts={resumo.topAlcance} valor={(p) => compacto(p.alcance)} />
        <Top titulo="Mais salvos" explica="Salvamentos sobre alcance: conteúdo que as pessoas querem guardar." posts={resumo.topSalvamento} valor={(p) => pct(p.taxaSalvamento)} />
        <Top titulo="Mais compartilhados" explica="Compartilhamentos sobre alcance: conteúdo que leva a marca adiante." posts={resumo.topCompartilhamento} valor={(p) => pct(p.taxaCompartilhamento)} />
      </div>

      <section className="cartao" aria-labelledby="t-legendas">
        <h2 id="t-legendas">Legendas e hashtags</h2>
        <p className="sub">
          Alcance mediano com legenda de até 300 caracteres: <strong>{num(resumo.legendas.curtas)}</strong> · acima:{" "}
          <strong>{num(resumo.legendas.longas)}</strong>
        </p>
        {resumo.hashtags.length > 0 && (
          <p className="sub">Mais usadas: {resumo.hashtags.map(([t, n]) => `#${t} (${n})`).join(", ")}</p>
        )}
      </section>

      <section className="cartao" aria-labelledby="t-posts">
        <h2 id="t-posts">Posts recentes</h2>
        <div className="posts">
          {resumo.posts.map((p) => (
            <a key={p.id} className="post" href={p.url ?? undefined} target="_blank" rel="noreferrer"
              aria-label={`${FORMATOS[p.formato]} de ${p.data}, alcance ${num(p.alcance)}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              {p.imagem && <img src={p.imagem} alt="" loading="lazy" />}
              <span className="fmt">{FORMATOS[p.formato]}</span>
              <span className="sob"><span>{p.data.slice(8)}/{p.data.slice(5, 7)}</span><span>{compacto(p.alcance)} alc.</span></span>
            </a>
          ))}
        </div>
      </section>

      <p className="sub" style={{ fontSize: "0.8rem" }}>
        Alcance é estimado pela Meta; visualizações são métrica em desenvolvimento. Com “Baixar dados para o estúdio”,
        o arquivo entra no pipeline do repositório: <code>sincronizar.py --cliente {usuario} --de-arquivo bruto.json</code>.
      </p>
    </>
  );
}

function FragmentoDia({ dia, linha, max }: { dia: string; linha: { posts: number; alcance: number | null }[]; max: number }) {
  return (
    <>
      <span className="dia">{dia}</span>
      {linha.map((c, j) => (
        <span key={j} className="celula" tabIndex={0} style={{ background: nivel(c.alcance, max) }}
          data-dica={c.alcance != null ? `${dia} ${JANELAS[j]}: ${num(c.alcance)} (${c.posts} posts)` : `${dia} ${JANELAS[j]}: ${c.posts} post(s), pouco para medir`} />
      ))}
    </>
  );
}
