# Estúdio Social — webapp

Painel web para conectar o Instagram dos clientes e ver o que funciona no perfil
com as métricas de dentro da conta: alcance, salvamentos e compartilhamentos por
post, desempenho por formato e mapa de dia × horário.

Três formas de entrar:

| | Para quê | Precisa de |
|---|---|---|
| **Entrar com Instagram** | caminho curto: o dono autoriza e o app recebe o retorno sozinho | app da Meta + variáveis `IG_APP_ID`/`IG_APP_SECRET` |
| **Modo dev** | app da Meta em desenvolvimento: cola o token gerado no painel da Meta para uma conta testadora | só a senha do estúdio |
| **Demonstração** | ver o painel com uma conta fictícia | nada |

## Deploy na Vercel

1. **Add New → Project** → importe `andrehmontanha/redes-sociais`.
2. **Root Directory: `webapp`** (o resto do repositório é o estúdio em Python).
3. Framework: Next.js (detectado). Node 20+.
4. **Environment Variables** (ver `.env.example`):
   - `ESTUDIO_SENHA` — senha da equipe (8+ caracteres)
   - `SESSAO_SEGREDO` — `openssl rand -base64 48`
   - `IG_APP_ID`, `IG_APP_SECRET` — quando o app da Meta existir
5. Deploy. Sem `ESTUDIO_SENHA`/`SESSAO_SEGREDO` o app sobe **só com a demonstração**.

## App da Meta

1. developers.facebook.com → **Criar app** → caso de uso de API do Instagram com
   **login do Instagram**.
2. Em **Configurar login de empresa do Instagram**, cadastre a URI de redirecionamento
   `https://<seu-projeto>.vercel.app/api/instagram/callback` (a página **Modo dev** do
   app mostra a URI exata do deploy).
3. Permissões: `instagram_business_basic`, `instagram_business_manage_insights`,
   `instagram_business_content_publish`.
4. Em modo de desenvolvimento, adicione as contas como **testadoras do Instagram** (a
   pessoa aceita em Instagram → Configurações → Apps e sites). Para atender qualquer
   cliente, envie o app para a **Análise do app**.

## Segurança

- Tokens do Instagram ficam **criptografados (AES-256-GCM)** num cookie `httpOnly` do
  navegador que conectou — o JavaScript da página não lê, e nenhum banco guarda.
  Consequência: a conta conectada aparece só nesse navegador. Um banco (Supabase) para a
  equipe inteira compartilhar contas é o próximo passo.
- Tudo exige a senha do estúdio, menos `/entrar` e a demonstração.
- O login é o **oficial do Instagram**: o app nunca vê nem pede senha de Instagram.
  Não há — nem haverá — login por usuário e senha do Instagram dentro do app: isso viola
  os termos da Meta, bloqueia contas e expõe a senha do cliente.
- `state` anti-CSRF no OAuth, cabeçalhos de segurança, sem `X-Powered-By`.

## Ponte com o estúdio (Python)

“Baixar dados para o estúdio” gera o `bruto.json` que o pipeline do repositório lê:

```bash
python .claude/skills/conectar-instagram/scripts/sincronizar.py --cliente <handle> --de-arquivo bruto.json
```

Daí seguem análise, identidade visual e criativos com os dados de dentro.

## Desenvolvimento

```bash
cd webapp
npm install
cp .env.example .env.local   # preencha
npm run dev                  # http://localhost:3000
npm test                     # lógica: criptografia, resumo, fuso
npm run build
```
