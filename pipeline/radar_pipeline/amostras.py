"""Baixa amostras de todas as fontes para validação de layout (P0.4).

Uso: ``uv run python -m radar_pipeline.amostras [AAAA-MM]``
(mês opcional para compras/licitações/CNPJ; padrão: mês anterior ao atual)

Baixa para ``data/raw/``: snapshots do dia das 4 bases de sanções, um mês de
compras e licitações, e do CNPJ apenas Socios0 + tabelas de domínio (a amostra
mínima para validar o layout — o dump completo só entra na Fase 1).
"""

import itertools
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from radar_pipeline import fontes

ARQUIVOS_CNPJ_AMOSTRA = ("Socios0.zip", "Cnaes.zip", "Qualificacoes.zip", "Municipios.zip")


def main() -> None:
    raiz = Path(__file__).resolve().parents[2] / "data" / "raw"
    hoje = date.today()
    if len(sys.argv) > 1:
        ano, mes = map(int, sys.argv[1].split("-"))
    else:
        fim_mes_passado = hoje.replace(day=1) - timedelta(days=1)
        ano, mes = fim_mes_passado.year, fim_mes_passado.month

    for base in fontes.BASES_SANCOES:
        destino, dia = fontes.baixar_sancao_mais_recente(base, raiz / "sancoes", a_partir=hoje)
        print(f"↓ {base} (snapshot de {dia:%d/%m/%Y}) → {destino}")

    for base in fontes.BASES_MENSAIS:
        # licitações está congelada em 04/2024 (ver fontes.ULTIMO_MES_LICITACOES)
        a, m = fontes.ULTIMO_MES_LICITACOES if base == "licitacoes" else (ano, mes)
        destino, (a, m) = fontes.baixar_mensal_mais_recente(base, raiz / base, ano=a, mes=m)
        print(f"↓ {base} ({m:02d}/{a}) → {destino}")

    ultima_semana = hoje - timedelta(days=7)
    for nome, iterador in (
        ("contratos", fontes.contratos_pncp(ultima_semana, hoje)),
        ("contratacoes_pregao", fontes.contratacoes_pncp(ultima_semana, hoje, 6)),
    ):
        destino = raiz / "pncp" / f"{hoje:%Y%m%d}_{nome}_amostra.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        amostra = list(itertools.islice(iterador, 50))
        destino.write_text(json.dumps(amostra, ensure_ascii=False, indent=1))
        print(f"↓ pncp/{nome} (última semana, 50 primeiros) → {destino}")

    for arquivo in ARQUIVOS_CNPJ_AMOSTRA:
        destino = raiz / "cnpj" / f"{ano:04d}-{mes:02d}" / arquivo
        print(f"↓ cnpj/{arquivo} ({mes:02d}/{ano}) → {destino}")
        fontes.baixar(
            fontes.url_cnpj(ano, mes, arquivo), destino, auth=(fontes.RECEITA_SHARE_ID, "")
        )

    print("✓ amostras baixadas em", raiz)


if __name__ == "__main__":
    main()
