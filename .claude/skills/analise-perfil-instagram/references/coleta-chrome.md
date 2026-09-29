# Coleta de dados no Chrome logado

O objetivo é sair com um `dados_<handle>.json` completo e honesto — inclusive sobre o que não deu para pegar.

## Ferramentas

Carregue tudo de uma vez (uma chamada só de `ToolSearch`):

```
select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__tabs_close_mcp
```

Comece por `tabs_context_mcp`. Não reaproveite IDs de aba de sessões anteriores — crie uma nova.

Use `browser_batch` para agrupar navegar → esperar → extrair de 2 a 3 posts por chamada. Uma coleta de 12 posts feita chamada a chamada leva o triplo do tempo e não fica mais segura. Feche a aba com `tabs_close_mcp` ao terminar.

**Nunca clique em botões que abrem diálogo modal** (`confirm`/`alert`) — isso trava a extensão e derruba a sessão.

## Cinco armadilhas que já quebraram esta análise

Leia antes de confiar em qualquer número. Todas foram observadas em coleta real.

### 1. A grade mistura posts próprios com collabs de terceiros

Publicações em colaboração aparecem na grade do perfil, mas a URL revela quem hospeda: `instagram.com/<outro_handle>/p/CODE/`. Elas **contam como conteúdo da grade, mas não como engajamento do perfil analisado** — vivem numa conta com outra base de seguidores, e calcular ER delas sobre os seguidores do cliente produz um número sem significado.

Separe sempre: `autor_proprio: true/false` e, quando falso, `anfitriao: "<handle>"`. A proporção entre os dois grupos costuma ser uma das descobertas mais fortes da análise — uma marca cuja grade recente é 60% conteúdo de criadores terceirizou a própria comunicação, e isso merece uma seção no relatório.

### 2. A ordem dos contadores da barra de ação

O bloco de números que aparece abaixo do post (ex.: `164 / 8 / 12`) é **curtidas / comentários / compartilhamentos**, nessa ordem. Quando o perfil esconde curtidas, sobram dois números e um parser ingênuo lê comentários como curtidas.

**Dois números não significam sempre curtidas + comentários.** Quando o post tem **zero comentários**, o Instagram omite aquele contador e a sequência vira `curtidas / compartilhamentos`. Uma conta nova, em que ninguém comentou ainda, é exatamente o caso em que o parser ingênuo inventa comentários que não existem.

O desempate é textual: se a página contém *"Ainda não há nenhum comentário"*, comentários é **zero** — e o segundo número é compartilhamento.

Confirme a ancoragem em vez de contar posições:

```js
[...document.querySelectorAll('[role="button"],button,svg[aria-label]')]
  .filter(e => /curtir|coment|compartil/i.test(e.getAttribute('aria-label')||''))
  .map(e => e.getAttribute('aria-label') + ' | ' +
       (e.closest('div')?.parentElement?.innerText||'').replace(/\n/g,'/').slice(0,40))
```

O vizinho do botão "Compartilhar" traz a sequência completa (`164/8/12`), o que confirma qual número é qual. Cheque também se existe a linha "Curtido por fulano e outras **N** pessoas": se ela aparece sem número, as curtidas estão ocultas naquele post.

### 3. A data do post é o *último* `<time>` da página

A página de um post contém vários `<time>`: os primeiros são timestamps de comentários. Pegue o último e leia o atributo `datetime`, nunca o texto visível ("há 3 semanas"):

```js
[...document.querySelectorAll('time')].map(e => e.getAttribute('datetime')).pop()
```

### 4. Post fixado no topo pode ter meses de idade

A grade abre pelos posts fixados, que podem ser bem antigos. Se ele entrar na amostra sem ressalva, a cadência calculada desaba (quatro posts em "244 dias" em vez de 18) e a média de engajamento mistura épocas diferentes.

Detecte pela data: se o primeiro item da grade for muito mais antigo que o segundo, é fixado. Registre em `observacoes.post_fixado_fora_da_amostra` e **não o inclua em `posts`**. O conteúdo dele ainda importa para a auditoria — o post fixado ocupa o espaço mais valioso da grade, e um comunicado burocrático ali é um achado.

### 5. Views de Reels não existem para o visitante

O contador de visualizações **não é exposto** a quem não é dono da conta na versão web, nem na página do Reel nem na miniatura da grade. Não prometa taxa de visualização no relatório; use `null` e registre a limitação. Compartilhamentos, que aparecem, são o melhor substituto disponível — e são um sinal mais forte que curtidas para o algoritmo.

## Sequência

### Passo 0 — Verificar o login

Abra `https://www.instagram.com/` e leia a página. Se aparecer o formulário de login, pare: peça ao usuário que entre no Chrome dele e avise quando terminar.

### Passo 1 — Página do perfil

Navegue para `https://www.instagram.com/<handle>/` e aguarde. Se o texto vier vazio, espere 2s e leia de novo.

A bio vem truncada com um "mais". Expanda antes de ler:

```js
(() => { const b = [...document.querySelectorAll('span,button,div[role="button"]')]
  .find(e => e.innerText === 'mais'); if (b) b.click(); return !!b; })()
```

Extraia com `get_page_text`:

| Campo | Observação |
|---|---|
| Nome de exibição | É o campo indexado na busca, junto do @ |
| Categoria profissional | Confira se bate com o negócio — categoria errada é achado de auditoria |
| Bio completa | Depois de expandir o "mais" |
| Link(s) | O texto exibido pode diferir do destino; "e mais 1" esconde links num modal. Registre o que conseguiu ver e marque o resto como não verificado |
| Publicações / Seguidores / Seguindo | Linha de contadores |
| Verificado, privado | Presença ou ausência |
| Nomes dos destaques, na ordem | O primeiro é o mais clicado |
| Botões de contato | E-mail, telefone, endereço, WhatsApp |

