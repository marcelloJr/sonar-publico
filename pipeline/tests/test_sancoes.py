import zipfile
from pathlib import Path

import duckdb
import pytest
from radar_pipeline.config import Config
from radar_pipeline.sancoes import carrega_sancoes

CABECALHO_CEIS = [
    "CADASTRO", "CÓDIGO DA SANÇÃO", "TIPO DE PESSOA", "CPF OU CNPJ DO SANCIONADO",
    "NOME DO SANCIONADO", "NOME INFORMADO PELO ÓRGÃO SANCIONADOR",
    "RAZÃO SOCIAL - CADASTRO RECEITA", "NOME FANTASIA - CADASTRO RECEITA",
    "NÚMERO DO PROCESSO", "CATEGORIA DA SANÇÃO", "DATA INÍCIO SANÇÃO",
    "DATA FINAL SANÇÃO", "DATA PUBLICAÇÃO", "PUBLICAÇÃO",
    "DETALHAMENTO DO MEIO DE PUBLICAÇÃO", "DATA DO TRÂNSITO EM JULGADO",
    "ABRAGÊNCIA DA SANÇÃO", "ÓRGÃO SANCIONADOR", "UF ÓRGÃO SANCIONADOR",
    "ESFERA ÓRGÃO SANCIONADOR", "FUNDAMENTAÇÃO LEGAL", "DATA ORIGEM INFORMAÇÃO",
    "ORIGEM INFORMAÇÕES", "OBSERVAÇÕES",
]
CABECALHO_CNEP = CABECALHO_CEIS[:10] + ["VALOR DA MULTA"] + CABECALHO_CEIS[10:]
CABECALHO_CEPIM = [
    "CNPJ ENTIDADE", "NOME ENTIDADE", "NÚMERO CONVÊNIO", "ÓRGÃO CONCEDENTE",
    "MOTIVO DO IMPEDIMENTO",
]
# cabeçalho real vem em cp1252 com en dash (byte 0x96) nos nomes compostos
CABECALHO_ACORDOS = [
    "ID DO ACORDO", "CNPJ DO SANCIONADO", "RAZÃO SOCIAL – CADASTRO RECEITA",
    "NOME FANTASIA – CADASTRO RECEITA", "DATA DE INÍCIO DO ACORDO",
    "DATA DE FIM DO ACORDO", "SITUAÇÃO DO ACORDO DE LENIÊNICA",
    "DATA DA INFORMAÇÃO", "NÚMERO DO PROCESSO", "TERMOS DO ACORDO",
    "ÓRGÃO SANCIONADOR",
]


def _grava_zip(
    pasta: Path,
    nome_zip: str,
    nome_csv: str,
    cabecalho: list[str],
    linhas: list[dict],
    encoding: str = "iso-8859-1",
):
    pasta.mkdir(parents=True, exist_ok=True)
    corpo = [";".join(f'"{c}"' for c in cabecalho)]
    for linha in linhas:
        corpo.append(";".join(f'"{linha.get(c, "")}"' for c in cabecalho))
    with zipfile.ZipFile(pasta / nome_zip, "w") as z:
        z.writestr(nome_csv, "\r\n".join(corpo).encode(encoding))


