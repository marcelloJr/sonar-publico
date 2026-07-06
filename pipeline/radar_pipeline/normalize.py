"""Normalização de identificadores e nomes (SPEC §4.3 e P1.3).

Regras: CNPJ/CPF apenas dígitos; nomes sem acentos, uppercase, espaços
colapsados — é a chave de matching de sócios, então qualquer mudança aqui
altera a tabela `vinculos` inteira.
"""

import re
import unicodedata

_NAO_DIGITO = re.compile(r"\D")
_ESPACOS = re.compile(r"\s+")


def normaliza_cnpj(valor: str) -> str:
    """Reduz um CNPJ a 14 dígitos, preservando zeros à esquerda."""
    digitos = _NAO_DIGITO.sub("", valor)
    return digitos.zfill(14) if digitos else ""


def normaliza_nome(valor: str) -> str:
    """Nome sem acentos, uppercase, espaços colapsados."""
    sem_acento = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode("ascii")
    return _ESPACOS.sub(" ", sem_acento).strip().upper()


def chave_socio(nome: str, cpf_mascarado: str) -> str:
    """Chave de matching de sócio: nome normalizado + fragmento do CPF.

    O QSA público mascara o CPF (ex.: ``***123456**``); mantemos apenas os
    dígitos visíveis para compor a chave.
    """
    return f"{normaliza_nome(nome)}|{_NAO_DIGITO.sub('', cpf_mascarado)}"
