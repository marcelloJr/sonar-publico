from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def cliente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    banco = tmp_path / "sonar.duckdb"
    with duckdb.connect(banco) as con:
        con.execute("""
        CREATE TABLE empresas (cnpj_basico VARCHAR, razao_social VARCHAR,
            natureza_juridica VARCHAR, capital_social DECIMAL(18,2), porte VARCHAR);
        INSERT INTO empresas VALUES
            ('11111111', 'CONSTRUTORA AÇAÍ LTDA', '2062', 1000, '03'),
            ('22222222', 'SUCESSORA ENGENHARIA LTDA', '2062', 500, '01'),
            ('33333333', 'LIMPA E SEM VINCULO SA', '2054', 900, '05');

        CREATE TABLE estabelecimentos (cnpj VARCHAR, cnpj_basico VARCHAR,
            matriz_filial VARCHAR, nome_fantasia VARCHAR, situacao_cadastral VARCHAR,
            data_inicio_atividade DATE, cnae_principal VARCHAR, uf VARCHAR,
            municipio_codigo VARCHAR);
        INSERT INTO estabelecimentos VALUES
            ('11111111000195', '11111111', '1', 'AÇAÍ', '02', DATE '2010-01-01',
             '4120400', 'SC', '8105'),
            ('22222222000110', '22222222', '1', NULL, '02', DATE '2023-06-01',
             '4120400', 'SC', '8105'),
            ('33333333000155', '33333333', '1', NULL, '02', DATE '2015-01-01',
             '9999999', 'SP', '0001');

        CREATE TABLE empresas_risco (cnpj_basico VARCHAR, grau INT, relacionada VARCHAR,
            socio_comum VARCHAR, confianca VARCHAR, indicio_sucessora BOOLEAN);
        INSERT INTO empresas_risco VALUES
            ('11111111', 0, NULL, NULL, NULL, false),
            ('22222222', 1, '11111111', 'JOAO DA SILVA', 'alta', true);

        CREATE TABLE sancoes (fonte VARCHAR, categoria VARCHAR, orgao VARCHAR,
            uf_orgao VARCHAR, esfera_orgao VARCHAR, data_inicio DATE, data_fim DATE,
            vigente BOOLEAN, processo VARCHAR, cnpj_cpf VARCHAR, nome VARCHAR);
        INSERT INTO sancoes VALUES
            ('CEIS', 'Inidoneidade', 'TCU', 'DF', 'FEDERAL', DATE '2022-01-01',
             NULL, true, 'P1', '11111111000195', 'CONSTRUTORA ACAI LTDA');

        CREATE TABLE contratos (origem VARCHAR, esfera VARCHAR, numero_contrato VARCHAR,
            orgao VARCHAR, objeto VARCHAR, situacao VARCHAR, valor_final DECIMAL(18,2),
            data_inicio_vigencia DATE, data_fim_vigencia DATE, cnpj_contratado VARCHAR,
            nome_contratado VARCHAR);
        INSERT INTO contratos VALUES
            ('PORTAL', 'F', 'C-1', 'Ministério X', 'Obra', 'Ativo', 1000000,
             DATE '2025-01-01', DATE '2030-01-01', '11111111000195',
             'CONSTRUTORA ACAI LTDA'),
            ('PORTAL', 'F', 'C-2', 'Ministério Y', 'Consultoria', 'Ativo', 5000,
             DATE '2025-01-01', DATE '2026-12-01', '44444444000144',
             'SO NO CONTRATO LTDA');  -- fora do dump da Receita: ficha via fallback

        CREATE TABLE socios (cnpj_basico VARCHAR, nome_socio VARCHAR,
            cpf_mascarado VARCHAR, qualificacao VARCHAR, data_entrada DATE);
        INSERT INTO socios VALUES
            ('11111111', 'JOAO DA SILVA', '***123456**', '49', DATE '2010-01-01'),
            ('22222222', 'JOAO DA SILVA', '***123456**', '49', DATE '2023-06-01');

        CREATE TABLE vinculos (cnpj_a VARCHAR, cnpj_b VARCHAR, socio_comum VARCHAR,
            confianca VARCHAR);
        INSERT INTO vinculos VALUES ('11111111', '22222222', 'JOAO DA SILVA', 'alta');
        """)
    monkeypatch.setenv("SONAR_DB", str(banco))
    from app.main import app

    return TestClient(app)
