"""Carga de contratos: Portal da Transparência (federal) + PNCP (E/M).

Materializa a tabela ``contratos`` no DuckDB a partir de:
- ZIPs mensais de compras do Portal da Transparência (esfera federal);
- API de consulta do PNCP, em chunks mensais (esferas estadual/municipal,
  conforme ``config.esferas``) — filtros de esfera/UF/município aplicados
  client-side porque o endpoint /contratos ignora o parâmetro ``uf``
  (verificado em 06/07/2026) e limita o intervalo a 365 dias.

Uso: ``uv run python -m radar_pipeline.contratos``
"""

from collections.abc import Callable, Iterator
from datetime import date, timedelta
from pathlib import Path

import duckdb
import httpx

from radar_pipeline import fontes
from radar_pipeline.config import Config
from radar_pipeline.staging import (
    DATA_BR,
    NOME_NORMALIZADO,
    SO_DIGITOS,
    VALOR_BRL,
    extrai_zip,
)

_DDL = """
CREATE OR REPLACE TABLE contratos (
    origem VARCHAR,             -- PORTAL | PNCP
    esfera VARCHAR,             -- F | E | M
    competencia VARCHAR,        -- AAAAMM do arquivo/chunk
    numero_contrato VARCHAR,
    orgao_codigo VARCHAR,
    orgao VARCHAR,
    orgao_superior VARCHAR,
    ug_codigo VARCHAR,
    ug VARCHAR,
    uf VARCHAR,
    municipio_codigo_ibge VARCHAR,
    cnpj_contratado VARCHAR,
    nome_contratado VARCHAR,
    nome_contratado_normalizado VARCHAR,
    objeto VARCHAR,
    situacao VARCHAR,
    modalidade VARCHAR,
    valor_inicial DECIMAL(18,2),
    valor_final DECIMAL(18,2),
    data_assinatura DATE,
    data_inicio_vigencia DATE,
    data_fim_vigencia DATE,
)
"""


def meses_desde(desde: str, ate: date | None = None) -> list[tuple[int, int]]:
    """Lista (ano, mês) de ``desde`` (AAAA-MM) até o mês atual, inclusive."""
    ate = ate or date.today()
    ano, mes = (int(p) for p in desde.split("-"))
    meses = []
    while (ano, mes) <= (ate.year, ate.month):
        meses.append((ano, mes))
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    return meses


def baixa_compras(config: Config) -> list[Path]:
    """Garante os ZIPs mensais de compras desde ``contratos_desde``.

    Meses já baixados são reaproveitados, EXCETO os 2 mais recentes — o mês
    corrente é publicado com defasagem (06/2026 tinha 33 contratos no dia 06/07
    vs 2.548 no mês fechado), então re-baixamos para capturar o que entrou.
    Meses ainda não publicados (403) são pulados.
    """
    pasta = config.raw / "compras"
    meses = meses_desde(config.contratos_desde)
    baixados = []
    for i, (ano, mes) in enumerate(meses):
        destino = pasta / f"{ano:04d}{mes:02d}_compras.zip"
        recente = i >= len(meses) - 2
        if destino.exists() and not recente:
            baixados.append(destino)
            continue
        try:
            fontes.baixar(fontes.url_mensal("compras", ano, mes), destino)
            baixados.append(destino)
        except httpx.HTTPStatusError as erro:
            if erro.response.status_code != 403:
                raise
            print(f"  compras {mes:02d}/{ano}: ainda não publicado, pulando")
    return baixados


def carrega_contratos(
    config: Config,
    con: duckdb.DuckDBPyConnection,
    busca_pncp: Callable[[date, date], Iterator[dict]] = fontes.contratos_pncp,
) -> dict[str, int]:
    """Materializa a tabela ``contratos``; retorna contagens por origem."""
    con.execute(_DDL)
    if "F" in config.esferas:
        _carrega_portal(config, con)
    esferas_pncp = [e for e in config.esferas if e != "F"]
    if esferas_pncp:
        _carrega_pncp(config, con, esferas_pncp, busca_pncp)
    return dict(
        con.execute("SELECT origem, count(*) FROM contratos GROUP BY origem ORDER BY 1").fetchall()
    )


