import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { AVISO_METODOLOGIA } from "@/lib/glossario";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Sonar Público",
    template: "%s · Sonar Público",
  },
  description:
    "Consulte sanções, contratos públicos e vínculos societários de qualquer " +
    "empresa que negocia com o governo. Dados oficiais, de graça, em linguagem simples.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="pt-BR"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <a
          href="#conteudo"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-foreground focus:px-4 focus:py-2 focus:text-background"
        >
          Pular para o conteúdo
        </a>
        <header className="border-b">
          <nav
            aria-label="Principal"
            className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4"
          >
            <Link href="/" className="text-lg font-bold tracking-tight">
              Sonar Público
            </Link>
            <div className="flex gap-4 text-sm">
              <Link href="/orgaos" className="hover:underline">
                Órgãos
              </Link>
              <Link href="/metodologia" className="hover:underline">
                Metodologia
              </Link>
              <a
                href="http://localhost:8000/docs"
                className="hover:underline"
                rel="external"
              >
                API aberta
              </a>
            </div>
          </nav>
        </header>
        <main id="conteudo" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
          {children}
        </main>
        <footer className="border-t">
          <div className="mx-auto max-w-5xl space-y-2 px-4 py-6 text-sm text-muted-foreground">
            <p>{AVISO_METODOLOGIA}</p>
            <p>
              Fontes: Portal da Transparência (CEIS, CNEP, CEPIM, Leniência,
              Contratos), PNCP e Receita Federal (CNPJ/QSA) — conjuntos
              catalogados no dados.gov.br. Projeto para o 2º Concurso de Reúso
              de Dados Abertos da CGU.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
