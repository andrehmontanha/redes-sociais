# Captura de assets e material de referência

Este módulo transforma a análise em matéria-prima: os arquivos do cliente prontos para o site, e o material de terceiros organizado como referência visual para orientar o que produzir.

## A fronteira que rege tudo aqui

Uma única regra separa o que a skill baixa do que ela apenas fotografa:

| Origem | O que capturar | Uso permitido |
|---|---|---|
| **Conta do cliente** | Arquivo original (imagem e vídeo) | Livre — é material dele, indo para o site dele |
| **Criadores e UGC sobre o cliente** | Arquivo, quando a marca tem a autorização | Só publica com autorização escrita do criador. Sem ela: referência interna |
| **Concorrentes** | Captura de tela e frames | **Nunca publicar.** Referência interna, moodboard, direção de arte |
| **Bancos livres** | Arquivo original | Conforme a licença do banco (checar uso comercial) |

O motivo de não baixar arquivo de concorrente não é técnico, é prático: para extrair o padrão — enquadramento, paleta, ritmo de corte, estrutura de capa — captura de tela e contact sheet bastam. Guardar o `.mp4` do concorrente na pasta do cliente não acrescenta nada à análise e cria um arquivo que alguém, em algum momento, vai publicar por engano.

Todo arquivo capturado entra no `inventario.csv` com origem, dono e uso permitido, e a página de moodboard repete o aviso por bloco. Isso não é burocracia: seis meses depois, ninguém lembra de onde veio a foto do café da manhã.

## O que capturar, por objetivo

### Para construir o site do cliente

Do perfil do cliente, priorize nesta ordem — é a ordem em que um site precisa de imagem:

1. **Hero** — a imagem mais ampla e limpa disponível: fachada, área externa, piscina ao entardecer. Vídeo curto em loop funciona ainda melhor.
2. **Prova de experiência** — pessoas usando o espaço, rosto visível, luz natural. É o que converte, e quase sempre está nos Reels, não nas fotos.
3. **Detalhe e textura** — quarto, prato, elementos de identidade. Preenche as seções intermediárias.
4. **Institucional** — logo, fachada com placa, equipe.

Colete de 15 a 25 arquivos. Menos que isso não fecha uma landing page; mais vira trabalho de triagem sem retorno.

### Para moodboard de referência

De concorrentes e criadores, capture o que sustenta uma decisão de direção de arte:

- A **grade completa** do concorrente, em um screenshot — é a leitura de identidade visual que nenhuma métrica dá.
- As **capas de Reels** que performaram, em conjunto: revela o padrão de tipografia, cor e enquadramento que funciona no nicho.
- **Contact sheet** dos 2 ou 3 Reels de melhor desempenho — o ritmo de corte fica visível quando você vê 9 frames lado a lado.

## Como capturar

### 1. Screenshots via Chrome

Use `computer` com `action: "screenshot"` e **`save_to_disk: true`** — sem isso a imagem só passa pelo seu contexto e não vira arquivo.

Para a grade, role até o topo do perfil antes de capturar. Para uma capa de Reel específica, abra o post e capture; a página do post mostra o primeiro frame parado quando o vídeo ainda não deu play.

Se a janela do navegador estiver estreita, parte da interface fica cortada. Não force: capture o que aparece e registre no inventário que o enquadramento foi parcial.

### 2. Frames de vídeo (contact sheet)

Reels não expõem arquivo para o visitante, mas expõem imagem na tela. Para extrair o ritmo:

1. Abra o Reel e deixe reproduzir.
2. Capture com `screenshot` + `save_to_disk` a cada ~2 segundos, de 6 a 9 vezes.
3. Junte tudo com `scripts/preparar_assets.py --contact-sheet`.

O resultado é uma folha de contatos que mostra, numa imagem só, quantos cortes o vídeo tem, onde entra o texto na tela e como o assunto evolui. É a peça mais útil do moodboard e a mais fácil de esquecer de fazer.

### 3. Baixar os arquivos do cliente — método verificado

Só para a conta do cliente. E há um detalhe que derruba a abordagem óbvia: **a URL da mídia não pode passar por você.** As URLs do CDN carregam token em query string, e o sanitizador da ponte devolve `[BLOCKED: Cookie/query string data]` no lugar delas. Extrair a URL para baixar depois não funciona, e tentar contornar o bloqueio não é opção.

O que funciona é o navegador baixar sozinho: um script roda **dentro da página**, busca a mídia e dispara o download. A URL nunca sai do contexto do navegador.

**Isto grava arquivo no disco do usuário — peça autorização explícita antes**, dizendo quantos arquivos, de onde e o tamanho aproximado.

A página que serve melhor é a de **embed**, não a do post: ela expõe a imagem de forma estável, sem a interface e sem depender de lazy-loading.

```
https://www.instagram.com/p/<CODIGO>/embed/
```

Com a página aberta, rode (é `javascript_tool`, com top-level `await` — **não** embrulhe num IIFE assíncrono, o retorno se perde):

```js
let g = [];
for (let i = 0; i < 12; i++) {
  g = [...document.querySelectorAll('img')].filter(e => e.naturalWidth >= 600);
  if (g.length) break;
  await new Promise(s => setTimeout(s, 700));
}
let out = { erro: 'sem imagem grande' };
if (g.length) {
  const im = g[0];
  const r = await fetch(im.currentSrc || im.src);
  const b = await r.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(b);
  a.download = 'cliente-post01-capa.jpg';   // nome semântico, sempre
  document.body.appendChild(a); a.click(); a.remove();
  out = { ok: r.ok, kb: Math.round(b.size / 1024), tipo: b.type };
}
out
```

