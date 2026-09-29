# Estúdio Social

Um agente do Claude Code que cuida do Instagram de clientes de ponta a ponta:

0. **Conecta** a conta do cliente pelo login oficial do Instagram. O agente passa a ler posts, mídia original e métricas internas (alcance, salvamentos, compartilhamentos), dados que só o dono vê.
1. **Analisa** o perfil, os concorrentes, os anúncios e as tendências do nicho.
2. **Extrai a identidade visual**: paleta medida nas fotos do próprio perfil, tipografia, composição, tom de voz e ritmo de vídeo. Tudo isso vira um brand kit confirmado por vocês.
3. **Gera os criativos** com o material do cliente:
   - **imagens** (post, carrossel, story) renderizadas a partir de templates que seguem o brand kit;
   - **Reels** com motion graphics (HyperFrames), trilha e efeitos sonoros livres de direitos;
   - **avatares** de pessoas da marca (HeyGen, Avatar V), só com consentimento documentado, gravado pela própria pessoa, e revogável.
4. **Pede aprovação**: uma prévia no celular, e nada vai ao ar sem "aprovado" e o nome de quem aprovou.
5. **Publica** pela Instagram Graph API no horário planejado e **coleta as métricas** para a próxima rodada.

## Como usar

No Claude Code, dentro deste repositório:

> Use o estudio-social para cuidar do @nomedocliente: segmento hotelaria, vende serviços, objetivo venda direta, posta 3x por semana.

O agente conduz o ciclo e para em cada decisão que é de vocês:
- confirmar a identidade visual;
- confirmar a pauta;
- aprovar cada peça.

As skills também funcionam sozinhas, por exemplo "monta um carrossel sobre X para o @cliente" ou "sonoriza este Reel".

## Instalação

```bash
pip install -r requirements.txt
playwright install chromium        # ou aponte CHROMIUM_PATH para um Chrome/Chromium existente
# ffmpeg e Node.js 18+ precisam estar instalados no sistema
cp .env.example .env               # credenciais da Meta e da hospedagem
python tests/teste_ponta_a_ponta.py --com-video
```

Para conectar e publicar, é preciso uma configuração única: app na Meta com login do Instagram ([`conectar.md`](.claude/skills/conectar-instagram/references/conectar.md)) e bucket privado no Supabase ([`configuracao-meta.md`](.claude/skills/publicar-instagram/references/configuracao-meta.md)). Para avatares, uma chave de API do HeyGen ([`heygen.md`](.claude/skills/avatares/references/heygen.md)).

## Estrutura

```
.claude/
├── agents/
│   ├── estudio-social.md          orquestrador: análise → identidade → pauta → criação → aprovação → publicação
│   └── dossie-social.md           modo dossiê da análise (acervo completo)
├── skills/
│   ├── conectar-instagram/        OAuth, sincronização de posts, mídia e métricas internas
│   ├── analise-perfil-instagram/  diagnóstico, benchmark, tendências, teardown de vídeo
│   ├── identidade-visual/         brand kit medido + confirmado
│   ├── criativos-imagem/          templates HTML → JPEG 1080 px
│   ├── criativos-video/           roteiro de cenas → projeto HyperFrames → Reel
│   ├── efeitos-sonoros/           biblioteca de sons + catálogo de licenças + mixagem
│   ├── avatares/                  termo, treino, consentimento, geração e revogação de avatares
│   └── publicar-instagram/        fila, prévia, aprovação, Graph API, métricas
└── settings.json                  pede confirmação antes de aprovar/publicar; bloqueia leitura do .env
clientes/                          uma pasta por cliente (fora do git)
tests/teste_ponta_a_ponta.py       teste completo com cliente sintético
```

## Garantias embutidas

- **Aprovação por impressão digital.** A aprovação grava o hash da mídia, da legenda e do horário, e o publicador recusa qualquer item que tenha mudado depois do "ok".
- **Avatar com consentimento em duas camadas.** Só maiores de 18 anos, com termo assinado e registrado, mais o vídeo de consentimento gravado pela própria pessoa no HeyGen. Cada geração confere validade, uso autorizado e temas proibidos. Todo vídeo leva selo de IA na tela e na legenda. A revogação apaga o avatar e cancela a fila, e não há reconhecimento facial automático.
- **Só material do cliente.** Foto e vídeo de concorrente ou de tendência nunca entram num criativo; os scripts recusam.
- **Som com licença.** Nenhum som é usado sem licença registrada no catálogo. A biblioteca inicial é sintetizada por código (obra própria), e sons CC-BY geram crédito automático na legenda.
- **Especificação da API conferida antes de publicar.** São checados codec, fps, duração, áudio a -14 LUFS e limites de legenda.
- **Contraste e área segura verificados.** Texto que não cabe ou fica sob a interface do app é apontado antes da prévia.
