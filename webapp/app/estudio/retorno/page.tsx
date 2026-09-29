import { urlDoApp } from "@/lib/config";
import Copiar from "./Copiar";

export const dynamic = "force-dynamic";

// Retorno do OAuth iniciado pelo ESTÚDIO (conectar.py url), não pelo webapp.
// O webapp não troca o código: só mostra a URL completa para colar no chat do
// estúdio, onde `conectar.py trocar` confere o state e troca pelo token.
export default async function RetornoEstudio({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const q = await searchParams;
  const url = `${urlDoApp()}/estudio/retorno?${new URLSearchParams(q)}`;

  return (
    <main style={{ maxWidth: 720 }}>
      <section className="cabeca">
        <h1>Conectar ao estúdio</h1>
        {q.error ? (
          <p className="aviso erro" role="alert">
            <strong>Autorização negada:</strong> {q.error_description ?? q.error}. Gere um novo link no estúdio.
          </p>
        ) : q.code && q.state ? (
          <p className="sub">
            Autorização recebida. Copie a URL abaixo e cole no chat do estúdio (Claude Code). Ela vale uma vez só,
            por poucos minutos, e só funciona com o link que o estúdio gerou.
          </p>
        ) : (
          <p className="aviso erro">Esta página só faz sentido depois de autorizar pelo link gerado no estúdio.</p>
        )}
      </section>
      {q.code && q.state && !q.error && (
        <section className="cartao">
          <label>URL de retorno
            <textarea readOnly rows={4} value={url} spellCheck={false} style={{ fontFamily: "ui-monospace, monospace", fontSize: "0.85rem" }} />
          </label>
          <div className="acoes"><Copiar texto={url} /></div>
          <p className="sub" style={{ fontSize: "0.85rem" }}>
            Não é senha nem token: é um código de uso único que só vira token no estúdio, com a chave secreta do app.
          </p>
        </section>
      )}
    </main>
  );
}
