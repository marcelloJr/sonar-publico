export function formataCnpj(cnpj: string): string {
  const d = cnpj.replace(/\D/g, "");
  if (d.length !== 14) return cnpj;
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}

export function formataMoeda(valor: number | string | null): string {
  if (valor == null) return "—";
  // a API pode serializar DECIMAL como string — normaliza antes de formatar
  const n = typeof valor === "string" ? Number(valor) : valor;
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

export function limpaObjeto(objeto: string | null): string {
  if (!objeto) return "—";
  // a origem às vezes traz o rótulo embutido ("Objeto: ...") e lixo de
  // encoding no início ("??????Execução...")
  return objeto.replace(/^objeto:\s*/i, "").replace(/^\?+\s*/, "").trim() || "—";
}

export function formataMoedaCompacta(valor: number): string {
  if (valor >= 1e9) return `R$ ${(valor / 1e9).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} bi`;
  if (valor >= 1e6) return `R$ ${(valor / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
  return formataMoeda(valor);
}

export function formataData(iso: string | null): string {
  if (!iso) return "—";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

const SITUACAO_CADASTRAL: Record<string, string> = {
  "01": "Nula",
  "02": "Ativa",
  "03": "Suspensa",
  "04": "Inapta",
  "08": "Baixada",
};

export function formataSituacao(codigo: string | null | undefined): string {
  if (!codigo) return "—";
  return SITUACAO_CADASTRAL[codigo] ?? codigo;
}
