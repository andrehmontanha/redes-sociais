# Reedição de vídeo com apresentador — estilo padrão

Modelo: `scripts/reeditar_apresentador.py`. Referência aprovada: Reel "IA é coisa de
empresa grande?" da Braturix (02/10/2026), reeditado a partir do vídeo do próprio
cliente. Toda edição de vídeo com uma pessoa falando para a câmera parte daqui.

## O que o estilo é

| Camada | O que faz | Por quê |
|---|---|---|
| Vídeo em tela cheia | o vídeo do cliente, cortado em `corte`, com a voz original | a pessoa é o que segura (rosto > ilustração) |
| Punch-ins (`zooms`) | escala do vídeo em batidas da fala, ancorada em `origem_zoom_y` | ritmo sem cortar a fala |
| Manchete no quadro 0 | gancho escrito numa placa na cor de fundo do kit | anúncio roda mudo; a capa precisa do gancho |
| Legenda (`legendas`) | 1–4 palavras por vez, *ênfase* na cor de destaque, numa tarja da marca | legenda sempre, na paleta (nunca amarela) |
| Cobertura (`cobrir_legenda_antiga`) | a mesma tarja fica sobre a faixa da legenda queimada no original | reaproveitar vídeo antigo sem a legenda fora da marca |
| Ícones (`tile`) | objetos vetoriais originais que ilustram o que é dito, entram com rebote | didático e interativo; nada de marca de terceiros |
| Risco | traço na cor primária atravessando a manchete ("Não, não é.") | virada de crença visível |
| Cartela (`cartela`) | tela cheia na cor de fundo, título grande + fileira de ícones; a voz segue | o nome da oferta ou o ponto principal ganha destaque |
| Logo | logo do kit no alto quando a marca é dita | assinatura sem cartela extra |
| Cartela final | rótulo, título, botão com o WhatsApp de `contato.whatsapp`, ilustração do cliente | CTA de anúncio com 3,4 s de leitura |
| Som | voz + trilha da biblioteca com ducking + SFX da família do kit | −14 LUFS no mixador |

Sem contagem na tela: nada de `01/06`, número de cena ou barra de progresso.

## Roteiro (`roteiro-reedicao.json`)

Tempos em segundos **do vídeo original** (o script subtrai o início do `corte`).
Caminhos relativos à pasta do roteiro.

```json
{
  "brand_kit": "../../brand-kit.json",
  "video": "../../referencias/cliente/videos/ig-XXXX.mp4",
  "corte": [0, 18.53],
  "trilha": "pulso-leve-100bpm", "ganho_trilha": -12,
  "origem_zoom_y": 67.2,
  "cobrir_legenda_antiga": {"topo": 1218, "de": 0.25},
  "zooms": [{"t": 3.5, "s": 1.08, "d": 0.3}, {"t": 13.1, "s": 1.0, "d": 0.5, "ease": "power2.inOut"}],
  "legendas": [[0.3, 1.3, "Você acha que"], [2.3, 3.5, "de *empresa grande?*"]],
  "graficos": [
    {"tipo": "manchete", "t": 0.0, "ate": 4.6, "texto": "Gancho *escrito*", "topo": 250, "tam": 96, "sfx": "pop"},
    {"tipo": "tile", "icone": "predio-grande", "x": 700, "y": 560, "t": 0.6, "ate": 4.6, "tam": 200},
    {"tipo": "risco", "t": 3.55, "ate": 4.6, "topo": 418, "largura": 690, "sfx": "swipe"},
    {"tipo": "tile", "icone": "relogio", "icone_texto": "24h", "x": 72, "y": 560, "t": 9.5, "ate": 13.1, "sfx": "ding"},
    {"tipo": "cartela", "t": 14.85, "ate": 16.7, "rotulo": "A gente chama de", "texto": "Nome da *oferta.*",
     "icones": [["loja", "Pequena"], ["predio-medio", "Média"], ["predio-grande", "Grande"]], "sfx": "brilho"},
    {"tipo": "logo", "t": 16.7, "ate": 18.53, "topo": 260}
  ],
  "cta_duracao": 3.4,
  "cta": {"rotulo": "Nome da oferta", "titulo": "Chama no *WhatsApp.*", "botao_sub": "Fale com a <marca>",
          "sub": "<assinatura do kit, se omitido>", "ilustracao": "../../material-cliente/ilustracao.png"}
}
```

Ícones da biblioteca (`reeditar_apresentador.py --icones`): loja, predio-medio,
predio-grande, torre, tesoura, secador, chave, chat-ia, chip, faisca, relogio (com
`icone_texto` opcional), check (traço animado), calendario, sino, lua, pessoa,
seta-cresce, balanca. Precisa de outro? Desenhe no script, genérico e original, no mesmo traço.

## De onde vêm os tempos

1. **Legenda queimada no vídeo do cliente** (como no DdtjnazBQHh): extraia a faixa da
   legenda a 10 fps, monte tiras com o tempo e leia com `Read`; cada troca de texto é
   uma entrada de `legendas`. A faixa vira o `topo` de `cobrir_legenda_antiga`.
2. **Transcrição** com tempo por palavra, se houver ferramenta no ambiente.
3. **Sem transcrição**: envelope de energia do áudio para achar as frases, e **nada de
   legenda**. Use só manchetes com texto que o cliente publicou e diga ao usuário que o
   vídeo não está legendado (anúncio roda mudo).

## Layout seguro (1080×1920)

Topo 220 px, base 460 px e coluna direita 170 px ficam livres (interface do app e do
anúncio). Rosto costuma ocupar y 540–1000 no centro: ícones nas laterais (x 72 ou
x 700–720, até 200 px), manchete em y ≥ 250, tarja em torno de y 1218. Pontos que cobririam
o rosto viram `cartela`.

## Revisão antes da prévia

- `npx hyperframes check` sem erro (contraste inclusive); `validar_reel.py` saída 0.
- Folha de quadros e quadro 0 lidos com `Read`: gancho legível no quadro 0, nenhum
  ícone sobre o rosto, nada na base/coluna direita, CTA com o número do kit.
- Com cobertura de legenda antiga: recorte ampliado da faixa em 3–4 momentos, sem
  sobra da legenda original.
- Fala do cliente com preço, prazo ou promessa: a legenda é fiel, mas aponte o trecho
  ao usuário antes de virar anúncio.
