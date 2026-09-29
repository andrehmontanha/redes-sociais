# Estudo de material de referência

Estudar o que outros criadores fazem é prática profissional normal e é como se aprende ofício. Este módulo transforma esse estudo em algo reproduzível: o Claude olha o material de verdade, quadro a quadro, e devolve um teardown que vira diretriz de produção.

## A fronteira que importa

O risco de estudar material de terceiro não está em olhar. Está no que sai da pasta de estudo.

**Pode:** baixar para assistir com atenção, extrair frames, medir ritmo, transcrever texto de tela, escrever um documento sobre o que faz aquilo funcionar, e aplicar o *princípio* aprendido em conteúdo próprio.

**Não pode:** republicar o arquivo, usar o material no site ou no feed do cliente, revender como template, ou reproduzir o conteúdo em vez do padrão. "É referência" não converte material de terceiro em ativo próprio.

Na prática isso se resolve com uma regra simples de pasta: material de estudo vive em `referencia/estudo/`, nunca em `cliente/`. O `inventario.csv` marca a origem, e a origem decide o destino. O que sobrevive ao estudo é o **teardown** — o documento. O arquivo original é insumo temporário, e apagá-lo depois do estudo é higiene, não paranoia.

E o teardown precisa ser sobre mecanismo, não sobre conteúdo. "Ele abre com uma contradição e resolve no segundo 12" é diretriz. "Copiar o vídeo dele sobre X" não é estudo, é cópia — e além do problema óbvio, não funciona: o post do concorrente já capturou aquela audiência.

## Como o Claude assiste um vídeo

O Claude não recebe stream. Ele lê imagens. `scripts/analisar_video.py` faz a ponte: detecta os cortes, extrai um frame de cada plano, grava o timestamp em cada quadro e monta uma folha de contatos.

```bash
python scripts/analisar_video.py referencia/estudo/reel.mp4 \
    --saida referencia/estudo/reel-teardown/ --limiar 0.30
```

Depois — e esta é a parte que não pode ser pulada — **leia a folha de contatos e os frames individuais com a ferramenta Read**. O script prepara; quem assiste é você. Um teardown escrito só a partir do `analise.json` descreve estatística de corte e não diz nada sobre o conteúdo.

**Como a detecção de corte funciona, e por que ela precisa dos dois parâmetros.** O detector do ffmpeg sozinho erra nas duas direções: com limiar alto perde os cortes de uma montagem de viagem (céu, piscina e areia têm histograma parecido), e com limiar baixo dispara em rajada durante movimento de câmera, devolvendo "planos" de 0,03s que não existem. Num teste real, o mesmo vídeo de 62s deu 4 cortes com limiar 0,30 e 62 com 0,12 — nenhum dos dois verdadeiro.

A correção é temporal: limiar baixo (0,15, o padrão) para não perder corte, e `--min-plano 0.5` fundindo tudo que estiver a menos de meio segundo de distância. O mesmo vídeo passou a devolver 18 planos com média de 2,46s, que é a leitura correta. Se o vídeo tiver cortes legitimamente mais rápidos que 0,5s, baixe o `--min-plano`; se ainda vier ruído, suba.

Ajuste do `--limiar`: 0,15 é o padrão. Vídeo com muito movimento de câmera gera falsos cortes — suba para 0,45. Vídeo de plano fixo com trocas sutis de texto na tela não dispara nada — desça para 0,15. Se voltar com zero cortes, o script distribui frames uniformemente, e um vídeo de plano único ainda tem progressão de texto para ler.

**Limite honesto:** o script não escuta o áudio. Ele informa se existe faixa e qual codec, mas locução e música ficam de fora. Quando o áudio for central — e num Reel de fala ele quase sempre é — peça ao usuário a legenda automática do Instagram ou uma transcrição, e trate a análise como incompleta até ter isso.

## Baixar o vídeo — método verificado

Funciona, e o caminho não é o óbvio. O elemento `<video>` da página é inútil: o Instagram entrega Reel por MSE com `src` do tipo `blob:`, e em contexto automatizado ele fica em `readyState 0` para sempre — sem duração, sem buffer, sem frame. Não perca tempo com `play()`, clique no botão ou `currentTime`.

O que funciona é **pedir o arquivo à API interna do próprio Instagram, de dentro da página**. A página já está autenticada; a chamada usa a sessão do usuário e a URL nunca sai do contexto do navegador — o que resolve também o bloqueio do sanitizador.

**Isto grava arquivo no disco do usuário — peça autorização explícita antes.**

### Passo 1 — pegar o `media_id` e o `X-IG-App-ID`

Na página do Reel, os dois estão no HTML:

```js
const h = document.documentElement.innerHTML;
({
  mid: (h.match(/"media_id"\s*:\s*"(\d+)"/) || h.match(/"pk"\s*:\s*"?(\d{15,})/) || [])[1],
  appid: (h.match(/"X-IG-App-ID"\s*:\s*"(\d+)"/) || [])[1]
})
```

