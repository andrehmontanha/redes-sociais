import { redis } from "./armazenamento";
import type { Item } from "./fila";

// Persistência da fila no Redis: um JSON por item e um índice ordenado pelo
// horário de publicação (ou de criação, para o que não tem horário).

const INDICE = "fila:itens";
const chave = (id: string) => `fila:item:${id}`;

const pontuacao = (i: Item) => Date.parse(i.agendado_para ?? i.criadoEm);

export async function lerItem(id: string): Promise<Item | null> {
  const v = await redis().get<string>(chave(id));
  return v ? (JSON.parse(v) as Item) : null;
}

export async function gravarItem(item: Item) {
  await redis().set(chave(item.id), JSON.stringify(item));
  await redis().zadd(INDICE, { score: pontuacao(item), member: item.id });
}

/** Grava só se o id ainda não existe — o motor pode reenviar sem duplicar. */
export async function criarItem(item: Item): Promise<boolean> {
  const ok = (await redis().set(chave(item.id), JSON.stringify(item), { nx: true })) === "OK";
  if (ok) await redis().zadd(INDICE, { score: pontuacao(item), member: item.id });
  return ok;
}

export async function listarItens(filtro?: { cliente?: string; status?: string[] }): Promise<Item[]> {
  const ids = await redis().zrange<string[]>(INDICE, 0, -1);
  if (!ids.length) return [];
  const valores = await redis().mget<(string | null)[]>(...ids.map(chave));
  return valores
    .filter((v): v is string => !!v)
    .map((v) => JSON.parse(v) as Item)
    .filter((i) => !filtro?.cliente || i.cliente === filtro.cliente)
    .filter((i) => !filtro?.status || filtro.status.includes(i.status));
}
