import { headers } from "next/headers";
import { config, oauthDisponivel, protegido, redirectOAuth } from "@/lib/config";

export const dynamic = "force-dynamic";

export default async function ModoDev({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const q = await searchParams;
  const h = await headers();
  const origem = `${h.get("x-forwarded-proto") ?? "http"}://${h.get("host")}`;
  const redirect = redirectOAuth(origem);

  return (
    <main>
      <section className="cabeca">
        <h1>Modo dev</h1>
        <p className="sub">
          Enquanto o app da Meta está em <strong>modo de desenvolvimento</strong>, só contas adicionadas como
          testadoras conseguem autorizar. Há dois jeitos de testar: pelo login do Instagram (com a conta testadora)
          ou colando aqui o token que o próprio painel da Meta gera.
        </p>
      </section>

      {q.erro && <p className="aviso erro" role="alert"><strong>Token recusado:</strong> {q.erro}</p>}
      {q.faltando === "app" && (
        <p className="aviso erro" role="alert">
          O botão “Entrar com Instagram” precisa de <code>IG_APP_ID</code> e <code>IG_APP_SECRET</code> nas variáveis de
          ambiente. Enquanto isso, use o token de teste abaixo.
        </p>
      )}

      <div className="grade-2">
        <section className="cartao" aria-labelledby="t-token">
          <h2 id="t-token">Colar token de teste</h2>
          <ol className="lista-passos">
            <li>Em <strong>developers.facebook.com → seu app → Instagram → Configuração da API com login do Instagram</strong>.</li>
            <li>Em <strong>Gerar tokens de acesso</strong>, adicione a conta do Instagram (ela precisa aceitar o convite de testadora em Instagram → Configurações → Apps e sites).</li>
            <li>Clique em <strong>Gerar token</strong>, faça login com a conta e copie o token.</li>
            <li>Cole abaixo. O app confere o token com a API antes de guardar.</li>
          </ol>
          <form action="/api/instagram/token" method="post" style={{ display: "grid", gap: 12 }}>
            <label>Token de acesso
              <textarea name="token" rows={3} required spellCheck={false} autoComplete="off" disabled={!protegido()}
                placeholder="IGAA…" />
            </label>
            <div className="acoes">
              <button className="botao primario" type="submit" disabled={!protegido()}>Conectar com o token</button>
            </div>
          </form>
          <p className="sub" style={{ fontSize: "0.85rem" }}>
            O token vai direto para este app e fica criptografado num cookie deste navegador. Não cole token em chat,
            e-mail ou planilha.
          </p>
        </section>

        <section className="cartao" aria-labelledby="t-app">
          <h2 id="t-app">Configurar o login do Instagram</h2>
          <ol className="lista-passos">
            <li>Crie o app em <strong>developers.facebook.com</strong> com o caso de uso de API do Instagram (login do Instagram).</li>
            <li>Em <strong>Configurar login de empresa do Instagram</strong>, cadastre esta URI de redirecionamento:<br /><code>{redirect}</code></li>
            <li>Permissões: <code>instagram_business_basic</code>, <code>instagram_business_manage_insights</code>, <code>instagram_business_content_publish</code>.</li>
            <li>Na Vercel, em <strong>Settings → Environment Variables</strong>: <code>IG_APP_ID</code> e <code>IG_APP_SECRET</code> (os do app <em>do Instagram</em>, não do Facebook).</li>
            <li>Para atender qualquer cliente sem convite de testador, envie o app para a <strong>Análise do app</strong> da Meta.</li>
          </ol>
          <dl className="sub" style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 12px", margin: 0 }}>
            <dt>Senha do estúdio</dt><dd style={{ margin: 0 }}>{protegido() ? "configurada" : "falta"}</dd>
            <dt>App da Meta</dt><dd style={{ margin: 0 }}>{oauthDisponivel() ? `configurado (${config.igAppId.slice(0, 4)}…)` : "falta"}</dd>
            <dt>Versão da API</dt><dd style={{ margin: 0 }}>{config.graphVersao}</dd>
          </dl>
        </section>
      </div>
    </main>
  );
}
