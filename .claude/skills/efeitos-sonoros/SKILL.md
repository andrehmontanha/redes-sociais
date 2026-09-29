---
name: efeitos-sonoros
description: Biblioteca de efeitos sonoros e trilhas livres de direitos, com catálogo e licença registrada para cada som, e o mixador que aplica trilha + efeitos num vídeo por folha de deixas, masterizado a -14 LUFS. Use ao sonorizar um Reel ou vídeo, escolher trilha, pôr whoosh/pop/impacto nos cortes, pedir sound design, efeitos sonoros, SFX, trilha de fundo, ou ao adicionar um som novo à biblioteca.
---

# Efeitos sonoros e trilhas

Toda peça de áudio que vai para um vídeo publicado sai **desta biblioteca**, e
todo item da biblioteca tem licença registrada no `biblioteca/catalogo.json`.
Áudio em alta do Instagram é referência de ritmo e clima (vem da análise),
nunca arquivo a embutir: a licença dele vale dentro do app, não num MP4 publicado
pela API.

## O que tem

```bash
python .claude/skills/efeitos-sonoros/scripts/catalogo.py listar
python .claude/skills/efeitos-sonoros/scripts/catalogo.py buscar "impacto revelação"
```

A base é **sintetizada por código** (`gerar_biblioteca.py`, licença `propria`):
15 efeitos (whoosh, swipe, riser, impacto, hit, pop, clique, digitação, notificação,
ding, brilho, obturador, glitch) e 3 trilhas em loop (leve 100 bpm, energética 124
bpm, ambiente calmo). É determinística — rodar de novo recria os mesmos arquivos.

A família de efeitos de cada cliente está em `brand-kit.video.sfx_familia`:
`sutil` usa só a família `sutil`; `impacto` pode usar as duas; `nenhum` = só trilha.

## Sonorizar um vídeo

### 1. A folha de deixas nasce dos cortes, não do gosto

Cada efeito responde a um evento visual. Parta do roteiro cena a cena ou, com o
vídeo renderizado, dos cortes detectados:

```bash
python .claude/skills/analise-perfil-instagram/scripts/analisar_video.py <video.mp4> --saida <pasta>/cortes/
```

| Evento na tela | Efeito típico | Ganho |
|---|---|---|
| gancho (0–2 s) | `riser` terminando em `impacto-grave` ou `hit-seco` | −6 a −8 dB |
| corte de cena | `whoosh-curto` (enérgico) · `swipe` (sóbrio) | −10 a −12 dB |
| texto/elemento surgindo | `pop` · `clique` | −8 a −12 dB |
| número, preço, revelação | `impacto-grave` · `brilho` | −6 dB |
| dica, check, acerto | `ding` | −10 dB |
| CTA final | `riser` curto → `hit-seco` no logo | −8 dB |

Regras: no máximo **um efeito a cada ~1,5 s** (mais que isso vira ruído), nenhum
efeito sobre fala, e o efeito entra **2–3 quadros antes** do evento (t − 0,08 s):
o ouvido percebe som adiantado como sincronizado e som atrasado como erro.

Trilha: o `bpm` deve casar com o `ritmo_corte_s` do kit (100 bpm = batida a cada
0,6 s; cortes em múltiplos disso). Ganho entre −4 e −8 dB com voz, −2 a −4 sem.

### 2. Mixar

```bash
python .claude/skills/efeitos-sonoros/scripts/mixar_sfx.py <video.mp4> <deixas.json> --saida <final.mp4>
```

Formato de `deixas.json` no cabeçalho do script. O resultado sai com vídeo
intacto (sem recompressão), áudio AAC 48 kHz, −14 LUFS e pico −1 dBTP. Trilha
abaixa sozinha sob a voz quando `manter_audio_original` e `ducking` estão ligados.

Se a composição HyperFrames já mixa áudio (skill `hyperframes-audio`), use os
arquivos da biblioteca lá dentro e pule este passo — mas **nunca mixe duas vezes**.

### 3. Conferir

Não dá para ouvir aqui; dá para medir. Gere o espectrograma e leia com `Read`:

```bash
ffmpeg -i <final.mp4> -lavfi showspectrumpic=s=1600x400:legend=1 <final>-espectro.png
```

Cada efeito precisa aparecer no segundo previsto na folha. Efeito que não aparece
é deixa fora da duração ou ganho baixo demais.

## Adicionar som de fora

Só com licença que permita uso comercial em rede social, e registrada:

```bash
python .claude/skills/efeitos-sonoros/scripts/catalogo.py adicionar ~/Downloads/som.wav \
    --id aplauso-curto --tipo sfx --categoria destaque --familia sutil \
    --uso "comemoração, resultado" --licenca cc0 \
    --fonte "https://freesound.org/s/12345/" --autor "fulano"
python .claude/skills/efeitos-sonoros/scripts/catalogo.py validar
```

Fontes seguras: Freesound filtrado por **CC0**, Pixabay (Pixabay Content License),
bibliotecas pagas com o comprovante da licença (`--comprovante`). **CC-BY exige
crédito**: registre `--credito` e o mixador gera `<saida>.creditos.txt`, que o
publicador anexa à legenda. Arquivo sem registro no catálogo é recusado pelo mixador.
