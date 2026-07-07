// Explicações em LINGUAGEM SIMPLES (SPEC §1.2.4 e P3.3) — cada sanção
// acompanha um "o que isso significa?". Tom informativo, nunca acusatório.

const EXPLICACOES: [RegExp, string][] = [
  [
    /inidon/i,
    "Declaração de inidoneidade é a sanção mais grave: a empresa foi considerada " +
      "não confiável para contratar com o poder público, em geral por fraude ou " +
      "irregularidade grave comprovada em processo. Vale em todo o país enquanto " +
      "durar a sanção.",
  ],
  [
    /suspens/i,
    "Suspensão significa que a empresa está temporariamente proibida de participar " +
      "de licitações e contratos — em regra, apenas com o órgão ou governo que " +
      "aplicou a punição. Um contrato com outro órgão pode ser legal; verifique o " +
      "órgão sancionador.",
  ],
  [
    /impedimento/i,
    "Impedimento de licitar e contratar: a empresa descumpriu regras de uma " +
      "licitação ou contrato e ficou proibida de fazer novos contratos com o ente " +
      "que a puniu, por prazo determinado.",
  ],
  [
    /leni[êe]ncia/i,
    "Acordo de leniência não é uma punição comum: a empresa admitiu envolvimento em " +
      "irregularidades e se comprometeu a colaborar com as investigações e reparar " +
      "danos, em troca de continuar operando. Estar 'em cumprimento' significa que o " +
      "acordo segue ativo.",
  ],
  [
    /cepim|entidade impedida/i,
    "Esta organização sem fins lucrativos está impedida de receber novos recursos " +
      "públicos federais (convênios e parcerias), em geral por problemas na " +
      "prestação de contas de repasses anteriores.",
  ],
  [
    /multa/i,
    "Multa aplicada com base na Lei Anticorrupção: a empresa foi condenada " +
      "administrativamente a pagar um valor por atos contra a administração pública.",
  ],
  [
    /publica[çc][ãa]o extraordin/i,
    "Publicação extraordinária: a empresa foi obrigada a publicar, às próprias " +
      "custas, a decisão que a condenou — uma forma de dar transparência à punição.",
  ],
];

export function explicaSancao(categoria: string): string {
  for (const [padrao, texto] of EXPLICACOES) {
    if (padrao.test(categoria)) return texto;
  }
  return (
    "Sanção registrada nos cadastros públicos do governo federal. Consulte o " +
    "órgão sancionador para detalhes do processo."
  );
}

export const AVISO_METODOLOGIA =
  "O Sonar Público aponta vínculos a partir de dados oficiais — não acusa. " +
  "Vínculo societário com empresa sancionada não é prova de irregularidade, e o " +
  "alcance de cada sanção varia conforme o órgão que a aplicou.";
