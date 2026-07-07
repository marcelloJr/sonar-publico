"""Conexão read-only com o banco gerado pelo pipeline.

O DuckDB aceita múltiplas conexões read-only ao mesmo arquivo; abrimos uma
por requisição via dependency (barato: o arquivo já está no page cache).
O caminho vem de ``SONAR_DB`` ou do default do monorepo (data/sonar.duckdb).
"""

import os
from collections.abc import Iterator
from pathlib import Path

import duckdb
from fastapi import HTTPException

_RAIZ_REPO = Path(__file__).resolve().parents[2]


def caminho_banco() -> Path:
    return Path(os.environ.get("SONAR_DB", _RAIZ_REPO / "data" / "sonar.duckdb"))


def get_con() -> Iterator[duckdb.DuckDBPyConnection]:
    caminho = caminho_banco()
    if not caminho.exists():
        raise HTTPException(503, detail="banco de dados indisponível — rode `make pipeline`")
    con = duckdb.connect(caminho, read_only=True)
    try:
        yield con
    finally:
        con.close()


def linhas_como_dicts(con: duckdb.DuckDBPyConnection, sql: str, params: list) -> list[dict]:
    resultado = con.execute(sql, params)
    colunas = [d[0] for d in resultado.description]
    return [dict(zip(colunas, linha, strict=True)) for linha in resultado.fetchall()]
