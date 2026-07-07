"""Download do dump CNPJ da Receita e filtragem do universo (P1.2 + P1.5).

O dump completo tem ~60M empresas (~85 GB descompactado). A filtragem reduz
ao universo relevante ANTES de materializar qualquer tabela grande:

1. ``universo_base``: raízes (cnpj_basico, 8 dígitos) de empresas sancionadas
   ou com contrato carregado;
2. ``socios_todos``: todas as partes de Socios*.zip (≈25M linhas — DuckDB
   aguenta; cada ZIP é extraído, lido e apagado do staging em sequência);
3. vizinhas: empresas que compartilham chave de sócio (nome normalizado +
   fragmento do CPF, SPEC §4.3) com alguma sancionada;
4. ``universo`` = base ∪ vizinhas; ``socios``/``empresas``/``estabelecimentos``
   são materializadas já filtradas pelo universo.

Uso: ``uv run python -m radar_pipeline.cnpj`` (respeita config.amostra:
modo amostra processa só a parte 0 de cada arquivo — teste de laptop).
"""

from datetime import date
from pathlib import Path

import duckdb
import httpx

from radar_pipeline import fontes
from radar_pipeline.config import Config

PREFIXOS = ("Socios", "Empresas", "Estabelecimentos")

_COLUNAS_SOCIOS = [
    "cnpj_basico", "identificador_socio", "nome_socio", "cnpj_cpf_socio",
    "qualificacao_socio", "data_entrada", "pais", "representante_legal",
    "nome_representante", "qualificacao_representante", "faixa_etaria",
]
_COLUNAS_EMPRESAS = [
    "cnpj_basico", "razao_social", "natureza_juridica",
    "qualificacao_responsavel", "capital_social", "porte", "ente_federativo",
]
_COLUNAS_ESTABELECIMENTOS = [
    "cnpj_basico", "cnpj_ordem", "cnpj_dv", "matriz_filial", "nome_fantasia",
    "situacao_cadastral", "data_situacao_cadastral", "motivo_situacao",
    "cidade_exterior", "pais", "data_inicio_atividade", "cnae_principal",
    "cnae_secundaria", "tipo_logradouro", "logradouro", "numero",
    "complemento", "bairro", "cep", "uf", "municipio", "ddd1", "telefone1",
    "ddd2", "telefone2", "ddd_fax", "fax", "email", "situacao_especial",
    "data_situacao_especial",
]


def mes_cnpj_disponivel(a_partir: date | None = None, janela_meses: int = 4) -> tuple[int, int]:
    """Mês mais recente com dump publicado no share da Receita."""
    dia = a_partir or date.today()
    ano, mes = dia.year, dia.month
    for _ in range(janela_meses):
        resposta = httpx.head(
            fontes.url_cnpj(ano, mes, "Socios0.zip"),
            auth=(fontes.RECEITA_SHARE_ID, ""),
            timeout=60,
        )
        if resposta.status_code == 200:
            return ano, mes
        ano, mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    raise RuntimeError(f"nenhum dump CNPJ encontrado nos últimos {janela_meses} meses")


def baixa_cnpj(config: Config) -> Path:
    """Baixa as partes do dump do mês mais recente; retorna a pasta local."""
    ano, mes = mes_cnpj_disponivel()
    pasta = config.raw / "cnpj" / f"{ano:04d}-{mes:02d}"
    partes = [0] if config.amostra else range(10)
    for prefixo in PREFIXOS:
        for i in partes:
            arquivo = f"{prefixo}{i}.zip"
            destino = pasta / arquivo
            if destino.exists():
                continue
            print(f"↓ cnpj/{ano:04d}-{mes:02d}/{arquivo}")
            fontes.baixar(
                fontes.url_cnpj(ano, mes, arquivo), destino,
                auth=(fontes.RECEITA_SHARE_ID, ""),
            )
    return pasta


def _le_partes(
    con: duckdb.DuckDBPyConnection,
    pasta: Path,
    prefixo: str,
    colunas: list[str],
    staging: Path,
    sql_insert: str,
) -> None:
    """Extrai cada parte, roda o INSERT (com {csv} no FROM) e apaga o CSV."""
    import zipfile

    from radar_pipeline.staging import transcodifica_utf8

    staging.mkdir(parents=True, exist_ok=True)
    nomes = ", ".join(f"'{c}'" for c in colunas)
    for zip_path in sorted(pasta.glob(f"{prefixo}*.zip")):
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                extraido = Path(z.extract(info, staging))
                # CP1252 primeiro (aspas tipográficas em endereços/e-mails
                # derrubam o leitor latin-1 do DuckDB); se nem latin-1 servir,
                # transcodifica em Python linha a linha e lê como UTF-8
                for encoding in ("CP1252", "latin-1", None):
                    if encoding is None:
                        transcodifica_utf8(extraido)
                    clausula = f"encoding='{encoding}', " if encoding else ""
                    leitura = (
                        f"read_csv('{extraido}', delim=';', quote='\"', header=false, "
                        f"{clausula}all_varchar=true, names=[{nomes}])"
                    )
                    try:
                        con.execute(sql_insert.format(csv=leitura))
                        break
                    except duckdb.InvalidInputException:
                        if encoding is None:
                            raise
                extraido.unlink()


