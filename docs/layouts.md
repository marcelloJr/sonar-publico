# Layouts reais das bases (validados com amostras — P0.4)

> Amostras baixadas e inspecionadas em **06/07/2026** via `uv run python -m radar_pipeline.amostras`.
> Regra geral de leitura no pipeline: **encoding ISO-8859-1, separador `;`, campos entre aspas duplas**. Os arquivos do CNPJ **não têm cabeçalho**; os do Portal da Transparência têm.

## Sanções (Portal da Transparência) — snapshot único, com cabeçalho, CRLF

| Base | Arquivo(s) no ZIP | Colunas | Linhas na amostra |
|---|---|---|---|
| CEIS | `AAAAMMDD_CEIS.csv` | 24 | 23.130 |
| CNEP | `AAAAMMDD_CNEP.csv` | 25 (= CEIS + `VALOR DA MULTA`) | 1.696 |
| CEPIM | `AAAAMMDD_CEPIM.csv` | 5 | 3.551 |
| Leniência | **2 arquivos**: `AAAAMMDD_Acordos.csv` (11 col) e `AAAAMMDD_Efeitos.csv` (3 col, N:1 com acordos via `ID DO ACORDO`) | 11 / 3 | 151 / 172 |

Colunas do CEIS (CNEP idem + multa): `CADASTRO`, `CÓDIGO DA SANÇÃO`, `TIPO DE PESSOA`, `CPF OU CNPJ DO SANCIONADO`, `NOME DO SANCIONADO`, `NOME INFORMADO PELO ÓRGÃO SANCIONADOR`, `RAZÃO SOCIAL - CADASTRO RECEITA`, `NOME FANTASIA - CADASTRO RECEITA`, `NÚMERO DO PROCESSO`, `CATEGORIA DA SANÇÃO`, `DATA INÍCIO SANÇÃO`, `DATA FINAL SANÇÃO`, `DATA PUBLICAÇÃO`, `PUBLICAÇÃO`, `DETALHAMENTO DO MEIO DE PUBLICAÇÃO`, `DATA DO TRÂNSITO EM JULGADO`, `ABRAGÊNCIA DA SANÇÃO` *(sic — typo oficial)*, `ÓRGÃO SANCIONADOR`, `UF ÓRGÃO SANCIONADOR`, `ESFERA ÓRGÃO SANCIONADOR`, `FUNDAMENTAÇÃO LEGAL`, `DATA ORIGEM INFORMAÇÃO`, `ORIGEM INFORMAÇÕES`, `OBSERVAÇÕES`.

CEPIM: `CNPJ ENTIDADE`, `NOME ENTIDADE`, `NÚMERO CONVÊNIO`, `ÓRGÃO CONCEDENTE`, `MOTIVO DO IMPEDIMENTO`.

⚠️ Gotchas:
- O snapshot **não é diário em todas as bases** (CEPIM mais recente era de 03/07 num dia 06/07). O pipeline recua dia a dia até achar (`baixar_sancao_mais_recente`).
- Cabeçalhos têm typos oficiais (`ABRAGÊNCIA`, `LENIÊNICA`) — mapear pelos nomes exatos, não corrigir.
- Sanções federais, estaduais e municipais misturadas — filtrar/deixar claro por `ESFERA ÓRGÃO SANCIONADOR`.

## Compras/Contratos (Portal da Transparência) — mensal, com cabeçalho, CRLF

ZIP `AAAAMM_Compras.zip` com 4 CSVs: `Compras` (24 col), `ItemCompra` (10), `TermoAditivo` (10), `Apostilamento` (12).

Colunas de `Compras`: `Número do Contrato`, `Objeto`, `Fundamento Legal`, `Modalidade Compra`, `Situação Contrato`, `Código/Nome Órgão Superior`, `Código/Nome Órgão`, `Código/Nome UG`, `Data Assinatura Contrato`, `Data Publicação DOU`, `Data Início/Fim Vigência`, **`Código Contratado` (CNPJ)**, `Nome Contratado`, `Valor Inicial/Final Compra`, `Número Licitação`, `Código/Nome UG Licitação`, `Código/Modalidade Compra Licitação`.

⚠️ Gotchas:
- **Defasagem de publicação**: 06/2026 tinha só 33 contratos vs 2.548 em 05/2026. Carregar meses com pelo menos ~30–40 dias de maturidade e recarregar os 2 últimos meses a cada execução.
- Volume: ~2,5 mil contratos/mês → carga histórica de anos é tranquila.

## Licitações (Portal da Transparência) — ⚠️ DESCONTINUADA

Arquivos disponíveis **somente de 01/2013 a 04/2024** (migração para o PNCP com a Lei 14.133/2021). ZIP com 4 CSVs: `Licitação` (17 col), `ItemLicitação` (14), `ParticipantesLicitação` (13), `EmpenhosRelacionados` (10) — nomes de arquivo **com acento**.

Decisão v1: usar apenas como histórico complementar (participantes de licitação); dados novos de licitação ficariam no PNCP (fase futura).

## CNPJ / Receita Federal — mensal, SEM cabeçalho, LF

Nome interno dos arquivos: `K3241.K03200Y0.D60613.SOCIOCSV` (o `D60613` codifica a data de geração AAMMDD), tabelas de domínio como `F.K03200$Z.D60613.CNAECSV`.

`Socios0.zip` (1 de 10 partes): 991 MB descompactado, **9.666.098 linhas**, 11 colunas (ordem do PDF de metadados):

| # | Campo | Exemplo na amostra |
|---|---|---|
| 1 | `cnpj_basico` (**só 8 dígitos!**) | `20119930` |
| 2 | `identificador_socio` (1=PJ, 2=PF, 3=estrangeiro) | `2` |
| 3 | `nome_socio` / razão social | `CARLOS JOAQUIM BOITRAGO` |
| 4 | `cnpj_cpf_socio` (CPF mascarado `***NNNNNN**`) | `***846761**` |
| 5 | `qualificacao_socio` (código → tabela Qualificacoes) | `49` |
| 6 | `data_entrada_sociedade` (AAAAMMDD) | `20181123` |
| 7 | `pais` | vazio |
| 8 | `representante_legal` (CPF mascarado) | `***000000**` |
| 9 | `nome_representante` | vazio |
| 10 | `qualificacao_representante` | `00` |
| 11 | `faixa_etaria` | `6` |

⚠️ Gotchas:
- **`cnpj_basico` tem 8 dígitos** (raiz do CNPJ, sem ordem/DV). O vínculo sócio→empresa é pela raiz; para chegar ao CNPJ de 14 dígitos é preciso juntar com `Estabelecimentos*` (que tem `cnpj_basico + cnpj_ordem + cnpj_dv`). Impacto direto no modelo (§4.1 do SPEC): a tabela `socios` deve usar `cnpj_basico`.
- Encoding: tabelas de domínio (Cnaes, Qualificacoes) são ISO-8859-1 com acentos; `Socios0` amostrado era ASCII puro (nomes já sem acento). **Ler tudo como ISO-8859-1** é seguro.
- Total estimado dos sócios: ~10 partes × ~9,7M ≈ 25M+ linhas (partes têm tamanhos diferentes).
- Nomes de sócio já vêm uppercase e aparentemente sem acento — a `normaliza_nome` ainda se aplica (colapso de espaços, defesa contra exceções).
