"""Carga normalizada das 4 bases de sanções no DuckDB (P1.3 + P1.4).

Unifica CEIS, CNEP, CEPIM e Acordos de Leniência na tabela ``sancoes``:
uma linha por sanção, com CNPJ/CPF só dígitos, nomes normalizados, datas ISO
e flag ``vigente``. Layouts reais (colunas, encoding): docs/layouts.md.

Uso: ``uv run python -m radar_pipeline.sancoes``
"""

from pathlib import Path

import duckdb

from radar_pipeline.config import Config
from radar_pipeline.fontes import BASES_SANCOES
from radar_pipeline.staging import (
    DATA_BR as _DATA_BR,
)
from radar_pipeline.staging import (
    NOME_NORMALIZADO as _NOME_NORMALIZADO,
)
from radar_pipeline.staging import (
    SO_DIGITOS as _SO_DIGITOS,
)
from radar_pipeline.staging import (
    VALOR_BRL as _VALOR_BRL,
)
from radar_pipeline.staging import (
    extrai_zip as _extrai,
)
from radar_pipeline.staging import (
    sql_csv as _csv,
)


def _zip_mais_recente(pasta: Path, base: str) -> Path:
    candidatos = sorted(pasta.glob(f"*_{base}.zip"))
    if not candidatos:
        raise FileNotFoundError(
            f"nenhum ZIP de {base!r} em {pasta} — rode `python -m radar_pipeline.amostras`"
        )
    return candidatos[-1]


def carrega_sancoes(config: Config, con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Materializa a tabela ``sancoes`` unificada; retorna contagens por fonte."""
    pasta = config.raw / "sancoes"
    csvs: dict[str, dict[str, Path]] = {
        base: _extrai(_zip_mais_recente(pasta, base), config.staging / "sancoes")
        for base in BASES_SANCOES
    }
    ceis = next(c for nome, c in csvs["ceis"].items() if "ceis" in nome)
    cnep = next(c for nome, c in csvs["cnep"].items() if "cnep" in nome)
    cepim = next(c for nome, c in csvs["cepim"].items() if "cepim" in nome)
    acordos = next(c for nome, c in csvs["acordos-leniencia"].items() if "acordos" in nome)

    # CEIS e CNEP compartilham layout (CNEP tem VALOR DA MULTA a mais)
    def ceis_like(caminho: Path, fonte: str, multa: str) -> str:
        nome = """coalesce(nullif(trim("RAZÃO SOCIAL - CADASTRO RECEITA"), ''),
                           "NOME DO SANCIONADO")"""
        return f"""
        SELECT
            '{fonte}'                                                    AS fonte,
            "TIPO DE PESSOA"                                             AS tipo_pessoa,
            {_SO_DIGITOS.format(col='"CPF OU CNPJ DO SANCIONADO"')}      AS cnpj_cpf,
            {nome}                                                       AS nome,
            {_NOME_NORMALIZADO.format(col=nome)}                         AS nome_normalizado,
            "CATEGORIA DA SANÇÃO"                                        AS categoria,
            "ÓRGÃO SANCIONADOR"                                          AS orgao,
            "UF ÓRGÃO SANCIONADOR"                                       AS uf_orgao,
            "ESFERA ÓRGÃO SANCIONADOR"                                   AS esfera_orgao,
            {_DATA_BR.format(col='"DATA INÍCIO SANÇÃO"')}                AS data_inicio,
            {_DATA_BR.format(col='"DATA FINAL SANÇÃO"')}                 AS data_fim,
            "NÚMERO DO PROCESSO"                                         AS processo,
            "FUNDAMENTAÇÃO LEGAL"                                        AS fundamentacao,
            {multa}                                                      AS valor_multa
        FROM {_csv(caminho)}
        """

    multa_brl = _VALOR_BRL.format(col='"VALOR DA MULTA"')
    # cabeçalho real usa en dash (0x96/cp1252); a transcodificação normaliza p/ hífen
    nome_leniencia = """coalesce(nullif(trim("RAZÃO SOCIAL - CADASTRO RECEITA"), ''),
                                 "NOME FANTASIA - CADASTRO RECEITA")"""
    con.execute(f"""
    CREATE OR REPLACE TABLE sancoes AS
    WITH todas AS (
        {ceis_like(ceis, "CEIS", "NULL")}
        UNION ALL BY NAME
        {ceis_like(cnep, "CNEP", multa_brl)}
        UNION ALL BY NAME
        SELECT
            'CEPIM'                                              AS fonte,
            'Jurídica'                                           AS tipo_pessoa,
            {_SO_DIGITOS.format(col='"CNPJ ENTIDADE"')}          AS cnpj_cpf,
            "NOME ENTIDADE"                                      AS nome,
            {_NOME_NORMALIZADO.format(col='"NOME ENTIDADE"')}    AS nome_normalizado,
            'Entidade impedida (CEPIM)'                          AS categoria,
            "ÓRGÃO CONCEDENTE"                                   AS orgao,
            NULL                                                 AS uf_orgao,
            'FEDERAL'                                            AS esfera_orgao,
            NULL::DATE                                           AS data_inicio,
            NULL::DATE                                           AS data_fim,
            "NÚMERO CONVÊNIO"                                    AS processo,
            "MOTIVO DO IMPEDIMENTO"                              AS fundamentacao,
            NULL                                                 AS valor_multa
        FROM {_csv(cepim)}
        UNION ALL BY NAME
        SELECT
            'LENIENCIA'                                          AS fonte,
            'Jurídica'                                           AS tipo_pessoa,
            {_SO_DIGITOS.format(col='"CNPJ DO SANCIONADO"')}     AS cnpj_cpf,
            {nome_leniencia}                                     AS nome,
            {_NOME_NORMALIZADO.format(col=nome_leniencia)}       AS nome_normalizado,
            'Acordo de leniência (' || "SITUAÇÃO DO ACORDO DE LENIÊNICA" || ')' AS categoria,
            "ÓRGÃO SANCIONADOR"                                  AS orgao,
            NULL                                                 AS uf_orgao,
            'FEDERAL'                                            AS esfera_orgao,
            {_DATA_BR.format(col='"DATA DE INÍCIO DO ACORDO"')}  AS data_inicio,
            {_DATA_BR.format(col='"DATA DE FIM DO ACORDO"')}     AS data_fim,
            "NÚMERO DO PROCESSO"                                 AS processo,
            "TERMOS DO ACORDO"                                   AS fundamentacao,
            NULL                                                 AS valor_multa
        FROM {_csv(acordos)}
    ),
    dedup AS (
        SELECT DISTINCT ON (fonte, cnpj_cpf, processo, categoria, data_inicio) *
        FROM todas
        WHERE cnpj_cpf <> ''
    )
    SELECT *,
        -- vigente: sem data de fim (inidoneidade, CEPIM) ou fim no futuro
        (data_fim IS NULL OR data_fim >= current_date) AS vigente
    FROM dedup
    """)

    contagens = con.execute(
        "SELECT fonte, count(*) FROM sancoes GROUP BY fonte ORDER BY fonte"
    ).fetchall()
    return dict(contagens)


def main() -> None:
    config = Config.carrega()
    config.dados.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(config.banco) as con:
        contagens = carrega_sancoes(config, con)
        vigentes = con.execute("SELECT count(*) FROM sancoes WHERE vigente").fetchone()[0]
    total = sum(contagens.values())
    for fonte, n in contagens.items():
        print(f"  {fonte}: {n}")
    print(f"✓ tabela sancoes: {total} registros ({vigentes} vigentes) em {config.banco}")


if __name__ == "__main__":
    main()
