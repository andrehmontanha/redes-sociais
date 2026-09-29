# Bibliotecas de anúncios — Meta e Google

Este módulo responde a uma pergunta que o feed sozinho nunca responde: **o
concorrente está comprando mídia, e em quê?** Duas bibliotecas públicas, sem
login, sem API paga, mostram todo anúncio ativo de qualquer anunciante.

O achado aqui costuma ser o mais acionável do relatório inteiro. Numa execução
real desta skill, o cliente tinha **22 anúncios ativos no Google e zero na
Meta**, enquanto o termo central do negócio dele — "Thermas dos Laranjais" —
tinha **280 anúncios ativos** de mais de vinte anunciantes. Isso não aparece em
taxa de engajamento.

---

## O que dá e o que não dá para saber

**Dá:** quem anuncia, quantos anúncios ativos, desde quando cada um está no ar,
o criativo inteiro (imagem, vídeo, texto), o destino do clique, em quais
plataformas roda, quantos anúncios reaproveitam o mesmo criativo, e — no Google —
se a identidade do anunciante foi verificada.

**Não dá:** investimento, impressões, CPM, CTR, público-alvo ou resultado.
Esses números só existem para anúncios de política e eleição. **Nunca estime
verba a partir do número de anúncios** — muitos anúncios podem ser um teste de
criativo com R$ 20/dia, e um anúncio só pode carregar seis dígitos.

O que o número de anúncios ativos mede de verdade é **intenção e maturidade
operacional**: quem tem 300 anúncios ativos tem estrutura de mídia; quem tem
zero não está no jogo.

**A métrica mais subestimada é o tempo no ar.** Ninguém mantém anúncio ruim
rodando. Um criativo ativo há três meses é um criativo que está pagando as
contas — e é o melhor palpite disponível sobre o que funciona no nicho.

---

## Meta — Biblioteca de Anúncios

Tudo é endereçável por URL, e a página abre sem login.

### Busca por termo (share of voice)

```
https://www.facebook.com/ads/library/?active_status=active&ad_type=all
  &country=BR&q=%22<termo entre aspas>%22
  &search_type=keyword_exact_phrase&media_type=all
```

`search_type=keyword_exact_phrase` com o termo entre aspas evita o ruído do
`keyword_unordered`. Troque `media_type` por `image`, `video` ou `meme` para
contar formato — **o contador do topo muda com o filtro**, e essa é a forma
confiável de medir mix de formato.

### Busca por anunciante (deep link estável)

`search_type=page` **não funciona pela URL numa busca nova** — a página reescreve
para `keyword_unordered`. O caminho é:

1. Digitar o nome da marca no campo de busca da página.
2. Escolher a marca na seção **"Anunciantes"** do dropdown.
3. A URL vira `...&search_type=page&view_all_page_id=<ID>`.

**Guarde esse `view_all_page_id` no JSON da análise.** A partir daí a URL é
estável e reutilizável em toda análise futura — é o que transforma esta etapa
numa série histórica em vez de uma garimpagem repetida.

### Extração

Os cartões não têm classe estável (a Meta ofusca), mas o texto é previsível.
Parseie `document.body.innerText`:

```js
const t = document.body.innerText;
const total = (t.match(/~?\s*([\d.,]+)\s+resultados?/) || [])[1] || '0';
const blocos = t.split(/Identificação da biblioteca:\s*/).slice(1);
const ads = blocos.map(b => {
  const linhas = b.split('\n').map(s => s.trim()).filter(Boolean);
  const iPat = linhas.findIndex(l => l === 'Patrocinado');
  return {
    id:        (b.match(/^(\d+)/) || [])[1],
    inicio:    (b.match(/Veiculação iniciada em ([^\n]+)/) || [])[1],
    reuso:    +((b.match(/(\d+)\s+anúncios? usam esse criativo/) || [])[1] || 1),
    anunciante: iPat > 0 ? linhas[iPat - 1] : null,
    destino:   (b.match(/\n([A-Z0-9.-]+\.(COM|COM\.BR|BR|NET|IO)[^\n]*)\n/) || [])[1],
    copy:      iPat >= 0 ? linhas.slice(iPat + 1)
                 .filter(l => !/^(Ver detalhes|Ver resumo|Acessar|Saiba mais|Plataformas|Ativo|Inativo)/.test(l))
                 .slice(0, 6).join(' ').slice(0, 320) : null,
  };
});
```

**Armadilhas verificadas:**

- **Os ícones de plataforma não são legíveis.** São `<div>` com máscara CSS, sem
  `aria-label` e sem `alt`. Não tente parsear — use o filtro `publisher_platforms`
  na URL e compare os contadores, ou registre "não medido".
- **O contador é aproximado** ("~280 resultados") e o feed carrega por rolagem.
  Registre o total declarado *e* quantos cartões você realmente leu — são
  números diferentes e o relatório precisa dizer qual é qual.
