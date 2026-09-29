---
name: analise-perfil-instagram
description: Analisa perfis do Instagram, cruza com tendências, estuda vídeo de referência e captura o material visual — auditoria de bio, pilares de conteúdo, engajamento calibrado por nicho, benchmark de concorrentes, biblioteca de anúncios da Meta e do Google, tendências e áudios em alta, calendário editorial, roteiros de Reel, teardown de vídeo quadro a quadro, e download de imagens prontas para site. Use ao mencionar analisar, auditar ou diagnosticar um perfil do Instagram, @arroba, conta, feed ou concorrente; pedir taxa de engajamento, raio-x, ideias de conteúdo, pauta, calendário, o que postar, tendências, trends, áudios em alta; perguntar que anúncios a marca ou o concorrente roda, biblioteca de anúncios, ad library, transparência de anúncios, mídia paga; pedir para assistir ou destrinchar um Reel, entender por que um conteúdo funciona, estudar referência de criador; ou pedir para raspar conteúdo, baixar imagens, montar moodboard ou reunir assets para um site. Vale também ao colar um link instagram.com.
---

# Análise de perfil no Instagram

Esta skill transforma um @ em um diagnóstico defensável e num plano do que postar em seguida: o que o perfil comunica, o que publica, como o público responde, o que o nicho está fazendo agora e quais tendências ainda têm janela aberta para essa marca entrar.

O público-alvo típico é um consultor de social media atendendo **carteira de clientes de nichos variados**. Logo, nada aqui pode assumir um setor fixo: os benchmarks se calibram pelo nicho detectado, e os perfis de referência são descobertos a cada análise.

## Princípio que rege tudo aqui

Números de Instagram observados de fora são **estimativas**, não verdade absoluta. Só o dono da conta vê alcance, impressões e salvamentos. Curtidas podem estar ocultas, views de Reels não aparecem para visitantes na web, e a amostra é sempre pequena. Isso não invalida a análise — invalida a *falsa precisão*.

Nunca invente um número. E quando faltar um dado que muda a conclusão, **pare e pergunte ao usuário** antes de seguir: ele quase sempre tem acesso ao Insights do cliente, ou sabe o contexto que fecha a lacuna. Só siga sozinho se ele estiver claramente ausente — e, nesse caso, marque a lacuna em destaque no relatório.

## Modo dossiê — quando a skill vira agente

Esta skill cobre a análise de um perfil. Quando o pedido é **dossiê** — acervo
completo, material baixado de concorrentes e de tendências, raspagem de sites,
tudo num diretório escolhido pelo usuário — quem conduz é o agente
`dossie-social`, em `agent/dossie-social.md`.

Instale copiando esse arquivo para `.claude/agents/` e chame com o Task/Agent.
Ele usa esta skill como base metodológica e acrescenta três coisas:

- **cotas obrigatórias de acervo** — 3 vídeos do cliente, 3 de concorrentes, 3 de
  tendência, 5 áudios e 10 imagens, conferidos no disco;
- **caçada de tendências em quatro plataformas** (`references/cacada-de-tendencias.md`)
  — YouTube, TikTok, Instagram e X, com o mesmo conjunto de termos;
- **raspagem dos sites** (`references/raspagem.md`) — o que a marca vende, que
  nem o feed nem a biblioteca de anúncios contam.

A trava roda com `--dossie` e passa a exigir tudo isso.

## Limites de uso

A coleta acontece no navegador do próprio usuário, olhando o que qualquer visitante logado veria. Isso é leitura, não raspagem em massa.

- Só perfis públicos, ou privados que a conta logada já segue. Nunca tente contornar privacidade.
- Nada de curtir, seguir, comentar ou enviar DM durante a análise — só navegação e leitura.
- Ritmo humano: pausa de 2–4 segundos entre navegações. Rajadas disparam o rate limit e podem bloquear temporariamente a conta do usuário. Se aparecer "Try again later" ou um desafio de login, **pare imediatamente**, avise e siga com o que já tem.
- Nunca clique em botões que abrem diálogo modal (`confirm`/`alert`) — isso trava a extensão do Chrome e derruba a sessão.
- Dados de pessoas físicas entram de forma agregada, nunca como lista nominal.

