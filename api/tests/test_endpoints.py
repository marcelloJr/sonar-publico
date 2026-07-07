def test_busca_por_nome(cliente):
    corpo = cliente.get("/busca", params={"q": "acai"}).json()
    assert len(corpo["resultados"]) == 1
    r = corpo["resultados"][0]
    assert r["cnpj_basico"] == "11111111"
    assert r["grau"] == 0


def test_busca_por_cnpj_com_pontuacao(cliente):
    corpo = cliente.get("/busca", params={"q": "22.222.222/0001-10"}).json()
    assert corpo["resultados"][0]["razao_social"] == "SUCESSORA ENGENHARIA LTDA"
    assert corpo["resultados"][0]["indicio_sucessora"] is True


def test_busca_curta_rejeitada(cliente):
    assert cliente.get("/busca", params={"q": "ab"}).status_code == 422


def test_ficha_completa(cliente):
    corpo = cliente.get("/empresas/11111111000195").json()
    assert corpo["cadastro"]["razao_social"] == "CONSTRUTORA AÇAÍ LTDA"
    assert corpo["risco"][0]["grau"] == 0
    assert corpo["sancoes"][0]["vigente"] is True
    assert corpo["contratos"][0]["numero_contrato"] == "C-1"
    assert corpo["socios"][0]["nome_socio"] == "JOAO DA SILVA"


def test_ficha_grau1_com_sucessora(cliente):
    corpo = cliente.get("/empresas/22222222000110").json()
    risco = corpo["risco"][0]
    assert risco["grau"] == 1
    assert risco["relacionada"] == "11111111"
    assert risco["indicio_sucessora"] is True
    assert corpo["sancoes"] == []


def test_ficha_fora_do_universo(cliente):
    resposta = cliente.get("/empresas/99999999000199")
    assert resposta.status_code == 404
    assert "universo" in resposta.json()["detail"]


def test_ficha_sem_nome_algum_mas_no_universo(cliente):
    # nó do grafo sem nome em nenhuma base: a ficha existe mesmo assim
    corpo = cliente.get("/empresas/66666666000166").json()
    assert corpo["cadastro"]["razao_social"] is None
    assert corpo["cadastro"]["cadastro_receita_disponivel"] is False
    assert corpo["socios"][0]["nome_socio"] == "SOCIO SEM EMPRESA NOMEADA"


def test_ficha_sem_cadastro_receita_usa_fallback(cliente):
    corpo = cliente.get("/empresas/44444444000144").json()
    assert corpo["cadastro"]["razao_social"] == "SO NO CONTRATO LTDA"
    assert corpo["cadastro"]["cadastro_receita_disponivel"] is False
    assert corpo["contratos"][0]["numero_contrato"] == "C-2"


def test_grafo(cliente):
    corpo = cliente.get("/empresas/11111111000195/grafo").json()
    assert corpo["centro"] == "11111111"
    assert {n["id"] for n in corpo["nos"]} == {"11111111", "22222222"}
    assert corpo["arestas"][0]["socio_comum"] == "JOAO DA SILVA"


def test_orgaos_ordenados_por_alerta(cliente):
    corpo = cliente.get("/orgaos").json()
    assert corpo["orgaos"][0]["orgao"] == "Ministério X"  # tem contrato de sancionada
    assert corpo["orgaos"][0]["contratos_sob_alerta"] == 1
    assert float(corpo["orgaos"][0]["valor_sob_alerta"]) == 1000000.0
    assert corpo["orgaos"][1]["contratos_sob_alerta"] == 0


def test_fornecedores_do_orgao(cliente):
    corpo = cliente.get("/orgaos/26000/fornecedores").json()
    assert corpo["orgao"] == "Ministério X"
    f = corpo["fornecedores"][0]
    assert f["nome"] == "CONSTRUTORA ACAI LTDA"
    assert f["grau"] == 0
    assert f["contratos_vigentes"] == 1


def test_fornecedores_filtrados_por_grau(cliente):
    corpo = cliente.get("/orgaos/27000/fornecedores", params={"grau": 0}).json()
    assert corpo["fornecedores"] == []  # fornecedor do Y não tem sanção


def test_orgao_inexistente(cliente):
    assert cliente.get("/orgaos/99999/fornecedores").status_code == 404


def test_estatisticas(cliente):
    corpo = cliente.get("/estatisticas").json()
    assert corpo["sancionadas_vigentes"] == 1
    assert corpo["empresas_grau1"] == 1
    assert corpo["candidatas_sucessora"] == 1
    assert corpo["valor_sob_alerta"] == 1000000.0


def test_banco_ausente_responde_503(cliente, monkeypatch):
    monkeypatch.setenv("SONAR_DB", "/nao/existe.duckdb")
    assert cliente.get("/estatisticas").status_code == 503
