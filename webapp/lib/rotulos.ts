import type { Status, Tipo } from "./fila";

export const NOME_STATUS: Record<Status, string> = {
  aguardando_aprovacao: "aguardando aprovação",
  aprovado: "aprovado · agendado",
  publicando: "publicando",
  publicado: "publicado",
  rejeitado: "rejeitado",
  erro: "erro",
};

export const NOME_TIPO: Record<Tipo, string> = { feed: "post", carrossel: "carrossel", reel: "reel", story: "story" };

const formato = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "America/Sao_Paulo",
  weekday: "short",
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

/** Data no horário de Brasília, ex.: "sáb., 03/10, 12:00". */
export function quando(iso: string | null | undefined): string {
  return iso ? formato.format(new Date(iso)) : "assim que aprovado";
}
