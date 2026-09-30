# Brand kit — campo a campo

Cada bloco tem `origem`: `medido` (script), `observado` (você olhou e cita o post),
`manual` (veio do manual de marca do cliente) ou `informado` (o cliente disse).
`PENDENTE` bloqueia a validação.

## cores

| Campo | O que é | Como decidir |
|---|---|---|
| `papeis.fundo` | cor de fundo das artes sem foto | a cor sólida que o feed usa em posts de texto; se não houver, a mais clara ou escura da paleta que carrega texto |
| `papeis.primaria` | cor da marca | a que aparece em logo, faixas e destaques recorrentes |
| `papeis.destaque` | CTA, preço, número | a de maior contraste com o fundo entre as da paleta — use com parcimônia |
| `papeis.texto` | texto corrido | precisa de contraste ≥ 4.5 contra `fundo` |
| `paleta` | medição bruta | não edite; é o registro do que o script viu |

Opcional: `papeis.texto_sobre_foto` quando a marca usa uma cor específica sobre fotografia.
`papeis.texto_sobre_destaque`: cor do texto dentro do botão/CTA (padrão: `fundo`). A validação exige contraste ≥ 3 com `destaque` — laranja com texto branco, comum em sites, costuma reprovar.

## tratamento_foto

Medido. A leitura ("claro, saturado, quente, contraste médio") orienta a escolha
das fotos do cliente para os criativos: uma foto fria e escura num feed quente e
claro quebra a grade mesmo com a tipografia certa.

## tipografia

```json
"titulo": {"familia": "Playfair Display", "peso": 700, "caixa": "normal", "google_fonts": true},
"texto":  {"familia": "Inter", "peso": 400, "google_fonts": true}
```

- `caixa`: `normal`, `maiusculas` ou `minusculas`.
- Fonte proprietária do cliente: `"google_fonts": false` e `"arquivo": "clientes/<handle>/material-cliente/fontes/<arquivo>.woff2"`.
  Só use arquivo de fonte que o cliente enviou.
- Serifada × sem serifa, condensada × larga, e o peso do título são o que mais
  pesa no reconhecimento. Acertar a família exata importa menos que acertar esses três.

## composicao

| Campo | Valores |
|---|---|
| `alinhamento` | `esquerda`, `centro` |
| `margem_px` | margem de segurança em 1080 px de largura (padrão 72) |
| `raio_borda_px` | 0 para cantos retos; cards arredondados, o raio observado |
| `texto_sobre_foto` | `nunca`, `faixa` (texto numa barra sólida), `degrade` (gradiente escuro sob o texto), `direto` |
| `densidade_texto` | `minima` (até 6 palavras), `media` (até 20), `alta` (carrossel educativo) |

## elementos

- `logo`: caminho do arquivo (PNG transparente ou SVG) enviado pelo cliente, e
  `logo_posicao`: `topo-esquerda`, `rodape-centro` etc. `null` se o feed não usa logo.
- `logo_variantes` (opcional): `{"sobre_escuro", "sobre_claro", "sobre_primaria", "sobre_secundaria"}` —
  a versão que entra sozinha em cada fundo (tema da linha editorial, cartelas de vídeo). PNG
  transparente ou **SVG só com paths** (sem script, fonte externa ou imagem embutida). Escolha
  olhando cada arquivo sobre o fundo: variante com traço na cor primária some no fundo primária.
  Sem `sobre_primaria`, o renderizador usa `sobre_claro`; sem `sobre_secundaria`, `sobre_escuro`.
- `logo_outras_variantes` (opcional): símbolo, monograma para capa de Reel, avatar — registro do que o cliente enviou.
- `assinatura`: o @ ou o site no rodapé? Escreva o texto exato, ou `nenhuma`.
- `recorrentes`: lista curta — "selo circular com o ano de fundação", "moldura fina de 12 px na cor primária".
  Nunca contador de peças (01/06), barra de progresso ou numeração de slide: regra do estúdio.
- `proibidos` (opcional): o que não se repete nas peças, com quem decidiu e quando.

## voz

| Campo | Exemplo |
|---|---|
| `tom` | "acolhedor e direto, sem gírias" |
| `pessoa` | `nós → você` |
| `emojis` | `nenhum`, `pontual` (1–2 por legenda), `frequente` |
| `hashtags_fixas` | as que aparecem em quase toda legenda |
| `cta_preferido` | "Reserve pelo link da bio" |
| `palavras_evitar` | o que o cliente não quer ("barato", "promoção relâmpago") |

## video

Vem dos teardowns da análise (Passo 8), só dos vídeos **do cliente** e dos que ele
aprovou como referência.

| Campo | Exemplo |
|---|---|
| `ritmo_corte_s` | 1.8 (duração média de plano) |
| `legenda_na_tela` | `sempre`, `gancho` (só nos 3 s iniciais), `nunca` |
| `estilo_movimento` | `sobrio` (fades, deslizes curtos), `energico` (cortes secos, zooms, textos que entram batendo) |
| `sfx_familia` | `sutil` (cliques, pops leves), `impacto` (whoosh, hits), `nenhum` |

## contato e diretrizes de anúncio (opcionais)

- `contato.whatsapp`: número exibido no botão do template `cta-card` — só o que o cliente informou.
- `diretrizes_anuncio.regras`: quando as peças viram anúncio (Meta), as regras que o cliente
  passou (CTA, zonas seguras, nada de preço/prazo/resultado não informado, nada de afirmar
  atributos pessoais do espectador, nada de marca de terceiros). A revisão confere cada peça contra elas.
- `cores.papeis.secundaria` e `cores.papeis.claro` (opcionais) viram `--secundaria` e `--claro`
  nos templates; `tipografia.rotulo` vira `--fonte-rotulo`/`--peso-rotulo`/`--espacamento-rotulo`.
