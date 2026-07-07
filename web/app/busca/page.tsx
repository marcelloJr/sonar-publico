import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { BadgeGrau } from "@/components/badge-grau";
import { BarraBusca } from "@/components/barra-busca";
import { api } from "@/lib/api";
import { formataSituacao } from "@/lib/formato";

export const metadata: Metadata = { title: "Busca" };

export default async function Busca({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const consulta = q?.trim() ?? "";
  const resultados =
    consulta.length >= 3 ? (await api.buscar(consulta)).resultados : [];

  return (
    <div className="space-y-6">
      <BarraBusca defaultValue={consulta} />

      {consulta.length < 3 ? (
        <p role="alert">
          Digite pelo menos 3 caracteres para buscar por nome ou CNPJ.
        </p>
      ) : (
        <>
          <h1 className="text-2xl font-bold">
            Resultados para “{consulta}”{" "}
            <span className="font-normal text-muted-foreground">
              ({resultados.length}
              {resultados.length === 20 ? "+" : ""})
            </span>
          </h1>

          {resultados.length === 0 && (
            <div className="space-y-4 rounded-lg border bg-muted/30 p-6">
              <p className="font-medium">Nenhuma empresa encontrada.</p>
              <p className="text-sm text-muted-foreground">
                O Sonar cobre empresas com sanção registrada, contrato público
                federal recente ou vínculo societário com sancionadas — uma
                empresa fora dessas condições não aparece aqui. Confira a
                grafia ou tente outro termo acima.
              </p>
              <Button asChild variant="outline">
                <Link href="/">Voltar para a página inicial</Link>
              </Button>
            </div>
          )}

          <ul className="space-y-3">
            {resultados.map((r) => (
              <li key={r.cnpj_basico}>
                <Link
                  href={`/empresa/${r.cnpj_basico}`}
                  className="block rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2"
                >
                  <Card className="transition-colors hover:border-foreground/30 hover:bg-muted/50">
                    <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
                      <div className="min-w-0">
                        <p className="font-medium">{r.razao_social}</p>
                        <p className="text-sm text-muted-foreground">
                          CNPJ raiz {r.cnpj_basico}
                          {r.uf ? ` · ${r.uf}` : ""}
                          {r.situacao_cadastral
                            ? ` · ${formataSituacao(r.situacao_cadastral)}`
                            : ""}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <BadgeGrau
                          grau={r.grau}
                          indicioSucessora={r.indicio_sucessora}
                        />
                        <span aria-hidden className="text-muted-foreground">
                          →
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