Resultado verificado numa coleta real: `{ok: true, kb: 50, tipo: "image/jpeg"}`, arquivo na pasta Downloads do usuário.

**Tamanho real do que vem:** `1080×1350` para foto de feed e `1080×1920` para story — o que o Instagram armazena. O atributo `naturalWidth` às vezes reporta um valor maior (2293) referente a outra entrada do `srcset`; o blob baixado é o de 1080. Não prometa mais que isso ao cliente.

### 4. Trazer os arquivos de volta para otimizar

O download caiu no computador do usuário, não no seu ambiente — o navegador é dele. Para otimizar e empacotar você precisa enxergar a pasta:

1. `device_request_folder_access` na pasta de Downloads (o usuário aprova uma vez).
2. `device_stage_files` nos arquivos baixados.
3. Seguir com `--otimizar` normalmente.

Round-trip verificado ponta a ponta: download no navegador → disco do usuário → staging → WebP/JPEG em múltiplas larguras.

### 5. O que NÃO funciona, e por quê

Estas três coisas foram testadas em coleta real e falharam. Não prometa nenhuma delas ao cliente, e não gaste rodadas tentando de novo:

**Slides 2 em diante de um carrossel — resolvido por outra via.** A página de embed serve só a capa e ignora `?img_index=`, e na página normal os `<img>` grandes não materializam de forma confiável. Mas a **API interna** (`/api/v1/media/<id>/info/`, ver `estudo-de-referencia.md`) devolve `carousel_media` com todos os slides em `image_versions2.candidates`. Use esse caminho para carrossel completo.

**O que segue sem solução:**

**~~Slides de carrossel pela página~~ (obsoleto).** A página de embed serve só a capa e ignora `?img_index=`. Na página normal do post, os `<img>` grandes simplesmente não materializam no DOM neste contexto automatizado — testado em várias larguras de janela, sempre zero. Para os demais slides, o caminho honesto é o dono da conta exportar do próprio Instagram ou da ferramenta de design. Capture-os por screenshot se precisar deles só como referência.

**Frames pelo elemento `<video>` da página.** Continua impossível — MSE com `blob:`, `readyState 0` permanente. Mas isso deixou de importar: **baixe o MP4 pela API interna** (`estudo-de-referencia.md`) e extraia os frames com `analisar_video.py`, que é mais preciso de qualquer forma, porque detecta os cortes reais em vez de amostrar às cegas.

**Qualquer rota alternativa para contornar o sanitizador.** Fragmentar a URL, codificá-la, passá-la por outro canal: não. O bloqueio existe porque essas URLs carregam token de sessão. Se o download não passa, o caminho é screenshot ou o cliente exportar do original.

## Preparar para web

```bash
python scripts/preparar_assets.py --otimizar assets/cliente/originais --destino assets/cliente/web
```

O script gera, para cada imagem: WebP e JPEG nas larguras 400, 800 e 1600, com nome semântico derivado do tema do post. Para cada vídeo: MP4 H.264 comprimido (CRF 26) e um poster JPEG do primeiro frame — porque vídeo de fundo sem poster mostra retângulo preto enquanto carrega, e é o erro mais comum em site de hotelaria.

Ele também preenche o `inventario.csv` com dimensões, peso, origem e uso permitido, e deixa a coluna `alt` com uma sugestão a partir do tema do post — sugestão, não verdade: revise antes de publicar, porque alt text errado é pior que alt text ausente.

**Não otimize material de referência.** Ele não vai para lugar nenhum; comprimir só gasta tempo e ainda faz parecer que é asset de produção.

## Montar o moodboard

```bash
python scripts/montar_moodboard.py assets/ --saida moodboard.html
```

Gera uma página autocontida — miniaturas embutidas como data URI, então ela abre sozinha em qualquer lugar — organizada por origem, com o aviso de uso em cada bloco e o link para o post original de cada peça.

O moodboard não é uma galeria bonita: é um argumento. Cada bloco precisa responder "por que este material está aqui e o que ele deve influenciar". Uma folha de contatos sem legenda dizendo o que observar é decoração.

## Empacotar e entregar

```bash
python scripts/preparar_assets.py --empacotar assets/ --saida assets-<handle>-<data>.zip
```

Estrutura do pacote:

```
assets-<handle>-<AAAA-MM-DD>/
├── cliente/
│   ├── originais/          arquivos como vieram
│   └── web/                webp + jpg em 3 larguras, vídeo comprimido, posters
├── referencia/
│   ├── concorrentes/       screenshots de grade e capas
│   └── criadores/          capturas e contact sheets
├── moodboard.html
└── inventario.csv
```

Entregue o `.zip` e o `moodboard.html` com `SendUserFile`. Se houver pasta conectada do computador do usuário, grave lá também — uma biblioteca de assets pertence ao disco dele, não a uma conversa.

## Limites

- **Não capture material de perfis privados**, mesmo que a conta logada os siga. Ver não é o mesmo que arquivar.
- **Não capture pessoas identificáveis** de posts de terceiros para uso em site. Rosto de hóspede em foto de criador exige autorização da pessoa, não só do criador.
- **URLs de mídia expiram.** Se um download falhar por URL vencida, recolete a URL; não é bloqueio, é validade.
- **Vídeo do cliente vem sem áudio original licenciado.** Se o Reel usa faixa musical de terceiro, o vídeo não pode ir para o site com esse áudio — use mudo, em loop, que é o padrão de hero de qualquer forma.
