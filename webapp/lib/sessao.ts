import { cookies } from "next/headers";
import { config, protegido } from "./config";
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

export async function lerContas(): Promise<Conta[]> {
  if (!protegido()) return [];
  const c = await cookies();
  return abrir<Conta[]>(c.get(COOKIE_CONTAS)?.value, config.segredo, "contas") ?? [];
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
  const contas = (await lerContas()).filter((c) => c.id !== nova.id);
  await salvarContas([...contas, nova]);
}

export async function contaPorUsuario(usuario: string): Promise<Conta | undefined> {
  return (await lerContas()).find((c) => c.usuario.toLowerCase() === usuario.toLowerCase());
}

export const opcoesCookie = baseCookie;
