import { NextResponse, type NextRequest } from "next/server";
import { config, motorConfigurado } from "@/lib/config";
import { portadorValido } from "@/lib/chave";
import { agora, hashDaUrl, idDoItem, impressaoDoItem, midiaDe, validarEnvio, type Envio, type Item } from "@/lib/fila";
import { criarItem, lerItem, listarItens } from "@/lib/fila-servidor";

export const maxDuration = 60;

// Entrada do motor: o estúdio gera o criativo, sobe a mídia para o Blob e manda o
// item aqui. O webapp baixa cada arquivo, calcula a impressão digital ele mesmo e
// só então grava. Se o item já veio aprovado no estúdio, a aprovação só é aceita
// quando a impressão daqui bate byte a byte com a que foi aprovada lá.

function urlDoBlob(url: string) {
  try {
    const u = new URL(url);
    return u.protocol === "https:" && u.hostname.endsWith(".blob.vercel-storage.com");
  } catch {
    return false;
  }
}

export async function POST(req: NextRequest) {
  if (!motorConfigurado()) return NextResponse.json({ erro: "armazenamento ou ESTUDIO_API_CHAVE não configurados" }, { status: 503 });
  if (!portadorValido(req, config.apiChave)) return NextResponse.json({ erro: "chave do estúdio inválida" }, { status: 401 });

  const envio = (await req.json().catch(() => null)) as Envio | null;
  if (!envio) return NextResponse.json({ erro: "corpo JSON inválido" }, { status: 400 });
  const erros = validarEnvio(envio);
  const arquivos = [...(envio.midias ?? []), ...(envio.capa ? [envio.capa] : [])];
  for (const m of arquivos) {
    if (!urlDoBlob(m.url) || !new URL(m.url).pathname.slice(1).startsWith(`fila/${envio.cliente}/`)) {
      erros.push(`mídia fora do armazenamento do estúdio: ${m.url}`);
    }
  }
  if (erros.length) return NextResponse.json({ erro: "envio inválido", detalhes: erros }, { status: 422 });

  const id = idDoItem(envio.cliente, envio.nome);
  let hashes: string[];
  try {
    hashes = await Promise.all(arquivos.map((m) => hashDaUrl(m.url)));
  } catch (e) {
    return NextResponse.json({ erro: (e as Error).message }, { status: 422 });
  }
  const campos = {
    tipo: envio.tipo,
    legenda: envio.legenda,
    agendado_para: envio.agendado_para,
    thumb_offset_ms: envio.thumb_offset_ms,
    avatares: envio.avatares,
  };
  const digital = impressaoDoItem(hashes, campos);

  if (envio.aprovacao && envio.aprovacao.impressao !== digital) {
    return NextResponse.json(
      { erro: "a mídia ou a legenda que chegaram não são as que foram aprovadas no estúdio — nada foi gravado" },
      { status: 409 },
    );
  }

  const existente = await lerItem(id);
  if (existente) {
    const mesmo = existente.impressao === digital;
    return NextResponse.json(
      mesmo ? { id, status: existente.status, repetido: true } : { erro: `já existe um item ${id} com outro conteúdo — gere um item novo no estúdio` },
      { status: mesmo ? 200 : 409 },
    );
  }

  const quando = agora();
  const midias = envio.midias.map((m, k) => midiaDe(m, hashes[k]));
  const item: Item = {
    ...campos,
    id,
    cliente: envio.cliente,
    status: envio.aprovacao ? "aprovado" : "aguardando_aprovacao",
    criadoEm: quando,
    midias,
    capa: envio.capa ? midiaDe(envio.capa, hashes[hashes.length - 1]) : null,
    impressao: digital,
    aprovacao: envio.aprovacao
      ? {
          por: envio.aprovacao.por.trim(),
          em: envio.aprovacao.em,
          impressao: envio.aprovacao.impressao,
          origem: "estudio",
          mensagem: envio.aprovacao.mensagem ?? null,
        }
      : null,
    historico: [
      { em: quando, evento: "recebido do estúdio" },
      ...(envio.aprovacao
        ? [{ em: quando, evento: `aprovação de ${envio.aprovacao.por.trim()} (${envio.aprovacao.em}) conferida pela impressão digital` }]
        : []),
    ],
  };
  if (!(await criarItem(item))) return NextResponse.json({ erro: "item criado em paralelo — reenvie" }, { status: 409 });
  return NextResponse.json({ id, status: item.status, impressao: digital }, { status: 201 });
}

/** Resumo da fila para o motor (`enviar_webapp.py status`). */
export async function GET(req: NextRequest) {
  if (!motorConfigurado()) return NextResponse.json({ erro: "armazenamento ou ESTUDIO_API_CHAVE não configurados" }, { status: 503 });
  if (!portadorValido(req, config.apiChave)) return NextResponse.json({ erro: "chave do estúdio inválida" }, { status: 401 });
  const cliente = req.nextUrl.searchParams.get("cliente") ?? undefined;
  const itens = await listarItens({ cliente });
  return NextResponse.json(
    itens.map((i) => ({
      id: i.id,
      cliente: i.cliente,
      tipo: i.tipo,
      status: i.status,
      agendado_para: i.agendado_para,
      aprovado_por: i.aprovacao?.por ?? null,
      permalink: i.resultado?.permalink ?? null,
      erro: i.erro ?? null,
      rejeicao: i.rejeicao?.motivo ?? null,
    })),
  );
}
