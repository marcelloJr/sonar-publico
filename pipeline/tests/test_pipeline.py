from pathlib import Path

import pytest
from radar_pipeline import pipeline
from radar_pipeline.config import Config


def test_roda_encadeia_etapas_na_ordem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ordem = []

    monkeypatch.setattr(pipeline, "baixa_sancoes", lambda c: ordem.append("baixa_sancoes"))
    monkeypatch.setattr(
        pipeline.sancoes, "carrega_sancoes", lambda c, con: ordem.append("sancoes") or {}
    )
    monkeypatch.setattr(
        pipeline.contratos, "baixa_compras", lambda c: ordem.append("baixa_compras")
    )
    monkeypatch.setattr(
        pipeline.contratos, "carrega_contratos", lambda c, con: ordem.append("contratos") or {}
    )
    monkeypatch.setattr(pipeline.cnpj, "baixa_cnpj", lambda c: ordem.append("baixa_cnpj"))
    monkeypatch.setattr(
        pipeline.cnpj, "carrega_cnpj", lambda c, con: ordem.append("cnpj") or {}
    )

    def vinculos_falso(con):
        ordem.append("vinculos")
        con.execute("CREATE TABLE contratos (cnpj_contratado VARCHAR, valor_final DECIMAL, "
                    "data_fim_vigencia DATE)")
        con.execute("CREATE TABLE empresas_risco (cnpj_basico VARCHAR, grau INT)")
        return {}

    monkeypatch.setattr(pipeline.vinculos, "carrega_vinculos", vinculos_falso)

    pipeline.roda(Config(dados=tmp_path))
    assert ordem == [
        "baixa_sancoes", "sancoes", "baixa_compras", "contratos",
        "baixa_cnpj", "cnpj", "vinculos",
    ]


def test_roda_sem_esfera_federal_pula_compras(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ordem = []
    monkeypatch.setattr(pipeline, "baixa_sancoes", lambda c: None)
    monkeypatch.setattr(pipeline.sancoes, "carrega_sancoes", lambda c, con: {})
    monkeypatch.setattr(
        pipeline.contratos, "baixa_compras", lambda c: ordem.append("baixa_compras")
    )
    monkeypatch.setattr(pipeline.contratos, "carrega_contratos", lambda c, con: {})
    monkeypatch.setattr(pipeline.cnpj, "baixa_cnpj", lambda c: None)
    monkeypatch.setattr(pipeline.cnpj, "carrega_cnpj", lambda c, con: {})

    def vinculos_falso(con):
        con.execute("CREATE TABLE contratos (cnpj_contratado VARCHAR, valor_final DECIMAL, "
                    "data_fim_vigencia DATE)")
        con.execute("CREATE TABLE empresas_risco (cnpj_basico VARCHAR, grau INT)")
        return {}

    monkeypatch.setattr(pipeline.vinculos, "carrega_vinculos", vinculos_falso)

    pipeline.roda(Config(dados=tmp_path, esferas=("M",)))
    assert "baixa_compras" not in ordem
