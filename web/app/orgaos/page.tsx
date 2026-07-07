import type { Metadata } from "next";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { formataMoeda } from "@/lib/formato";

export const metadata: Metadata = { title: "Órgãos" };
export const dynamic = "force-dynamic";

export default async function Orgaos() {
  const { orgaos } = await api.orgaos();

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold">Órgãos contratantes</h1>
        <p className="max-w-3xl text-muted-foreground">
          Ordenados pelo valor de contratos com empresas que têm sanção vigente
          (&quot;sob alerta&quot;). Um contrato sob alerta não é
          necessariamente irregular — o alcance de cada sanção varia; veja a{" "}
          <Link href="/metodologia" className="underline">
            metodologia
          </Link>
          .
        </p>
      </header>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Órgão</TableHead>
              <TableHead className="text-right">Contratos</TableHead>
              <TableHead className="text-right">Valor total</TableHead>
              <TableHead className="text-right">Sob alerta</TableHead>
              <TableHead className="text-right">Valor sob alerta</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orgaos.map((o) => (
              <TableRow key={o.orgao_codigo}>
                <TableCell>
                  <Link
                    href={`/orgao/${o.orgao_codigo}`}
                    className="font-medium underline-offset-2 hover:underline"
                  >
                    {o.orgao}
                  </Link>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {o.contratos.toLocaleString("pt-BR")}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formataMoeda(o.valor_total)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {o.contratos_sob_alerta.toLocaleString("pt-BR")}
                </TableCell>
                <TableCell className="text-right font-medium tabular-nums">
                  {formataMoeda(o.valor_sob_alerta)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
