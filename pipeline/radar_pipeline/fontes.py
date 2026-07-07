"""URLs e download das fontes de dados (ver docs/fontes.md).

Padrões verificados em 06/07/2026:
- Sanções (snapshot diário, só o mais recente disponível):
  portaldatransparencia.gov.br/download-de-dados/{base}/AAAAMMDD
- Compras e licitações (mensal):
  portaldatransparencia.gov.br/download-de-dados/{base}/AAAAMM
- CNPJ (mensal): share Nextcloud público da Receita, download via WebDAV.
  O endereço da Receita já mudou 3+ vezes; se o share morrer, resolver o novo
  endereço pela página do conjunto no dados.gov.br (docs/fontes.md).
"""

import time
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import httpx

PORTAL_TRANSPARENCIA = "https://portaldatransparencia.gov.br/download-de-dados"

BASES_SANCOES = ("ceis", "cnep", "cepim", "acordos-leniencia")
BASES_MENSAIS = ("compras", "licitacoes")

# A base de licitações foi descontinuada no Portal da Transparência (Lei
# 14.133 — dados novos estão no PNCP); o último mês publicado é 04/2024.
ULTIMO_MES_LICITACOES = (2024, 4)

# API de consulta do PNCP (contratações pós-Lei 14.133, todas as esferas).
# Pública, sem token, paginada; rate limit agressivo (429) exige backoff.
PNCP_CONSULTA = "https://pncp.gov.br/api/consulta/v1"

# Códigos de modalidade exigidos pelo endpoint de contratações. Nomes 1 e
# 4-14 confirmados na própria API em 06/07/2026; 2 e 3 existiam sem registros
# no período sondado (nomes conforme Lei 14.133, art. 28).
MODALIDADES_PNCP = {
    1: "Leilão - Eletrônico",
    2: "Diálogo Competitivo",
    3: "Concurso",
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão - Presencial",
    14: "Inaplicabilidade da Licitação",
}

RECEITA_SHARE_ID = "YggdBLfdninEJX9"
RECEITA_WEBDAV = "https://arquivos.receitafederal.gov.br/public.php/webdav"

_HEADERS = {"User-Agent": "SonarPublico/0.1 (+concurso reuso dados abertos CGU)"}


def url_sancao(base: str, dia: date) -> str:
    """URL de download de CEIS/CNEP/CEPIM/Leniência para um dia."""
    if base not in BASES_SANCOES:
        raise ValueError(f"base desconhecida: {base!r}")
    return f"{PORTAL_TRANSPARENCIA}/{base}/{dia:%Y%m%d}"


def url_mensal(base: str, ano: int, mes: int) -> str:
    """URL de download de compras/licitações para um mês."""
    if base not in BASES_MENSAIS:
        raise ValueError(f"base desconhecida: {base!r}")
    return f"{PORTAL_TRANSPARENCIA}/{base}/{ano:04d}{mes:02d}"


def url_cnpj(ano: int, mes: int, arquivo: str) -> str:
    """URL WebDAV de um arquivo do dump mensal do CNPJ (ex.: 'Socios0.zip')."""
    return f"{RECEITA_WEBDAV}/{ano:04d}-{mes:02d}/{arquivo}"


def baixar_sancao_mais_recente(
    base: str, pasta: Path, *, a_partir: date | None = None, janela_dias: int = 14
) -> tuple[Path, date]:
    """Baixa o snapshot mais recente de uma base de sanções.

    O bucket da CGU só serve o snapshot mais atual, mas a data dele varia por
    base (nem toda base publica todo dia) — então tentamos de `a_partir` para
    trás até `janela_dias`. Retorna (caminho, data do snapshot).
    """
    dia = a_partir or date.today()
    for _ in range(janela_dias):
        try:
            destino = pasta / f"{dia:%Y%m%d}_{base}.zip"
            return baixar(url_sancao(base, dia), destino), dia
        except httpx.HTTPStatusError as erro:
            if erro.response.status_code != 403:
                raise
            dia -= timedelta(days=1)
    raise RuntimeError(f"nenhum snapshot de {base!r} nos últimos {janela_dias} dias")


