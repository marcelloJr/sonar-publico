# Radar de Sanções

Plataforma pública que cruza **sanções** (CEIS, CNEP, CEPIM, Acordos de Leniência), **contratos do governo federal** e **quadro societário** (CNPJ/QSA da Receita Federal) para expor empresas sancionadas que seguem contratando com o poder público — e possíveis "empresas sucessoras" via sócios em comum.

> Projeto para o [2º Concurso de Reúso de Dados Abertos da CGU](https://www.gov.br/cgu/pt-br/acesso-a-informacao/dados-abertos/concurso-dados-abertos) (Edital CGU nº 46/2026). Inscrições até **11/09/2026**.

## Estrutura

| Pasta | O quê | Stack |
|---|---|---|
| [`pipeline/`](pipeline/) | Download, normalização e cruzamento das bases (batch mensal) | Python + DuckDB |
| [`api/`](api/) | API pública | FastAPI |
| [`web/`](web/) | Frontend (Fase 3) | Next.js |
| [`docs/`](docs/) | [Spec](SPEC.md) · [Fontes de dados](docs/fontes.md) · [Regulamento](docs/regulamento.md) | — |

## Desenvolvimento

Requisitos: [uv](https://docs.astral.sh/uv/) (gerencia Python e dependências) e Node 20+ (Fase 3).

```sh
make setup   # instala tudo
make test    # testes de pipeline + api
make lint    # ruff
make api     # API local em http://localhost:8000 (docs em /docs)
```

## Dados

Nenhum dado bruto é versionado (o dump do CNPJ tem ~85 GB descompactado). URLs, formatos e dicionários de cada fonte: [docs/fontes.md](docs/fontes.md).

## Aviso

A plataforma **aponta vínculos, não acusa**: os dados vêm de fontes oficiais públicas; vínculo societário com empresa sancionada não é prova de irregularidade; a metodologia de matching tem limitações documentadas.
