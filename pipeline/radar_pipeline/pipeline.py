"""Pipeline completo (P1.9): download → normalização → cruzamento.

Encadeia as quatro etapas na ordem de dependência:
1. sanções   (snapshots mais recentes do Portal da Transparência)
2. contratos (compras mensais + PNCP conforme escopo do config.toml)
3. cnpj      (dump da Receita + filtragem do universo — a etapa pesada)
4. vínculos  (arestas de sócio em comum + graus de risco)

Uso: ``uv run python -m radar_pipeline.pipeline [--amostra]``
(ou ``make pipeline`` / ``make pipeline-amostra``)
"""

import sys
from dataclasses import replace
from datetime import date

import duckdb

from radar_pipeline import cnpj, contratos, fontes, sancoes, vinculos
from radar_pipeline.config import Config


def baixa_sancoes(config: Config) -> None:
    for base in fontes.BASES_SANCOES:
        destino, dia = fontes.baixar_sancao_mais_recente(
            base, config.raw / "sancoes", a_partir=date.today()
        )
        print(f"  ↓ {base}: snapshot de {dia:%d/%m/%Y}")


def roda(config: Config) -> None:
    config.dados.mkdir(parents=True, exist_ok=True)

    print("[1/4] sanções")
    baixa_sancoes(config)
    with duckdb.connect(config.banco) as con:
        for fonte, n in sancoes.carrega_sancoes(config, con).items():
            print(f"  {fonte}: {n}")

    print("[2/4] contratos")
    if "F" in config.esferas:
        contratos.baixa_compras(config)
    with duckdb.connect(config.banco) as con:
        for origem, n in contratos.carrega_contratos(config, con).items():
            print(f"  {origem}: {n}")

    print("[3/4] cnpj (universo)" + (" — MODO AMOSTRA" if config.amostra else ""))
    cnpj.baixa_cnpj(config)
    with duckdb.connect(config.banco) as con:
        for tabela, n in cnpj.carrega_cnpj(config, con).items():
            print(f"  {tabela}: {n}")

    print("[4/4] vínculos e graus de risco")
    with duckdb.connect(config.banco) as con:
        for nome, n in vinculos.carrega_vinculos(con).items():
            print(f"  {nome}: {n}")

        empresas_alerta, contratos_alerta, valor = con.execute("""
            SELECT count(DISTINCT c.cnpj_contratado), count(*), coalesce(sum(c.valor_final), 0)
            FROM contratos c
            JOIN empresas_risco r ON r.cnpj_basico = c.cnpj_contratado[:8] AND r.grau = 0
            WHERE c.data_fim_vigencia >= current_date
        """).fetchone()

    print(f"✓ pipeline completo em {config.banco}")
    print(
        f"  radar: {empresas_alerta} empresas com sanção vigente mantêm "
        f"{contratos_alerta} contratos em vigência (R$ {valor:,.2f})"
    )


def main() -> None:
    config = Config.carrega()
    if "--amostra" in sys.argv:
        config = replace(config, amostra=True)
    roda(config)


if __name__ == "__main__":
    main()
