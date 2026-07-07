import zipfile
from pathlib import Path

import duckdb
import pytest
from radar_pipeline.cnpj import carrega_cnpj
from radar_pipeline.config import Config

MES = "2026-06"


def _zip_cnpj(pasta: Path, nome_zip: str, nome_interno: str, linhas: list[list[str]]):
    pasta.mkdir(parents=True, exist_ok=True)
    corpo = "\n".join(";".join(f'"{campo}"' for campo in linha) for linha in linhas)
    with zipfile.ZipFile(pasta / nome_zip, "w") as z:
        z.writestr(nome_interno, corpo.encode("iso-8859-1"))


def _socio(raiz, nome, cpf, qualificacao="49", entrada="20200101"):
    return [raiz, "2", nome, cpf, qualificacao, entrada, "", "***000000**", "", "00", "6"]


def _empresa(raiz, razao):
    return [raiz, razao, "2062", "49", "1000,00", "03", ""]


def _estabelecimento(raiz, ordem="0001", dv="95", situacao="02", uf="SC", municipio="8105"):
    linha = [raiz, ordem, dv, "1", "FANTASIA", situacao, "20230101", "0", "", "",
             "20230101", "4120400", "", "RUA", "X", "1", "", "CENTRO", "88000000",
             uf, municipio, "48", "999", "", "", "", "", "a@b.c", "", ""]
    assert len(linha) == 30
    return linha


@pytest.fixture
def config(tmp_path: Path) -> Config:
    cfg = Config(dados=tmp_path, amostra=True)
    pasta = cfg.raw / "cnpj" / MES
    _zip_cnpj(pasta, "Socios0.zip", "K1.SOCIOCSV", [
        _socio("12345678", "JOÃO DA SILVA", "***123456**"),      # sócio da SANCIONADA
        _socio("12345678", "PADRAO ZERADO", "***000000**"),      # CPF zerado: não gera chave
        _socio("55666777", "Joao  da Silva", "***123456**", "22", "20230501"),  # VIZINHA
        _socio("22222222", "PADRAO ZERADO", "***000000**"),      # zerado ≠ vizinha
        _socio("11111111", "MARIA OUTRA", "***654321**"),        # irrelevante
        _socio("99888777", "SOCIA DA CONTRATADA", "***777777**"),
    ])
    _zip_cnpj(pasta, "Empresas0.zip", "K1.EMPRECSV", [
        _empresa("12345678", "SANCIONADA LTDA"),
        _empresa("55666777", "VIZINHA LTDA"),
        _empresa("11111111", "IRRELEVANTE LTDA"),
        _empresa("22222222", "ZERADA LTDA"),
        _empresa("99888777", "CONTRATADA SA"),
    ])
    _zip_cnpj(pasta, "Estabelecimentos0.zip", "K1.ESTABELE", [
        _estabelecimento("12345678"),
        _estabelecimento("55666777", uf="PR"),
        _estabelecimento("11111111"),
        _estabelecimento("99888777"),
    ])
    return cfg


def test_carrega_cnpj_filtra_universo(config: Config):
    with duckdb.connect() as con:
        con.execute("CREATE TABLE sancoes (cnpj_cpf VARCHAR, vigente BOOLEAN)")
        con.execute("INSERT INTO sancoes VALUES ('12345678000195', true)")
        con.execute("CREATE TABLE contratos (cnpj_contratado VARCHAR)")
        con.execute("INSERT INTO contratos VALUES ('99888777000110')")

        contagens = carrega_cnpj(config, con)

        universo = {
            r[0] for r in con.execute("SELECT cnpj_basico FROM universo").fetchall()
        }
        # sancionada + contratada + vizinha; NUNCA a irrelevante nem a do CPF zerado
        assert universo == {"12345678", "55666777", "99888777"}
        assert contagens["universo_base"] == 2
        assert contagens["universo"] == 3
        assert contagens["empresas"] == 3
        assert contagens["estabelecimentos"] == 3

        # nome do sócio normalizado e chave composta (SPEC §4.3)
        chaves = dict(con.execute(
            "SELECT cnpj_basico, chave_socio FROM socios WHERE chave_socio LIKE 'JOAO%'"
        ).fetchall())
        assert chaves["12345678"] == "JOAO DA SILVA|123456"
        assert chaves["55666777"] == "JOAO DA SILVA|123456"

        # cnpj completo composto no estabelecimento
        cnpj14 = con.execute(
            "SELECT cnpj FROM estabelecimentos WHERE cnpj_basico = '12345678'"
        ).fetchone()[0]
        assert cnpj14 == "12345678000195"
