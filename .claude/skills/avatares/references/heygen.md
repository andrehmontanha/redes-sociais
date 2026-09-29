# HeyGen — configuração

1. Conta HeyGen com **plano de API** (app.heygen.com/developers). OAuth/MCP servem para
   testes pequenos; produção usa chave de API.
2. Gere a chave em Settings → API e grave no `.env` (nunca no chat):

```bash
HEYGEN_API_KEY=...
```

3. Confira: `curl -s https://api.heygen.com/v3/users/me -H "x-api-key: $HEYGEN_API_KEY"`.

## Endpoints usados (API v3)

| Etapa | Chamada |
|---|---|
| criar digital twin | `POST /v3/avatars` `{type: "digital_twin", name, file: {type: "url", url}}` |
| treino | `GET /v3/avatars/looks/{look_id}` → `status` |
| consentimento | `POST /v3/avatars/{group_id}/consent` → `url` (24 h, uma gravação) |
| estado do consentimento | `GET /v3/avatars/{group_id}` → `consent_status` |
| gerar vídeo | `POST /v3/videos` `{type: "avatar", avatar_id, voice_id, script, resolution: "1080p", aspect_ratio: "9:16", engine: {type: "avatar_v"}, output_format: "webm"}` |
| acompanhar | `GET /v3/videos/{video_id}` → `status`, `video_url` |
| revogar | `DELETE /v3/avatars/{group_id}` (apaga todas as looks e a voz vinculada) |

Notas:
- `output_format: "webm"` já remove o fundo (canal alfa) e não aceita `background`.
  Exige avatar treinado com matting — o padrão nos avatares recentes.
- A voz é clonada da mesma gravação de treino (`default_voice_id`). Se o termo não
  autoriza voz clonada, use uma voz de catálogo com `--voice-id`.
- O upload de gravação ou vídeo de consentimento pré-gravado (nível 2) é só para
  contas Enterprise; o fluxo padrão é a pessoa gravar pelo link.
- O treino passa por moderação do HeyGen; `moderation_failed` não se contorna.

A rede do ambiente precisa liberar `api.heygen.com`, `*.heygen.ai` e `*.supabase.co`
(a gravação de treino sobe por URL assinada da hospedagem do estúdio).