def _carrega_portal(config: Config, con: duckdb.DuckDBPyConnection) -> None:
    """Carrega os CSVs de Compras extraídos dos ZIPs mensais (esfera federal)."""
    pasta = config.raw / "compras"
    desde = config.contratos_desde.replace("-", "")
    zips = sorted(z for z in pasta.glob("*_compras.zip") if z.name[:6] >= desde)
    if not zips:
        raise FileNotFoundError(f"nenhum ZIP de compras >= {desde} em {pasta}")
    csvs = []
    for zip_path in zips:
        extraidos = extrai_zip(zip_path, config.staging / "compras")
        csvs.extend(str(c) for nome, c in extraidos.items() if "_compras.csv" in nome)
    lista = ", ".join(f"'{c}'" for c in sorted(csvs))
    nome = '"Nome Contratado"'
    con.execute(f"""
    INSERT INTO contratos
    SELECT * FROM (
        SELECT
            'PORTAL'                                            AS origem,
            'F'                                                 AS esfera,
            regexp_extract(filename, '(\\d{{6}})_Compras', 1)   AS competencia,
            "Número do Contrato"                                AS numero_contrato,
            "Código Órgão"                                      AS orgao_codigo,
            "Nome Órgão"                                        AS orgao,
            "Nome Órgão Superior"                               AS orgao_superior,
            "Código UG"                                         AS ug_codigo,
            "Nome UG"                                           AS ug,
            NULL                                                AS uf,
            NULL                                                AS municipio_codigo_ibge,
            {SO_DIGITOS.format(col='"Código Contratado"')}      AS cnpj_contratado,
            {nome}                                              AS nome_contratado,
            {NOME_NORMALIZADO.format(col=nome)}                 AS nome_contratado_normalizado,
            "Objeto"                                            AS objeto,
            "Situação Contrato"                                 AS situacao,
            "Modalidade Compra"                                 AS modalidade,
            {VALOR_BRL.format(col='"Valor Inicial Compra"')}    AS valor_inicial,
            {VALOR_BRL.format(col='"Valor Final Compra"')}      AS valor_final,
            {DATA_BR.format(col='"Data Assinatura Contrato"')}  AS data_assinatura,
            {DATA_BR.format(col='"Data Início Vigência"')}      AS data_inicio_vigencia,
            {DATA_BR.format(col='"Data Fim Vigência"')}         AS data_fim_vigencia
        FROM read_csv([{lista}], delim=';', quote='"', header=true,
                      all_varchar=true, filename=true)
        WHERE {SO_DIGITOS.format(col='"Código Contratado"')} <> ''
    )
    -- um contrato republicado em meses seguintes fica só com a versão mais recente
    QUALIFY row_number() OVER (
        PARTITION BY numero_contrato, ug_codigo, cnpj_contratado
        ORDER BY competencia DESC
    ) = 1
    """)


def _carrega_pncp(
    config: Config,
    con: duckdb.DuckDBPyConnection,
    esferas: list[str],
    busca_pncp: Callable[[date, date], Iterator[dict]],
) -> None:
    """Busca contratos no PNCP em chunks mensais e insere os do escopo."""
    hoje = date.today()
    for ano, mes in meses_desde(config.contratos_desde):
        inicio = date(ano, mes, 1)
        fim = min(hoje, (inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1))
        lote = []
        for r in busca_pncp(inicio, fim):
            unidade = r.get("unidadeOrgao") or {}
            orgao = r.get("orgaoEntidade") or {}
            if orgao.get("esferaId") not in esferas:
                continue
            if config.uf and unidade.get("ufSigla") != config.uf:
                continue
            municipio = str(unidade.get("codigoIbge") or "")
            if config.codigo_municipio_ibge and municipio != config.codigo_municipio_ibge:
                continue
            lote.append((
                "PNCP", orgao.get("esferaId"), f"{ano:04d}{mes:02d}",
                r.get("numeroControlePNCP"), orgao.get("cnpj"), orgao.get("razaoSocial"),
                None, unidade.get("codigoUnidade"), unidade.get("nomeUnidade"),
                unidade.get("ufSigla"), municipio or None, r.get("niFornecedor"),
                r.get("nomeRazaoSocialFornecedor"), None, r.get("objetoContrato"),
                None, (r.get("tipoContrato") or {}).get("nome"), r.get("valorInicial"),
                r.get("valorGlobal"), r.get("dataAssinatura"), r.get("dataVigenciaInicio"),
                r.get("dataVigenciaFim"),
            ))
        if lote:
            con.executemany(
                f"INSERT INTO contratos VALUES ({', '.join('?' * 22)})", lote
            )
            con.execute("""
                UPDATE contratos SET nome_contratado_normalizado =
                    regexp_replace(trim(upper(strip_accents(nome_contratado))), '\\s+', ' ', 'g')
                WHERE origem = 'PNCP' AND nome_contratado_normalizado IS NULL
            """)


def main() -> None:
    import duckdb as _duckdb

    config = Config.carrega()
    config.dados.mkdir(parents=True, exist_ok=True)
    if "F" in config.esferas:
        baixa_compras(config)
    with _duckdb.connect(config.banco) as con:
        contagens = carrega_contratos(config, con)
        valor = con.execute("SELECT sum(valor_final) FROM contratos").fetchone()[0]
    for origem, n in contagens.items():
        print(f"  {origem}: {n}")
    print(f"✓ tabela contratos: {sum(contagens.values())} registros, R$ {valor:,.2f} totais")


if __name__ == "__main__":
    main()
