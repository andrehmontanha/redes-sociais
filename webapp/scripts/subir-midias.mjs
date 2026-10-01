#!/usr/bin/env node
// Sobe a mídia de um item da fila do estúdio para o Vercel Blob, pelo upload
// oficial do SDK: o webapp emite um token curto (/api/estudio/upload) e o arquivo
// vai direto para o Blob, em partes quando é vídeo. Chamado pelo enviar_webapp.py.
//
// Uso: ESTUDIO_API_CHAVE=... node subir-midias.mjs <url-do-webapp> <cliente> <item> <arquivo>...
// Saída (stdout): JSON [{ nome, url, pathname }] na mesma ordem dos arquivos.

import { readFile } from "node:fs/promises";
import { basename } from "node:path";
import { upload } from "@vercel/blob/client";

const [webapp, cliente, item, ...arquivos] = process.argv.slice(2);
const chave = process.env.ESTUDIO_API_CHAVE;
if (!webapp || !cliente || !item || !arquivos.length || !chave) {
  console.error("uso: ESTUDIO_API_CHAVE=... node subir-midias.mjs <url-do-webapp> <cliente> <item> <arquivo>...");
  process.exit(2);
}

const TIPOS = { ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".mp4": "video/mp4", ".mov": "video/quicktime" };
const saida = [];
try {
  for (const arquivo of arquivos) {
    const nome = basename(arquivo);
    const ext = nome.slice(nome.lastIndexOf(".")).toLowerCase();
    const dados = await readFile(arquivo);
    const blob = await upload(`fila/${cliente}/${item}/${nome}`, new Blob([dados], { type: TIPOS[ext] }), {
      access: "public",
      contentType: TIPOS[ext],
      handleUploadUrl: `${webapp.replace(/\/$/, "")}/api/estudio/upload`,
      headers: { authorization: `Bearer ${chave}` },
      multipart: dados.length > 8 * 1024 * 1024,
    });
    saida.push({ nome, url: blob.url, pathname: blob.pathname });
  }
} catch (e) {
  console.error(`erro: ${e?.message ?? e}`);
  process.exit(1);
}
process.stdout.write(JSON.stringify(saida));
