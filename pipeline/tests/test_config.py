from pathlib import Path

import pytest
from radar_pipeline.config import Config


def test_defaults_sem_arquivo(tmp_path: Path):
    config = Config.carrega(tmp_path / "inexistente.toml")
    assert config.esferas == ("F",)
    assert config.uf is None
    assert config.amostra is False
    assert config.banco.name == "sonar.duckdb"


def test_carrega_toml(tmp_path: Path):
    arquivo = tmp_path / "config.toml"
    arquivo.write_text(
        """
[escopo]
esferas = ["F", "M"]
uf = "SC"
codigo_municipio_ibge = 4205407

[periodo]
contratos_desde = "2025-06"

[modo]
amostra = true
"""
    )
    config = Config.carrega(arquivo)
    assert config.esferas == ("F", "M")
    assert config.uf == "SC"
    assert config.codigo_municipio_ibge == "4205407"
    assert config.contratos_desde == "2025-06"
    assert config.amostra is True


def test_esfera_invalida():
    with pytest.raises(ValueError, match="esferas inválidas"):
        Config(esferas=("F", "X"))


def test_periodo_invalido():
    with pytest.raises(ValueError, match="contratos_desde"):
        Config(contratos_desde="junho/2024")


def test_config_real_da_raiz():
    config = Config.carrega()
    assert config.esferas == ("F",)