## Fluxo de trabalho

### 0. Abrir o projeto — sempre, antes de qualquer coleta

Toda análise ganha pasta própria no computador do usuário, e nada é coletado antes dela existir. Uma análise produz JSON de coleta, dezenas de imagens, vídeos de referência, moodboard, relatório em dois formatos e um zip — despejar isso solto mistura o material de um cliente com o de outro.

**Peça permissão primeiro** e proponha o caminho. Com o "sim", **quem cria é você** — o usuário autorizou, fazer o trabalho é seu.

**A raiz é sempre o @ do cliente**, e cada análise é uma subpasta datada:

```
<PASTA_BASE>/
└── thermasdeolimpiaresort/          ← o @ do cliente, nunca muda
    ├── analise - 15-06-2026/         ← análise anterior, preservada
    ├── analise - 27-08-2026/         ← esta análise
    │   ├── dados/  assets/  entregas/
    └── perfis de comparação/
        └── enjoyolimpiaparkresort/
            └── analise - 27-08-2026/
```

**Se a pasta do @ já existir, some uma subpasta — nunca sobrescreva.** Confira com `device_list_dir` antes de criar. Análise nova não substitui a anterior porque **é a série que permite dizer "melhorou"**; sem histórico, toda análise recomeça do zero e o consultor fica repetindo diagnóstico. Se já houver uma análise da mesma data, acrescente `(2)` — análise do mesmo dia é revisão, não substituição.

```bash
python scripts/abrir_projeto.py --handle <handle> --tipo cliente \
    --segmento "<...>" --oferta <produtos|servicos|ambos> \
    --objetivo "<...>" --frequencia "<...>" --nicho <nicho> \
    --pasta-base "<caminho aprovado>" --saida projeto/

# para cada perfil de comparação:
python scripts/abrir_projeto.py --handle <concorrente> --tipo comparacao \
    --cliente <handle-do-cliente> --pasta-base "<...>" --saida projeto/
```

Entregue o README com `SendUserFile` e grave com `device_commit_files` no caminho impresso. **É a gravação do arquivo que cria a árvore de diretórios** — não há shell na máquina do usuário, então `mkdir` não existe por essa ponte. As subpastas (`dados/`, `assets/`, `entregas/`) nascem quando o primeiro arquivo cair em cada uma.

**Se não houver aparelho conectado, ou o usuário recusar:** trabalhe no workspace da sessão com a mesma estrutura e entregue por `SendUserFile`. Diga em uma frase que os arquivos ficam só na conversa e somem com a sessão — a escolha precisa ser informada.

### 0.1 Consolidar o histórico, quando já houver série

Se a pasta do @ já tinha análises, leia-as **antes** de coletar de novo. É isso que transforma um relatório avulso numa leitura de evolução.

1. `device_list_dir --recursive` na pasta do cliente para mapear o que existe.
2. `device_stage_files` nos `dados/metricas-*.json` de cada análise anterior — do cliente e dos perfis de comparação.
3. Rode o consolidador:

```bash
python scripts/historico.py --pasta <staged> --cliente <handle> --saida historico.md
```

Ele devolve a evolução do cliente ao longo do tempo, a posição relativa dentro do nicho e um alerta de defasagem. Duas exclusões estão embutidas e são deliberadas: **perfil de nicho diferente não entra no ranking** (ER de B2B e de turismo vivem em escalas distintas) e **base abaixo de 1.000 seguidores também não** (5 curtidas em 31 seguidores dão 14% de ER e apareceriam como líder). Os excluídos continuam valendo como referência de formato — só não entram na comparação numérica.

