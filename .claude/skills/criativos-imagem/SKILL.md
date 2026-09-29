---
name: criativos-imagem
description: Gera criativos estáticos de Instagram — post único, carrossel de até 10 peças e story — a partir do brand kit do cliente e das fotos do próprio perfil, renderizados em JPEG 1080 px prontos para a Graph API. Use quando pedirem post, arte, carrossel, story, criativo estático, peça para feed, "monta um post sobre…", ou quando o calendário editorial tiver uma pauta de imagem. Exige `brand-kit.json` validado (skill `identidade-visual`).
---

# Criativos de imagem

Criativo aqui não é inventado: é **montado** com o material do cliente dentro da
identidade que o perfil já tem. As fotos vêm de `clientes/<handle>/referencias/cliente/`
ou `material-cliente/`; as cores, fontes, margens e o tratamento de texto
vêm do `brand-kit.json`. Os templates não têm cor nem fonte própria — trocar
de cliente é trocar o kit.

## Antes de começar

1. `brand-kit.json` validado (`extrair_identidade.py --validar` com saída 0).
   O renderizador confere sozinho e recusa sem isso.
2. A pauta: do calendário editorial da análise, ou do pedido do usuário. Cada
   criativo responde a **um** objetivo (alcance, salvamento, clique, venda) e isso
   define o template.
3. As fotos: escolha pelo `tratamento_foto` do kit. Uma foto escura e fria num feed
   claro e quente quebra a grade mesmo com a tipografia certa. Leia as candidatas
   com `Read` antes de escolher.

## Templates

| Template | Para quê | Campos |
|---|---|---|
| `capa-carrossel` | primeira peça de carrossel: promessa + convite a arrastar | `titulo`, `rotulo`?, `subtitulo`?, `foto`?, `arraste`? |
| `lista` | peça de conteúdo: até 5 itens numerados | `titulo`, `itens` (lista), `rotulo`? |
| `texto-destaque` | frase de impacto, dado, pergunta — fundo sólido | `titulo`, `rotulo`?, `subtitulo`? |
| `foto-titulo` | foto do cliente em tela cheia com título | `foto`, `titulo`, `rotulo`?, `subtitulo`? |
| `citacao` | prova social — depoimento **real** | `citacao`, `autor`, `contexto`?, `foto`? |
| `oferta` | produto/serviço, preço, CTA | `titulo`, `preco`?, `cta`?, `rotulo`?, `foto`? |
| `prova-brand-kit` | prova visual do kit para o humano confirmar | — (lê do kit) |

`?` = opcional. Logo, assinatura, contador de carrossel e margem de segurança do
story entram sozinhos a partir do kit.

Densidade de texto segue `composicao.densidade_texto`: `minima` → títulos de até 6
palavras e nada de `subtitulo`; `media` → até 20 palavras por peça; `alta` → carrossel
educativo com `lista`.

Precisa de um layout que não existe? Crie `templates/<nome>.html` seguindo os
existentes: só variáveis CSS do kit, texto em elementos `.ajustar` (encolhe até caber)
ou `.seguro` (conferido contra a margem), e `data-campo` para o relatório apontar o campo.

## Fluxo

### 1. Escrever o roteiro

`clientes/<handle>/criativos/<AAAA-MM-DD>-<slug>/roteiro.json`:

```json
{
  "brand_kit": "../../brand-kit.json",
  "formato": "feed",
  "pauta": "pilar educativo · objetivo salvamento · calendário semana 2",
  "pecas": [
    {"template": "capa-carrossel", "campos": {"rotulo": "Guia rápido", "titulo": "5 motivos para…", "foto": "../../referencias/cliente/post01.jpg"}},
    {"template": "lista", "campos": {"titulo": "O que está incluso", "itens": ["…", "…"]}},
    {"template": "oferta", "campos": {"titulo": "…", "cta": "Reserve pelo link da bio"}}
  ]
}
```

Formatos: `feed` 1080×1350 (4:5, o que ocupa mais tela no feed — padrão), `quadrado`
1080×1080, `story` 1080×1920.

Texto: escreva na `voz` do kit (pessoa, emojis, CTA preferido). Nada de dado, preço,
depoimento ou promessa que o cliente não forneceu — criativo publicado vira compromisso.

### 2. Renderizar

```bash
python .claude/skills/criativos-imagem/scripts/renderizar_criativo.py \
    clientes/<handle>/criativos/<id>/roteiro.json
```

Gera `render/NN-<template>.jpg`, `render/folha.jpg` e `render/relatorio.json`.
Saída 1 = texto que não coube, fonte que não carregou ou foto fora da pasta do cliente.
Corrija o roteiro (encurte o texto — não reduza a fonte mínima) e rode de novo.

### 3. Revisar — você olha antes do humano

Leia `render/folha.jpg` e cada peça com `Read`. Confira:

- [ ] parece o feed do cliente lado a lado com a `grade.jpg` das referências?
- [ ] texto legível no tamanho do celular (a folha é quase isso)?
- [ ] nada importante sob o degradê ou atrás do logo?
- [ ] ortografia, acentos, preço e datas batendo com o que o cliente informou?
- [ ] a capa funciona sozinha — é ela que aparece no feed?

Só então a peça vai para a fila de aprovação (skill `publicar-instagram`).

## Limites

- Máximo de 10 peças por carrossel (limite da API).
- Foto de concorrente, de tendência ou de banco de imagem sem licença: o script
  recusa qualquer foto fora da pasta do cliente, e isso é de propósito.
- Fontes do Google Fonts são baixadas uma vez para `~/.cache/estudio-social/fontes/`.
  Fonte proprietária só com o arquivo enviado pelo cliente (`google_fonts: false` no kit).
