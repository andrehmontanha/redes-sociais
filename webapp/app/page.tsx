import Link from "next/link";
import { oauthDisponivel, protegido } from "@/lib/config";
import { USUARIO_DEMO } from "@/lib/demo";
import { lerContas } from "@/lib/sessao";

export const dynamic = "force-dynamic";

function diasAte(iso: string) {
  return Math.round((Date.parse(iso) - Date.now()) / 86400_000);
}

export default async function Inicio({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const q = await searchParams;
  const contas = await lerContas();
  const seguro = protegido();
  const oauth = oauthDisponivel();

  return (
    <main>
      <section className="cabeca">
        <h1>Contas do Instagram</h1>
        <p className="sub">
          Conecte a conta profissional de um cliente para ler posts, mídia original e as métricas que só o dono
          vê — alcance, salvamentos, compartilhamentos — e descobrir o que funciona no perfil.
        </p>
      </section>

      {q.erro && <p className="aviso erro" role="alert"><strong>Não conectou:</strong> {q.erro}</p>}
      {q.desconectado && <p className="aviso ok">@{q.desconectado} desconectado deste navegador.</p>}
      {!seguro && (
        <div className="aviso erro" role="alert">
          <strong>Modo somente demonstração.</strong> Para conectar contas reais, defina <code>ESTUDIO_SENHA</code>{" "}
          (8+ caracteres) e <code>SESSAO_SEGREDO</code> (32+ caracteres) nas variáveis de ambiente da Vercel e faça
          um novo deploy. Sem elas o app não guarda tokens de ninguém.
        </div>
      )}

      <section className="grade-3" aria-label="Formas de conectar">
        <div className="cartao">
          <span className="selo">caminho curto</span>
          <h2>Entrar com Instagram</h2>
          <p className="sub">
            O dono da conta faz login na tela oficial do Instagram e autoriza. O app recebe o retorno sozinho e já
            abre o painel.
          </p>
          <div className="acoes">
            <a className="botao primario" href="/api/instagram/login" aria-disabled={!oauth}>Entrar com Instagram</a>
          </div>
          {!oauth && seguro && (
            <p className="sub">Falta configurar <code>IG_APP_ID</code> e <code>IG_APP_SECRET</code> — veja o <Link href="/modo-dev">modo dev</Link>.</p>
          )}
        </div>
        <div className="cartao">
          <span className="selo">app em desenvolvimento</span>
          <h2>Modo dev</h2>
          <p className="sub">
            Com o app da Meta em modo de desenvolvimento, gere o token da conta testadora no painel da Meta e cole
            no formulário. Bom para testar antes da análise do app.
          </p>
          <div className="acoes"><Link className="botao" href="/modo-dev" aria-disabled={!seguro}>Usar token de teste</Link></div>
        </div>
        <div className="cartao">
          <span className="selo">sem configuração</span>
          <h2>Demonstração</h2>
          <p className="sub">Painel completo com uma conta fictícia, para ver o que o app faz antes de configurar a Meta.</p>
          <div className="acoes"><Link className="botao" href={`/conta/${USUARIO_DEMO}`}>Abrir demonstração</Link></div>
        </div>
      </section>

      <section className="cartao" aria-labelledby="conectadas">
        <h2 id="conectadas">Conectadas neste navegador</h2>
        {contas.length === 0 ? (
          <p className="sub">Nenhuma conta conectada ainda.</p>
        ) : (
          <div className="rolagem">
            <table>
              <thead><tr><th>Conta</th><th>Tipo</th><th>Origem</th><th className="n">Token vence em</th><th /></tr></thead>
              <tbody>
                {contas.map((c) => {
                  const dias = diasAte(c.expira);
                  return (
                    <tr key={c.id}>
                      <td><Link href={`/conta/${encodeURIComponent(c.usuario)}`}>@{c.usuario}</Link></td>
                      <td>{c.tipo === "MEDIA_CREATOR" ? "criador" : c.tipo === "BUSINESS" ? "empresa" : c.tipo ?? "—"}</td>
                      <td>{c.origem === "oauth" ? "login do Instagram" : "token de teste"}</td>
                      <td className="n" style={{ color: dias < 10 ? "var(--erro)" : undefined }}>{dias} dias</td>
                      <td className="n">
                        <form action="/api/instagram/sair" method="post">
                          <input type="hidden" name="usuario" value={c.usuario} />
                          <button className="botao" type="submit">Desconectar</button>
                        </form>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="sub" style={{ fontSize: "0.85rem" }}>
          Os tokens ficam criptografados num cookie deste navegador (AES-256-GCM, inacessível ao JavaScript da
          página). Nenhum servidor de terceiros guarda as contas.
        </p>
      </section>
    </main>
  );
}