O histórico entra no relatório como seção própria, e muda o tom da entrega: em vez de "o engajamento está baixo", vira "o engajamento subiu 50% desde junho e a base cresceu 6% junto" — que é uma frase que só existe porque a pasta anterior foi preservada.

**Perfil defasado não compara.** Se a última análise de um perfil de comparação tem mais de 30 dias, recolete antes de usar. Número velho contra número novo produz conclusão errada, e o script sinaliza isso.

### 1. As perguntas de abertura

Antes de qualquer coleta, e de uma vez só, pergunte:

1. **Em qual segmento o cliente atua?** — define o nicho e, com ele, a régua de engajamento. Sem isso o veredito sai errado com número certo.
2. **O cliente vende produtos ou serviços?** — produto se vende mostrando; serviço se vende provando. Muda o peso da prova social e o tipo de CTA recomendado.
3. **Qual é o objetivo principal?** — venda direta, alcance, autoridade ou comunidade. Reordena o plano de ação inteiro e não dá para adivinhar.
4. **Com que frequência ele posta hoje?** — a resposta declarada raramente bate com a cadência medida, e a diferença entre as duas costuma ser um dos achados mais úteis do relatório.

Aproveite a mesma rodada para confirmar: acesso ao Insights, apetite para trends (conservador / equilibrado / agressivo) e o caminho da pasta do projeto.

**Guarde as respostas no README do projeto.** Elas são o contrato da análise — daqui a três meses é o que explica por que o benchmark foi aquele e por que o plano priorizou o que priorizou.

### 2. Coletar o perfil

Leia `references/coleta-chrome.md` **antes** da primeira chamada de navegador. Ele traz a sequência, os seletores que funcionam, e as cinco armadilhas que já quebraram esta análise antes: posts em collab hospedados em contas de terceiros, a ordem dos contadores da barra de ação, qual `<time>` é a data do post, post fixado antigo no topo da grade e views de Reels indisponíveis.

Salve em `dados_<handle>.json`. Esse arquivo é a fonte da verdade: todo número do relatório precisa ser rastreável até ele.

### 3. Detectar o nicho e calibrar

Antes de julgar qualquer métrica, nomeie o nicho a partir da bio, da categoria e dos temas dos posts. `references/metricas.md` traz a tabela de calibração por setor — um ER de 1,2% é fraco para gastronomia e excelente para B2B industrial. Sem esse passo, o veredito sai errado com número certo.

### 4. Calcular

```bash
python scripts/calcular_metricas.py dados_<handle>.json --nicho <nicho>
```

O script separa **posts próprios de collabs** (collab hospedado em conta de terceiro tem base de seguidores diferente e não pode virar ER do cliente), ignora post fixado fora da janela, e devolve ER médio e mediano, distribuição por formato e pilar, cadência, proporção comentário/curtida e o benchmark já ajustado ao nicho.

### 5. Auditar e analisar

`references/auditoria.md` traz a rubrica do perfil (bio, foto, destaques, link, categoria) e o método de análise de conteúdo.

O trabalho difícil não é listar o que existe — é explicar **por que** o que performa performa. "Os Reels sobre a cultura da cidade tiveram 3x o engajamento dos Reels promocionais" é uma descoberta. "Poste mais Reels" é ruído que o cliente já ouviu.

### 6. Cruzar com tendências

Leia `references/tendencias.md`. Esse é o módulo que separa um relatório de diagnóstico de um plano de conteúdo. Ele cobre:

- como coletar o que está circulando agora (Explorar, Reels em alta, áudios em alta) e nos perfis de referência do nicho;
- as **duas camadas de recorte** que este usuário quer: tendências do nicho e da região do cliente, e tendências gerais do Instagram brasileiro;
- a descoberta dos perfis de referência — a skill **sugere de 5 a 8 e espera aprovação** antes de coletar;
- **a mineração dos seguidos do próprio perfil**, que é a fonte de referência mais honesta que existe: quem uma marca segue revela o nicho real dela, os concorrentes que ela observa e os criadores que orbitam o negócio;
- **o filtro de "em alta"** — referência precisa estar performando agora, não ter performado um dia;
- a rubrica de aderência de 0 a 10;
- o modelo de ciclo de vida que estima quanto tempo a trend ainda rende.

