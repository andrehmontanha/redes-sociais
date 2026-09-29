# Estúdio Social — contexto para o Claude

Estúdio de social media para clientes no Instagram: analisa o perfil, extrai a
identidade visual, gera criativos de imagem e vídeo na identidade do cliente, leva
à aprovação humana e publica pela Graph API.

Ponto de entrada: o agente **`estudio-social`** (`.claude/agents/estudio-social.md`),
que conduz o ciclo e chama as skills na ordem.

| Skill | Papel |
|---|---|
| `conectar-instagram` | OAuth da conta do cliente; sincroniza posts, mídia original e métricas internas |
| `analise-perfil-instagram` | diagnóstico, benchmark, tendências, teardown, captura do material do cliente |
| `identidade-visual` | brand kit medido + observado + confirmado (`clientes/<h>/brand-kit.json`) |
| `criativos-imagem` | post, carrossel e story em JPEG a partir de templates HTML + brand kit |
| `criativos-video` | Reels com HyperFrames (motion) a partir de roteiro de cenas |
| `efeitos-sonoros` | biblioteca de SFX/trilhas livres de direitos, catálogo com licença, mixagem −14 LUFS |
| `avatares` | avatares HeyGen de pessoas do perfil, com termo + consentimento gravado, aviso de IA e revogação |
| `publicar-instagram` | fila, prévia, aprovação com trava por hash, publicação e métricas pela Graph API |

O agente `dossie-social` é o modo dossiê da análise (acervo completo).
As skills `hyperframes*` vêm do plugin HyperFrames da conta, não deste repositório.

## Regras do repositório

- **Aprovação humana antes de publicar, sem exceção.** Nunca rode `fila.py aprovar`
  sem mensagem explícita do usuário aprovando aquele item, com nome. Nunca edite
  `post.json` à mão para mudar status ou aprovação.
- **Criativo só com material do cliente.** Os scripts recusam mídia fora de
  `clientes/<handle>/` ou em pastas de referência de terceiros; não contorne
  (nem copiando o arquivo para dentro da pasta do cliente).
- **Avatar só de maior de 18 anos com consentimento ativo** (termo registrado + consentimento
  gravado pela própria pessoa no HeyGen). Nunca rode reconhecimento/agrupamento facial nos
  vídeos do cliente; nunca edite `registro.json` à mão; revogação se atende no mesmo dia.
- **Token do Instagram só pelo `conectar.py`** — nunca peça senha nem token no chat; o único dado
  que transita é a URL de retorno com o código de uso único, que o `trocar` consome.
- **Som só da biblioteca**, com licença no catálogo (`catalogo.py validar`).
- **Credenciais só no `.env`** (ignorado pelo git) ou nas variáveis do ambiente.
- `clientes/` fica fora do git — nunca force a adição de mídia ou dado de cliente.

## Comandos

```bash
pip install -r requirements.txt            # numpy, pillow, playwright, requests (+ ffmpeg e Node 18+ no sistema)
python tests/teste_ponta_a_ponta.py        # teste completo com cliente sintético, sem publicar nada
python tests/teste_ponta_a_ponta.py --com-video   # + Reel com HyperFrames
python .claude/skills/efeitos-sonoros/scripts/gerar_biblioteca.py   # regenera a biblioteca base de sons
```

Rode o teste de ponta a ponta depois de mexer em qualquer script ou template.

## Webapp (`webapp/`, Next.js 16 → Vercel)

Painel para conectar o Instagram (login oficial ou token de teste do modo dev) e ler
métricas internas. Tokens ficam criptografados em cookie httpOnly; tudo exige
`ESTUDIO_SENHA`, menos `/entrar` e a demonstração. Nunca implemente login por
usuário e senha do Instagram. Next 16: `proxy.ts` (não `middleware.ts`), `params`
e `cookies()` assíncronos.

```bash
cd webapp && npm install && npm test && npm run build
```

## Convenções

- Scripts em Python 3.11, nomes e mensagens em português, `argparse` com a docstring
  como ajuda, saída 1 quando a trava bloqueia. Cada script é executável sozinho.
- Templates de imagem (`criativos-imagem/templates/`) não definem cor nem fonte:
  só variáveis CSS do brand kit.
- Renders não dependem de rede: fontes e GSAP são baixados uma vez para
  `~/.cache/estudio-social/` e embutidos localmente. Se o Chromium do Playwright não
  bater com a versão instalada, `renderizar_criativo.py` procura outro ou usa `CHROMIUM_PATH`.
- HyperFrames fixado em `0.8.90` (`montar_reel.py`); ao atualizar, rode o teste com `--com-video`.
