"""Consultas SQL da API sobre as tabelas do pipeline.

Grãos: empresas/socios/risco usam a raiz do CNPJ (8 dígitos — o QSA público
só tem a raiz); sanções e contratos usam o CNPJ completo (14). A ficha junta
os dois níveis e o front deixa isso explícito.
"""

import re

import duckdb

from app.db import linhas_como_dicts

_NAO_DIGITO = re.compile(r"\D")

NORMALIZA_SQL = "regexp_replace(trim(upper(strip_accents(?))), '\\s+', ' ', 'g')"


# Nomes vêm de 3 fontes (prioridade: cadastro da Receita > sanções >
# contratos) — a ficha e a busca não podem depender só do dump do CNPJ:
# no modo amostra ele é parcial, e mesmo completo há defasagem de 1 mês.
_NOMES_SQL = """
    nomes AS (
        SELECT cnpj_basico, razao_social AS nome, 1 AS prioridade FROM empresas
        UNION ALL
        SELECT cnpj_cpf[:8], nome, 2 FROM sancoes WHERE length(cnpj_cpf) = 14
        UNION ALL
        SELECT cnpj_contratado[:8], nome_contratado, 3 FROM contratos
    )
"""


def busca(con: duckdb.DuckDBPyConnection, q: str, limite: int = 20) -> list[dict]:
    digitos = _NAO_DIGITO.sub("", q)
    if len(digitos) >= 8:
        filtro, valor = "n.cnpj_basico = ?", digitos[:8]
    else:
        filtro = (
            "regexp_replace(trim(upper(strip_accents(n.nome))), '\\s+', ' ', 'g')"
            f" LIKE '%' || {NORMALIZA_SQL} || '%'"
        )
        valor = q
    return linhas_como_dicts(con, f"""
        WITH {_NOMES_SQL},
        encontradas AS (
            SELECT cnpj_basico, arg_min(nome, prioridade) AS razao_social
            FROM nomes n
            WHERE nome IS NOT NULL AND {filtro}
            GROUP BY cnpj_basico
        )
        SELECT e.cnpj_basico, e.razao_social, m.uf, m.situacao_cadastral,
               min(r.grau) AS grau,
               bool_or(coalesce(r.indicio_sucessora, false)) AS indicio_sucessora
        FROM encontradas e
        LEFT JOIN estabelecimentos m ON m.cnpj_basico = e.cnpj_basico AND m.matriz_filial = '1'
        LEFT JOIN empresas_risco r ON r.cnpj_basico = e.cnpj_basico
        GROUP BY ALL
        ORDER BY grau NULLS LAST, e.razao_social
        LIMIT {int(limite)}
    """, [valor])