```bash
python scripts/ciclo_tendencia.py tendencias_<handle>.json
```

### 6.1 Perfis de comparação — obrigatório, mínimo 3

**Esta etapa não é opcional e não aceita ser pulada.** Um perfil de comparação sozinho não é benchmark, é anedota: não dá para saber se o número do cliente é bom, ruim ou apenas típico do setor. E reaproveitar a comparação de uma análise anterior não conta — perfil de comparação precisa ser coletado nesta rodada, ou explicitamente marcado como defasado.

**Mínimo 3, ideal de 5 a 8.** Se você não conseguir 3, isso é um resultado a relatar — "só encontrei 2 concorrentes ativos no nicho e na região" é uma frase legítima — e não uma licença para seguir com um.

Como montar a lista:

1. **Minere os seguidos do cliente** (`references/tendencias.md`, seção B1). É a fonte mais honesta: quem a marca segue revela concorrentes reais, imprensa local e criadores do setor.
2. **Complete com busca** por termos do nicho e da cidade.
3. **Aplique o filtro de "em alta"** (seção B2): publicou nos últimos 7 dias, ao menos 3 posts em 30 dias, e não está em queda.
4. **Apresente de 5 a 8 e espere aprovação** antes de coletar.
5. **Colete cada um aprovado** com o mesmo extrator do perfil principal, e grave em `perfis de comparação/<handle>/analise - DD-MM-AAAA/dados/`.

Sem os três mínimos gravados em disco, a trava de entrega bloqueia a análise — e ela está certa em bloquear.

### 6.2 Bibliotecas de anúncios — o que o mercado está comprando

**Obrigatório sempre que houver concorrente identificado.** A análise de feed
responde "o que ele posta" e nunca "o que ele compra". As bibliotecas públicas da
Meta e do Google mostram todo anúncio ativo de qualquer anunciante, sem login e
sem API paga — e o achado costuma ser o mais acionável do relatório.

Numa execução real desta skill o cliente tinha **22 anúncios ativos no Google e
zero na Meta**, enquanto o termo central do negócio dele tinha **280 anúncios
ativos** de vinte anunciantes. Nenhuma métrica de engajamento mostra isso.

Leia `references/biblioteca-de-anuncios.md`. O essencial:

- **Meta, por termo** (share of voice) — URL direta com
  `search_type=keyword_exact_phrase` e o termo entre aspas.
- **Meta, por anunciante** — `search_type=page` **não funciona por URL numa busca
  nova**; escolha a marca no dropdown e guarde o `view_all_page_id`, que vira
  deep link estável para as próximas análises.
- **Google, por domínio** — `?region=BR&domain=<dominio>` é o caminho totalmente
  endereçável e deve ser o padrão. A página do anunciante (`/advertiser/<AR-ID>`)
  exige achar o id no dropdown, e o campo de busca do Google frequentemente
  ignora digitação sintética — se falhar duas vezes, caia para o domínio.

**Colete, no mínimo:** o cliente e três concorrentes nas duas bibliotecas, mais
dois termos de mercado (o termo central do negócio e um adjacente). Grave em
`dados/anuncios-<handle>.json` no formato do reference, classificando o **ângulo**
de cada criativo com o vocabulário fixo — `oferta`, `urgencia`, `prova`,
`institucional`, `destino`, `evento`.

```bash
python scripts/anuncios.py dados/anuncios-<handle>.json --resumo
python scripts/anuncios.py dados/anuncios-<handle>.json --html secao-anuncios.html
```

O script consolida as duas plataformas por marca, ordena por longevidade e emite
a seção pronta para o HTML. Ele **se recusa a ranquear** se os anunciantes do
Google estiverem em recortes diferentes ("anunciante" e "domínio" dão números
distintos para a mesma empresa) — isso é proposital.

