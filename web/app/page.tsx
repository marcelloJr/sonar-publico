import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";
import { BarraBusca } from "@/components/barra-busca";
import { api } from "@/lib/api";
import { formataMoedaCompacta } from "@/lib/formato";

// números da home vêm da API a cada acesso (senão o build congela stats=null)
export const dynamic = "force-dynamic";

export default async function Home() {
  const stats = await api.estatisticas().catch(() => null);

  return (
    <div className="space-y-12">
      <section className="space-y-4 pt-8 text-center">
        <h1 className="text-4xl font-bold tracking-tight">
          Quem negocia com o governo?
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
          Busque uma empresa e veja sanções, contratos públicos e vínculos
          societários — dados oficiais, de graça, em linguagem simples.
        </p>
        <div className="flex justify-center">
          <BarraBusca tamanho="lg" />
        </div>
      </section>

      {stats && (
        <section aria-label="Números do radar" className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="pt-6">
              <CardTitle className="text-3xl tabular-nums">
                {formataMoedaCompacta(stats.valor_sob_alerta)}
              </CardTitle>
              <CardDescription className="mt-2">
                em contratos federais vigentes com empresas que têm sanção ativa
              </CardDescription>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <CardTitle className="text-3xl tabular-nums">
                {stats.sancionadas_com_contrato_vigente.toLocaleString("pt-BR")}
              </CardTitle>
              <CardDescription className="mt-2">
                empresas sancionadas mantêm contratos em vigência com o governo
                federal
              </CardDescription>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <CardTitle className="text-3xl tabular-nums">
                {stats.empresas_grau1.toLocaleString("pt-BR")}
              </CardTitle>
              <CardDescription className="mt-2">
                empresas compartilham sócios com sancionadas — incluindo{" "}
                {stats.candidatas_sucessora.toLocaleString("pt-BR")} possíveis
                sucessoras
              </CardDescription>
            </CardContent>
          </Card>
        </section>
      )}
    </div>
  );
}
