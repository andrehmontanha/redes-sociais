# Métricas: fórmulas, benchmarks e leitura

## As fórmulas

**Taxa de engajamento por seguidores (ER) — a que dá para calcular de fora**

```
ER do post = (curtidas + comentários) / seguidores × 100
ER do perfil = média dos ER dos posts da amostra
```

É a métrica padrão de mercado justamente porque qualquer um consegue calcular. A fraqueza dela: ignora alcance. Uma conta cujo conteúdo é entregue majoritariamente para não-seguidores (Reels virais) aparece com ER inflado; uma conta com muitos seguidores inativos herdados aparece penalizada.

**Taxa de engajamento por alcance (ERR) — a boa, só com Insights**

```
ERR = (curtidas + comentários + salvamentos + compartilhamentos) / alcance × 100
```

É o que mais se aproxima do sinal que o algoritmo usa. Se o usuário tiver acesso ao Insights, priorize esta e apresente a de seguidores como secundária. Referência: acima de 5% é forte, 2–5% saudável, abaixo de 1% pede revisão de conteúdo.

**Proporção comentário/curtida**

```
C/L = comentários / curtidas × 100
```

Comentário custa mais esforço que curtida, então essa razão mede profundidade, não volume. Entre 1% e 5% é o normal. Acima de 5% costuma indicar conteúdo que provoca conversa (ou uma pergunta explícita na legenda — confira antes de elogiar). Abaixo de 0,5% com muitas curtidas é o padrão clássico de engajamento comprado ou de conteúdo bonito que não pede nada.

**Cadência**

```
posts por semana = nº de posts / (dias entre o post mais antigo e o mais novo) × 7
```

Calcule também o maior intervalo sem publicar dentro da amostra. Duas contas com "3 posts por semana" na média são coisas muito diferentes se uma publica de forma regular e a outra concentra tudo em rajadas seguidas de três semanas de silêncio — e a segunda perde alcance por isso.

**Taxa de visualização de Reels**

```
views / seguidores × 100
```

Acima de 100% significa que o Reel saiu da base de seguidores e foi distribuído para fora — o sinal mais claro de que o algoritmo está favorecendo aquele conteúdo. Vale destacar no relatório quais Reels passaram desse limiar e o que eles têm em comum.

## Benchmarks por faixa de seguidores

O ER cai conforme a conta cresce — é matemático, não é fracasso. Comparar uma conta de 200 mil com uma de 3 mil sem ajustar a faixa produz conclusão errada.

| Faixa de seguidores | Baixo | Saudável | Forte |
|---|---|---|---|
| < 1.000 | < 3% | 3–8% | > 8% |
| 1.000 – 10.000 | < 2% | 2–5% | > 5% |
| 10.000 – 50.000 | < 1,5% | 1,5–3,5% | > 3,5% |
| 50.000 – 200.000 | < 1% | 1–2,5% | > 2,5% |
| 200.000 – 1M | < 0,8% | 0,8–2% | > 2% |
| > 1M | < 0,5% | 0,5–1,5% | > 1,5% |

Ajustes de contexto antes de dar o veredito:

- **Conta nova** (menos de 6 meses) tende a ter ER alto e instável. Não trate como sustentável.
- **Amostra pequena** (menos de 9 posts próprios) → apresente o resultado como indicativo, não conclusivo.

## Calibração por nicho

Este é o passo que impede o erro mais comum da análise externa: dar um veredito duro com o número certo e a régua errada. Um ER de 1,2% é fraco numa conta de gastronomia e excelente numa de contabilidade — e o cliente sabe disso, mesmo que não saiba explicar.

A lógica por trás dos multiplicadores é uma só: **as pessoas interagem por prazer ou por decisão racional?** Conteúdo que dá vontade de marcar um amigo engaja muito; conteúdo que alguém consome pensando em contratar engaja pouco e converte muito. Os dois podem ser bem-sucedidos.

| Nicho | Multiplicador | Lógica |
|---|---|---|
| Humor e entretenimento | ×1,5 | interação é o próprio produto |
| Pet | ×1,4 | afeto gera marcação e compartilhamento |
| Moda e beleza | ×1,3 | consumo visual, salvamento alto |
| Fitness | ×1,3 | comunidade e identificação |
| Gastronomia | ×1,3 | desejo imediato, marcação de acompanhante |
| Turismo e hotelaria | ×1,2 | aspiracional, mas ciclo de compra longo |
| Varejo e e-commerce | ×1,0 | referência neutra |
| Educação | ×1,0 | referência neutra |
| Casa e decoração | ×1,0 | referência neutra |
| Serviços locais | ×1,0 | referência neutra |
| Saúde e clínicas | ×0,8 | tema sensível, gente evita interagir em público |
| Imobiliário | ×0,7 | decisão longa, audiência pequena e qualificada |
| Tecnologia | ×0,7 | consumo informativo |
| Financeiro | ×0,6 | interagir publicamente expõe |
| Jurídico | ×0,6 | idem, com restrição adicional de publicidade |
| B2B e industrial | ×0,5 | audiência mínima e altamente específica |