**Duas regras que não se negociam:**

1. **Contagem de anúncios não é verba.** As bibliotecas não expõem investimento,
   impressões nem resultado. Muitos anúncios podem ser teste de criativo a R$
   20/dia. O que a contagem mede é presença e maturidade de operação — escreva
   assim, sempre.
2. **Tempo no ar pesa mais que volume.** Ninguém mantém anúncio ruim rodando. O
   criativo mais antigo do nicho é o melhor palpite disponível sobre o que
   converte, e é ele que vira diretriz.

Termine a seção nomeando **o espaço vago** — o ângulo, o formato ou o termo que
ninguém está cobrindo — e não o ranking de quem anuncia mais.

### 7. Capturar assets e material de referência

**Obrigatório, e captura de tela não cumpre a cota.** Uma análise sem material baixado entrega opinião sem evidência: o moodboard não existe, o relatório não tem os posts que sustentam cada achado, o cliente não recebe nada aproveitável para o site, e o Passo 8 fica sem insumo.

**Cota mínima de download — a trava confere no disco:**

| O quê | Mínimo | Para quê |
|---|---|---|
| Vídeos do cliente | **2 Reels** | teardown do que a marca já faz |
| Vídeos de referência | **2 Reels** de concorrentes ou criadores | teardown do que funciona fora |
| Imagens do cliente | **6 arquivos** em resolução original | matéria-prima de site |
| Capturas de tela | a grade de cada perfil de comparação | leitura de padrão de capa |

Escolha os vídeos por desempenho, não por conveniência: o de **maior alcance**, o de **maior engajamento por alcance** e o **pior dos dois** — o contraste é o que produz diretriz. Baixar só o melhor vídeo não ensina nada.

Se o download falhar, isso é um **bloqueio a relatar ao usuário na hora**, com o motivo e o que ele precisa fazer — não uma limitação a documentar no rodapé e seguir em frente.

Leia `references/captura-assets.md`. Este módulo transforma a análise em matéria-prima: os arquivos do cliente prontos para o site, e o material de terceiros organizado como referência visual.

Uma regra separa os dois, e ela não é negociável por conveniência:

- **Conta do cliente** → arquivo original, otimizado para web. É material dele indo para o site dele.
- **Criadores e UGC** → arquivo só quando há autorização escrita; sem ela, referência interna.
- **Concorrentes** → captura de tela e contact sheet. **Nunca vão para o site.**

O motivo de não guardar o `.mp4` do concorrente não é técnico: para extrair enquadramento, paleta e ritmo de corte, screenshot e folha de contatos bastam — e um arquivo de vídeo de terceiro na pasta do cliente é algo que alguém vai publicar por engano seis meses depois.

**Baixar de verdade tem um único caminho que funciona**, e ele está detalhado no reference: o navegador baixa sozinho, por um script rodado dentro da página de embed (`/p/<CODIGO>/embed/`). A URL da mídia nunca passa por você — o sanitizador da ponte a bloqueia, e contornar não é opção. Isso grava arquivo no disco do usuário: **peça autorização explícita antes**. Depois, `device_request_folder_access` na pasta de Downloads e `device_stage_files` trazem os arquivos para otimizar.

Duas coisas **não funcionam** e não devem ser prometidas: slides 2+ de carrossel (o embed só serve a capa) e frames de vídeo de Reel (MSE com `blob:`, o elemento nunca carrega). O substituto do frame é o poster do Reel, que o embed serve normalmente.

```bash
# depois de baixar pelo navegador e trazer os arquivos de volta:
python scripts/preparar_assets.py --otimizar assets/cliente/originais --destino assets/cliente/web
python scripts/preparar_assets.py --contact-sheet frames/ --saida assets/referencia/concorrentes/cs.jpg
python scripts/preparar_assets.py --inventario assets/
python scripts/montar_moodboard.py assets/ --saida moodboard.html --handle <handle> --notas notas.json
python scripts/preparar_assets.py --empacotar assets/ --saida assets-<handle>-<data>.zip
```

