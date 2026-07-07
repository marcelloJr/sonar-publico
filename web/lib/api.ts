// Cliente da API do Sonar Público (FastAPI — ver /api no monorepo).
// Server Components fazem fetch direto; a URL vem do ambiente.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type NoGrafo = {
  id: string;
  nome: string | null;
  grau: number | null;
};

export type ArestaGrafo = {
  cnpj_a: string;
  cnpj_b: string;
  socio_comum: string;
  confianca: string;
};

export type Grafo = {
  centro: string;
  nos: NoGrafo[];
  arestas: ArestaGrafo[];
};

export type ResultadoBusca = {
  cnpj_basico: string;
  razao_social: string;
  uf: string | null;
  situacao_cadastral: string | null;
  grau: number | null;
  indicio_sucessora: boolean;
};

export type Sancao = {
  fonte: string;
  categoria: string;
  orgao: string | null;
  uf_orgao: string | null;
  esfera_orgao: string | null;
  data_inicio: string | null;
  data_fim: string | null;
  vigente: boolean;
  processo: string | null;
  cnpj_cpf: string;
};

export type Contrato = {
  origem: string;
  esfera: string;
  numero_contrato: string | null;
  orgao: string | null;
  objeto: string | null;
  situacao: string | null;
  modalidade: string | null;
  valor_final: number | string | null;
  data_inicio_vigencia: string | null;
  data_fim_vigencia: string | null;
  cnpj_contratado: string;
};

export type Socio = {
  nome_socio: string;
  cpf_mascarado: string | null;
  qualificacao: string | null;
  data_entrada: string | null;
};

export type Risco = {
  grau: number;
  relacionada: string | null;
  socio_comum: string | null;
  confianca: string | null;
  indicio_sucessora: boolean;
};

export type Ficha = {
  cadastro: {
    cnpj_basico: string;
    razao_social: string | null;
    cadastro_receita_disponivel: boolean;
    cnpj?: string | null;
    nome_fantasia?: string | null;
    situacao_cadastral?: string | null;
    data_inicio_atividade?: string | null;
    cnae_principal?: string | null;
    uf?: string | null;
    natureza_juridica?: string | null;
    capital_social?: number | null;
    porte?: string | null;
  };
  risco: Risco[];
  sancoes: Sancao[];
  contratos: Contrato[];
  socios: Socio[];
};

export type Estatisticas = {
  sancionadas_vigentes: number;
  empresas_grau1: number;
  candidatas_sucessora: number;
  sancionadas_com_contrato_vigente: number;
  contratos_vigentes_sob_alerta: number;
  valor_sob_alerta: number;
};

async function busca<T>(caminho: string): Promise<T> {
  // Next 16: fetch em Server Component não é cacheado por padrão — certo para
  // nós (a API local responde em ms e os dados mudam 1x/dia via pipeline).
  const resposta = await fetch(`${API_URL}${caminho}`);
  if (!resposta.ok) {
    if (resposta.status === 404) throw new ForaDoUniversoError();
    throw new Error(`API ${resposta.status} em ${caminho}`);
  }
  return resposta.json();
}

export class ForaDoUniversoError extends Error {}

export const api = {
  estatisticas: () => busca<Estatisticas>("/estatisticas"),
  buscar: (q: string) =>
    busca<{ resultados: ResultadoBusca[] }>(`/busca?q=${encodeURIComponent(q)}`),
  ficha: (cnpj: string) => busca<Ficha>(`/empresas/${cnpj}`),
};
