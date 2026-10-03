import { NextResponse, type NextRequest } from "next/server";
import { agendadorConfigurado, config } from "@/lib/config";
import { portadorValido } from "@/lib/chave";
import { rodarAgendador } from "@/lib/publicacao";

export const maxDuration = 60;

// Disparo do agendador. Chamado pelo GitHub Actions a cada 10 minutos e pelo cron
// diário da Vercel (o plano Hobby só permite um por dia), sempre com
// `Authorization: Bearer $CRON_SECRET`. Só publica item aprovado e com a trava intacta.
export async function GET(req: NextRequest) {
  if (!agendadorConfigurado()) return NextResponse.json({ erro: "armazenamento ou CRON_SECRET não configurados" }, { status: 503 });
  if (!portadorValido(req, config.cronSegredo)) return NextResponse.json({ erro: "não autorizado" }, { status: 401 });
  return NextResponse.json(await rodarAgendador(45_000));
}
