from radar_pipeline.normalize import chave_socio, normaliza_cnpj, normaliza_nome


def test_normaliza_cnpj_remove_pontuacao():
    assert normaliza_cnpj("12.345.678/0001-95") == "12345678000195"


def test_normaliza_cnpj_preserva_zeros_a_esquerda():
    assert normaliza_cnpj("1.234.567/0001-95") == "01234567000195"


def test_normaliza_cnpj_vazio():
    assert normaliza_cnpj("") == ""
    assert normaliza_cnpj("sem dígitos") == ""


def test_normaliza_nome():
    assert normaliza_nome("  João   da  Silva Júnior ") == "JOAO DA SILVA JUNIOR"


def test_normaliza_nome_cedilha_e_simbolos():
    assert normaliza_nome("Construções Açaí Ltda.") == "CONSTRUCOES ACAI LTDA."


def test_chave_socio():
    assert chave_socio("José Ávila", "***123456**") == "JOSE AVILA|123456"