O multiplicador incide sobre os pisos da faixa de seguidores. Turismo com 96,9 mil seguidores, por exemplo, sai de "saudável a partir de 1,0%" para "1,2%".

`scripts/calcular_metricas.py --listar-nichos` mostra a tabela, e `--nicho <nome>` aplica. Se o nicho do cliente não estiver na lista, escolha o mais próximo **em lógica de consumo**, não em aparência: uma clínica de estética funciona mais como beleza que como saúde, e uma consultoria de RH mais como B2B que como educação. Diga no relatório qual régua você usou — é o tipo de transparência que sustenta a conclusão quando o cliente questiona.

## Collabs não entram no ER

Publicações em colaboração hospedadas na conta de um criador aparecem na grade do cliente, mas as curtidas vieram da audiência **do criador**. Dividir esse número pelos seguidores do cliente produz uma taxa que não descreve nada.

Trate-as como um bloco separado, em números absolutos, e use a comparação para uma leitura que costuma ser reveladora: quando um único post de criador gera mais comentários que um mês inteiro de conteúdo próprio, a marca não tem um problema de audiência — tem um problema de voz.

O percentual da grade ocupado por collabs também é um dado por si só. Acima de 50%, a marca terceirizou a própria comunicação, e vale dizer isso com todas as letras: aquele conteúdo mora na conta do criador e sai de cena quando o contrato acaba.

## Média versus mediana: leia as duas

O script devolve as duas de propósito. Quando divergem muito, a diferença **é** a descoberta:

- **Média bem acima da mediana** → um ou dois posts virais puxam o resultado. O perfil não tem engajamento consistente; ele teve sorte (ou acertou uma fórmula que não repetiu). A pergunta certa para o relatório é: o que aquele post fez de diferente, e por que não virou padrão?
- **Média próxima da mediana** → desempenho previsível. Bom para planejar, e sinal de que mudanças de conteúdo terão efeito visível.
- **Mediana acima da média** → alguns posts muito fracos derrubam o conjunto. Vale identificar o que eles têm em comum — normalmente é um formato ou um tema que não pertence ali.

Sempre reporte a **mediana** como número principal quando a amostra tiver menos de 12 posts. Ela resiste melhor a outliers.

## Quando as curtidas estão ocultas

Cada vez mais comum, e não impede a análise. Nesse caso:

- Use **comentários por post / seguidores × 100** como proxy comparativo. Não é ER e não deve ser rotulado como tal no relatório — nomeie como "taxa de comentários".
- Referência aproximada: 0,05%–0,2% é a faixa comum; acima disso indica conteúdo que gera conversa.
- Reels ainda mostram visualizações, então a taxa de visualização vira sua métrica mais forte.
- Diga isso explicitamente na seção de limitações e ofereça fechar a lacuna com um print do Insights.

## Sinais de engajamento artificial

Vale checar sempre em análise de prospect — o cliente pode estar comprando sem saber, ou o concorrente pode parecer maior do que é. Nenhum sinal isolado prova nada; três juntos são forte indício:

- Muitas curtidas com quase nenhum comentário (C/L abaixo de 0,3%).
- Comentários genéricos e repetidos ("top!", "🔥🔥🔥", "nice") de perfis sem foto, sem posts ou com @ alfanumérico aleatório.
- Salto abrupto de seguidores sem post correspondente que explique.
- Razão seguidores/seguindo muito alta numa conta pequena e recente.
- ER muito acima do benchmark da faixa combinado com Reels de visualização baixa — engajamento comprado infla curtidas, não a entrega do algoritmo.

Como escrever isso no relatório: descreva os sinais observados e o que eles costumam indicar, sem acusar. "O padrão de comentários — 18 dos 20 são emoji isolado, vindos de perfis sem publicações — é típico de engajamento pago" é defensável. "Essa conta compra seguidores" não é, e você não tem como provar.

## Métricas do Insights (quando o usuário tem acesso)

Peça e incorpore, em ordem de valor:

1. **Alcance x impressões (30 dias)** — a razão impressões/alcance mostra quantas vezes a mesma pessoa viu. Muito acima de 1,5 sugere que o conteúdo circula na mesma bolha.
2. **Seguidores ganhos e perdidos** — crescimento líquido é o que importa. Perda alta em semana de muito post indica desalinhamento entre conteúdo e audiência.
3. **Salvamentos e compartilhamentos por post** — os sinais mais fortes para o algoritmo hoje. Um post com poucas curtidas e muitos salvamentos é um acerto que a análise externa não enxerga.
4. **Visitas ao perfil e cliques no link** — a taxa de conversão real de conteúdo em interesse. Cliques baixos com visitas altas apontam problema de bio, não de conteúdo.
5. **Horários de atividade da audiência** — vira recomendação direta de agenda de postagem.
6. **Demografia** — confirma ou desmente para quem o perfil acha que está falando. É a fonte das descobertas mais desconfortáveis e mais valiosas.
