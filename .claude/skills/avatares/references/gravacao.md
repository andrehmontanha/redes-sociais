# Gravação de treino para avatar em altíssima qualidade

O avatar nunca fica melhor que a gravação que o treinou. Vídeo do feed quase nunca
serve: tem música por baixo, cortes, outras pessoas, câmera em movimento. Uma sessão
dedicada de 15 minutos resolve.

## Requisitos do HeyGen (digital twin)

| Item | Mínimo | Ideal |
|---|---|---|
| Duração | 15 s | **2 a 5 min** de fala contínua (máx. 10 min) |
| Pessoas no quadro | 1 | 1, do início ao fim |
| Rosto | no quadro o tempo todo | olhando para a lente |
| Áudio | fala audível | fala limpa, sem música nem eco |

## Set

- **Câmera:** celular recente na câmera traseira, **4K 30 fps**, travado em tripé.
  Formato **vertical 9:16** se o avatar for usado em Reels (o treino herda o enquadramento).
- **Enquadramento:** do meio do peito para cima, olhos no terço superior, um palmo de
  folga acima da cabeça. Mesmo enquadramento que o avatar vai ter nos vídeos.
- **Luz:** janela de frente ou dois softboxes a 45°; nada de luz de teto dura, nada de
  contraluz. Rosto sem sombra no nariz.
- **Fundo:** liso e diferente da roupa e do cabelo (o recorte do fundo fica mais limpo).
- **Som:** microfone de lapela no celular; ambiente sem ar-condicionado barulhento.
- **Roupa:** a que a pessoa usa no trabalho (uniforme da marca, se houver). Sem listras
  finas, sem verde se houver fundo verde, sem logotipos de terceiros.

## Direção

- Fale naturalmente sobre o próprio trabalho, como se explicasse a um hóspede ou
  cliente — em português, no tom da marca. Gesticule como normalmente gesticula.
- Pausas curtas entre frases, boca fechada ao fim de cada pausa.
- Nada de ler roteiro com os olhos correndo: se precisar, teleprompter atrás da lente.
- Grave 2 ou 3 tomadas de 3 minutos; escolha a melhor.

## Depois

1. Copie o arquivo para `clientes/<handle>/avatares/<pessoa>/gravacao/`.
2. `avatar.py criar` confere duração e áudio antes de enviar.
3. `avatar.py consentimento` gera o link para a **própria pessoa** gravar a declaração
   de consentimento no HeyGen (vale 24 h, uma gravação).