Entregue o `.zip` e o `moodboard.html`. O moodboard não é galeria — é argumento: cada bloco precisa de uma nota dizendo o que observar ali, senão é decoração.

**O Chrome bloqueia o segundo download em diante.** É a permissão "Downloads automáticos" do site: o primeiro arquivo baixa, e a partir do segundo o Chrome bloqueia em silêncio — a chamada em JavaScript devolve sucesso e nada chega ao disco. Um clique sintético não resolve; a permissão é do site, não do gesto.

**Confirme sempre no disco, nunca no retorno do JavaScript:** depois de cada lote, rode `device_list_dir` na pasta de Downloads e confira se os arquivos existem. Se não existirem, pare e peça ao usuário:

> Chrome → `chrome://settings/content/automaticDownloads` → em "Podem baixar vários arquivos automaticamente", adicionar `https://www.instagram.com`. Ou clicar no ícone de download bloqueado na barra de endereços e escolher "Sempre permitir".

Não tente proxies, espelhos ou rotas alternativas. Se a permissão não vier, caia para captura de tela, **diga no relatório e no chat quais vídeos ficaram sem teardown por causa disso**, e retome assim que for liberada.

### 8. Assistir os vídeos e escrever o teardown — obrigatório

**Baixar sem assistir não vale.** Um arquivo na pasta não é análise; o que o cliente compra é a leitura do material. Cada vídeo baixado no Passo 7 tem que virar teardown escrito, e o teardown tem que falar do **conteúdo** — o que aparece na tela, em que segundo, com que ritmo — e não só da estatística de corte.

**Mínimo: 2 vídeos do cliente e 2 de referência, cada um com teardown.**

O procedimento é sempre o mesmo, e a etapa que não pode ser pulada é a terceira:

1. `analisar_video.py` detecta os cortes, extrai um frame por plano e monta a folha de contatos.
2. Extraia também um **strip de gancho** — frames em 0,2s / 1,0s / 2,0s / 3,0s — porque a decisão de rolar acontece aí e um frame por plano não cobre esses instantes.
3. **Leia a folha de contatos e o strip com a ferramenta `Read`.** É aqui que você assiste. Teardown escrito só a partir do JSON descreve cadência de corte e não diz nada sobre o vídeo.
4. Escreva: o que acontece em cada bloco com o timestamp, por que funciona ou não, o que copiar e o que não repetir.

Compare sempre **pelo menos dois vídeos com desempenho diferente**. O número que vira diretriz nasce do contraste — "plano médio de 2,3s reteve 7x melhor que plano médio de 8,3s" é diretriz; "o vídeo tem 26 cortes" não é.

Leia `references/estudo-de-referencia.md`. Este módulo faz o Claude **assistir** um vídeo de verdade e devolver um teardown que vira diretriz de produção.

```bash
python scripts/analisar_video.py referencia/estudo/reel.mp4 --saida referencia/estudo/teardown/
```

O script detecta os cortes, extrai um frame por plano com o timestamp gravado e monta a folha de contatos. **Depois disso, leia a folha e os frames com a ferramenta `Read`** — o script prepara, quem assiste é você. Teardown escrito só a partir do JSON descreve estatística de corte e não diz nada sobre o conteúdo.

**Vídeo do Instagram é baixável** — mas não pelo elemento `<video>`, que fica em `readyState 0` para sempre (MSE com `blob:`). O caminho é pedir à API interna do Instagram de dentro da página autenticada: `/api/v1/media/<id>/info/` devolve `video_versions` com MP4 direto. O reference traz o script verificado. O mesmo endpoint resolve carrossel completo, que a página de embed não expõe.

Isso grava arquivo no disco do usuário: **peça autorização explícita antes**. Depois, `device_request_folder_access` e `device_stage_files` trazem o arquivo para o `analisar_video.py`.

