import type { Metadata } from "next";
import Link from "next/link";
import { protegido } from "@/lib/config";
import "./globals.css";

export const metadata: Metadata = {
  title: "Estúdio Social",
  description: "Conecte o Instagram dos clientes e veja o que funciona, com as métricas de dentro da conta.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="topo">
          <Link href="/" className="marca">Estúdio <span>Social</span></Link>
          <nav className="nav" aria-label="Principal">
            <Link href="/">Contas</Link>
            <Link href="/fila">Fila</Link>
            <Link href="/modo-dev">Modo dev</Link>
            <Link href="/demo">Demonstração</Link>
            {protegido() && <Link href="/sair" prefetch={false}>Sair</Link>}
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
