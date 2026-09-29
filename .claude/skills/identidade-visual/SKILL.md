---
name: identidade-visual
description: Extrai a identidade visual de um perfil do Instagram a partir do material do próprio cliente e grava o brand kit (`brand-kit.json`) que todos os criativos seguem — paleta medida, tratamento de foto, tipografia, composição, elementos recorrentes, tom de voz e estilo de vídeo. Use depois da análise do perfil e antes de gerar qualquer criativo; também quando pedirem identidade visual, brand kit, manual de marca, paleta do perfil, "fontes que o cliente usa", ou quando um criativo "não parece da marca".
---

# Identidade visual — do feed ao brand kit

O brand kit é o contrato entre a análise e a criação. Todo criativo de imagem e
de vídeo lê `clientes/<handle>/brand-kit.json`; nada é desenhado "no olho".
Se o kit estiver errado, todos os criativos saem errados do mesmo jeito — por
isso ele é **medido onde dá, observado onde não dá, e confirmado por um humano
antes de valer**.

## De onde vem o material

Só do **próprio cliente**:

- as imagens baixadas no Passo 7 da `analise-perfil-instagram`
  (`assets/cliente/originais/`) copiadas para `clientes/<handle>/referencias/cliente/`;
- material que o cliente enviou (logo, fotos de produto, manual de marca) em
  `clientes/<handle>/material-cliente/`.

Concorrentes e tendências **não** entram na medição. Eles informam formato e
ritmo (via teardown), nunca cor, fonte ou foto — criativo com a paleta do
concorrente é criativo do concorrente.

Se houver manual de marca enviado pelo cliente, ele vence a medição: registre os
valores dele com `"origem": "manual"` e use a medição só para conferir se o feed
segue o manual (a diferença é um achado para o relatório).

## Fluxo

### 1. Medir

```bash
python .claude/skills/identidade-visual/scripts/extrair_identidade.py \
    clientes/<handle>/referencias/cliente/ --handle <handle> \
    --saida clientes/<handle>/brand-kit.json
```

Mede paleta (k-means com peso por área), sugere papéis de cor (fundo, primária,
destaque, texto — o texto escolhido pelo maior contraste WCAG) e o tratamento de
foto (brilho, contraste, saturação, temperatura). Grava um rascunho com todos os
campos não mensuráveis marcados `PENDENTE`.

Mínimo de **9 imagens** (três linhas da grade) para a paleta ser da marca e não
de um post. Com menos, avise que a paleta é provisória.

### 2. Observar — é aqui que você olha

Monte uma folha com as referências e **leia com `Read`** — a grade inteira e ao
menos 6 posts individuais, incluindo os de melhor desempenho da análise:

```bash
python .claude/skills/analise-perfil-instagram/scripts/preparar_assets.py \
    --contact-sheet clientes/<handle>/referencias/cliente/ \
    --saida clientes/<handle>/referencias/grade.jpg
```

Preencha cada campo `PENDENTE` trocando `origem` para `observado` e citando
em qual post viu. Guia campo a campo em `references/brand-kit.md`. O essencial:

- **tipografia** — nomeie a fonte do Google Fonts mais próxima; título e texto
  separados. Se o feed não usa texto sobre imagem, diga isso: é uma decisão de
  marca, e os templates precisam respeitá-la.
- **composição** — alinhamento, margem, se o texto vai sobre foto ou em faixa,
  densidade de texto (palavras por arte).
- **elementos** — logo e onde ele aparece, selos, molduras, grafismos.
- **voz** — leia 10 legendas: pessoa (eu/nós/você), emojis, tamanho, CTA, hashtags fixas.
- **vídeo** — dos teardowns da análise: ritmo de corte, legenda na tela, estilo de movimento.

Os papéis de cor sugeridos podem estar errados — o fundo mais frequente em foto
de restaurante é a madeira da mesa, não a cor da marca. Corrija olhando.

### 3. Confirmar com o humano

Mostre o kit **como imagem**, não como JSON: renderize a prova do brand kit com
o template `prova-brand-kit` da skill `criativos-imagem` e envie com
`SendUserFile`, junto com as 3 a 6 referências que o sustentam.

Pergunte: "É assim que a marca se apresenta? Algo que o cliente não quer mais
repetir?" Só depois do "sim":

- `confirmado_por`: nome de quem confirmou e a data;
- `referencias_aprovadas`: os posts (shortcode ou arquivo) que definem a marca.

### 4. Validar

```bash
python .claude/skills/identidade-visual/scripts/extrair_identidade.py \
    --validar clientes/<handle>/brand-kit.json
```

Bloqueia com campo pendente, contraste texto/fundo abaixo de 4.5, sem
confirmação humana ou com menos de 3 referências aprovadas. **Código de saída
1 = nenhum criativo pode ser gerado ainda.**

## Versões

O brand kit não se sobrescreve (o script recusa). Quando a marca muda,
grave `brand-kit.json` novo com `"versao"` incrementada e mova o anterior para
`clientes/<handle>/historico/brand-kit-v<N>.json`. Criativos antigos continuam
rastreáveis à versão que os gerou.