Estudar material de terceiro é prática normal. A fronteira é o que sai da pasta: estudo vive em `referencia/estudo/`, o que se leva adiante é o **teardown**, não o arquivo. O documento fala de mecanismo — "abre com uma contradição e resolve no segundo 12" — e fecha nomeando o que não deve ser copiado.

### 9. Entregar — e passar na trava antes de dizer que acabou

**Sempre os dois formatos.** O `.md` é o documento de trabalho; o `.html` é o que vai para o cliente. Entregar só o Markdown é entregar metade — e foi exatamente o que aconteceu numa execução real desta skill.

Antes de declarar a análise pronta, rode:

```bash
python scripts/verificar_entrega.py "<pasta da analise>" --min-comparacao 3 --min-videos 4 --min-teardowns 2
```

Ele confere no disco: manifesto com as respostas de abertura, coleta em `dados/`, material em `assets/` com inventário, **vídeos `.mp4` de fato baixados**, **teardowns escritos** para eles, **o levantamento das bibliotecas de anúncios**, relatório em `.md` **e** em `.html`, e o mínimo de perfis de comparação com dados.

**Enquanto o código de saída for 1, a análise não está pronta** — nem para o cliente, nem para você dizer que terminou. Corrija o que faltou e rode de novo. "Lembrar de entregar tudo" não é um mecanismo; esta verificação é.

Se algum bloqueio for impossível de resolver — por exemplo, o nicho realmente só tem dois concorrentes ativos — diga isso ao usuário explicitamente, com o motivo, em vez de entregar em silêncio com a lacuna.

### 9.1 O que entregar

Sempre os dois formatos, a partir de `assets/`:

- `analise-<handle>-<AAAA-MM-DD>.md`
- `analise-<handle>-<AAAA-MM-DD>.html` — autocontido, feito para o cliente abrir

O HTML não é o Markdown com estilo. Ele carrega o que só funciona visualmente: **exemplos de referência** (os posts concretos, próprios e de terceiros, que sustentam cada achado), **correlações** em barras comparativas (pilar × engajamento, formato × compartilhamento, cadência × desempenho), cards de tendência com estágio e janela, o calendário editorial e os roteiros cena a cena. Um relatório que afirma "conteúdo cultural rende 3x mais" e mostra os dois posts lado a lado convence; um que só afirma, não.

Entregue com `SendUserFile` **e grave em `entregas/` dentro da pasta do projeto** — é para isso que ela existe. Relatório, moodboard e zip vivem lá; o chat é cópia, não o destino. Se `Artifact` estiver disponível e for apresentação a cliente, publique o HTML.

No chat, no máximo três frases: o veredito e as duas coisas mais urgentes.

## Estrutura do relatório

1. **Veredito em uma frase** — a verdade central do perfil.
2. **Números-chave** — poucos, com data da coleta e tamanho da amostra visíveis.
3. **Auditoria do perfil** — nota por item, cada uma citando o que está lá.
4. **Conteúdo** — pilares, o que funciona, o que não funciona, com exemplos reais.
5. **Engajamento** — leitura dos números, não repetição deles.
6. **Tendências e oportunidades** — o cruzamento, com aderência e janela.
7. **Calendário editorial** — 2 a 4 semanas equilibrando pilares e trends.
8. **Roteiros** — cena a cena para as 2–3 melhores pautas.
9. **Plano de ação** — 5 a 8 ações priorizadas pelo **objetivo declarado** do cliente.
10. **Anúncios** — quem compra mídia, em que ângulo, o que está no ar há mais tempo e o espaço vago.
11. **Teardowns de referência** — mecanismo aprendido e o que não copiar.
12. **Assets e referências** — o que foi capturado, com o uso permitido de cada origem.
13. **Limitações** — o que não deu para medir e como fechar a lacuna.

Duas regras de tom que fazem diferença numa entrega para cliente:

