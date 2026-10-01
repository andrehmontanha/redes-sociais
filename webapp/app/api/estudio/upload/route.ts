import { handleUpload, type HandleUploadBody } from "@vercel/blob/client";
import { NextResponse, type NextRequest } from "next/server";
import { config, motorConfigurado } from "@/lib/config";
import { portadorValido } from "@/lib/chave";

// Token curto para o motor subir a mídia direto para o Vercel Blob (vídeo de Reel
// passa do limite de corpo de uma função). Só aceita JPEG/MP4/MOV dentro de
// `fila/<cliente>/`, com nome aleatório e sem sobrescrever nada que já esteja lá.
export async function POST(req: NextRequest) {
  if (!motorConfigurado()) return NextResponse.json({ erro: "armazenamento ou ESTUDIO_API_CHAVE não configurados" }, { status: 503 });
  if (!portadorValido(req, config.apiChave)) return NextResponse.json({ erro: "chave do estúdio inválida" }, { status: 401 });
  try {
    const resposta = await handleUpload({
      request: req,
      body: (await req.json()) as HandleUploadBody,
      token: config.blobToken,
      onBeforeGenerateToken: async (pathname) => {
        if (!/^fila\/[a-z0-9._]{1,30}\/[\w.-]{1,80}\/[\w.-]{1,80}\.(jpe?g|mp4|mov)$/i.test(pathname)) {
          throw new Error(`caminho não permitido: ${pathname}`);
        }
        return {
          allowedContentTypes: ["image/jpeg", "video/mp4", "video/quicktime"],
          maximumSizeInBytes: 300 * 1024 * 1024, // teto de Reel na Graph API
          addRandomSuffix: true,
          allowOverwrite: false,
          validUntil: Date.now() + 30 * 60_000,
        };
      },
    });
    return NextResponse.json(resposta);
  } catch (e) {
    return NextResponse.json({ erro: (e as Error).message }, { status: 400 });
  }
}
