"""Helpers de extração/transcodificação e fragmentos SQL de normalização.

Compartilhados pelas cargas (sanções, contratos). As regras espelham
``normalize.py`` — qualquer mudança aqui afeta o matching inteiro.
"""

import zipfile
from pathlib import Path

SO_DIGITOS = "regexp_replace({col}, '[^0-9]', '', 'g')"
NOME_NORMALIZADO = "regexp_replace(trim(upper(strip_accents({col}))), '\\s+', ' ', 'g')"
DATA_BR = "try_strptime(nullif(trim({col}), ''), '%d/%m/%Y')::DATE"
# "1.234.567,89" -> 1234567.89
VALOR_BRL = """try_cast(replace(replace(nullif(trim({col}), ''),
             '.', ''), ',', '.') AS DECIMAL(18,2))"""


def extrai_zip(zip_path: Path, staging: Path) -> dict[str, Path]:
    """Extrai o ZIP para o staging, transcodificando para UTF-8.

    Retorna {nome_do_csv_minusculo: caminho}.
    """
    destino = staging / zip_path.stem
    destino.mkdir(parents=True, exist_ok=True)
    extraidos = {}
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            caminho = Path(z.extract(info, destino))
            transcodifica_utf8(caminho)
            extraidos[Path(info.filename).name.lower()] = caminho
    return extraidos


def transcodifica_utf8(caminho: Path) -> None:
    """Reescreve o arquivo em UTF-8, decidindo o encoding LINHA A LINHA.

    Necessário porque há arquivos do Portal da Transparência com encoding
    misto (ex.: Acordos.csv de 06/07/2026: cabeçalho Windows-1252, linhas
    UTF-8) — nenhum encoding único decodifica o arquivo inteiro. cp1252 no
    fallback porque 0x80–0x9F são tipográficos lá (ex.: 0x96 = en dash no
    cabeçalho real da Leniência), não controles como no ISO-8859-1.
    """
    bruto = caminho.read_bytes()
    linhas = []
    for linha in bruto.split(b"\n"):
        try:
            linhas.append(linha.decode("utf-8"))
        except UnicodeDecodeError:
            try:
                linhas.append(linha.decode("cp1252"))
            except UnicodeDecodeError:
                linhas.append(linha.decode("iso-8859-1"))
    # normaliza o CABEÇALHO para nomes de coluna estáveis: en dash (U+2013)
    # e o controle U+0096 (0x96 mal decodificado) viram hífen; NBSP, espaço
    if linhas:
        linhas[0] = (
            linhas[0].replace(chr(0x2013), '-').replace(chr(0x96), '-').replace(chr(0xA0), ' ')
        )
    caminho.write_text("\n".join(linhas), encoding="utf-8")


def sql_csv(caminho: Path | str) -> str:
    """Fragmento read_csv do formato do Portal (staging já em UTF-8)."""
    return f"read_csv('{caminho}', delim=';', quote='\"', header=true, all_varchar=true)"
