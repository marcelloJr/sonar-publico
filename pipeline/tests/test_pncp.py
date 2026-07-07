import json
from datetime import date

import httpx
import pytest
from radar_pipeline import fontes


def _transporte(respostas: list[httpx.Response]):
    fila = iter(respostas)

    def handler(request: httpx.Request) -> httpx.Response:
        resposta = next(fila)
        resposta._request = request
        return resposta

    return httpx.MockTransport(handler)


def _pagina(registros: list[dict], total_paginas: int) -> httpx.Response:
    return httpx.Response(
        200, content=json.dumps({"data": registros, "totalPaginas": total_paginas})
    )


def test_consulta_pncp_pagina_ate_o_fim(monkeypatch):
    chamadas = []
    respostas = iter([_pagina([{"id": 1}, {"id": 2}], 2), _pagina([{"id": 3}], 2)])

    def get_falso(url, params=None, **kwargs):
        chamadas.append(params)
        resposta = next(respostas)
        resposta._request = httpx.Request("GET", url)
        return resposta

    monkeypatch.setattr(fontes.httpx, "get", get_falso)
    registros = list(fontes.consulta_pncp("/contratos"))
    assert [r["id"] for r in registros] == [1, 2, 3]
    assert [c["pagina"] for c in chamadas] == [1, 2]


def test_consulta_pncp_backoff_em_429(monkeypatch):
    respostas = iter([httpx.Response(429), _pagina([{"id": 1}], 1)])
    esperas = []

    def get_falso(url, params=None, **kwargs):
        resposta = next(respostas)
        resposta._request = httpx.Request("GET", url)
        return resposta

    monkeypatch.setattr(fontes.httpx, "get", get_falso)
    monkeypatch.setattr(fontes.time, "sleep", esperas.append)
    assert [r["id"] for r in fontes.consulta_pncp("/contratos")] == [1]
    assert esperas == [5]


def test_consulta_pncp_vazio_204(monkeypatch):
    def get_falso(url, params=None, **kwargs):
        resposta = httpx.Response(204)
        resposta._request = httpx.Request("GET", url)
        return resposta

    monkeypatch.setattr(fontes.httpx, "get", get_falso)
    assert list(fontes.consulta_pncp("/contratos")) == []


def test_contratacoes_pncp_modalidade_invalida():
    with pytest.raises(ValueError):
        next(fontes.contratacoes_pncp(date(2026, 7, 1), date(2026, 7, 6), 99))
