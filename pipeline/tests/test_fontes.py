from datetime import date

import pytest
from radar_pipeline import fontes


def test_url_sancao():
    assert (
        fontes.url_sancao("ceis", date(2026, 7, 6))
        == "https://portaldatransparencia.gov.br/download-de-dados/ceis/20260706"
    )


def test_url_sancao_base_invalida():
    with pytest.raises(ValueError):
        fontes.url_sancao("compras", date(2026, 7, 6))


def test_url_mensal():
    assert (
        fontes.url_mensal("compras", 2026, 5)
        == "https://portaldatransparencia.gov.br/download-de-dados/compras/202605"
    )


def test_url_cnpj():
    assert (
        fontes.url_cnpj(2026, 6, "Socios0.zip")
        == "https://arquivos.receitafederal.gov.br/public.php/webdav/2026-06/Socios0.zip"
    )