- **`active_status=all` costuma devolver o mesmo que `active`** para anunciante
  não político. Não prometa histórico que a biblioteca não entrega.
- **Um cartão pode representar vários anúncios** ("2 anúncios usam esse criativo
  e esse texto"). Some o campo `reuso` para não subcontar.

---

## Google — Central de Transparência de Anúncios

### Busca por domínio — o caminho robusto

```
https://adstransparency.google.com/?region=BR&domain=<dominio.com.br>
```

**Este é o único caminho totalmente endereçável por URL**, e é o que a skill deve
usar por padrão. Devolve a contagem ("66 anúncios"), os criativos e o anunciante
atribuído a cada um, com selo de verificação.

### Busca por anunciante

```
https://adstransparency.google.com/advertiser/<AR-ID>?region=BR
```

O `AR-ID` só aparece depois de escolher o anunciante no dropdown de busca.
**Guarde no JSON** — a partir daí vira deep link.

**O campo de busca é chato e essa é a armadilha conhecida:** digitação sintética
frequentemente não entra. O que funcionou foi focar por script antes de digitar:

```js
const i = document.querySelector('input'); i.focus(); i.click();
```

…e só então enviar o texto. Se depois de duas tentativas o valor continuar
vazio, **caia para a busca por domínio** em vez de insistir.

### Anunciante ≠ domínio

O mesmo anunciante apareceu com **~300 anúncios** na página dele e **66** na
busca pelo domínio principal — porque ele anuncia para vários domínios. São
recortes diferentes e **não podem ser comparados entre si**. Escolha um recorte
e use o mesmo para todo mundo; diga qual no relatório.

Os filtros de formato e plataforma do Google **não funcionam por URL** — são
dropdowns client-side. Ou você clica, ou registra "não medido".

---

## O que extrair de cada anúncio

Grave em `dados/anuncios-<handle>.json`:

```json
{
  "coletado_em": "2026-08-27",
  "pais": "BR",
  "cliente": "turisthermas",
  "meta": {
    "por_anunciante": [
      {"anunciante": "...", "handle": "...", "papel": "cliente|concorrente|mercado",
       "view_all_page_id": "...", "ativos": 0, "cartoes_lidos": 0,
       "formatos": {"video": 0, "image": 0},
       "ads": [{"id": "...", "inicio": "2026-08-21", "dias_no_ar": 6,
                "reuso": 1, "destino": "INSTAGRAM.COM", "angulo": "oferta",
                "copy": "..."}]}
    ],
    "por_termo": [{"termo": "thermas dos laranjais", "ativos": 280,
                   "anunciantes_vistos": 20, "cliente_presente": false}]
  },
  "google": {
    "por_anunciante": [
      {"anunciante": "...", "ar_id": "...", "dominio": "...",
       "verificado": true, "ativos": 22, "recorte": "dominio|anunciante"}
    ]
  }
}
```

**`angulo`** é classificação sua, não do dado. Use um vocabulário curto e o mesmo
para todos: `oferta` (preço, desconto, prazo), `urgencia` (últimas vagas, acaba
hoje), `prova` (depoimento, avaliação, número de clientes), `institucional`
(marca, história), `destino` (o lugar, sem oferta), `evento` (data marcada).
Sem vocabulário fixo a comparação vira opinião.

---

## Como virar leitura, não tabela

Quatro perguntas que o relatório precisa responder:

1. **Quem está no jogo e quem não está.** Presença por plataforma, lado a lado.
   "Zero na Meta enquanto 280 anúncios disputam o seu termo" é uma frase que
   fecha reunião.
2. **Em que ângulo o mercado bate.** Se todo mundo anuncia oferta e ninguém
   anuncia prova, a prova é o espaço vago.
3. **O que está no ar há mais tempo.** Ordene por `dias_no_ar` e leia os três
   mais antigos do nicho. Aquilo é o que funciona.
4. **Para onde o clique vai.** Site próprio, WhatsApp, Instagram ou landing por
   destino. Muda a leitura do funil inteiro.

Termine nomeando a oportunidade — o ângulo, o formato ou o termo que ninguém
está cobrindo — e não o ranking de quem gasta mais.

---

## Limites e ética

- Leitura de páginas públicas, no ritmo de um humano. Sem raspagem em massa,
  sem contornar bloqueio.
- Criativo de concorrente é **estudo**: captura de tela e teardown entram no
  relatório; o arquivo não vai para o feed nem para o site do cliente.
- Nunca apresente contagem de anúncios como investimento. Se o cliente pedir
  verba estimada, diga que a biblioteca não expõe isso e que só o Insights ou
  uma ferramenta paga de estimativa chegariam perto — sempre como estimativa.
