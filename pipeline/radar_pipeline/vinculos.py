"""Vínculos societários e graus de risco (P1.6 + P1.7, SPEC §4.2 e §4.3).

- ``vinculos``: arestas entre empresas do universo que compartilham sócio.
  Confiança ``alta`` = nome normalizado idêntico + mesmo fragmento de
  CPF/documento; ``media`` = nome idêntico com documento ausente em um dos
  lados. Nunca apresentar match de média confiança como certeza (SPEC §4.3.3).
- ``empresas_risco``: grau 0 (sanção vigente) e grau 1 (sócio em comum com
  grau 0), com o sinal complementar de possível sucessora — empresa aberta
  APÓS o início da sanção da relacionada, no mesmo CNAE e município.

Pré-requisitos no banco: tabelas sancoes, socios, estabelecimentos
(``radar_pipeline.sancoes`` e ``radar_pipeline.cnpj``).

Uso: ``uv run python -m radar_pipeline.vinculos``
"""

import duckdb

from radar_pipeline.config import Config

# Um mesmo nome em dezenas de empresas do universo é quase sempre
# representante institucional (fundos, advogados, interventores) — vira um
# hiperconector que liga tudo a tudo sem significado societário real.
MAX_EMPRESAS_POR_SOCIO_MEDIA = 20


def carrega_vinculos(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Materializa ``vinculos`` e ``empresas_risco``; retorna contagens."""
    con.execute(f"""
    CREATE OR REPLACE TABLE vinculos AS
    WITH s AS (
        SELECT DISTINCT cnpj_basico, nome_socio,
               regexp_replace(coalesce(cpf_mascarado, ''), '[^0-9]', '', 'g') AS doc
        FROM socios
        WHERE nullif(trim(nome_socio), '') IS NOT NULL
    ),
    alta AS (
        SELECT s1.cnpj_basico AS cnpj_a, s2.cnpj_basico AS cnpj_b,
               s1.nome_socio AS socio_comum, 'alta' AS confianca
        FROM s s1
        JOIN s s2 ON s1.nome_socio = s2.nome_socio AND s1.doc = s2.doc
                 AND s1.cnpj_basico < s2.cnpj_basico
        WHERE s1.doc <> '' AND s1.doc <> '000000'
    ),
    -- documento ausente em pelo menos um lado: match só por nome
    hiperconectores AS (
        SELECT nome_socio FROM s
        GROUP BY nome_socio
        HAVING count(DISTINCT cnpj_basico) > {MAX_EMPRESAS_POR_SOCIO_MEDIA}
    ),
    media AS (
        SELECT s1.cnpj_basico, s2.cnpj_basico, s1.nome_socio, 'media'
        FROM s s1
        JOIN s s2 ON s1.nome_socio = s2.nome_socio
                 AND s1.cnpj_basico < s2.cnpj_basico
        WHERE (s1.doc = '' OR s2.doc = '')
          AND s1.nome_socio NOT IN (SELECT nome_socio FROM hiperconectores)
    )
    SELECT DISTINCT ON (cnpj_a, cnpj_b, socio_comum) *
    FROM (SELECT * FROM alta UNION ALL SELECT * FROM media)
    ORDER BY cnpj_a, cnpj_b, socio_comum, confianca   -- 'alta' < 'media': alta vence
    """)

    con.execute("""
    CREATE OR REPLACE TABLE empresas_risco AS
    WITH grau0 AS (
        SELECT cnpj_cpf[:8] AS cnpj_basico,
               min(data_inicio) AS primeira_sancao_vigente
        FROM sancoes
        WHERE vigente AND length(cnpj_cpf) = 14
        GROUP BY 1
    ),
    arestas AS (  -- vínculo em qualquer direção entre empresa e sancionada
        SELECT cnpj_b AS cnpj_basico, cnpj_a AS relacionada, socio_comum, confianca
        FROM vinculos WHERE cnpj_a IN (SELECT cnpj_basico FROM grau0)
        UNION ALL
        SELECT cnpj_a, cnpj_b, socio_comum, confianca
        FROM vinculos WHERE cnpj_b IN (SELECT cnpj_basico FROM grau0)
    ),
    matriz AS (
        SELECT cnpj_basico, cnae_principal, municipio_codigo, uf, data_inicio_atividade
        FROM estabelecimentos WHERE matriz_filial = '1'
    ),
    grau1 AS (
        SELECT a.cnpj_basico, 1 AS grau, a.relacionada, a.socio_comum, a.confianca,
               -- sinal de sucessora (SPEC §4.2): aberta após a sanção da
               -- relacionada, mesmo CNAE e mesmo município
               coalesce(
                   m.data_inicio_atividade > g0.primeira_sancao_vigente
                   AND m.cnae_principal = mr.cnae_principal
                   AND m.municipio_codigo = mr.municipio_codigo, false
               ) AS indicio_sucessora
        FROM arestas a
        JOIN grau0 g0 ON g0.cnpj_basico = a.relacionada
        LEFT JOIN matriz m ON m.cnpj_basico = a.cnpj_basico
        LEFT JOIN matriz mr ON mr.cnpj_basico = a.relacionada
        WHERE a.cnpj_basico NOT IN (SELECT cnpj_basico FROM grau0)
        QUALIFY row_number() OVER (
            PARTITION BY a.cnpj_basico, a.relacionada, a.socio_comum
            ORDER BY a.confianca, indicio_sucessora DESC
        ) = 1
    )
    SELECT cnpj_basico, 0 AS grau, NULL AS relacionada, NULL AS socio_comum,
           NULL AS confianca, false AS indicio_sucessora
    FROM grau0
    UNION ALL
    SELECT * FROM grau1
    """)

    return {
        "vinculos": con.execute("SELECT count(*) FROM vinculos").fetchone()[0],
        "vinculos_alta": con.execute(
            "SELECT count(*) FROM vinculos WHERE confianca = 'alta'"
        ).fetchone()[0],
        "grau0": con.execute(
            "SELECT count(DISTINCT cnpj_basico) FROM empresas_risco WHERE grau = 0"
        ).fetchone()[0],
        "grau1": con.execute(
            "SELECT count(DISTINCT cnpj_basico) FROM empresas_risco WHERE grau = 1"
        ).fetchone()[0],
        "indicio_sucessora": con.execute(
            "SELECT count(DISTINCT cnpj_basico) FROM empresas_risco WHERE indicio_sucessora"
        ).fetchone()[0],
    }


def main() -> None:
    config = Config.carrega()
    with duckdb.connect(config.banco) as con:
        contagens = carrega_vinculos(con)
    for nome, n in contagens.items():
        print(f"  {nome}: {n}")
    print(f"✓ vinculos e empresas_risco materializados em {config.banco}")


if __name__ == "__main__":
    main()
