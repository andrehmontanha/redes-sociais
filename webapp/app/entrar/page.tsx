import { redirect } from "next/navigation";
import { config, protegido } from "@/lib/config";
import { iguais } from "@/lib/cripto";
import { iniciarSessao } from "@/lib/sessao";

async function entrar(form: FormData) {
  "use server";
  const senha = String(form.get("senha") ?? "");
  const volta = String(form.get("volta") ?? "/");
  const destino = volta.startsWith("/") && !volta.startsWith("//") ? volta : "/";
  if (!protegido() || !iguais(senha, config.senha)) {
    await new Promise((r) => setTimeout(r, 700)); // freia tentativa em série
    redirect(`/entrar?erro=1&volta=${encodeURIComponent(destino)}`);
  }
  await iniciarSessao();
  redirect(destino);
}

export default async function Entrar({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const q = await searchParams;
  return (
    <main style={{ maxWidth: 440 }}>
      <section className="cabeca">
        <h1>Entrar no estúdio</h1>
        <p className="sub">Acesso da equipe. A demonstração continua aberta sem senha.</p>
      </section>
      {!protegido() && (
        <p className="aviso erro">Senha do estúdio não configurada — defina <code>ESTUDIO_SENHA</code> e <code>SESSAO_SEGREDO</code>.</p>
      )}
      {q.erro && <p className="aviso erro" role="alert">Senha incorreta.</p>}
      <form action={entrar} className="cartao">
        <input type="hidden" name="volta" value={q.volta ?? "/"} />
        <label>Senha do estúdio
          <input type="password" name="senha" autoComplete="current-password" required autoFocus />
        </label>
        <button className="botao primario" type="submit">Entrar</button>
      </form>
    </main>
  );
}
