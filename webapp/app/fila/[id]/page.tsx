import { cookies } from "next/headers";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { destravar, travar } from "@/lib/armazenamento";
import { armazenamento } from "@/lib/config";
import { aplicar, impressaoAtual, type Acao } from "@/lib/fila";
import { gravarItem, lerItem } from "@/lib/fila-servidor";
import { publicarItem } from "@/lib/publicacao";
import { NOME_STATUS, NOME_TIPO, quando } from "@/lib/rotulos";
import { exigirSessao, opcoesCookie } from "@/lib/sessao";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

const COOKIE_NOME = "estudio_aprovador";

async function decidir(form: FormData) {
  "use server";
  await exigirSessao();
  const id = String(form.get("id"));
  const tipo = String(form.get("acao")) as Acao["tipo"];
  const por = String(form.get("por") ?? "").trim();
  const volta = (msg: string, campo = "erro") => redirect(`/fila/${encodeURIComponent(id)}?${campo}=${encodeURIComponent(msg)}`);

  if (!(await travar(id, 30))) volta("a peça está sendo publicada agora — espere um minuto");
  let mensagem = "";
  try {
    const item = await lerItem(id);
    if (!item) notFound();
    if (tipo === "aprovar") {
      // confere os bytes do Blob antes de registrar o "ok": aprova exatamente o que está na tela
      if ((await impressaoAtual(item)) !== item.impressao) {
        mensagem = "a mídia no armazenamento não confere com a recebida do estúdio — reenvie a peça";
        throw new Error(mensagem);
      }
    }
    const acao: Acao =
      tipo === "rejeitar" ? { tipo, por, motivo: String(form.get("motivo") ?? "") }
        : tipo === "aprovar" ? { tipo, por, mensagem: String(form.get("mensagem") ?? "").trim() || undefined }
          : { tipo, por } as Acao;
    const novo = aplicar(item, acao);
    if (typeof novo === "string") {
      mensagem = novo;
      throw new Error(novo);
    }
    await gravarItem(novo);
    mensagem = tipo === "aprovar" ? `aprovado por ${por}` : tipo === "rejeitar" ? "rejeitado" : tipo === "desaprovar" ? "aprovação desfeita" : "volta para a fila de publicação";
  } catch (e) {
    if (!mensagem) mensagem = (e as Error).message;
    await destravar(id);
    volta(mensagem);
  }
  await destravar(id);
  (await cookies()).set(COOKIE_NOME, por, { ...opcoesCookie, maxAge: 60 * 60 * 24 * 365 });
  volta(mensagem, "ok");
}

async function publicarAgora(form: FormData) {
  "use server";
  await exigirSessao();
  const id = String(form.get("id"));
  const depois = await publicarItem(id, Date.now() + 45_000, true);
  const msg = !depois ? "a peça já está sendo publicada por outro disparo"
    : depois.status === "publicado" ? "publicado"
      : depois.status === "publicando" ? "enviado — o Instagram ainda está processando; o agendador termina em alguns minutos"
        : depois.erro ?? `situação: ${depois.status}`;
  redirect(`/fila/${encodeURIComponent(id)}?${depois?.status === "erro" ? "erro" : "ok"}=${encodeURIComponent(msg)}`);
}

