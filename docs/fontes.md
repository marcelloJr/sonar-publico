# Fontes de Dados — URLs verificadas

> Deliverable do **P0.3**. Todas as URLs foram verificadas em **06/07/2026** (HTTP direto; amostras de CEIS, Compras e tabelas do CNPJ foram baixadas para confirmar formato).
> Requisito do concurso (Edital CGU nº 46/2026, item 6.3): a iniciativa deve referenciar **ao menos 1** conjunto do dados.gov.br no cadastro de reúso — usamos 6.

## Resumo

| # | Base | dados.gov.br | Download | Dicionário |
|---|---|---|---|---|
| 1 | CEIS | [conjunto](https://dados.gov.br/dados/conjuntos-dados/ceis) | [download](https://portaldatransparencia.gov.br/download-de-dados/ceis) | [dicionário](https://portaldatransparencia.gov.br/dicionario-de-dados/ceis) |
| 2 | CNEP | [conjunto](https://dados.gov.br/dados/conjuntos-dados/cnep) | [download](https://portaldatransparencia.gov.br/download-de-dados/cnep) | [dicionário](https://portaldatransparencia.gov.br/dicionario-de-dados/cnep) |
| 3 | CEPIM | [conjunto](https://dados.gov.br/dados/conjuntos-dados/cepim-entidades-privadas-sem-fins-lucrativos-impedidas) | [download](https://portaldatransparencia.gov.br/download-de-dados/cepim) | [dicionário](https://portaldatransparencia.gov.br/dicionario-de-dados/cepim) |
| 4 | Acordos de Leniência | [conjunto](https://dados.gov.br/dados/conjuntos-dados/acordos-de-leniencia) | [download](https://portaldatransparencia.gov.br/download-de-dados/acordos-leniencia) | [dicionário](https://portaldatransparencia.gov.br/dicionario-de-dados/acordos-leniencia) |
| 5 | Compras/Contratos + Licitações (Executivo Federal) | [conjunto](https://dados.gov.br/dados/conjuntos-dados/licitacoes-e-contratos-do-governo-federal) | [compras](https://portaldatransparencia.gov.br/download-de-dados/compras) · [licitações](https://portaldatransparencia.gov.br/download-de-dados/licitacoes) | [contratos](https://portaldatransparencia.gov.br/dicionario-de-dados/contratos) · [licitações](https://portaldatransparencia.gov.br/dicionario-de-dados/licitacoes) |
| 6 | CNPJ + QSA (Receita Federal) | [conjunto](https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj) | [share Nextcloud](https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9) | [layout (PDF)](https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf) |

## 1–4. Sanções (CEIS, CNEP, CEPIM, Leniência) — Portal da Transparência / CGU

- **URL direta de download:** `https://portaldatransparencia.gov.br/download-de-dados/{base}/AAAAMMDD` → 302 → `https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/{base}/AAAAMMDD_{Nome}.zip`
  - `{base}` ∈ `ceis`, `cnep`, `cepim`, `acordos-leniencia`
- **Atualização DIÁRIA (não mensal como o spec assumia)** e **apenas o snapshot mais recente fica disponível** — datas anteriores retornam 403. Se quisermos histórico próprio, temos que arquivar snapshots por conta.
- **Formato (verificado no ZIP real do CEIS de 06/07/2026):** CSV com cabeçalho, separador `;`, campos entre aspas duplas, **encoding ISO-8859-1 (Latin-1)**, quebras CRLF. CEIS tem 24 colunas (cabeçalho do próprio CSV).
- As páginas de dicionário existem, mas renderizam via JavaScript — conferir os campos no navegador.

## 5. Compras/Contratos e Licitações — Portal da Transparência

- **Compras (mensal, ativa):** `.../download-de-dados/compras/AAAAMM` → `AAAAMM_Compras.zip` com 4 CSVs: `Compras`, `ItemCompra`, `TermoAditivo`, `Apostilamento`.
  - ⚠️ **Defasagem de publicação:** o mês mais recente sai quase vazio no início (06/2026 tinha 33 contratos em 06/07, vs 2.548 em 05/2026). Recarregar os últimos 2 meses a cada execução.
- **Licitações — ⚠️ DESCONTINUADA em 04/2024** (migração ao PNCP, Lei 14.133). Arquivos disponíveis de 01/2013 a 04/2024 em `.../download-de-dados/licitacoes/AAAAMM`. Histórico complementar; dados novos vêm do PNCP (abaixo).

### PNCP — Portal Nacional de Contratações Públicas (licitações/contratações pós-2024)

- **API de consulta:** `https://pncp.gov.br/api/consulta/v1` — pública, **sem token**, JSON paginado. Cliente implementado em `radar_pipeline.fontes` (`contratos_pncp`, `contratacoes_pncp`).
- Endpoints usados: `/contratos?dataInicial&dataFinal` (tamanhoPagina ≤ **500**) e `/contratacoes/publicacao?dataInicial&dataFinal&codigoModalidadeContratacao` (tamanhoPagina ≤ **50**; a modalidade é obrigatória — as 14 estão em `MODALIDADES_PNCP`, confirmadas na API em 06/07/2026).
- ⚠️ **Rate limit agressivo (HTTP 429)** — o cliente faz backoff exponencial respeitando `Retry-After`. Não paralelizar requisições.
- ⚠️ **Cobre todas as esferas** (federal/estadual/municipal): filtrar `orgaoEntidade.esferaId == "F"` no consumo (~3% dos registros na sondagem). Bônus: expansão para estados/municípios (roadmap §8 do SPEC) já teria fonte pronta.
- Volume sondado: ~31 mil contratos/6 dias (todas as esferas); federais ≈ 1 mil/semana.
- dados.gov.br: o PNCP é sítio oficial do governo federal (aceito pelo edital, item 6.3); para o cadastro do reúso, citar também o conjunto correspondente no dados.gov.br se disponível.
- **Formato (verificado em 202605_Compras.zip):** CSV `;`, aspas duplas, ISO-8859-1, CRLF, com cabeçalho. Layouts completos: [layouts.md](layouts.md).
- **Fonte alternativa:** [Compras.gov.br / MGI](https://dados.gov.br/dados/conjuntos-dados/compras-publicas-do-governo-federal).

### API de Dados do Portal da Transparência

- Base: `https://api.portaldatransparencia.gov.br` — [Swagger UI](https://api.portaldatransparencia.gov.br/swagger-ui/index.html) · [OpenAPI](https://api.portaldatransparencia.gov.br/v3/api-docs)
- **Exige token gratuito** (header `chave-api-dados`), obtido via [cadastro de e-mail Gov.br](https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email).
- Endpoints úteis confirmados: `/api-de-dados/ceis`, `/cnep`, `/cepim`, `/acordos-leniencia`, `/licitacoes*`, `/contratos*` — bom para testes de sanidade (P1.8), não para carga em massa.

## 6. CNPJ + QSA — Receita Federal

- **Download atual:** share Nextcloud público [`arquivos.receitafederal.gov.br/.../YggdBLfdninEJX9`](https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9), pastas mensais de `2023-05` até `2026-06`.
- Cada pasta mensal contém: `Empresas0..9.zip`, `Estabelecimentos0..9.zip`, **`Socios0..9.zip` (QSA)**, `Simples.zip` + tabelas de domínio (`Cnaes`, `Motivos`, `Municipios`, `Naturezas`, `Paises`, `Qualificacoes`).
- **Download programático:** WebDAV público `https://arquivos.receitafederal.gov.br/public.php/webdav/AAAA-MM/Arquivo.zip`, usuário `YggdBLfdninEJX9`, senha vazia (testado).
- **Formato (layout PDF + amostra):** CSV **sem cabeçalho**, separador `;`, aspas duplas. Encoding não documentado oficialmente; na prática ISO-8859-1 — **validar com amostra de `Socios*.zip` antes de fixar no pipeline (P0.4)**. Volume ≈ 85 GB descompactado.
- CPF do sócio vem parcialmente descaracterizado no próprio layout (base do matching do §4.3 do SPEC).
- **URLs antigas mortas (não usar):** `dadosabertos.rfb.gov.br/CNPJ/` (timeout) e `arquivos.receitafederal.gov.br/cnpj/dados_abertos_cnpj/` (404).
- ⚠️ O endereço da Receita já mudou 3+ vezes. **No pipeline, resolver a URL a partir da página do conjunto no dados.gov.br em cada execução**, com o share atual como fallback, e falhar com mensagem clara se ambos quebrarem.

## Pendências / verificação humana

- [ ] Conferir no navegador o conteúdo dos dicionários do Portal da Transparência (páginas são JS-rendered).
- [x] ~~Validar encoding dos arquivos `Socios*.zip` do CNPJ com amostra real (P0.4).~~ Feito 06/07 — ver [layouts.md](layouts.md); ler tudo como ISO-8859-1.
- [ ] Decidir se vamos arquivar snapshots diários das bases de sanções (o bucket da CGU só serve o mais recente e nem toda base publica todo dia — CEPIM estava em 03/07 no dia 06/07).
- [ ] Criar token da API do Portal da Transparência (um por dev, para testes de sanidade).
- [ ] Decidir se PNCP entra como fonte de licitações pós-04/2024 (roadmap; a base antiga foi descontinuada).
