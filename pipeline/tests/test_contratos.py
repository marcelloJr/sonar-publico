import zipfile
from datetime import date
from pathlib import Path

import duckdb
import pytest
from radar_pipeline.config import Config
from radar_pipeline.contratos import carrega_contratos, meses_desde

CABECALHO_COMPRAS = [
    "Número do Contrato", "Objeto", "Fundamento Legal", "Modalidade Compra",
    "Situação Contrato", "Código Órgão Superior", "Nome Órgão Superior",
    "Código Órgão", "Nome Órgão", "Código UG", "Nome UG",
    "Data Assinatura Contrato", "Data Publicação DOU", "Data Início Vigência",
    "Data Fim Vigência", "Código Contratado", "Nome Contratado",
    "Valor Inicial Compra", "Valor Final Compra", "Número Licitação",
    "Código UG Licitação", "Nome UG Licitação",
    "Código Modalidade Compra Licitação", "Modalidade Compra Licitação",
]


def _zip_compras(pasta: Path, competencia: str, linhas: list[dict]):
    pasta.mkdir(parents=True, exist_ok=True)
    corpo = [";".join(f'"{c}"' for c in CABECALHO_COMPRAS)]
    for linha in linhas:
        corpo.append(";".join(f'"{linha.get(c, "")}"' for c in CABECALHO_COMPRAS))
    with zipfile.ZipFile(pasta / f"{competencia}_compras.zip", "w") as z:
        z.writestr(f"{competencia}_Compras.csv", "\r\n".join(corpo).encode("iso-8859-1"))


def _linha(numero="C-1", cnpj="12.345.678/0001-95", valor="1.000,50", **extra):
    base = {
        "Número do Contrato": numero,
        "Objeto": "Serviços de TI",
        "Situação Contrato": "Ativo",
        "Código Órgão": "26000",
        "Nome Órgão": "Ministério X",
        "Nome Órgão Superior": "Ministério X",
        "Código UG": "110001",
        "Nome UG": "UG Central",
        "Data Assinatura Contrato": "15/03/2025",
        "Data Início Vigência": "01/04/2025",
        "Data Fim Vigência": "31/03/2026",
        "Código Contratado": cnpj,
        "Nome Contratado": "Fornecedora Ção Ltda",
        "Valor Inicial Compra": valor,
        "Valor Final Compra": valor,
        "Modalidade Compra": "Pregão",
    }
    base.update(extra)
    return base


def test_meses_desde():
    assert meses_desde("2025-11", ate=date(2026, 2, 15)) == [
        (2025, 11), (2025, 12), (2026, 1), (2026, 2),
    ]


def _pncp_falso(registros):
    def busca(inicio: date, fim: date):
        return iter(
            r for r in registros if inicio <= date.fromisoformat(r["dataAssinatura"]) <= fim
        )

    return busca


REGISTRO_PNCP = {
    "numeroControlePNCP": "80881915000192-2-000044/2026",
    "orgaoEntidade": {"cnpj": "80881915000192", "razaoSocial": "MUNICIPIO DE LINDOESTE",
                      "esferaId": "M", "poderId": "E"},
    "unidadeOrgao": {"codigoUnidade": "2", "nomeUnidade": "Prefeitura",
                     "ufSigla": "PR", "codigoIbge": "4113452"},
    "niFornecedor": "05333750000360",
    "nomeRazaoSocialFornecedor": "Fornecedor Municipal ME",
    "objetoContrato": "Merenda escolar",
    "tipoContrato": {"id": 1, "nome": "Contrato (termo inicial)"},
    "valorInicial": 1000.0,
    "valorGlobal": 1200.0,
    "dataAssinatura": "2026-06-19",
    "dataVigenciaInicio": "2026-06-19",
    "dataVigenciaFim": "2027-06-18",
}
REGISTRO_PNCP_ESTADUAL = {
    **REGISTRO_PNCP,
    "numeroControlePNCP": "11111111000111-2-000001/2026",
    "orgaoEntidade": {"cnpj": "11111111000111", "razaoSocial": "ESTADO DE SC",
                      "esferaId": "E", "poderId": "E"},
    "unidadeOrgao": {"codigoUnidade": "9", "nomeUnidade": "Secretaria",
                     "ufSigla": "SC", "codigoIbge": "4205407"},
}


def test_carrega_portal(tmp_path: Path):
    config = Config(dados=tmp_path, contratos_desde="2025-03")
    _zip_compras(config.raw / "compras", "202502", [_linha(numero="ANTIGO")])  # antes do desde
    _zip_compras(config.raw / "compras", "202503", [
        _linha(),
        _linha(numero="C-2", cnpj="99.888.777/0001-10", valor="2.500.000,00"),
    ])
    # C-1 republicado no mês seguinte com valor atualizado -> vence o mais recente
    _zip_compras(config.raw / "compras", "202504", [_linha(valor="9.999,99")])

    with duckdb.connect() as con:
        contagens = carrega_contratos(config, con, busca_pncp=_pncp_falso([]))
        assert contagens == {"PORTAL": 2}
        c1 = con.execute(
            "SELECT competencia, valor_final, cnpj_contratado, nome_contratado_normalizado "
            "FROM contratos WHERE numero_contrato = 'C-1'"
        ).fetchone()
        assert (c1[0], float(c1[1]), c1[2], c1[3]) == (
            "202504", 9999.99, "12345678000195", "FORNECEDORA CAO LTDA",
        )
        c2 = con.execute(
            "SELECT valor_final, data_assinatura FROM contratos WHERE numero_contrato = 'C-2'"
        ).fetchone()
        assert float(c2[0]) == 2500000.00
        assert c2[1] == date(2025, 3, 15)


def test_carrega_pncp_filtra_esfera_e_uf(tmp_path: Path):
    config = Config(dados=tmp_path, esferas=("M",), uf="PR", contratos_desde="2026-06")
    with duckdb.connect() as con:
        contagens = carrega_contratos(
            config, con, busca_pncp=_pncp_falso([REGISTRO_PNCP, REGISTRO_PNCP_ESTADUAL])
        )
        assert contagens == {"PNCP": 1}
        linha = con.execute(
            "SELECT esfera, uf, cnpj_contratado, nome_contratado_normalizado, valor_final "
            "FROM contratos"
        ).fetchone()
        assert linha == ("M", "PR", "05333750000360", "FORNECEDOR MUNICIPAL ME", 1200.00)


def test_carrega_federal_sem_zip_falha(tmp_path: Path):
    config = Config(dados=tmp_path)
    with duckdb.connect() as con, pytest.raises(FileNotFoundError, match="compras"):
        carrega_contratos(config, con, busca_pncp=_pncp_falso([]))
