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

## Fila de publicação (o webapp publica; o estúdio é o motor)

O estúdio em Python gera os criativos e envia para cá
(`.claude/skills/publicar-instagram/scripts/enviar_webapp.py`). Aqui a equipe aprova
em **/fila** vendo a prévia, e o agendador publica no horário. A trava é a mesma do
estúdio: a aprovação grava a impressão digital (sha256 da mídia + legenda + tipo +
horário, mesmo algoritmo do `fila.py`), e a publicação recalcula sobre os bytes no
Blob. Mudou qualquer coisa, precisa de novo “ok”.

Configuração, uma vez:

1. **Storage** no painel do projeto na Vercel:
   - **Create → Blob**, acesso **Public** (o Instagram baixa a mídia de lá, sem credencial;
     os nomes são aleatórios). Entra `BLOB_READ_WRITE_TOKEN`.
   - **Create → Upstash for Redis** pelo Marketplace (plano grátis serve). Entram
     `KV_REST_API_URL` e `KV_REST_API_TOKEN`.
   Marque Production (e Preview, se quiser testar em preview).
2. **Environment Variables**:
   - `ESTUDIO_API_CHAVE` — `openssl rand -base64 36`. O estúdio usa a mesma no `.env`.
   - `CRON_SECRET` — `openssl rand -base64 24`.
3. **Redeploy** de produção.
4. **Conecte as contas pelo webapp** (“Entrar com Instagram”): com o armazenamento
   ativo, o token fica no servidor (selado com AES-256-GCM) e o agendador publica sem
   navegador aberto. Conta conectada antes disso (só no cookie) precisa entrar de novo.
5. **Agendador** — o cron da Vercel no plano Hobby roda uma vez por dia (`vercel.json`,
   reforço às 12:00 de Brasília). Quem acerta o horário é o GitHub Actions
   (`.github/workflows/agendador.yml`, a cada 10 min — o GitHub pode atrasar alguns
   minutos em horário de pico). No GitHub: **Settings → Secrets and variables →
   Actions** → secret `CRON_SECRET` (o mesmo da Vercel). O workflow só roda a partir
   do branch padrão.

Estados: aguardando aprovação → aprovado → publicando → publicado (ou rejeitado/erro).
Erro mostra a causa e o botão “Tentar de novo”, que mantém a aprovação se nada mudou.
Post com avatar digital não entra por aqui: a checagem de consentimento é do estúdio.

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
  navegador que conectou — o JavaScript da página não lê. Com o armazenamento da fila
  ativo, ficam também no Redis, selados com a mesma criptografia, para o agendador
  publicar e a equipe inteira ver as mesmas contas. O agendador renova o token antes
  de vencer.
- Tudo exige a senha do estúdio, menos `/entrar`, a demonstração e as rotas de máquina:
  `/api/estudio/*` (chave `ESTUDIO_API_CHAVE`) e `/api/cron/*` (`CRON_SECRET`).
- A mídia enviada pelo estúdio fica no Blob com nome aleatório, sem sobrescrita. Vídeo
  é apagado depois de publicado.
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
