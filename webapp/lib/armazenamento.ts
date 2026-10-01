import { Redis } from "@upstash/redis";
import { config } from "./config";
import { abrir, selar } from "./cripto";
import type { Conta } from "./sessao";

// Dados no servidor: Redis guarda a fila e as contas conectadas; a mídia fica no
// Vercel Blob. Tokens do Instagram nunca ficam em claro: são selados com
// AES-256-GCM (SESSAO_SEGREDO) antes de ir para o Redis.

let cliente: Redis | null = null;

export function redis(): Redis {
  if (!config.redisUrl || !config.redisToken) {
    throw new Error("Redis não configurado: crie um banco Upstash Redis em Storage no painel da Vercel");
  }
  cliente ??= new Redis({ url: config.redisUrl, token: config.redisToken, automaticDeserialization: false });
  return cliente;
}

const CHAVE_CONTAS = "contas";
const chaveConta = (usuario: string) => usuario.toLowerCase();

export async function contasDoServidor(): Promise<Conta[]> {
  const todas = (await redis().hgetall<Record<string, string>>(CHAVE_CONTAS)) ?? {};
  return Object.values(todas)
    .map((v) => abrir<Conta>(v, config.segredo, "conta-servidor"))
    .filter((c): c is Conta => !!c);
}

export async function contaDoServidor(usuario: string): Promise<Conta | undefined> {
  const v = await redis().hget<string>(CHAVE_CONTAS, chaveConta(usuario));
  return abrir<Conta>(v ?? undefined, config.segredo, "conta-servidor") ?? undefined;
}

export async function guardarContaNoServidor(conta: Conta) {
  await redis().hset(CHAVE_CONTAS, { [chaveConta(conta.usuario)]: selar(conta, config.segredo, "conta-servidor") });
}

export async function removerContaDoServidor(usuario: string) {
  await redis().hdel(CHAVE_CONTAS, chaveConta(usuario));
}

/** Trava curta para dois disparos do agendador não mexerem no mesmo item. */
export async function travar(chave: string, segundos: number): Promise<boolean> {
  return (await redis().set(`trava:${chave}`, "1", { nx: true, ex: segundos })) === "OK";
}

export async function destravar(chave: string) {
  await redis().del(`trava:${chave}`);
}
