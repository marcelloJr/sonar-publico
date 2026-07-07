import duckdb
import pytest
from radar_pipeline.vinculos import carrega_vinculos


@pytest.fixture
def con():
    con = duckdb.connect()
    con.execute("""
    CREATE TABLE sancoes (cnpj_cpf VARCHAR, vigente BOOLEAN, data_inicio DATE);
    INSERT INTO sancoes VALUES
        ('11111111000101', true,  DATE '2022-01-01'),   -- SANCIONADA
        ('44444444000104', false, DATE '2010-01-01');   -- sanção expirada: NÃO é grau 0

    CREATE TABLE socios (cnpj_basico VARCHAR, nome_socio VARCHAR, cpf_mascarado VARCHAR);
    INSERT INTO socios VALUES
        ('11111111', 'JOAO DA SILVA',  '***123456**'),  -- sócio da sancionada
        ('22222222', 'JOAO DA SILVA',  '***123456**'),  -- ALTA: nome + doc
        ('33333333', 'JOAO DA SILVA',  ''),             -- MEDIA: doc ausente
        ('55555555', 'MARIA PEREIRA',  '***999999**'),  -- sem relação
        ('44444444', 'JOAO DA SILVA',  '***123456**');  -- ligada, mas à expirada tb

    CREATE TABLE estabelecimentos (
        cnpj_basico VARCHAR, matriz_filial VARCHAR, cnae_principal VARCHAR,
        municipio_codigo VARCHAR, uf VARCHAR, data_inicio_atividade DATE
    );
    INSERT INTO estabelecimentos VALUES
        ('11111111', '1', '4120400', '8105', 'SC', DATE '2010-05-01'),
        ('22222222', '1', '4120400', '8105', 'SC', DATE '2023-03-01'),  -- SUCESSORA
        ('33333333', '1', '9999999', '0001', 'SP', DATE '2023-03-01'),  -- outro ramo
        ('44444444', '1', '4120400', '8105', 'SC', DATE '2005-01-01');
    """)
    yield con
    con.close()


def test_vinculos_e_risco(con):
    contagens = carrega_vinculos(con)

    vinculos = {
        (a, b): (socio, conf)
        for a, b, socio, conf in con.execute(
            "SELECT cnpj_a, cnpj_b, socio_comum, confianca FROM vinculos"
        ).fetchall()
    }
    assert vinculos[("11111111", "22222222")] == ("JOAO DA SILVA", "alta")
    assert vinculos[("11111111", "33333333")] == ("JOAO DA SILVA", "media")
    assert ("11111111", "55555555") not in vinculos

    assert contagens["grau0"] == 1  # só a sanção vigente
    grau1 = {
        linha[0]: linha
        for linha in con.execute("""
            SELECT cnpj_basico, relacionada, confianca, indicio_sucessora
            FROM empresas_risco WHERE grau = 1
        """).fetchall()
    }
    # 22222222: alta confiança + aberta APÓS a sanção, mesmo CNAE/município
    assert grau1["22222222"] == ("22222222", "11111111", "alta", True)
    # 33333333: média confiança, ramo/município diferentes -> sem indício
    assert grau1["33333333"] == ("33333333", "11111111", "media", False)
    # 44444444: aberta ANTES da sanção -> vínculo sim, sucessora não
    assert grau1["44444444"][3] is False
    # a própria sancionada nunca aparece como grau 1
    assert "11111111" not in grau1


def test_hiperconector_excluido_da_media():
    con = duckdb.connect()
    con.execute("CREATE TABLE sancoes (cnpj_cpf VARCHAR, vigente BOOLEAN, data_inicio DATE)")
    con.execute("CREATE TABLE estabelecimentos (cnpj_basico VARCHAR, matriz_filial VARCHAR, "
                "cnae_principal VARCHAR, municipio_codigo VARCHAR, uf VARCHAR, "
                "data_inicio_atividade DATE)")
    con.execute("CREATE TABLE socios (cnpj_basico VARCHAR, nome_socio VARCHAR, "
                "cpf_mascarado VARCHAR)")
    # mesmo nome SEM documento em 25 empresas -> hiperconector, sem vínculos media
    for i in range(25):
        con.execute(f"INSERT INTO socios VALUES ('{i:08d}', 'FUNDO REPRESENTANTE', '')")
    contagens = carrega_vinculos(con)
    assert contagens["vinculos"] == 0
    con.close()
