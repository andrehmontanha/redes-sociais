---
name: conectar-instagram
description: Conecta a conta do Instagram do cliente pelo login oficial da Meta (OAuth) e sincroniza o que só o dono vê — posts, legendas, mídia original em alta resolução e métricas internas (alcance, salvamentos, compartilhamentos, visualizações) — gerando o resumo do que funciona no perfil, os melhores horários e os dados no formato da análise. Use quando pedirem para conectar, integrar ou autorizar o Instagram de um cliente, ler os posts/insights da conta, puxar as métricas reais, baixar o material original do perfil, ou quando a análise/criação precisar de dados de dentro em vez de estimativas de fora.
---

# Conectar o Instagram do cliente

Com a conta conectada, o estúdio deixa de estimar de fora e passa a ler de dentro:

| Sem conexão (análise pelo navegador) | Com conexão (esta skill) |
|---|---|
| curtidas visíveis, às vezes ocultas | alcance, salvamentos, compartilhamentos, views por post |
| imagens capturadas da página | mídia original (1080 px, vídeos em MP4) |
| engajamento sobre seguidores | salvamento e compartilhamento **sobre alcance** |
| horário "típico do nicho" | horário em que **este** perfil alcança mais |

O mesmo token serve para publicar (`publicar-instagram`) — uma autorização, as duas coisas.

## Quem autoriza

**O dono da conta**, no navegador dele. Você gera o link; ele faz login e aceita.
Você nunca pede senha, nunca pede o token, nunca pede que ele cole credencial no chat
— o que volta é só a URL de redirecionamento, que contém um código de uso único.

## Fluxo

Pré-requisito (uma vez por estúdio): app da Meta com Login do Instagram e
`IG_APP_ID`, `IG_APP_SECRET`, `IG_REDIRECT_URI` no `.env` — `references/conectar.md`.

### 1. Link de autorização

```bash
python .claude/skills/conectar-instagram/scripts/conectar.py url --cliente <handle>
```

Mande o link ao dono da conta (vale 15 minutos) com uma frase sobre o que ele autoriza:
ler perfil, posts e métricas, e publicar o que ele aprovar.

### 2. Trocar pelo token

Ele devolve a URL da barra de endereço depois de autorizar:

```bash
python .claude/skills/conectar-instagram/scripts/conectar.py trocar --cliente <handle> --retorno "<URL>"
```

O script confere o `state` (o link foi gerado aqui, para este cliente), troca o código
por token de 60 dias, **recusa se a conta autorizada não for o @ do cliente**, e grava
no `.env` sem imprimir o token.

### 3. Sincronizar

```bash
python .claude/skills/conectar-instagram/scripts/sincronizar.py --cliente <handle> --nicho <nicho>
```

Baixa os 60 posts mais recentes (`--limite`), com mídia original para
`referencias/cliente/` e métricas para `instagram/AAAA-MM-DD/`. Leia o `resumo.md`
gerado — é o ponto de partida da análise e da pauta:

- **maior alcance**, **mais salvos por alcance** e **mais compartilhados por alcance** —
  três rankings, porque respondem a perguntas diferentes (quem viu, quem quis guardar,
  quem levou adiante);
- mediana por formato; janelas de dia × horário com alcance mediano (só janelas com ≥ 3 posts);
- legenda curta × longa; hashtags recorrentes; cadência real.

Depois, as outras skills usam o material:

- `analise-perfil-instagram`: `calcular_metricas.py instagram/AAAA-MM-DD/dados_<handle>.json`
  — mesmo formato da coleta pelo navegador, agora com métricas internas. Os passos de
  coleta do perfil (2 a 4) e o download do material do cliente (7) já estão feitos;
  concorrentes, anúncios e tendências continuam pelo navegador.
- `identidade-visual`: mede a paleta nas imagens originais `ig-*.jpg`.
- `criativos-*`: fotos e vídeos originais, sem perda de resolução.

Sincronize de novo a cada análise; as pastas datadas formam a série histórica.

### 4. Manter

```bash
python .claude/skills/conectar-instagram/scripts/conectar.py status          # vence em quantos dias
python .claude/skills/conectar-instagram/scripts/conectar.py renovar --cliente <handle>
```

O token vale 60 dias e pode ser renovado enquanto válido. Uma rotina semanal de
`status` + `renovar` para quem vence em menos de 10 dias evita reconexão.
Encerrou o contrato: `desconectar` e oriente o cliente a remover o app em
Instagram → Configurações → Apps e sites.

## Limites

- Conta **profissional** (Empresa ou Criador). Conta pessoal não tem API.
- Posts anteriores à conversão para conta profissional não têm insights — o resumo avisa quantos.
- Stories só aparecem por 24 h na API; sincronize no dia se quiser guardá-los.
- Alcance é estimado pela Meta e views é métrica "em desenvolvimento" — o resumo diz isso.
- O ambiente de nuvem precisa liberar `graph.instagram.com`, `api.instagram.com` e os
  CDNs de mídia (`*.cdninstagram.com`, `*.fbcdn.net`).
