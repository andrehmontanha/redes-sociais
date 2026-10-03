---
name: publicar-instagram
description: Leva criativos prontos à publicação no Instagram com aprovação humana obrigatória — fila de publicação, prévia para o aprovador, trava por impressão digital (nada muda depois do "ok"), hospedagem temporária da mídia, publicação pela Instagram Graph API (post, carrossel, Reel, story), agendamento e coleta de métricas. Use quando pedirem para publicar, postar, agendar, subir para o Instagram, montar a fila, aprovar ou rejeitar um post, ou ver o desempenho de algo publicado.
---

# Publicar no Instagram — com aprovação

**Nada vai ao ar sem um humano dizer "aprovado".** O agente cria, revisa, monta a
prévia e espera. A aprovação é registrada com nome, horário e a impressão digital
exata do que foi aprovado; o publicador recusa qualquer coisa que tenha mudado
depois disso.

## Onde publica: o webapp (padrão)

O estúdio é o **motor**: gera, revisa e põe na fila local. Quem aprova, agenda e
publica é o **webapp** (`webapp/`, na Vercel), que fica no ar sem depender de uma
sessão do Claude:

```bash
python .claude/skills/publicar-instagram/scripts/fila.py criar ...            # item local, como sempre
python .claude/skills/publicar-instagram/scripts/enviar_webapp.py enviar clientes/<handle>/fila/<item>
python .claude/skills/publicar-instagram/scripts/enviar_webapp.py enviar --cliente <handle> --todos
python .claude/skills/publicar-instagram/scripts/enviar_webapp.py status --cliente <handle>
```

- Item em rascunho ou aguardando aprovação chega ao webapp **aguardando aprovação**:
  a equipe aprova lá, em `/fila`, vendo a prévia e digitando o nome. Mande o link.
- Item já aprovado no estúdio (`fila.py aprovar`, com o "ok" explícito no chat) leva
  a aprovação junto; o webapp recalcula a impressão digital sobre os bytes e recusa
  se não bater.
- Depois de enviado, o `post.json` ganha o campo `webapp` e o `publicar.py` recusa o
  item — nunca publicam os dois.
- Post com **avatar digital** não vai ao webapp (a checagem de consentimento é daqui):
  segue o fluxo abaixo, pelo `publicar.py`.
- Precisa de `ESTUDIO_API_CHAVE` (a mesma da Vercel) no `.env`, `cd webapp && npm install`
  uma vez, e rede liberada para o domínio do webapp, `vercel.com` e `*.blob.vercel-storage.com`.

O restante desta skill descreve a fila local e o `publicar.py`, que continuam valendo
para avatar e como alternativa sem o webapp.

## Pré-requisitos (uma vez por cliente)

Leia `references/configuracao-meta.md`. Em resumo:

1. Conta do Instagram **profissional** (Business ou Creator); no login pelo
   Facebook, ligada a uma Página.
2. App na Meta com `instagram_business_basic` e `instagram_business_content_publish`
   (login do Instagram) ou `instagram_basic` + `instagram_content_publish` +
   `pages_read_engagement` (login do Facebook).
3. `.env` na raiz: `IG_<HANDLE>_USER_ID`, `IG_<HANDLE>_TOKEN`, `IG_GRAPH_HOST`,
   `IG_GRAPH_VERSION`, e a hospedagem (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
   `SUPABASE_BUCKET`).
4. Conferir: `python .claude/skills/publicar-instagram/scripts/publicar.py conta --cliente <handle>`

## Fluxo

### 1. Pôr na fila

Com o criativo pronto e revisado (skills `criativos-imagem` / `criativos-video`):

```bash
python .claude/skills/publicar-instagram/scripts/fila.py criar --cliente <handle> --tipo carrossel \
    --midias clientes/<handle>/criativos/<id>/render/0*.jpg \
    --legenda-arquivo clientes/<handle>/criativos/<id>/legenda.txt \
    --agendar 2026-10-02T18:00-03:00
```

Tipos: `feed` (1 JPEG) · `carrossel` (2–10 JPEG/MP4) · `reel` (1 MP4, `--capa` ou
`--thumb-offset-ms`) · `story` (1 JPEG ou MP4, sem legenda).

