---
name: criativos-video
description: Produz Reels e vídeos de story na identidade do cliente — roteiro de cenas com fotos e vídeos do próprio perfil, motion graphics com HyperFrames (texto animado, zoom, transições no estilo do brand kit), efeitos sonoros e trilha da biblioteca livre de direitos, e validação contra a especificação da Graph API. Use quando pedirem Reel, vídeo, motion, animação, "transforma esse roteiro em vídeo", vídeo com efeitos sonoros, ou quando o calendário editorial tiver uma pauta de Reel. Exige `brand-kit.json` validado.
---

# Criativos de vídeo (Reels)

O Reel é montado, não inventado: **material do cliente** (fotos e vídeos em
`clientes/<handle>/referencias/cliente/` e `material-cliente/`) + **identidade do
kit** (cores, fontes, ritmo, estilo de movimento, família de efeitos) + **estrutura
que funciona no nicho** (vinda dos teardowns da análise — formato e ritmo, nunca
o conteúdo de terceiros).

Motor: **HyperFrames** (HTML → MP4, determinístico). As skills `hyperframes`,
`hyperframes-core`, `hyperframes-animation` e `hyperframes-creative` são a referência
técnica quando precisar ir além do montador — leia `hyperframes-core` antes de editar
o `index.html` gerado à mão.

## Fluxo

### 1. Roteiro de cenas

Parta do roteiro cena a cena da análise (seção "Roteiros" do relatório) e escreva
`clientes/<handle>/criativos/<AAAA-MM-DD>-<slug>/roteiro-video.json`:

```json
{
  "brand_kit": "../../brand-kit.json",
  "trilha": "pulso-leve-100bpm",
  "cenas": [
    {"tipo": "foto",  "midia": "../../referencias/cliente/piscina.jpg", "duracao": 2.4, "texto": "Seu domingo pode ser assim"},
    {"tipo": "video", "midia": "../../material-cliente/tour.mp4", "inicio_s": 3, "duracao": 3, "texto": "Piscinas a 38 °C", "som_original": false},
    {"tipo": "texto", "rotulo": "você sabia?", "titulo": "Direto da fonte, sem aquecimento", "duracao": 2.6},
    {"tipo": "cta",   "titulo": "Reserve pelo link da bio", "duracao": 3}
  ]
}
```

Regras de roteiro que valem para qualquer nicho:

- **Gancho nos 2 primeiros segundos, já visível no quadro 0.** O montador põe o
  texto da cena 1 na tela desde o início; escreva-o como promessa ou contradição, não
  como saudação.
- Duração de cena perto do `video.ritmo_corte_s` do kit (±30%). Reel sóbrio com
  cenas de 1 s parece outro perfil; Reel enérgico com cenas de 4 s perde a pessoa.
- 7 a 30 s para alcance; até 90 s só para conteúdo educativo que segura.
- Texto na tela: até 7 palavras por cena. Legenda completa vai na legenda do post.
- Termine com `cta` quando o objetivo for clique ou venda.
- Trilha: pelo `clima`/`bpm` do catálogo (`efeitos-sonoros`), casando com o ritmo.

### 2. Montar o projeto HyperFrames

```bash
python .claude/skills/criativos-video/scripts/montar_reel.py clientes/<handle>/criativos/<id>/roteiro-video.json
```

Gera `video/` com `index.html` (1080×1920, 30 fps, uma timeline GSAP pausada),
mídia copiada, **fontes e GSAP locais** (render não depende de CDN) e `deixas.json`
com a proposta de efeitos sonoros. Recusa mídia fora da pasta do cliente.

O estilo vem de `brand-kit.video.estilo_movimento`:

| | `sobrio` | `energico` |
|---|---|---|
| transição | crossfade 0,35 s | corte seco |
| texto | sobe com fade | palavra a palavra com rebote |
| foto | zoom 1 → 1,06 | zoom 1 → 1,12 |
| efeitos propostos | `pop`, `swipe`, `ding` | `hit-seco`, `whoosh-curto`, `impacto-grave` |

Texto fica dentro da área segura do Reel (220 px no topo, 460 px na base,
170 px à direita — onde a interface do app cobre).

Quer algo que o montador não faz (bloco do registry, transição com shader, legenda
sincronizada com fala)? Edite o `index.html` seguindo `hyperframes-core` e
`hyperframes-animation`; o montador é ponto de partida.

### 3. Checar e renderizar

```bash
cd clientes/<handle>/criativos/<id>/video
npx --yes hyperframes@0.8.90 check          # lint + runtime + layout + contraste WCAG
npx --yes hyperframes@0.8.90 render -o reel-mudo.mp4
```

`check` precisa terminar em **Check passed**. Erro de contraste é real (texto
branco sobre trecho claro da foto): troque a foto, mude o texto de cena ou
reforce o véu. Os avisos `nested_structure_needs_subcomposition` são sobre a
organização no Studio e não afetam o render.

### 4. Sonorizar

Revise `video/deixas.json` contra o vídeo (skill `efeitos-sonoros`) e mixe:

```bash
python .claude/skills/efeitos-sonoros/scripts/mixar_sfx.py video/reel-mudo.mp4 video/deixas.json --saida video/reel.mp4
```

### 5. Validar e assistir

```bash
python .claude/skills/criativos-video/scripts/validar_reel.py video/reel.mp4
python .claude/skills/analise-perfil-instagram/scripts/analisar_video.py video/reel.mp4 --saida video/revisao/
```

`validar_reel.py` confere a especificação da API (codec, fps, duração, tamanho,
áudio, faststart) — saída 1 bloqueia a publicação. Depois **leia
`video/revisao/contact-sheet.jpg` com `Read`** e extraia o quadro 0 (é a capa na
grade se não houver capa própria):

```bash
ffmpeg -ss 0 -i video/reel.mp4 -frames:v 1 video/revisao/quadro0.jpg
```

- [ ] o quadro 0 tem o gancho legível?
- [ ] cada cena parece o feed do cliente (cores, fonte, tratamento de foto)?
- [ ] nenhum texto sob a interface (base e coluna direita)?
- [ ] o CTA aparece com tempo de leitura (≥ 2 s)?

### Capa

Para a grade, gere uma capa com a skill `criativos-imagem` (template `foto-titulo`
ou `texto-destaque`, formato `story`, 1080×1920 — a grade mostra o recorte central
4:5). Sem capa própria, o publicador usa `thumb_offset` do quadro escolhido.

## Story em vídeo

Mesmo fluxo, com cenas curtas (até 15 s no total por story) e
`validar_reel.py --story`. Story não tem legenda nem capa.