Números vêm abreviados no formato local: `12,4 mil` → 12400 · `1,2 mi` → 1200000 · `12.4K` → 12400 · `1.2M` → 1200000.

Tire **um screenshot da grade** com `computer`. Ele é a única fonte para avaliar identidade visual, paleta e legibilidade das capas.

### Passo 2 — Listar os posts recentes

```js
[...document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]')]
  .map(a => a.getAttribute('href'))
  .filter((v,i,arr) => v && arr.indexOf(v) === i)
  .slice(0, 15)
```

Se a grade tiver poucos itens carregados, role (`window.scrollBy(0, 2000)`), espere 2s e rode de novo.

**Alvo: 12 posts próprios.** Como parte da grade pode ser collab, colete até 15 URLs para chegar a 12 próprios. Se o perfil não tiver 9 posts próprios recentes, **pare e pergunte ao usuário** se quer ampliar a janela ou aceitar uma amostra indicativa — a diferença muda o peso de tudo que vem depois.

### Passo 3 — Cada post

Para cada URL, `navigate` e leia, com pausa de 2–4 segundos entre um e outro. Extraia:

- `url`, `autor_proprio`, `anfitriao` (quando collab)
- `data` — o último `<time>`, atributo `datetime`
- `formato`: `reel`, `carrossel` ou `imagem`. **O botão "Próximo" do carrossel só entra no DOM depois do hover** — testar por ele numa leitura fria devolve `false` até para carrossel de 10 slides. Passe o mouse sobre a mídia antes de testar, ou navegue direto por `?img_index=N`, que é mais confiável e ainda serve para capturar slide a slide
- `curtidas`, `comentarios`, `compartilhamentos` — ancorados pelo `aria-label`
- `visualizacoes` — sempre `null` (ver armadilha 5)
- `legenda` (até ~500 caracteres), `hashtags`, `tem_cta`
- `audio` — nos Reels, o nome do áudio aparece no topo ("Áudio original" ou o nome da faixa). É a ponte entre a análise e o módulo de tendências: um perfil que só usa "Áudio original" está fora de toda distribuição por áudio em alta
- `tema` — em 2–4 palavras, o assunto real do post. Vira a base dos pilares

Campos não coletados vão como `null`, nunca como zero. Zero é um dado; `null` é a ausência dele, e confundir os dois envenena todas as médias.

### Passo 4 — Amostra de comentários

Em 2–3 posts com engajamento acima da média, leia os comentários visíveis. O padrão importa mais que o conteúdo: são perguntas reais ou só emojis? A marca responde? **Há reclamações sem resposta?** Reclamação pública sem retorno na grade é um dos achados de maior impacto comercial que esta análise produz, e é invisível para quem só olha números.

Registre de forma agregada em `observacoes.padrao_comentarios`. Nunca liste @s de comentaristas no relatório.

## Formato do `dados_<handle>.json`

```json
{
  "handle": "exemplo",
  "coletado_em": "2026-08-26",
  "nicho": "turismo e hotelaria",
  "objetivo_cliente": "venda direta",
  "perfil": {
    "nome_exibicao": "Exemplo | Resort",
    "categoria": "Criador(a) de conteúdo digital",
    "bio": "...",
    "links": ["exemplo.com.br (+1 não verificado)"],
    "seguidores": 96900,
    "seguindo": 937,
    "publicacoes": 541,
    "verificado": false,
    "privado": false,
    "destaques": ["Pacotes", "Ingressos"],
    "botoes_contato": ["Endereço"]
  },
  "posts": [
    {
      "url": "https://www.instagram.com/exemplo/reel/ABC123/",
      "autor_proprio": true,
      "anfitriao": null,
      "data": "2026-08-24",
      "formato": "reel",
      "curtidas": 42, "comentarios": 6, "compartilhamentos": 3,
      "visualizacoes": null,
      "audio": "Áudio original",
      "legenda": "...", "hashtags": ["#exemplo"], "tem_cta": true,
      "tema": "promoção feriado"
    }
  ],
  "observacoes": {
    "curtidas_ocultas": false,
    "post_fixado_fora_da_amostra": {"url": "...", "data": "2025-12-23", "tema": "..."},
    "padrao_comentarios": "...",
    "screenshot_grade": "grade_exemplo.png",
    "falhas": []
  }
}
```

## Quando a coleta falha

| Sintoma | O que fazer |
|---|---|
| "Try again later" / desafio de segurança | Pare tudo. Avise que o Instagram limitou a conta e siga com o que já coletou. Não tente de novo na mesma sessão. |
| Página em branco ou texto vazio | Espere 2s e releia. Se persistir, recarregue a aba uma vez. Depois disso, registre em `falhas`. |
| Perfil privado e não seguido | Só o cabeçalho é auditável. Pare e pergunte se o usuário quer a auditoria parcial. |
| Curtidas ocultas | Registre `curtidas_ocultas: true`. `metricas.md` explica como ajustar a leitura. |
| Seletor JS retorna `undefined` | Caia para `get_page_text` e leia como humano. Não invente valor. |
| Extensão não responde | Depois de 2–3 tentativas, pare e explique o que tentou. Não repita a mesma chamada. |

Quando a falha atinge um dado que muda a conclusão — o número de seguidores, a amostra mínima, o acesso ao perfil — **pare e pergunte ao usuário** em vez de seguir com meia análise. Toda falha entra em `observacoes.falhas` e reaparece em "Limitações".
