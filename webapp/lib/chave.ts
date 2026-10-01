import { iguais } from "./cripto";

// Autenticação das rotas de máquina (motor e agendador): `Authorization: Bearer <chave>`.
// Não usam a sessão de cookie da equipe — cada uma tem a sua chave, comparada em tempo constante.
export function portadorValido(req: Request, chave: string): boolean {
  const recebido = req.headers.get("authorization")?.replace(/^Bearer\s+/i, "") ?? "";
  return chave.length >= 16 && recebido.length > 0 && iguais(recebido, chave);
}