def ficha(con: duckdb.DuckDBPyConnection, cnpj: str) -> dict | None:
    raiz = _NAO_DIGITO.sub("", cnpj)[:8]
    cadastro = linhas_como_dicts(con, """
        SELECT e.cnpj_basico, e.razao_social, e.natureza_juridica, e.capital_social,
               e.porte, m.cnpj, m.nome_fantasia, m.situacao_cadastral,
               m.data_inicio_atividade, m.cnae_principal, m.uf, m.municipio_codigo,
               true AS cadastro_receita_disponivel
        FROM empresas e
        LEFT JOIN estabelecimentos m ON m.cnpj_basico = e.cnpj_basico AND m.matriz_filial = '1'
        WHERE e.cnpj_basico = ?
    """, [raiz])
    if not cadastro:
        # fora do dump da Receita (modo amostra ou defasagem): monta o mínimo
        # a partir dos nomes de sanções/contratos
        alternativo = linhas_como_dicts(con, f"""
            WITH {_NOMES_SQL}
            SELECT cnpj_basico, arg_min(nome, prioridade) AS razao_social,
                   false AS cadastro_receita_disponivel
            FROM nomes WHERE cnpj_basico = ? AND nome IS NOT NULL
            GROUP BY cnpj_basico
        """, [raiz])
        if not alternativo:
            # sem nome em lugar nenhum, mas pode estar no universo (aparece no
            # grafo como nó): a ficha deve existir mesmo assim
            no_universo = con.execute(
                """
                SELECT 1 FROM socios WHERE cnpj_basico = ?
                UNION ALL
                SELECT 1 FROM empresas_risco WHERE cnpj_basico = ?
                LIMIT 1
                """,
                [raiz, raiz],
            ).fetchone()
            if not no_universo:
                return None
            alternativo = [{
                "cnpj_basico": raiz,
                "razao_social": None,
                "cadastro_receita_disponivel": False,
            }]
        cadastro = alternativo
    return {
        "cadastro": cadastro[0],
        "risco": linhas_como_dicts(con, """
            SELECT grau, relacionada, socio_comum, confianca, indicio_sucessora
            FROM empresas_risco WHERE cnpj_basico = ?
            ORDER BY grau, indicio_sucessora DESC
        """, [raiz]),
        "sancoes": linhas_como_dicts(con, """
            SELECT fonte, categoria, orgao, uf_orgao, esfera_orgao,
                   data_inicio, data_fim, vigente, processo, cnpj_cpf
            FROM sancoes WHERE cnpj_cpf[:8] = ? AND length(cnpj_cpf) = 14
            ORDER BY vigente DESC, data_inicio DESC
        """, [raiz]),
        "contratos": linhas_como_dicts(con, """
            SELECT origem, esfera, numero_contrato, orgao, objeto, situacao,
                   modalidade, valor_final, data_inicio_vigencia,
                   data_fim_vigencia, cnpj_contratado
            FROM contratos WHERE cnpj_contratado[:8] = ?
            ORDER BY valor_final DESC NULLS LAST
            LIMIT 100
        """, [raiz]),
        "socios": linhas_como_dicts(con, """
            SELECT nome_socio, cpf_mascarado, qualificacao, data_entrada
            FROM socios WHERE cnpj_basico = ?
            ORDER BY nome_socio
        """, [raiz]),
    }


def grafo(con: duckdb.DuckDBPyConnection, cnpj: str, profundidade: int = 1) -> dict:
    raiz = _NAO_DIGITO.sub("", cnpj)[:8]
    profundidade = min(max(profundidade, 1), 2)
    arestas = linhas_como_dicts(con, """
        SELECT cnpj_a, cnpj_b, socio_comum, confianca
        FROM vinculos WHERE cnpj_a = ? OR cnpj_b = ?
    """, [raiz, raiz])
    if profundidade == 2:
        vizinhos = {a["cnpj_a"] for a in arestas} | {a["cnpj_b"] for a in arestas} - {raiz}
        if vizinhos:
            marcadores = ", ".join("?" * len(vizinhos))
            arestas += linhas_como_dicts(con, f"""
                SELECT cnpj_a, cnpj_b, socio_comum, confianca
                FROM vinculos
                WHERE cnpj_a IN ({marcadores}) OR cnpj_b IN ({marcadores})
            """, [*vizinhos, *vizinhos])
    ids = {raiz} | {a["cnpj_a"] for a in arestas} | {a["cnpj_b"] for a in arestas}
    marcadores = ", ".join("?" * len(ids))
    # nomes com fallback (Receita > sanções > contratos) para não deixar nó
    # sem rótulo quando a empresa está fora do dump do CNPJ
    nos = linhas_como_dicts(con, f"""
        WITH {_NOMES_SQL},
        ids(id) AS (VALUES {", ".join("(?)" for _ in ids)})
        SELECT i.id, arg_min(n.nome, n.prioridade) AS nome, min(r.grau) AS grau
        FROM ids i
        LEFT JOIN nomes n ON n.cnpj_basico = i.id AND n.nome IS NOT NULL
        LEFT JOIN empresas_risco r ON r.cnpj_basico = i.id
        GROUP BY i.id
    """, [*ids])
    # dedup de arestas (profundidade 2 pode repetir)
    unicas = {(a["cnpj_a"], a["cnpj_b"], a["socio_comum"]): a for a in arestas}
    return {"centro": raiz, "nos": nos, "arestas": list(unicas.values())}


