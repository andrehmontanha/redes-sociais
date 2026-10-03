import { cookies } from "next/headers";
import { contaDoServidor, contasDoServidor, guardarContaNoServidor } from "./armazenamento";
import { armazenamento, config, protegido } from "./config";
import { abrir, selar } from "./cripto";

export const COOKIE_SESSAO = "estudio_sessao";
export const COOKIE_CONTAS = "estudio_contas";
export const COOKIE_STATE = "estudio_oauth_state";
const DOZE_HORAS = 12 * 60 * 60;

export type Conta = {
  id: string;
  usuario: string;
  tipo?: string;
  token: string;
  expira: string; // ISO
  origem: "oauth" | "dev";
  conectadoEm: string;
};

const baseCookie = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  path: "/",
};

export function sessaoValida(valor: string | undefined): boolean {
  if (!protegido()) return false;
  const s = abrir<{ exp: number }>(valor, config.segredo, "sessao");
  return !!s && s.exp > Date.now() / 1000;
}

export async function iniciarSessao() {
  const exp = Math.floor(Date.now() / 1000) + DOZE_HORAS;
  (await cookies()).set(COOKIE_SESSAO, selar({ exp }, config.segredo, "sessao"), { ...baseCookie, maxAge: DOZE_HORAS });
}

export async function encerrarSessao() {
  const c = await cookies();
  c.delete(COOKIE_SESSAO);
}

async function contasDoCookie(): Promise<Conta[]> {
  if (!protegido()) return [];
  const c = await cookies();
  return abrir<Conta[]>(c.get(COOKIE_CONTAS)?.value, config.segredo, "contas") ?? [];
}

/** Contas deste navegador somadas às do servidor (com armazenamento configurado,
 *  toda a equipe vê as mesmas contas e o agendador publica sem navegador aberto). */
export async function lerContas(): Promise<Conta[]> {
  const doCookie = await contasDoCookie();
  if (!armazenamento()) return doCookie;
  const doServidor = await contasDoServidor();
  const ids = new Set(doServidor.map((c) => c.id));
  return [...doServidor, ...doCookie.filter((c) => !ids.has(c.id))];
}

export async function salvarContas(contas: Conta[]) {
  const c = await cookies();
  // cookie tem teto de ~4 KB; cada conta ocupa ~450 bytes selada
  c.set(COOKIE_CONTAS, selar(contas.slice(-6), config.segredo, "contas"), {
    ...baseCookie,
    maxAge: 60 * 60 * 24 * 60,
  });
}

export async function guardarConta(nova: Conta) {
  const contas = (await contasDoCookie()).filter((c) => c.id !== nova.id);
  await salvarContas([...contas, nova]);
  if (armazenamento()) await guardarContaNoServidor(nova);
}

/** Tira a conta só do cookie deste navegador (a do servidor sai pelo `removerContaDoServidor`). */
export async function esquecerNoNavegador(usuario: string) {
  await salvarContas((await contasDoCookie()).filter((c) => c.usuario.toLowerCase() !== usuario.toLowerCase()));
}

export async function contaPorUsuario(usuario: string): Promise<Conta | undefined> {
  if (armazenamento()) {
    const doServidor = await contaDoServidor(usuario);
    if (doServidor) return doServidor;
  }
  return (await contasDoCookie()).find((c) => c.usuario.toLowerCase() === usuario.toLowerCase());
}

export const opcoesCookie = baseCookie;

/** Confere a sessão de novo dentro de uma ação de servidor (além do proxy). */
export async function exigirSessao() {
  if (!sessaoValida((await cookies()).get(COOKIE_SESSAO)?.value)) throw new Error("sessão expirada — entre de novo");
}
