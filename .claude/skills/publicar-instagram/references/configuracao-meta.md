# Configuração da Meta e da hospedagem

Uma vez por estúdio (app + hospedagem) e uma vez por cliente (conta + token).

## 1. A conta do cliente

- Instagram **profissional**: Configurações → Tipo de conta e ferramentas → Mudar
  para conta profissional (Empresa ou Criador de conteúdo).
- Pelo caminho do **login do Facebook**: a conta precisa estar ligada a uma Página
  do Facebook, e quem gera o token precisa ter função na Página.
- Pelo caminho do **login do Instagram**: não precisa de Página.

## 2. O app na Meta (uma vez)

1. <https://developers.facebook.com/apps> → Criar app → tipo **Empresa**.
2. Adicione o produto **Instagram** e escolha um dos caminhos:

| Caminho | Host da API | Permissões |
|---|---|---|
| Login do Instagram (mais simples) | `graph.instagram.com` | `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_insights` |
| Login do Facebook | `graph.facebook.com` | `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `pages_read_engagement`, `pages_show_list` |

3. Enquanto o app está em modo de desenvolvimento, só contas com função no app
   (administrador, desenvolvedor, testador) publicam. Para contas de clientes, adicione
   cada uma como testadora do Instagram **ou** passe o app pela Análise do App da Meta
   com as permissões acima.

## 3. O token de cada cliente

1. Gere um token de usuário com as permissões (Explorador da Graph API ou fluxo de
   login do próprio app).
2. Troque por um token de **longa duração** (60 dias):
   - login do Instagram: `GET https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=<APP_SECRET>&access_token=<TOKEN_CURTO>`
   - login do Facebook: `GET https://graph.facebook.com/<versão>/oauth/access_token?grant_type=fb_exchange_token&client_id=<APP_ID>&client_secret=<APP_SECRET>&fb_exchange_token=<TOKEN_CURTO>`
3. Descubra o id da conta:
   - login do Instagram: `GET https://graph.instagram.com/me?fields=user_id,username&access_token=<TOKEN>`
   - login do Facebook: `GET https://graph.facebook.com/<versão>/me/accounts?fields=instagram_business_account{id,username}&access_token=<TOKEN>`
4. Grave no `.env` da raiz (que o `.gitignore` já exclui):

```bash
IG_GRAPH_HOST=graph.instagram.com
IG_GRAPH_VERSION=v23.0
IG_THERMASDEOLIMPIARESORT_USER_ID=17841400000000000
IG_THERMASDEOLIMPIARESORT_TOKEN=IGAA...
```

`<HANDLE>` = o @ em maiúsculas, com `.` e outros símbolos trocados por `_`.

5. Confira: `python .claude/skills/publicar-instagram/scripts/publicar.py conta --cliente <handle>`

**Renovação:** o token de longa duração vale 60 dias. Renove antes
(`grant_type=ig_refresh_token` no login do Instagram) — uma rotina mensal resolve.
Token é credencial do cliente: nunca em commit, chat, log ou prévia.

## 4. Hospedagem da mídia (uma vez)

A API busca a mídia por URL. Usamos um bucket **privado** do Supabase Storage com URL
assinada de 1 hora, apagada depois da publicação.

1. No projeto Supabase: Storage → New bucket → `instagram-fila`, **Public: desligado**.
   Limite de arquivo ≥ 300 MB se for subir Reels longos.
2. `.env`:

```bash
SUPABASE_URL=https://<projeto>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...        # Settings → API → service_role
SUPABASE_BUCKET=instagram-fila
```

3. Teste: `python .claude/skills/publicar-instagram/scripts/hospedar.py algum.jpg teste/algum.jpg`
   deve imprimir uma URL que abre a imagem no navegador.

## 5. Rodando no Claude Code na web (rotinas)

O ambiente de nuvem precisa liberar a saída para `graph.facebook.com` ou
`graph.instagram.com`, `*.supabase.co`, `fonts.googleapis.com`, `fonts.gstatic.com`
e `registry.npmjs.org`. Configure na política de rede do ambiente, e as credenciais
como variáveis de ambiente do ambiente (não no repositório).
