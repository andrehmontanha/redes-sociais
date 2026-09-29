---
name: avatares
description: Cria e usa avatares digitais de pessoas reais que aparecem no perfil do cliente (equipe, sócios, embaixadores), em altíssima qualidade (HeyGen digital twin + Avatar V, com voz clonada), sempre com consentimento documentado, só de maiores de 18 anos, com aviso de IA e revogação a qualquer momento. Use quando pedirem avatar, gêmeo digital, digital twin, clone de vídeo, "a pessoa do vídeo falando o roteiro", apresentador virtual, vídeo sem precisar gravar, ou para revogar/consultar o consentimento de alguém.
---

# Avatares com consentimento

Um avatar é a aparência, a expressão e a voz de uma pessoa real dizendo algo que ela
não disse. Isso só é aceitável com **consentimento livre, específico, documentado e
revogável** — e o estúdio trata esse consentimento como trava técnica, não como
formalidade. Imagem e voz para esse fim são **dados biométricos** (dado pessoal
sensível, LGPD art. 5º, II e art. 11).

## Regras que não se negociam

1. **Só maiores de 18 anos.** Criança e adolescente nunca viram avatar, nem com
   autorização dos pais. Na dúvida sobre a idade, não é candidato.
2. **Consentimento em duas camadas, as duas obrigatórias:** o termo assinado
   (`references/termo-consentimento.md`) registrado no estúdio **e** o vídeo de
   consentimento que a própria pessoa grava no HeyGen. Nenhuma dispensa a outra.
3. **Quem fala com a pessoa sobre o consentimento é o cliente ou o estúdio, nunca
   uma pressão velada.** Pessoa que é funcionária pode dizer não sem consequência —
   diga isso ao cliente com todas as letras.
4. **Sem reconhecimento facial.** Não rode detecção ou agrupamento de rostos nos
   vídeos do perfil para "achar pessoas" — isso já é tratar dado biométrico sem
   consentimento. Os vídeos servem para o **cliente apontar** quem aparece.
5. **O avatar só diz o que a pessoa aceitaria dizer.** Nada de depoimento de cliente,
   política, religião, promessa de saúde, sexualidade, nem falar em nome de terceiros.
   O script barra os temas óbvios; o roteiro inteiro passa por aprovação humana.
6. **Todo vídeo com avatar declara que é IA:** selo na tela durante o vídeo inteiro
   (o montador põe sozinho) e frase na legenda (a fila põe sozinha).
7. **Revogou, parou.** `revogar` apaga o avatar e a voz no HeyGen, cancela tudo que
   está na fila e lista o que já foi publicado para decidir a remoção pelo termo.

## Fluxo

### 1. Identificar candidatos (sem biometria)

Com a conta conectada (`conectar-instagram`), rode a triagem dos vídeos do perfil:

```bash
python .claude/skills/avatares/scripts/triagem_videos.py --cliente <handle>
```

Ela mede duração, fala e número de cortes de cada vídeo e monta folhas de contato —
**não** olha rostos. Leia as folhas com `Read`, descreva ao cliente quem aparece falando
para a câmera com frequência ("a pessoa de uniforme azul que apresenta os Reels de
dicas") e pergunte: quem é, qual o papel, e se o cliente quer convidar essa pessoa.
Hóspedes, clientes e crianças que aparecem nos vídeos **não** são candidatos.

### 2. Termo assinado → registro

O cliente envia o termo (modelo em `references/termo-consentimento.md`, revisado pelo
jurídico dele) e a pessoa assina. Com o arquivo assinado em mãos:

```bash
python .claude/skills/avatares/scripts/avatar.py registrar --cliente <h> --nome "Nome Completo" \
    --contato "email ou whatsapp" --papel "recepcionista" --termo termo-assinado.pdf \
    --assinado-em 2026-10-01 --validade 2027-09-30 --usos institucional,oferta,dicas \
    --voz sim --maior-de-idade [--proibido "concorrente X"] [--exige-aprovacao sim]
```

O registro reflete **exatamente** o termo — nunca mais amplo. Usos possíveis:
`institucional`, `oferta`, `dicas`, `bastidores`, `boas-vindas`, `evento`.

### 3. Gravação de treino

Qualidade máxima vem de gravação dedicada: 2 a 5 min, vertical, 4K, uma pessoa
olhando para a lente, fala limpa — `references/gravacao.md`. Vídeo do feed só serve
se atender aos mesmos critérios (a triagem aponta candidatos) e se o termo cobrir.

```bash
python .claude/skills/avatares/scripts/avatar.py criar --cliente <h> --pessoa <slug> \
    --video clientes/<h>/avatares/<slug>/gravacao/treino.mp4
```

### 4. Consentimento no HeyGen — pela própria pessoa

```bash
python .claude/skills/avatares/scripts/avatar.py consentimento --cliente <h> --pessoa <slug>
```

Imprime a mensagem com o link (24 h, uma gravação) para enviar **só à pessoa**. Depois:

```bash
python .claude/skills/avatares/scripts/avatar.py status --cliente <h>
```

Fica `ativo` quando o treino terminou **e** o HeyGen aceitou o consentimento.

### 5. Gerar a fala

Roteiro em `clientes/<h>/criativos/<id>/fala.txt`, na voz do brand kit, até ~90 s:

```bash
python .claude/skills/avatares/scripts/avatar.py gerar --cliente <h> --pessoa <slug> \
    --uso oferta --roteiro clientes/<h>/criativos/<id>/fala.txt --nome oferta-outubro --transparente
```

`--transparente` entrega WebM com canal alfa para compor no Reel; `--engine avatar_v`
(padrão) é o de maior fidelidade. Cada vídeo sai com um manifesto `.json` (pessoa, uso,
roteiro, termo) — sem ele, nenhum outro script aceita o vídeo como avatar.

Escreva o roteiro como a pessoa falaria no papel dela ("aqui na recepção a gente…"),
nunca como experiência que ela não viveu ("quando me hospedei…").

### 6. Compor, aprovar, publicar

- No `roteiro-video.json` da skill `criativos-video`, a cena `{"tipo": "avatar", "midia":
  "../../avatares/<slug>/videos/<arquivo>.webm", "fundo": "<foto do cliente>", "texto": "…",
  "enquadramento": "base"}` põe o avatar sobre a foto ou a cor da marca, com o título em
  caixa e o **selo de IA** fixo. A duração é a da fala.
- `fila.py criar` detecta o avatar sozinho e acrescenta o aviso de IA à legenda.
- Se o termo exige, `fila.py aprovar` pede `--pessoas "Nome Completo"`: mostre a prévia
  **à própria pessoa** e registre a aprovação dela, além da do cliente.
- `publicar.py` confere o consentimento de novo na hora de publicar.

### Revogar

```bash
python .claude/skills/avatares/scripts/avatar.py revogar --cliente <h> --pessoa <slug> --motivo "pedido em 30/09 por WhatsApp"
```

Pedido de revogação é atendido **no mesmo dia**, sem pedir justificativa.

## Rótulo de IA no Instagram

A Meta exige rotular conteúdo realista gerado por IA. O selo na tela e a frase na
legenda cumprem a transparência com o público; se a conta publicar pelo app, marque
também "Rótulo de IA" nas configurações avançadas do post.

## Custos e conta

HeyGen com plano de API (`HEYGEN_API_KEY` no `.env`, `references/heygen.md`). Digital
twin, voz clonada e minutos de vídeo são cobrados pelo HeyGen; confira no painel antes
de gerar em lote.
