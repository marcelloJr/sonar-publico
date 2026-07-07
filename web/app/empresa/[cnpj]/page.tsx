import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BadgeGrau } from "@/components/badge-grau";
import { BotaoCopiar } from "@/components/botao-copiar";
import { BotaoVoltar } from "@/components/botao-voltar";
import { GrafoVinculos } from "@/components/grafo-vinculos";
import { api, ForaDoUniversoError, type Ficha } from "@/lib/api";
import { explicaSancao } from "@/lib/glossario";
import {
  formataCnpj,
  formataData,
  formataMoeda,
  formataSituacao,
  limpaObjeto,
} from "@/lib/formato";

async function buscaFicha(cnpj: string): Promise<Ficha> {
  try {
    return await api.ficha(cnpj);
  } catch (erro) {
    if (erro instanceof ForaDoUniversoError) notFound();
    throw erro;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ cnpj: string }>;
}): Promise<Metadata> {
  const { cnpj } = await params;
  try {
    const ficha = await api.ficha(cnpj);
    return { title: ficha.cadastro.razao_social ?? cnpj };
  } catch {
    return { title: "Empresa" };
  }
}

export default async function Empresa({
  params,
}: {
  params: Promise<{ cnpj: string }>;
}) {
  const { cnpj } = await params;
  const ficha = await buscaFicha(cnpj);
  const { cadastro, risco, sancoes, contratos, socios } = ficha;
  const grau = risco.length ? Math.min(...risco.map((r) => r.grau)) : null;
  const sucessora = risco.some((r) => r.indicio_sucessora);
  const vinculos = risco.filter((r) => r.grau === 1);

  return (
    <article className="space-y-8">
      <header className="space-y-3">
        <BotaoVoltar />
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold">
            {cadastro.razao_social ?? `Empresa de raiz ${cadastro.cnpj_basico}`}
          </h1>
          {cadastro.razao_social && (
            <BotaoCopiar texto={cadastro.razao_social} rotulo="nome da empresa" />
          )}
          <BadgeGrau grau={grau} indicioSucessora={sucessora} />
        </div>
        <dl className="grid gap-x-8 gap-y-1 text-sm text-muted-foreground sm:grid-cols-2">
          <div className="flex items-center gap-2">
            <dt className="font-medium">CNPJ:</dt>
            <dd className="flex items-center gap-2">
              {cadastro.cnpj ? formataCnpj(cadastro.cnpj) : `raiz ${cadastro.cnpj_basico}`}
              <BotaoCopiar
                texto={cadastro.cnpj ? formataCnpj(cadastro.cnpj) : cadastro.cnpj_basico}
                rotulo="CNPJ"
              />
            </dd>
          </div>
          {cadastro.situacao_cadastral && (
            <div className="flex gap-2">
              <dt className="font-medium">Situação na Receita:</dt>
              <dd>{formataSituacao(cadastro.situacao_cadastral)}</dd>
            </div>
          )}
          {cadastro.data_inicio_atividade && (
            <div className="flex gap-2">
              <dt className="font-medium">Em atividade desde:</dt>
              <dd>{formataData(cadastro.data_inicio_atividade)}</dd>
            </div>
          )}
          {cadastro.uf && (
            <div className="flex gap-2">
              <dt className="font-medium">UF:</dt>
              <dd>{cadastro.uf}</dd>
            </div>
          )}
        </dl>
        {!cadastro.cadastro_receita_disponivel && (
          <p className="text-sm text-muted-foreground">
            Dados cadastrais completos da Receita indisponíveis para esta
            empresa nesta atualização — exibindo o nome registrado nas bases de
            sanções/contratos.
          </p>
        )}
      </header>

      {vinculos.length > 0 && (
        <Alert>
          <AlertTitle>
            {sucessora
              ? "Possível empresa sucessora"
              : "Vínculo societário com empresa sancionada"}
          </AlertTitle>
          <AlertDescription className="space-y-2">
            {vinculos.slice(0, 5).map((v, i) => (
              <p key={i}>
                Compartilha o sócio <strong>{v.socio_comum}</strong> com a
                empresa de raiz{" "}
                <Link className="underline" href={`/empresa/${v.relacionada}`}>
                  {v.relacionada}
                </Link>{" "}
                (confiança {v.confianca}
                {v.indicio_sucessora
                  ? "; aberta após a sanção, no mesmo ramo e município"
                  : ""}
                ).
              </p>
            ))}
            <p className="text-muted-foreground">
              Vínculo societário é indício para verificação — não é prova de
              irregularidade.
            </p>
          </AlertDescription>
        </Alert>
      )}

      <section aria-labelledby="grafo">
        <h2 id="grafo" className="mb-3 text-xl font-semibold">
          Rede de vínculos societários
        </h2>
        <GrafoVinculos cnpj={cadastro.cnpj_basico} />
      </section>

      <section aria-labelledby="sancoes">
        <h2 id="sancoes" className="mb-3 text-xl font-semibold">
          Sanções ({sancoes.length})
        </h2>
        {sancoes.length === 0 ? (
          <p className="text-muted-foreground">
            Nenhuma sanção registrada para esta empresa nos cadastros federais.
          </p>
        ) : (
          <Accordion type="multiple" className="w-full">
            {sancoes.map((s, i) => (
              <AccordionItem key={i} value={`s-${i}`}>
                <AccordionTrigger className="text-left">
                  <span className="flex flex-wrap items-center gap-2">
                    {s.vigente && (
                      <span className="rounded bg-red-700 px-1.5 py-0.5 text-xs font-medium text-white">
                        vigente
                      </span>
                    )}
                    {s.categoria} — {s.orgao ?? s.fonte}
                  </span>
                </AccordionTrigger>
                <AccordionContent className="space-y-2">
                  <p className="rounded bg-muted p-3">
                    <strong>O que isso significa?</strong>{" "}
                    {explicaSancao(s.categoria)}
                  </p>
                  <dl className="grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">
                    <div className="flex gap-2">
                      <dt className="font-medium">Cadastro:</dt>
                      <dd>{s.fonte}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium">Esfera do órgão:</dt>
                      <dd>{s.esfera_orgao ?? "—"}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium">Início:</dt>
                      <dd>{formataData(s.data_inicio)}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium">Fim:</dt>
                      <dd>{s.data_fim ? formataData(s.data_fim) : "sem prazo definido"}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium">CNPJ sancionado:</dt>
                      <dd>{formataCnpj(s.cnpj_cpf)}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium">Processo:</dt>
                      <dd>{s.processo ?? "—"}</dd>
                    </div>
                  </dl>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}
      </section>

      <section aria-labelledby="contratos">
        <h2 id="contratos" className="mb-3 text-xl font-semibold">
          Contratos públicos ({contratos.length}
          {contratos.length === 100 ? "+" : ""})
        </h2>
        {contratos.length === 0 ? (
          <p className="text-muted-foreground">
            Nenhum contrato federal recente encontrado (cobertura: Poder
            Executivo Federal desde 2024).
          </p>
        ) : (
          <Accordion type="multiple" className="w-full">
            {contratos.slice(0, 25).map((c, i) => (
              <AccordionItem key={i} value={`c-${i}`}>
                <AccordionTrigger className="text-left">
                  <span className="flex w-full flex-wrap items-center justify-between gap-x-4 gap-y-1 pr-2">
                    <span className="min-w-0 flex-1 truncate">{c.orgao ?? "—"}</span>
                    <span className="whitespace-nowrap font-semibold tabular-nums">
                      {formataMoeda(c.valor_final)}
                    </span>
                  </span>
                </AccordionTrigger>
                <AccordionContent className="space-y-3">
                  <p>{limpaObjeto(c.objeto)}</p>
                  <dl className="grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">
                    <div className="flex gap-2">
                      <dt className="font-medium">Contrato nº:</dt>
                      <dd>{c.numero_contrato ?? "—"}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium">Situação:</dt>
                      <dd>{c.situacao ?? "—"}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium">Modalidade:</dt>
                      <dd>{c.modalidade ?? "—"}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium">Vigência:</dt>
                      <dd>
                        {formataData(c.data_inicio_vigencia)} até{" "}
                        {formataData(c.data_fim_vigencia)}
                      </dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium">Fonte:</dt>
                      <dd>
                        {c.origem === "PORTAL"
                          ? "Portal da Transparência (federal)"
                          : `PNCP (esfera ${c.esfera})`}
                      </dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium">CNPJ contratado:</dt>
                      <dd>{formataCnpj(c.cnpj_contratado)}</dd>
                    </div>
                  </dl>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}
        {contratos.length > 25 && (
          <p className="mt-2 text-sm text-muted-foreground">
            Mostrando os 25 contratos de maior valor. A lista completa está
            disponível na API aberta.
          </p>
        )}
      </section>

      <section aria-labelledby="socios">
        <h2 id="socios" className="mb-3 text-xl font-semibold">
          Quadro societário ({socios.length})
        </h2>
        {socios.length === 0 ? (
          <p className="text-muted-foreground">
            Quadro societário indisponível nesta atualização.
          </p>
        ) : (
          <Card>
            <CardContent className="pt-6">
              <ul className="grid gap-2 sm:grid-cols-2">
                {socios.map((s, i) => (
                  <li key={i} className="text-sm">
                    <span className="font-medium">{s.nome_socio}</span>
                    <span className="text-muted-foreground">
                      {" "}
                      · CPF {s.cpf_mascarado ?? "—"} · desde{" "}
                      {formataData(s.data_entrada)}
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sobre estes dados</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Sanções: CEIS, CNEP, CEPIM e Acordos de Leniência (Portal da
          Transparência, atualização diária). Contratos: Poder Executivo
          Federal desde 2024. Quadro societário: dados abertos do CNPJ (Receita
          Federal, mensal, CPF parcialmente mascarado na origem). Defasagem de
          até 1 mês é esperada.
        </CardContent>
      </Card>
    </article>
  );
}