def baixar_mensal_mais_recente(
    base: str, pasta: Path, *, ano: int, mes: int, janela_meses: int = 3
) -> tuple[Path, tuple[int, int]]:
    """Baixa compras/licitações do mês pedido, recuando se ainda não publicado.

    Cada base mensal tem calendário próprio de publicação (ex.: compras de
    junho já no ar enquanto licitações ainda não). Retorna (caminho, (ano, mes)).
    """
    for _ in range(janela_meses):
        try:
            destino = pasta / f"{ano:04d}{mes:02d}_{base}.zip"
            return baixar(url_mensal(base, ano, mes), destino), (ano, mes)
        except httpx.HTTPStatusError as erro:
            if erro.response.status_code != 403:
                raise
            ano, mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    raise RuntimeError(f"nenhum mês de {base!r} disponível na janela de {janela_meses} meses")


def consulta_pncp(
    caminho: str, *, tamanho_pagina: int = 50, max_tentativas: int = 6, **params: object
) -> Iterator[dict]:
    """Itera todos os registros de um endpoint de consulta do PNCP.

    Percorre as páginas até o fim, com backoff exponencial em HTTP 429.
    `tamanho_pagina` máximo: 500 em /contratos, 50 em /contratacoes/*.
    """
    pagina = 1
    while True:
        resposta = _get_pncp(
            caminho, {**params, "pagina": pagina, "tamanhoPagina": tamanho_pagina}, max_tentativas
        )
        if resposta.status_code == 204 or not resposta.content:
            return
        corpo = resposta.json()
        yield from corpo.get("data", [])
        if pagina >= corpo.get("totalPaginas", 0):
            return
        pagina += 1


def _get_pncp(caminho: str, params: dict, max_tentativas: int) -> httpx.Response:
    for tentativa in range(max_tentativas):
        resposta = httpx.get(
            f"{PNCP_CONSULTA}{caminho}", params=params, headers=_HEADERS, timeout=120
        )
        if resposta.status_code == 429:
            espera = int(resposta.headers.get("Retry-After", 0)) or 5 * 2**tentativa
            time.sleep(min(espera, 120))
            continue
        resposta.raise_for_status()
        return resposta
    raise RuntimeError(f"PNCP: rate limit persistente após {max_tentativas} tentativas: {caminho}")


def contratos_pncp(inicio: date, fim: date) -> Iterator[dict]:
    """Contratos publicados no PNCP no período (todas as esferas).

    Filtrar esfera federal no consumidor: ``registro["orgaoEntidade"]["esferaId"] == "F"``.
    """
    return consulta_pncp(
        "/contratos",
        tamanho_pagina=500,
        dataInicial=f"{inicio:%Y%m%d}",
        dataFinal=f"{fim:%Y%m%d}",
    )


def contratacoes_pncp(inicio: date, fim: date, modalidade: int) -> Iterator[dict]:
    """Contratações (licitações + contratações diretas) publicadas no PNCP.

    O endpoint exige a modalidade — para cobrir tudo, iterar MODALIDADES_PNCP.
    """
    if modalidade not in MODALIDADES_PNCP:
        raise ValueError(f"modalidade desconhecida: {modalidade!r}")
    return consulta_pncp(
        "/contratacoes/publicacao",
        dataInicial=f"{inicio:%Y%m%d}",
        dataFinal=f"{fim:%Y%m%d}",
        codigoModalidadeContratacao=modalidade,
    )


def baixar(url: str, destino: Path, *, auth: tuple[str, str] | None = None) -> Path:
    """Baixa `url` para `destino` em streaming; retorna o caminho gravado.

    Para URLs do WebDAV da Receita, use ``auth=(RECEITA_SHARE_ID, "")``.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    with httpx.stream(
        "GET", url, follow_redirects=True, timeout=300, headers=_HEADERS, auth=auth
    ) as resposta:
        resposta.raise_for_status()
        with tmp.open("wb") as arquivo:
            for pedaco in resposta.iter_bytes():
                arquivo.write(pedaco)
    tmp.rename(destino)
    return destino