def orgaos(con: duckdb.DuckDBPyConnection, limite: int = 60) -> list[dict]:
    """Órgãos contratantes, ordenados pelo valor sob alerta (grau 0)."""
    return linhas_como_dicts(con, f"""
        SELECT c.orgao_codigo, any_value(c.orgao) AS orgao, any_value(c.esfera) AS esfera,
               count(*) AS contratos,
               coalesce(sum(c.valor_final), 0) AS valor_total,
               count(*) FILTER (r.grau = 0) AS contratos_sob_alerta,
               coalesce(sum(c.valor_final) FILTER (r.grau = 0), 0) AS valor_sob_alerta
        FROM contratos c
        LEFT JOIN empresas_risco r ON r.cnpj_basico = c.cnpj_contratado[:8] AND r.grau = 0
        WHERE c.orgao_codigo IS NOT NULL
        GROUP BY c.orgao_codigo
        ORDER BY valor_sob_alerta DESC, valor_total DESC
        LIMIT {int(limite)}
    """, [])


def fornecedores_do_orgao(
    con: duckdb.DuckDBPyConnection, codigo: str, grau: int | None = None
) -> dict | None:
    cabecalho = con.execute(
        "SELECT any_value(orgao), any_value(esfera) FROM contratos WHERE orgao_codigo = ?",
        [codigo],
    ).fetchone()
    if not cabecalho or cabecalho[0] is None:
        return None
    filtro_grau = ""
    params: list = [codigo]
    if grau is not None:
        filtro_grau = "HAVING min(r.grau) = ?"
        params.append(grau)
    fornecedores = linhas_como_dicts(con, f"""
        SELECT c.cnpj_contratado[:8] AS cnpj_basico,
               any_value(c.nome_contratado) AS nome,
               min(r.grau) AS grau,
               bool_or(coalesce(r.indicio_sucessora, false)) AS indicio_sucessora,
               count(DISTINCT c.numero_contrato) AS contratos,
               coalesce(sum(c.valor_final), 0) AS valor_total,
               count(*) FILTER (c.data_fim_vigencia >= current_date) AS contratos_vigentes
        FROM contratos c
        LEFT JOIN empresas_risco r ON r.cnpj_basico = c.cnpj_contratado[:8]
        WHERE c.orgao_codigo = ?
        GROUP BY 1
        {filtro_grau}
        ORDER BY (min(r.grau) IS NULL), min(r.grau), valor_total DESC
        LIMIT 200
    """, params)
    return {"orgao_codigo": codigo, "orgao": cabecalho[0], "esfera": cabecalho[1],
            "fornecedores": fornecedores}


def estatisticas(con: duckdb.DuckDBPyConnection) -> dict:
    radar = con.execute("""
        SELECT count(DISTINCT c.cnpj_contratado), count(*), coalesce(sum(c.valor_final), 0)
        FROM contratos c
        JOIN empresas_risco r ON r.cnpj_basico = c.cnpj_contratado[:8] AND r.grau = 0
        WHERE c.data_fim_vigencia >= current_date
    """).fetchone()
    return {
        "sancionadas_vigentes": con.execute(
            "SELECT count(DISTINCT cnpj_basico) FROM empresas_risco WHERE grau = 0"
        ).fetchone()[0],
        "empresas_grau1": con.execute(
            "SELECT count(DISTINCT cnpj_basico) FROM empresas_risco WHERE grau = 1"
        ).fetchone()[0],
        "candidatas_sucessora": con.execute(
            "SELECT count(DISTINCT cnpj_basico) FROM empresas_risco WHERE indicio_sucessora"
        ).fetchone()[0],
        "sancionadas_com_contrato_vigente": radar[0],
        "contratos_vigentes_sob_alerta": radar[1],
        "valor_sob_alerta": float(radar[2]),
    }