export default async function Peca({ params, searchParams }: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string>>;
}) {
  if (!armazenamento()) redirect("/fila");
  const { id } = await params;
  const q = await searchParams;
  const item = await lerItem(decodeURIComponent(id));
  if (!item) notFound();
  const nome = (await cookies()).get(COOKIE_NOME)?.value ?? "";
  const classeGaleria = `galeria ${item.tipo}`;

  const campoNome = (
    <label>Quem decide
      <input name="por" defaultValue={nome} required minLength={2} autoComplete="name" placeholder="Seu nome" />
    </label>
  );
  const oculto = <input type="hidden" name="id" value={item.id} />;

  return (
    <main style={{ maxWidth: 860 }}>
      <section className="cabeca">
        <p><Link href="/fila">← Fila</Link></p>
        <h1>{NOME_TIPO[item.tipo]} · @{item.cliente}</h1>
        <p className="sub">
          <span className={`estado ${item.status}`}>{NOME_STATUS[item.status]}</span>{" "}
          Publica em <strong>{quando(item.agendado_para)}</strong> (horário de Brasília).
        </p>
      </section>

      {q.ok && <p className="aviso ok" role="status">{q.ok}</p>}
      {q.erro && <p className="aviso erro" role="alert">{q.erro}</p>}
      {item.erro && item.status === "erro" && <p className="aviso erro"><strong>Último erro:</strong> {item.erro}</p>}
      {item.resultado?.permalink && (
        <p className="aviso ok">No ar: <a href={item.resultado.permalink} target="_blank" rel="noreferrer">{item.resultado.permalink}</a></p>
      )}

      <section className="cartao" aria-label="Prévia">
        <div className={classeGaleria}>
          {item.midias.map((m, k) =>
            m.video ? (
              <video key={m.url} src={m.url} controls playsInline preload="metadata" poster={item.capa?.url} />
            ) : (
              <img key={m.url} src={m.url} alt={`Peça ${k + 1} de ${item.midias.length}`} />
            ),
          )}
        </div>
        {item.tipo !== "story" && (
          <>
            <h2>Legenda</h2>
            <pre className="legenda">{item.legenda || "—"}</pre>
          </>
        )}
      </section>

      {item.status === "aguardando_aprovacao" && (
        <section className="grade-2">
          <form action={decidir} className="cartao">
            <h2>Aprovar</h2>
            <p className="sub">Aprova exatamente esta mídia, esta legenda e este horário. Qualquer mudança depois pede um novo “ok”.</p>
            {oculto}
            <input type="hidden" name="acao" value="aprovar" />
            {campoNome}
            <label>Observação (opcional)<input name="mensagem" maxLength={300} /></label>
            <button className="botao primario" type="submit">Aprovar e agendar</button>
          </form>
          <form action={decidir} className="cartao">
            <h2>Pedir ajuste</h2>
            <p className="sub">Volta para o estúdio com o motivo. A versão nova chega como outra peça.</p>
            {oculto}
            <input type="hidden" name="acao" value="rejeitar" />
            {campoNome}
            <label>O que mudar<textarea name="motivo" rows={3} required minLength={3} /></label>
            <button className="botao" type="submit">Rejeitar</button>
          </form>
        </section>
      )}

      {item.status === "aprovado" && (
        <section className="cartao">
          <h2>Aprovado por {item.aprovacao?.por}</h2>
          <p className="sub">
            Em {quando(item.aprovacao?.em)}{item.aprovacao?.origem === "estudio" ? ", no estúdio — conferido aqui pela impressão digital" : ""}.
            O agendador publica no horário marcado.
          </p>
          <div className="acoes">
            <form action={publicarAgora}>{oculto}<button className="botao primario" type="submit">Publicar agora</button></form>
          </div>
          <form action={decidir} className="acoes" style={{ alignItems: "end" }}>
            {oculto}
            <input type="hidden" name="acao" value="desaprovar" />
            {campoNome}
            <button className="botao" type="submit">Desfazer aprovação</button>
          </form>
        </section>
      )}

      {item.status === "erro" && (
        <section className="cartao">
          <h2>Não publicou</h2>
          <p className="sub">Corrija a causa (conta conectada, cota, mídia) e tente de novo. A aprovação continua valendo.</p>
          <form action={decidir} className="acoes" style={{ alignItems: "end" }}>
            {oculto}
            <input type="hidden" name="acao" value="tentar_de_novo" />
            {campoNome}
            <button className="botao primario" type="submit">Tentar de novo</button>
          </form>
        </section>
      )}

      {item.rejeicao && item.status === "rejeitado" && (
        <p className="aviso">Rejeitado por {item.rejeicao.por}: {item.rejeicao.motivo}</p>
      )}

      <section className="cartao">
        <h2>Histórico</h2>
        <ol className="historico">
          {item.historico.map((h, k) => <li key={k}>{quando(h.em)} — {h.evento}</li>)}
        </ol>
        <p className="sub" style={{ fontSize: "0.8rem" }}>Impressão digital: <code>{item.impressao.slice(0, 16)}…</code></p>
      </section>
    </main>
  );
}
