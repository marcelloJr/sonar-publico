import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { BadgeGrau } from "@/components/badge-grau";
import { BotaoVoltar } from "@/components/botao-voltar";
import { api, ForaDoUniversoError } from "@/lib/api";
import { formataMoeda } from "@/lib/formato";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ codigo: string }>;
}): Promise<Metadata> {
  const { codigo } = await params;
  try {
    const { orgao } = await api.fornecedores(codigo);
    return { title: orgao };
  } catch {
    return { title: "Órgão" };
  }
}

export default async function OrgaoPagina({
  params,
}: {
  params: Promise<{ codigo: string }>;
}) {
  const { codigo } = await params;
  let dados;
  try {
    dados = await api.fornecedores(codigo);
  } catch (erro) {
    if (erro instanceof ForaDoUniversoError) notFound();
    throw erro;
  }
  const comAlerta = dados.fornecedores.filter((f) => f.grau !== null);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <BotaoVoltar />
        <h1 className="text-2xl font-bold">{dados.orgao}</h1>
        <p className="text-muted-foreground">
          {dados.fornecedores.length} fornecedores nos contratos carregados —{" "}
          {comAlerta.length} com sanção ou vínculo. Ordenados por grau de risco
          e valor.
        </p>
      </header>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fornecedor</TableHead>
              <TableHead>Situação</TableHead>
              <TableHead className="text-right">Contratos</TableHead>
              <TableHead className="text-right">Vigentes</TableHead>
              <TableHead className="text-right">Valor total</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {dados.fornecedores.map((f) => (
              <TableRow key={f.cnpj_basico}>
                <TableCell>
                  <Link
                    href={`/empresa/${f.cnpj_basico}`}
                    className="font-medium underline-offset-2 hover:underline"
                  >
                    {f.nome ?? `Empresa de raiz ${f.cnpj_basico}`}
                  </Link>
                </TableCell>
                <TableCell>
                  <BadgeGrau grau={f.grau} indicioSucessora={f.indicio_sucessora} />
                </TableCell>
                <TableCell className="text-right tabular-nums">{f.contratos}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {f.contratos_vigentes}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formataMoeda(f.valor_total)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {dados.fornecedores.length === 200 && (
        <p className="text-sm text-muted-foreground">
          Mostrando os 200 fornecedores de maior relevância. Lista completa na
          API aberta.
        </p>
      )}
    </div>
  );
}