def carrega_cnpj(config: Config, con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Materializa universo, socios, empresas e estabelecimentos filtrados."""
    pasta = sorted((config.raw / "cnpj").glob("*"))[-1]
    staging = config.staging / "cnpj"

    # 1. raízes de interesse direto (8 primeiros dígitos de CNPJs de 14)
    con.execute("""
    CREATE OR REPLACE TABLE universo_base AS
    SELECT DISTINCT cnpj_basico FROM (
        SELECT cnpj_cpf[:8] AS cnpj_basico FROM sancoes WHERE length(cnpj_cpf) = 14
        UNION
        SELECT cnpj_contratado[:8] FROM contratos WHERE length(cnpj_contratado) = 14
    )
    """)

    # 2. todos os sócios (extrai/lê/apaga parte a parte), com chave de matching
    con.execute("""
    CREATE OR REPLACE TABLE socios_todos (
        cnpj_basico VARCHAR, identificador_socio VARCHAR, nome_socio VARCHAR,
        cpf_mascarado VARCHAR, qualificacao VARCHAR, data_entrada DATE,
        chave_socio VARCHAR
    )
    """)
    _le_partes(
        con, pasta, "Socios", _COLUNAS_SOCIOS, staging,
        """
        INSERT INTO socios_todos
        SELECT
            cnpj_basico,
            identificador_socio,
            regexp_replace(trim(upper(strip_accents(nome_socio))), '\\s+', ' ', 'g'),
            cnpj_cpf_socio,
            qualificacao_socio,
            try_strptime(nullif(trim(data_entrada), ''), '%Y%m%d')::DATE,
            regexp_replace(trim(upper(strip_accents(nome_socio))), '\\s+', ' ', 'g')
                || '|' || regexp_replace(coalesce(cnpj_cpf_socio, ''), '[^0-9]', '', 'g')
        FROM {csv}
        WHERE nullif(trim(nome_socio), '') IS NOT NULL
        """,
    )

    # 3. vizinhas: compartilham chave de sócio com alguma SANCIONADA
    #    (chaves de PF exigem nome + fragmento de CPF não-zerado; SPEC §4.3)
    con.execute("""
    CREATE OR REPLACE TABLE universo AS
    WITH sancionadas AS (
        SELECT DISTINCT cnpj_cpf[:8] AS cnpj_basico
        FROM sancoes WHERE length(cnpj_cpf) = 14
    ),
    chaves_sancionadas AS (
        SELECT DISTINCT s.chave_socio
        FROM socios_todos s
        JOIN sancionadas x USING (cnpj_basico)
        WHERE s.chave_socio NOT LIKE '%|'          -- sem fragmento de CPF
          AND s.chave_socio NOT LIKE '%|000000'
    ),
    vizinhas AS (
        SELECT DISTINCT s.cnpj_basico
        FROM socios_todos s
        JOIN chaves_sancionadas c USING (chave_socio)
    )
    SELECT cnpj_basico FROM universo_base
    UNION
    SELECT cnpj_basico FROM vizinhas
    """)

    # 4. socios do universo (encolhe as ~25M linhas para o relevante)
    con.execute("""
    CREATE OR REPLACE TABLE socios AS
    SELECT * FROM socios_todos WHERE cnpj_basico IN (SELECT cnpj_basico FROM universo)
    """)
    con.execute("DROP TABLE socios_todos")

    # 5. empresas e estabelecimentos, já filtrados
    con.execute("""
    CREATE OR REPLACE TABLE empresas (
        cnpj_basico VARCHAR, razao_social VARCHAR, natureza_juridica VARCHAR,
        capital_social DECIMAL(18,2), porte VARCHAR
    )
    """)
    _le_partes(
        con, pasta, "Empresas", _COLUNAS_EMPRESAS, staging,
        """
        INSERT INTO empresas
        SELECT cnpj_basico, razao_social, natureza_juridica,
               try_cast(replace(capital_social, ',', '.') AS DECIMAL(18,2)), porte
        FROM {csv}
        WHERE cnpj_basico IN (SELECT cnpj_basico FROM universo)
        """,
    )
    con.execute("""
    CREATE OR REPLACE TABLE estabelecimentos (
        cnpj VARCHAR, cnpj_basico VARCHAR, matriz_filial VARCHAR,
        nome_fantasia VARCHAR, situacao_cadastral VARCHAR,
        data_inicio_atividade DATE, cnae_principal VARCHAR,
        uf VARCHAR, municipio_codigo VARCHAR
    )
    """)
    _le_partes(
        con, pasta, "Estabelecimentos", _COLUNAS_ESTABELECIMENTOS, staging,
        """
        INSERT INTO estabelecimentos
        SELECT cnpj_basico || cnpj_ordem || cnpj_dv, cnpj_basico, matriz_filial,
               nome_fantasia, situacao_cadastral,
               try_strptime(nullif(trim(data_inicio_atividade), ''), '%Y%m%d')::DATE,
               cnae_principal, uf, municipio
        FROM {csv}
        WHERE cnpj_basico IN (SELECT cnpj_basico FROM universo)
        """,
    )

    return {
        tabela: con.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]
        for tabela in ("universo_base", "universo", "socios", "empresas", "estabelecimentos")
    }


def main() -> None:
    import sys
    from dataclasses import replace

    config = Config.carrega()
    if "--amostra" in sys.argv:
        config = replace(config, amostra=True)
    baixa_cnpj(config)
    with duckdb.connect(config.banco) as con:
        contagens = carrega_cnpj(config, con)
    for tabela, n in contagens.items():
        print(f"  {tabela}: {n}")
    print(f"✓ universo CNPJ materializado em {config.banco}")


if __name__ == "__main__":
    main()