A mídia é **copiada** para `clientes/<handle>/fila/<item>/` (congelada). Os créditos
de som CC-BY (`*.creditos.txt`) entram sozinhos na legenda. A legenda é validada:
≤ 2.200 caracteres, ≤ 30 hashtags, ≤ 20 menções.

**Legenda:** na `voz` do brand kit — gancho na primeira linha (é o que aparece
antes do "mais"), corpo curto, CTA do kit, hashtags fixas + 3 a 8 do tema. Horário:
o melhor da análise para esse perfil, não um genérico.

### 2. Prévia e pedido de aprovação

```bash
python .claude/skills/publicar-instagram/scripts/fila.py previa clientes/<handle>/fila/<item>
```

Envie `previa.html` com `SendUserFile` (display `render`) e pergunte, numa mensagem
só: o que é, quando vai ao ar, e "Aprova? Responda 'aprovado' com seu nome, ou diga
o que ajustar". Vários itens da mesma semana podem ir juntos, cada um identificado.

### 3. Registrar a decisão — só com resposta humana explícita

- Resposta clara de aprovação ("aprovado", "pode postar", "ok, manda") **com nome**:
  ```bash
  python .claude/skills/publicar-instagram/scripts/fila.py aprovar clientes/<handle>/fila/<item> \
      --por "Nome" --mensagem "<texto da resposta>"
  ```
  Sem nome, pergunte o nome — não aprove sem.
- Pedido de ajuste: `fila.py rejeitar … --motivo "…"`, corrija o criativo, crie um
  item **novo** e mande nova prévia. Item rejeitado não se reaproveita.
- Silêncio, "vou ver", "parece bom mas…", aprovação de outro item: **não é aprovação.**

O Claude Code pede confirmação de permissão antes de rodar `aprovar` e `publicar.py`
(regra em `.claude/settings.json`) — é a segunda chave da trava. Não contorne.

### 4. Publicar

```bash
python .claude/skills/publicar-instagram/scripts/publicar.py --simular item clientes/<handle>/fila/<item>  # ensaio
python .claude/skills/publicar-instagram/scripts/publicar.py item clientes/<handle>/fila/<item>            # respeita o horário
python .claude/skills/publicar-instagram/scripts/publicar.py item clientes/<handle>/fila/<item> --agora    # já
```

A Graph API não agenda post de feed. O agendamento é nosso: uma **rotina** do Claude
Code roda `publicar.py vencidos` de hora em hora e publica o que está aprovado e com
horário vencido. Configure uma vez por estúdio (`/schedule` ou pela rotina na web).

O publicador confere a cota (`content_publishing_limit`, normalmente 100 posts em 24 h),
sobe a mídia para URL assinada de 1 h, cria o container, espera o processamento do
vídeo, publica, grava o permalink no `post.json` e apaga a mídia hospedada.

### 5. Depois

```bash
python .claude/skills/publicar-instagram/scripts/publicar.py metricas clientes/<handle>/fila/<item>
```

Colete em 24 h e em 7 dias. As métricas acumulam no `post.json` e alimentam a próxima
análise (`analise-perfil-instagram`): é assim que o estúdio aprende o que funciona
para cada cliente, com números de dentro e não estimativas de fora.

## Erros comuns

| Erro | Causa | O que fazer |
|---|---|---|
| `credenciais ausentes` | `.env` sem `IG_<HANDLE>_*` | `references/configuracao-meta.md` |
| code 190 | token expirado | renovar token de longa duração (60 dias) |
| code 9004 / 2207052 | a Meta não conseguiu baixar a mídia | URL expirada ou bucket inacessível — rode de novo |
| code 2207026 | vídeo fora da especificação | `validar_reel.py`, corrigir e recriar o item |
| `cota de publicação esgotada` | limite de 24 h | publicar depois; `vencidos` tenta de novo na próxima hora |
| `status 'erro'` | falha anterior | leia `historico` no `post.json`; corrija; crie item novo e peça nova aprovação |
