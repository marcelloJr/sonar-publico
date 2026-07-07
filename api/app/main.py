from typing import Annotated

import duckdb
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app import consultas
from app.db import get_con

app = FastAPI(
    title="Sonar Público — API",
    description=(
        "API pública que cruza sanções (CEIS/CNEP/CEPIM/Leniência), contratos "
        "federais e quadro societário. Dados: Portal da Transparência, PNCP e "
        "Receita Federal, catalogados no dados.gov.br. Vínculo societário com "
        "empresa sancionada é INDÍCIO, não prova de irregularidade — leia a "
        "página de Metodologia."
    ),
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
)

Con = Annotated[duckdb.DuckDBPyConnection, Depends(get_con)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/busca")
def busca(con: Con, q: Annotated[str, Query(min_length=3)]) -> dict:
    return {"resultados": consultas.busca(con, q)}


@app.get("/empresas/{cnpj}")
def empresa(con: Con, cnpj: str) -> dict:
    ficha = consultas.ficha(con, cnpj)
    if ficha is None:
        raise HTTPException(
            404,
            detail=(
                "empresa fora do universo do Sonar (sem sanção, contrato público "
                "recente ou vínculo societário com sancionada)"
            ),
        )
    return ficha


@app.get("/empresas/{cnpj}/grafo")
def grafo(con: Con, cnpj: str, profundidade: int = 1) -> dict:
    return consultas.grafo(con, cnpj, profundidade)


@app.get("/orgaos")
def orgaos(con: Con) -> dict:
    return {"orgaos": consultas.orgaos(con)}


@app.get("/orgaos/{codigo}/fornecedores")
def fornecedores(con: Con, codigo: str, grau: int | None = None) -> dict:
    resultado = consultas.fornecedores_do_orgao(con, codigo, grau)
    if resultado is None:
        raise HTTPException(404, detail="órgão não encontrado nos contratos carregados")
    return resultado


@app.get("/estatisticas")
def estatisticas(con: Con) -> dict:
    return consultas.estatisticas(con)