O App-ID da web é estável (`936619743392459`), mas leia do HTML em vez de fixar no código — se a Meta trocar, o script sobrevive.

### Passo 2 — pedir a mídia e baixar

Top-level `await`, **não** embrulhe em IIFE assíncrono (o retorno se perde):

```js
const r = await fetch(`/api/v1/media/${MID}/info/`,
                      {headers: {'X-IG-App-ID': APPID}, credentials: 'include'});
const j = await r.json();
const it = j.items[0];
const best = it.video_versions.sort((a,b) => b.width*b.height - a.width*a.height)[0];
const vr = await fetch(best.url);
const b = await vr.blob();
const a = document.createElement('a');
a.href = URL.createObjectURL(b);
a.download = 'ref-<criador>-<codigo>.mp4';   // nome semântico, sempre
document.body.appendChild(a); a.click(); a.remove();
({ok: vr.ok, mb: Math.round(b.size/1048576*10)/10, dim: best.width+'x'+best.height})
```

Resultado verificado numa coleta real: `{ok: true, mb: 25.9, dim: "720x1280"}` — MP4 de 73s na pasta Downloads do usuário.

O mesmo endpoint serve **carrossel completo**: `it.carousel_media` traz todos os slides com `image_versions2.candidates`, o que resolve a lacuna dos slides 2+ que a página de embed não expõe.

### Passo 3 — trazer para assistir

O download caiu no computador do usuário, não no seu ambiente. `device_request_folder_access` na pasta de Downloads, `device_stage_files` no arquivo, e então `analisar_video.py`. Round-trip verificado ponta a ponta.

### Se a API mudar

Ela é interna e sem contrato público — pode mudar sem aviso. Se `status` vier 400/401/404, ou `video_versions` sumir, **pare**: não tente proxies, espelhos ou serviços de terceiros. Caia para captura de tela e diga ao usuário que o arquivo precisa vir por fora (gravação de tela, o download do próprio Instagram). Uma capacidade que falha honestamente vale mais que uma que contorna.

## O teardown

Estrutura fixa. Cada seção existe porque responde a uma pergunta que vira decisão de produção.

### 1. Ficha técnica
Duração, proporção, número de cortes, duração média do plano. Sai pronto do `analise.json`.

### 2. Os três primeiros segundos
É onde o vídeo é ganho ou perdido, e merece parágrafo próprio. O que aparece no primeiro quadro? Há texto na tela antes de qualquer fala? A primeira imagem já mostra o assunto ou é uma abertura genérica? Descreva o que você viu no frame de 0,0s, não o que imagina que estava lá.

### 3. Estrutura
Mapeie a progressão em blocos com timestamp: gancho → contexto → desenvolvimento → virada → CTA. Nem todo vídeo tem os cinco. Nomear os que faltam costuma ser mais revelador que descrever os presentes.

### 4. Texto na tela
Transcreva o que aparece escrito, na ordem, com timestamp. Depois avalie o padrão: quantas palavras por cartela, quanto tempo cada uma fica, posição na tela, se funciona sem som. A maior parte do consumo é mudo — texto que só faz sentido com áudio é falha de projeto, e reconhecer isso num vídeo de referência é metade do aprendizado.

### 5. Ritmo
Cruze a duração média do plano com o tipo de conteúdo. Corte a cada 0,8s num vídeo explicativo cansa; corte a cada 5s num vídeo de dança perde. O número sozinho não diz nada — a relação com o assunto diz.

### 6. O mecanismo
A seção que justifica o documento inteiro, em um parágrafo: **por que este vídeo funciona, dito de um jeito que se aplica a outro assunto.** Se a frase que você escrever aqui só serve para o vídeo analisado, você descreveu, não entendeu.

### 7. Diretrizes para o cliente
De 3 a 5 regras acionáveis, cada uma amarrada a um achado acima. Não "faça cortes rápidos" — "mantenha cada plano abaixo de 2s nos primeiros 6 segundos, que é onde este vídeo concentra 4 dos 9 cortes".

### 8. O que não copiar
Fecha o teardown e protege o cliente. O que naquele vídeo pertence àquele criador — o rosto, o bordão, a piada recorrente, o formato assinado — e não deve ser reproduzido. Escrever isso explicitamente evita a conversa desconfortável depois.

## Estudando um perfil inteiro

Rodando o teardown em 3 a 5 vídeos do mesmo criador, o que interessa deixa de ser o vídeo e passa a ser o **padrão entre eles**: o gancho repete estrutura? A duração converge? O CTA é sempre o mesmo mecanismo?

Um criador consistente tem fórmula, e a fórmula é o que se estuda. Um criador que acertou um viral e não repetiu tem sorte — e copiar sorte não é estratégia. A comparação entre vídeos é o que separa os dois casos, e é por isso que teardown isolado vale menos que série.

Fecha nomeando **o que o cliente pode fazer que aquele criador não faz** — a lacuna, não a imitação. Estudo de referência que termina em "faça igual" desperdiçou o trabalho.
