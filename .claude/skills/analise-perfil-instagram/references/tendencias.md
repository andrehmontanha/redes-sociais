# Tendências: coleta, aderência e ciclo de vida

Este módulo é o que separa um diagnóstico de um plano de conteúdo. O diagnóstico diz o que está errado; o cruzamento com tendências diz o que gravar na quinta-feira.

A pergunta que ele responde não é "o que está bombando?" — isso qualquer um vê no Explorar. É: **o que está bombando que esta marca consegue fazer bem, ainda tem janela aberta, e o nicho dela ainda não saturou?**

## Duas camadas de recorte

Toda coleta de tendência roda em duas camadas, e a diferença entre elas costuma ser onde mora a oportunidade:

1. **Nicho + região do cliente** — o que os concorrentes diretos e os criadores daquele setor e daquela cidade estão fazendo. É a camada que gera pauta imediatamente aplicável, e a que revela saturação.
2. **Instagram brasileiro em geral** — formatos, ganchos, áudios e estéticas circulando fora do nicho. É a camada que gera vantagem: uma trend que já rodou em moda e ainda não chegou ao setor do cliente chega com a curva de novidade intacta.

Quando as duas camadas apontam a mesma coisa, a trend provavelmente já está no pico. Quando só a camada geral aponta, é a hora de entrar.

## Fontes de coleta

Três fontes, todas dentro do Chrome logado do usuário. Elas se complementam: a primeira mostra o que o algoritmo está distribuindo, a segunda mostra o que o nicho já adotou, a terceira mostra a trilha sonora que está carregando alcance.

### A. Explorar e Reels em alta

`https://www.instagram.com/explore/` e a aba de Reels mostram o que o algoritmo está empurrando **para a conta logada** — ou seja, já filtrado pelos interesses dela. Isso é uma força e um viés ao mesmo tempo: se o usuário usa a conta da agência, o Explorar reflete o universo de social media, não o do cliente.

Diga isso ao usuário quando o Explorar vier claramente enviesado, e compense com a fonte B, que é ancorada no nicho real.

Colete de 15 a 25 itens: formato, gancho da primeira linha ou do primeiro segundo, tema, áudio e sinais de volume visíveis. Agrupe pelo que se repete — uma trend é um padrão que aparece três vezes ou mais, não um post que você achou bom.

### B. Perfis de referência do nicho

#### B1. Minerar os seguidos do próprio perfil — comece por aqui

Quem uma marca segue é a fonte de referência mais honesta que existe. Ela não escolheu aquelas contas para uma análise; escolheu porque interessam ao negócio. O resultado costuma revelar o nicho real, os concorrentes que ela observa, a imprensa local e os criadores que já orbitam a marca.

Verificado em coleta real, pela API interna, com a sessão do próprio usuário:

```js
// 1) o id do perfil está no HTML da página dele
const h = document.documentElement.innerHTML;
const uid = (h.match(/"profile_id"\s*:\s*"(\d+)"/) || [])[1];

// 2) a lista de seguidos, 50 por página
const r = await fetch(`/api/v1/friendships/${uid}/following/?count=50`,
                      {headers: {'X-IG-App-ID': '936619743392459'}, credentials: 'include'});
const j = await r.json();
({ n: j.users.length, temMais: !!j.next_max_id,
   users: j.users.map(u => ({u: u.username, v: u.is_verified})) })
```

`next_max_id` pagina (`&max_id=<valor>`). Para um perfil que segue centenas de contas, duas ou três páginas bastam — o que interessa está no topo, e varrer tudo só gasta chamada.

**Como ler a lista.** Agrupe antes de julgar: concorrentes diretos, fornecedores e parceiros, imprensa e poder público local, criadores, e contas sem relação com o negócio. A proporção já diz coisa — uma marca que só segue clientes e nenhuma referência do setor costuma ter conteúdo endogâmico.

E extraia **termos**, não só perfis: as palavras que se repetem nos nomes e nas bios dos seguidos são o vocabulário real do nicho, e servem de semente para busca de hashtag e de tendência.

Numa coleta real de um resort, os seguidos trouxeram a prefeitura, o portal de notícias da cidade, o festival local, restaurantes da região e criadores de viagem — mapa de nicho que nenhuma busca por palavra-chave teria montado tão bem.

#### B2. O filtro de "em alta"

Referência serve para dizer o que funciona **agora**. Um perfil que bombou há um ano e esfriou ensina história, não prática — e pior, ensina um formato que o algoritmo já deixou de premiar.

Antes de aceitar um perfil como referência, exija os três:

1. **Publicou nos últimos 7 dias.** Conta parada não tem leitura atual do algoritmo.
2. **Ao menos 3 posts nos últimos 30 dias.** Uma publicação isolada não mostra padrão.
3. **Não está em queda.** Compare a mediana dos 3 posts mais recentes com a mediana da amostra inteira: se os recentes estão abaixo, o perfil está esfriando e o que ele faz hoje não é o que deu certo.

Um perfil que falha em qualquer um dos três ainda pode entrar — mas **como referência histórica, rotulada assim no relatório**, nunca como "o que está funcionando". A distinção protege o cliente de copiar um formato vencido.

Registre a checagem no relatório em uma linha por perfil: última publicação, posts nos últimos 30 dias, e se está subindo ou caindo. É o que sustenta a escolha quando o cliente perguntar por que aqueles perfis e não outros.

#### B3. Coletar



**A skill sugere os perfis e espera aprovação antes de coletar.** Monte uma lista de 5 a 8 candidatos a partir de: contas que o perfil analisado segue, sugestões do próprio Instagram ("Sugestões para você" na página do perfil), busca por hashtags do nicho e da cidade, e perfis que aparecem nos collabs recentes.

Apresente a lista com uma linha de justificativa por perfil ("concorrente direto na mesma cidade", "criador de viagem que já postou sobre o cliente") e só colete depois do OK. Isso evita gastar vinte navegações em perfis que o usuário sabe que não servem.

De cada perfil aprovado, colete os 6 a 9 posts mais recentes com o mesmo extrator do perfil principal. O que interessa aqui não é o ranking de seguidores — é **quais formatos, ganchos e áudios estão repetindo no nicho e com que desempenho relativo**.

### C. Áudios em alta

O áudio é a alavanca de distribuição mais subestimada do Instagram, e é onde a maioria dos perfis corporativos perde de graça: quando todo Reel usa "Áudio original", a conta fica fora de toda a distribuição por áudio.

Como coletar: em cada Reel com bom desempenho (do Explorar ou dos perfis de referência), o nome do áudio aparece no topo e é clicável. A página do áudio (`/reels/audio/<id>/`) mostra **quantos Reels o usam** e os que estão performando com ele. Esse número é o melhor indicador público de volume que existe.

Para cada áudio candidato, registre:

- nome e link da página do áudio
- volume atual (nº de Reels)
- volume aproximado alguns dias antes, se estimável pelas datas dos Reels no topo da página — é o que permite calcular crescimento
- se o nicho do cliente já está usando (fonte B) ou se ainda é só camada geral
- o tipo: música, trecho de fala/meme, ou som ambiente

Limitação honesta: a web não expõe a curva histórica de uso de um áudio. A estimativa de crescimento é grosseira e deve ser apresentada como tal.

## Rubrica de aderência (0 a 10)

Cada tendência recebe uma nota. A rubrica existe para impedir as duas falhas clássicas: descartar tudo por conservadorismo, e entrar em qualquer coisa por oportunismo.

| Critério | Peso | O que avaliar |
|---|---|---|
| Ligação com o produto ou a oferta | 0–4 | A trend permite mostrar o que a marca vende sem forçar? Nota 4 quando o produto **é** o conteúdo; nota 0 quando só dá para encaixar a marca no final. |
| Encaixe com um pilar que já performa | 0–3 | Cruze com a tabela de pilares do relatório. Uma trend que cai no pilar de melhor ER começa na frente. |
| Viabilidade de produção | 0–2 | Dá para gravar com a estrutura que o cliente tem, nesta semana? Trend que exige equipe, locação ou ator não é pauta, é projeto. |
| Segurança de marca | 0–1 | Tom, contexto de origem e risco de leitura ambígua. Se a trend nasceu de polêmica ou humor de risco, é 0 — e vale dizer por quê. |

**Corte por apetite** (definido com o usuário no início):

- Conservador: entra o que tirou 8 ou mais.
- Equilibrado (padrão): entra de 6 para cima; entre 6 e 7 vai com adaptação sugerida.
- Agressivo: entra de 4 para cima, com o risco declarado por escrito.

Independente do apetite, **nota 0 em segurança de marca elimina a trend.** Alcance não compensa dano de posicionamento, e é o consultor que assina a recomendação.

## Ciclo de vida: quanto tempo essa trend ainda rende

Entrar tarde numa trend é pior que não entrar: sinaliza que a marca não acompanha, e o alcance já não vem. Por isso toda tendência sai do relatório com estágio, janela restante estimada e risco de saturação.

### Duração típica por categoria

Ponto de partida empírico, a ser ajustado pelos sinais observados:

| Categoria | Duração útil típica | Pico costuma cair em |
|---|---|---|
| Áudio viral (música/trecho) | 10 a 20 dias | dia 7 a 14 |
| Meme ou trecho de fala | 5 a 15 dias | dia 4 a 8 |
| Pauta ligada a evento (show, novela, notícia) | 3 a 10 dias | dia 2 a 4 |
| Challenge ou coreografia | 2 a 4 semanas | semana 2 |
| Formato ou estrutura de Reel ("POV", "3 coisas que") | 4 a 12 semanas | semana 3 a 5 |
| Estética visual (paleta, tipo de corte, filtro) | 3 a 6 meses | mês 2 |
| Pauta sazonal (feriado, férias, temporada) | janela fixa da data | 7 a 10 dias antes da data |

Formatos e estéticas duram muito mais que áudios — o que significa que uma marca com produção lenta deve apostar neles, e deixar os áudios para quem consegue gravar no mesmo dia. Essa é frequentemente a recomendação mais útil do módulo inteiro.

### Como estimar a janela restante

`scripts/ciclo_tendencia.py` faz a conta, mas o raciocínio precisa fazer sentido para você defender diante do cliente:

```
janela_restante = duração_típica_da_categoria − dias_desde_a_primeira_aparição_observada
```

ajustada por três multiplicadores:

- **Ainda crescendo** (volume subindo, ou os Reels de melhor desempenho com o áudio são dos últimos 3 dias): × 1,3
- **Já passou o pico** (os melhores Reels com o áudio têm mais de 10 dias): × 0,5
- **Saturada no nicho** (3 ou mais perfis de referência já publicaram usando): × 0,5

E classificada em quatro estágios:

- **Emergente** — volume subindo, nicho ainda não adotou. Melhor momento para entrar; é aqui que a trend entrega alcance desproporcional.
- **No pico** — volume alto e estável, nicho começando a adotar. Ainda vale, com execução rápida e um diferencial próprio.
- **Saturando** — o nicho todo já usou. Só entre com um ângulo genuinamente diferente, ou não entre.
- **Saindo** — volume caindo. Não entre. Registre no relatório como aprendizado de formato, não como pauta.

O que a durabilidade projetada realmente informa é **o prazo de produção**: uma trend com janela de 4 dias e um cliente que aprova pauta em uma semana são incompatíveis, e dizer isso no relatório vale mais que a pauta em si.

## Como isso vira entrega

O usuário desta skill quer os quatro formatos juntos. Eles se encaixam em cascata: a lista prioriza, a pauta detalha, o calendário distribui e o roteiro produz.

### 1. Lista com nota de aderência

Tabela: tendência · tipo · estágio · janela restante · aderência (0–10) · por que essa marca.

### 2. Pauta pronta

Para cada trend aprovada:

- **Ideia** em uma linha
- **Formato** e duração
- **Áudio sugerido**, com link da página do áudio
- **Gancho** — a primeira linha da legenda ou os 2 primeiros segundos, escritos, não descritos
- **CTA**, coerente com o formato e com o objetivo declarado do cliente
- **Pilar** que ela reforça

### 3. Calendário editorial (2 a 4 semanas)

Distribua respeitando três coisas: a cadência que o cliente consegue sustentar (não a ideal), o equilíbrio entre pilares — corrigindo o descompasso encontrado na análise — e a janela de cada trend, com as de prazo curto primeiro.

Reserve de 20% a 30% dos slots para conteúdo perene do pilar de melhor desempenho. Um calendário 100% de trends deixa a conta refém do que estiver bombando e apaga a identidade da marca.

### 4. Roteiro cena a cena

Para as 2 ou 3 melhores pautas:

| Tempo | Cena | Texto na tela | Áudio |
|---|---|---|---|
| 0–2s | o que aparece | o gancho, escrito | entrada da faixa |

Mais a legenda completa e os hashtags. O critério de qualidade aqui é simples: o cliente consegue gravar sem te ligar para perguntar o que fazer?

## O que nunca fazer neste módulo

- **Inventar volume de áudio ou número de Reels.** Se não conseguiu ler a página do áudio, diga que não conseguiu.
- **Apresentar a estimativa de janela como certeza.** É projeção baseada em duração típica, e o relatório precisa dizer isso.
- **Recomendar trend que a marca não consegue produzir.** Viabilidade vale 2 pontos na rubrica justamente porque pauta impossível é ruído caro.
- **Copiar o post do concorrente.** A referência serve para extrair o padrão — o gancho, a estrutura, o motivo de funcionar — não para reproduzir o conteúdo.