**Seja específico ao criticar.** "A bio não deixa claro o que você vende" é fraco. "A bio abre com 'transformando vidas desde 2019' — um visitante novo não descobre em 3 segundos que você vende consultoria financeira para autônomos" é acionável.

**Elogie com a mesma precisão.** Relatório só negativo é lido como venda de serviço, e o cliente desconta tudo. Se a cadência é boa ou os carrosséis salvam a conta, diga com número.

## Quando o usuário tem acesso ao Insights

É o melhor cenário e vale insistir. Peça: alcance dos últimos 30 dias, seguidores ganhos e perdidos, salvamentos e compartilhamentos por post, horários de atividade e demografia. Com isso entra a taxa de engajamento **por alcance** — a métrica que o algoritmo realmente premia — e a seção de limitações encolhe. As fórmulas estão em `references/metricas.md`.

## Benchmark de concorrentes

Rode a coleta em cada perfil aprovado, sem exceção — comparar dado coletado com dado lembrado produz conclusão errada. Monte a tabela lado a lado: seguidores, ER, cadência, mix de formatos, pilar dominante e trends já usadas.

A conclusão útil quase nunca é "o concorrente é melhor". É achar o espaço vago: o formato que ninguém no nicho usa bem, o assunto que gera comentário e ninguém cobre, a trend que o nicho inteiro ainda não pegou. Termine a seção nomeando a oportunidade, não o ranking.

## Arquivos desta skill

- `references/coleta-chrome.md` — navegação, extração e armadilhas conhecidas. Leia antes de coletar.
- `references/tendencias.md` — coleta de trends e áudios, rubrica de aderência, ciclo de vida. Leia antes do cruzamento.
- `references/captura-assets.md` — captura de telas, download do material do cliente, contact sheets e a fronteira de uso. Leia antes de capturar.
- `references/estudo-de-referencia.md` — como o Claude assiste um vídeo, a estrutura do teardown e a fronteira de uso do material de terceiro. Leia antes de estudar referência.
- `references/biblioteca-de-anuncios.md` — Meta e Google: URLs, extração e as armadilhas. Leia antes de levantar anúncios.
- `references/cacada-de-tendencias.md` — YouTube, TikTok, Instagram e X: método por plataforma e o cruzamento. Leia no modo dossiê.
- `references/raspagem.md` — Firecrawl, WebFetch e navegador; o que extrair de cada site.
- `references/metricas.md` — fórmulas, benchmarks por faixa **e por nicho**, sinais de engajamento artificial. Leia antes de interpretar.
- `references/auditoria.md` — rubrica do perfil e método de análise de conteúdo. Leia antes de escrever.
- `scripts/abrir_projeto.py` — gera o manifesto e o caminho da pasta, para cliente ou perfil de comparação.
- `scripts/verificar_entrega.py` — trava que bloqueia a entrega incompleta. Rode antes de dizer que acabou.
- `scripts/historico.py` — consolida análises anteriores em evolução e posição relativa.
- `scripts/calcular_metricas.py` — métricas a partir do JSON, com separação de collabs e calibração por nicho.
- `agent/dossie-social.md` — o agente do modo dossiê. Copie para `.claude/agents/`.
- `scripts/montar_dossie.py` — árvore do dossiê e índice HTML navegável do acervo.
- `scripts/extrair_audio.py` — separa a faixa, mede loudness e marca os picos para cruzar com os cortes.
- `scripts/anuncios.py` — consolida as duas bibliotecas por marca e gera a seção comparativa do HTML.
- `scripts/ciclo_tendencia.py` — estágio, janela restante e risco de saturação de cada tendência.
- `scripts/preparar_assets.py` — baixa, otimiza para web, monta contact sheet, inventaria e empacota.
- `scripts/analisar_video.py` — cortes, frames-chave com timestamp e folha de contatos para o Claude assistir.
- `scripts/montar_moodboard.py` — moodboard HTML autocontido a partir do inventário.
- `assets/template-relatorio.md` e `assets/template-relatorio.html` — os dois formatos de entrega.
