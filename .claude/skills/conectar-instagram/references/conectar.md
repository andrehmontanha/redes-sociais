# App da Meta para o Login do Instagram (uma vez por estúdio)

1. <https://developers.facebook.com/apps> → **Criar app** → caso de uso **Gerenciar
   mensagens e conteúdo no Instagram** (API do Instagram com login do Instagram).
2. Em **API do Instagram → Configuração da API com login do Instagram**:
   - anote o **ID do app do Instagram** e a **chave secreta do app do Instagram**
     (não são os do app do Facebook);
   - em **Configurar login de empresa do Instagram**, cadastre a **URI de
     redirecionamento OAuth** — precisa ser HTTPS. Qualquer página sua serve (o site do
     estúdio, uma página estática); o código chega na URL, a página não precisa fazer nada.
3. Permissões: `instagram_business_basic`, `instagram_business_manage_insights`,
   `instagram_business_content_publish`.
4. Enquanto o app está em **modo de desenvolvimento**, só contas adicionadas como
   **testadoras do Instagram** (Funções do app → Testadores do Instagram; a pessoa
   aceita o convite em Instagram → Configurações → Apps e sites → Convites de testador)
   conseguem autorizar. Para atender qualquer cliente sem convite, envie o app para
   **Análise do app** com as três permissões e a verificação de empresa.
5. `.env`:

```bash
IG_APP_ID=...
IG_APP_SECRET=...
IG_REDIRECT_URI=https://seu-dominio.com.br/instagram/retorno
IG_GRAPH_VERSION=v23.0
```

O `conectar.py trocar` grava por cliente: `IG_<HANDLE>_USER_ID`, `IG_<HANDLE>_TOKEN`,
`IG_<HANDLE>_TOKEN_EXPIRA` e `IG_<HANDLE>_GRAPH_HOST=graph.instagram.com`. O publicador
usa essas mesmas chaves.

## Privacidade (LGPD)

- O estúdio age como **operador** dos dados da conta do cliente: use só para o
  contrato de social media, e registre a base legal no contrato.
- Comentários e dados de seguidores entram de forma agregada nos relatórios, nunca
  como lista nominal.
- Fim de contrato: `desconectar`, apague `clientes/<handle>/instagram/` se o contrato
  pedir, e oriente a remoção do app na conta.