@pytest.fixture
def config(tmp_path: Path) -> Config:
    cfg = Config(dados=tmp_path)
    pasta = cfg.raw / "sancoes"
    _grava_zip(pasta, "20260101_ceis.zip", "20260101_CEIS.csv", CABECALHO_CEIS, [
        {
            "TIPO DE PESSOA": "Jurídica",
            "CPF OU CNPJ DO SANCIONADO": "12.345.678/0001-95",
            "NOME DO SANCIONADO": "informado",
            "RAZÃO SOCIAL - CADASTRO RECEITA": "Construções Açaí Ltda",
            "NÚMERO DO PROCESSO": "PROC-1",
            "CATEGORIA DA SANÇÃO": "Inidoneidade",
            "DATA INÍCIO SANÇÃO": "01/01/2020",
            "DATA FINAL SANÇÃO": "",  # sem fim -> vigente
            "ÓRGÃO SANCIONADOR": "TCU",
            "UF ÓRGÃO SANCIONADOR": "DF",
            "ESFERA ÓRGÃO SANCIONADOR": "FEDERAL",
        },
        {  # duplicata exata da anterior -> dedup
            "TIPO DE PESSOA": "Jurídica",
            "CPF OU CNPJ DO SANCIONADO": "12.345.678/0001-95",
            "RAZÃO SOCIAL - CADASTRO RECEITA": "Construções Açaí Ltda",
            "NÚMERO DO PROCESSO": "PROC-1",
            "CATEGORIA DA SANÇÃO": "Inidoneidade",
            "DATA INÍCIO SANÇÃO": "01/01/2020",
            "ÓRGÃO SANCIONADOR": "TCU",
        },
        {  # sanção expirada
            "TIPO DE PESSOA": "Jurídica",
            "CPF OU CNPJ DO SANCIONADO": "99.888.777/0001-10",
            "NOME DO SANCIONADO": "Empresa Expirada SA",
            "NÚMERO DO PROCESSO": "PROC-2",
            "CATEGORIA DA SANÇÃO": "Suspensão",
            "DATA INÍCIO SANÇÃO": "01/01/2020",
            "DATA FINAL SANÇÃO": "31/12/2021",
            "ESFERA ÓRGÃO SANCIONADOR": "ESTADUAL",
        },
    ])
    _grava_zip(pasta, "20260101_cnep.zip", "20260101_CNEP.csv", CABECALHO_CNEP, [
        {
            "TIPO DE PESSOA": "Jurídica",
            "CPF OU CNPJ DO SANCIONADO": "11.222.333/0001-44",
            "NOME DO SANCIONADO": "Multada SA",
            "NÚMERO DO PROCESSO": "PROC-3",
            "CATEGORIA DA SANÇÃO": "Multa",
            "VALOR DA MULTA": "1.234.567,89",
            "DATA INÍCIO SANÇÃO": "01/06/2025",
            "DATA FINAL SANÇÃO": "01/06/2030",
        },
    ])
    _grava_zip(pasta, "20260101_cepim.zip", "20260101_CEPIM.csv", CABECALHO_CEPIM, [
        {
            "CNPJ ENTIDADE": "55.666.777/0001-88",
            "NOME ENTIDADE": "ONG Impedida",
            "NÚMERO CONVÊNIO": "123",
            "ÓRGÃO CONCEDENTE": "Ministério X",
            "MOTIVO DO IMPEDIMENTO": "Prestação de contas rejeitada",
        },
    ])
    _grava_zip(
        pasta, "20260101_acordos-leniencia.zip", "20260101_Acordos.csv", CABECALHO_ACORDOS, [
            {
                "ID DO ACORDO": "7",
                "CNPJ DO SANCIONADO": "77.888.999/0001-00",
                "RAZÃO SOCIAL – CADASTRO RECEITA": "Leniente SA",
                "DATA DE INÍCIO DO ACORDO": "01/01/2024",
                "DATA DE FIM DO ACORDO": "01/01/2034",
                "SITUAÇÃO DO ACORDO DE LENIÊNICA": "Em cumprimento",
                "NÚMERO DO PROCESSO": "PROC-4",
                "ÓRGÃO SANCIONADOR": "CGU",
            },
        ],
        encoding="cp1252",  # como o arquivo real (en dash = 0x96)
    )
    return cfg


def test_carrega_sancoes(config: Config):
    with duckdb.connect() as con:
        contagens = carrega_sancoes(config, con)
        assert contagens == {"CEIS": 2, "CNEP": 1, "CEPIM": 1, "LENIENCIA": 1}

        linhas = con.execute(
            "SELECT fonte, cnpj_cpf, nome_normalizado, vigente FROM sancoes ORDER BY 1, 2"
        ).fetchall()
        assert ("CEIS", "12345678000195", "CONSTRUCOES ACAI LTDA", True) in linhas
        assert ("CEIS", "99888777000110", "EMPRESA EXPIRADA SA", False) in linhas
        assert ("CEPIM", "55666777000188", "ONG IMPEDIDA", True) in linhas

        multa = con.execute(
            "SELECT valor_multa FROM sancoes WHERE fonte = 'CNEP'"
        ).fetchone()[0]
        assert float(multa) == 1234567.89

        categoria = con.execute(
            "SELECT categoria FROM sancoes WHERE fonte = 'LENIENCIA'"
        ).fetchone()[0]
        assert categoria == "Acordo de leniência (Em cumprimento)"


def test_falha_sem_arquivos(tmp_path: Path):
    with duckdb.connect() as con, pytest.raises(FileNotFoundError, match="amostras"):
        carrega_sancoes(Config(dados=tmp_path), con)
