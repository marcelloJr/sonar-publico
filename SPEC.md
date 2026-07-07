# Sonar Público — Especificação do Projeto

> Nome anterior: "Radar de Sanções" (renomeado em 06/07/2026; domínio: sonarpublico.com.br)

> Projeto para o 2º Concurso de Reúso de Dados Abertos da CGU (2026)
> Equipe: 3 desenvolvedores | Prazo de inscrição: 11/09/2026

---

## 1. Visão Geral

### 1.1 O problema
Empresas sancionadas (declaradas inidôneas, suspensas ou punidas pela Lei Anticorrupção) continuam, na prática, acessando contratos públicos — seja porque gestores não verificam os cadastros, seja por meio de "empresas sucessoras" criadas pelos mesmos sócios. Não existe ferramenta pública, gratuita e acessível que cruze sanções, contratos e quadro societário para expor esses vínculos.

### 1.2 A solução
Plataforma web pública onde qualquer cidadão, jornalista ou gestor pode:
1. Buscar uma empresa (CNPJ ou nome) e ver sua ficha completa: sanções ativas e históricas, contratos com o governo federal, valor total contratado e quadro societário.
2. Buscar por órgão público e ver quais fornecedores contratados possuem sanções ou vínculos de risco.
3. Receber **alertas de vínculo societário**: "a empresa X não está sancionada, mas compartilha sócios com a empresa Y, declarada inidônea" (detecção de possíveis empresas sucessoras/de fachada).
4. Entender tudo em **linguagem simples**: cada sanção acompanha explicação acessível do que significa.

### 1.3 Alinhamento com os critérios de julgamento do concurso

Critérios oficiais do **Edital CGU nº 46/2026, item 8.2** (DOU 23/06/2026 — ver `docs/regulamento.md`). Nota: a página da CGU ainda exibe uma tabela de 7 critérios herdada da 1ª edição; a fonte normativa é o edital.

| Critério | Peso | Como atendemos |
|---|---|---|
| Apresentação e usabilidade | 1 | Vídeo demo com storytelling, interface limpa mobile-first, linguagem simples, WCAG 2.1 AA |
| Inovação e originalidade | 1 | Grafo de vínculos societários para detecção de sucessoras (inédito em ferramenta pública gratuita) |
| **Relevância e impacto** | **2** | Fiscalização direta de contratações públicas; casos reais de vínculo revelados pela ferramenta (P4.3) |
| **Benefício para a sociedade ou economia** | **2** | Gratuito para cidadãos, jornalistas e gestores; protege dinheiro público ao expor fornecedores de risco |
| Replicabilidade e escalabilidade | 1 | Código aberto + API pública documentada + pipeline reproduzível; arquitetura replicável para estados/municípios (roadmap §8) |

Os dois critérios de peso 2 concentram metade da nota: a apresentação e os textos devem ser construídos em torno de **impacto e benefício concreto** (casos reais, valor contratado sob alerta), não das features técnicas.

### 1.4 Posicionamento e cuidado jurídico
A plataforma **aponta vínculos, não acusa**. Todos os textos devem deixar claro que: (a) os dados vêm de fontes oficiais públicas; (b) vínculo societário com empresa sancionada não é prova de irregularidade; (c) a metodologia de matching tem limitações documentadas (ver §4.4).

---

## 2. Fontes de Dados (todas catalogadas no dados.gov.br — requisito do concurso)

| # | Base | Origem | Formato | Tamanho aprox. | Atualização |
|---|---|---|---|---|---|
| 1 | CEIS — Empresas Inidôneas e Suspensas | Portal da Transparência / CGU | CSV | pequeno (~23 mil linhas) | diária (snapshot único) |
| 2 | CNEP — Empresas Punidas (Lei Anticorrupção) | Portal da Transparência / CGU | CSV | pequeno | diária (snapshot único) |
| 3 | CEPIM — Entidades sem fins lucrativos impedidas | Portal da Transparência / CGU | CSV | pequeno | diária/irregular (snapshot único) |
| 4 | Acordos de Leniência | Portal da Transparência / CGU | CSV (2 arquivos: Acordos + Efeitos) | pequeno | diária (snapshot único) |
| 5 | Contratos (Compras) do Poder Executivo Federal | Portal da Transparência | CSV (planilhas mensais; mês corrente sai defasado) | médio (~2,5 mil contratos/mês) | mensal |
| 6 | Licitações/contratações públicas | **PNCP** (novas, pós-Lei 14.133) + Portal da Transparência (histórico 2013–04/2024) | API JSON paginada (PNCP) + CSV | médio | contínua (PNCP) |
| 7 | Cadastro Nacional da Pessoa Jurídica (CNPJ) + QSA | Receita Federal | CSVs sem cabeçalho em ZIPs (~85 GB descompactado) | muito grande (~60M empresas; QSA ≈ 25M+ linhas) | mensal |

> A base de licitações do Portal da Transparência foi **descontinuada em 04/2024** (migração ao PNCP). O PNCP cobre todas as esferas — filtramos federal (`esferaId == "F"`) na v1. URLs verificadas, formatos e gotchas: `docs/fontes.md` e `docs/layouts.md`.

**Ação obrigatória na semana 1:** ✅ feita — URLs registradas em `docs/fontes.md`, layouts validados com amostras reais em `docs/layouts.md`.

---

## 3. Arquitetura

```
┌─────────────────────────────────────────────────────┐
│ PIPELINE (batch mensal, Python)                     │
│  download → limpeza → normalização → cruzamento     │
│  Ferramentas: Python + DuckDB (ou Polars)           │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ BANCO CONSOLIDADO (PostgreSQL)                      │
│  empresas | sancoes | contratos | socios | vinculos │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ API (FastAPI, Python)                               │
│  /busca | /empresa/{cnpj} | /orgao/{id} | /grafo    │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ FRONTEND (Next.js, mobile-first, WCAG 2.1 AA)       │
│  busca | ficha da empresa | grafo de vínculos       │
│  painel por órgão | glossário em linguagem simples  │
└─────────────────────────────────────────────────────┘
```

**Decisões técnicas:**
- **DuckDB no pipeline**: lê os CSVs gigantes do CNPJ direto do disco sem estourar memória; pandas puro não aguenta o dump da Receita.
- **PostgreSQL como banco final**: o resultado do cruzamento é enxuto (só empresas relevantes: sancionadas + contratadas + vizinhas de grafo). Alternativa aceitável: SQLite/DuckDB read-only se a hospedagem for estática.
- **Grafo sem Neo4j**: tabela de arestas `vinculos(cnpj_a, cnpj_b, tipo, detalhe)` + consultas recursivas (CTE) resolve para 1–2 graus de separação. Não adicionar complexidade desnecessária.
- **Infra gratuita/barata**: Vercel (front) + Railway/Fly.io/Render (API + banco). Atualização mensal via GitHub Actions rodando o pipeline.

---

## 4. Modelo de Dados e Lógica de Risco

### 4.1 Tabelas principais
```sql
empresas   (cnpj PK, razao_social, nome_fantasia, uf, municipio, situacao_cadastral, cnae)
socios     (cnpj FK, nome_socio, cpf_mascarado, qualificacao, data_entrada)
sancoes    (id PK, cnpj/cpf FK, tipo_cadastro [CEIS|CNEP|CEPIM|LENIENCIA],
            tipo_sancao, orgao_sancionador, data_inicio, data_fim, fundamentacao)
contratos  (id PK, cnpj FK, orgao, objeto, valor, data_inicio, data_fim, situacao)
vinculos   (cnpj_a, cnpj_b, tipo_vinculo, socio_comum, confianca)
```

### 4.2 Graus de risco
- **Grau 0 (vermelho):** empresa possui sanção vigente (CEIS/CNEP/CEPIM).
- **Grau 1 (laranja):** empresa sem sanção, mas com ≥1 sócio em comum com empresa sancionada (sanção vigente).
- **Grau 2 (amarelo, opcional/fase 2):** sócio em comum com empresa de grau 1, ou sanção expirada há menos de N anos.
- **Sinal complementar:** empresa de grau 1 criada *após* a data da sanção da empresa relacionada, no mesmo CNAE e município → forte indício de sucessora (destacar na ficha).

### 4.3 Matching de sócios (o desafio técnico central)
O QSA público da Receita **mascara o CPF** (ex.: `***123456**`). Estratégia:
1. Chave de matching: `nome_normalizado + cpf_mascarado` (nome sem acentos, uppercase, espaços colapsados).
2. Classificar confiança: `alta` (nome completo idêntico + CPF mascarado idêntico), `media` (nome idêntico, CPF mascarado ausente em uma das bases).
3. Exibir o nível de confiança na interface — nunca apresentar match de média confiança como certeza.

### 4.4 Limitações a documentar publicamente (página "Metodologia")
- Homônimos com mesmo fragmento de CPF são possíveis (raros, mas possíveis).
- Cobertura: contratos apenas do Poder Executivo **Federal** (estaduais/municipais ficam para versão futura — mencionar como roadmap).
- Defasagem de até 1 mês (dados mensais).

---

## 5. Plano de Execução em Passos

### FASE 0 — Setup (Semana 1: 06/07 → 13/07)
- [ ] **P0.1** Criar repositório (monorepo: `/pipeline`, `/api`, `/web`, `/docs`), CI básico.
- [ ] **P0.2** Ler o regulamento completo do concurso; confirmar se a inscrição pode ser editada após envio; listar anexos exigidos.
- [ ] **P0.3** Localizar no dados.gov.br as URLs dos 6 conjuntos de dados; salvar em `/docs/fontes.md` com links dos dicionários de dados.
- [ ] **P0.4** Baixar amostras de todas as bases; validar encoding (bases do governo costumam ser ISO-8859-1/Latin-1), separador e layout contra o dicionário.
- [ ] **P0.5** Definir nome final e registrar domínio (opcional, ~R$40/ano) — ajuda na apresentação.

### FASE 1 — Pipeline de dados (Semanas 2–4: 13/07 → 03/08) — Dev 1 (líder), apoio Dev 2
- [ ] **P1.1** Script de download automatizado: CEIS, CNEP, CEPIM, Leniência, Contratos (planilhas mensais do Portal da Transparência).
- [ ] **P1.2** Script de download do dump CNPJ da Receita (todos os ZIPs: Empresas, Estabelecimentos, Sócios).
- [ ] **P1.3** Normalização com DuckDB: CNPJ apenas dígitos, datas ISO, nomes sem acento/uppercase, encoding UTF-8.
- [ ] **P1.4** Carga das sanções + contratos; deduplicação; marcar sanções vigentes vs. expiradas.
- [ ] **P1.5** Filtragem do universo CNPJ: manter apenas (a) empresas sancionadas, (b) empresas com contrato federal, (c) todas as empresas que compartilham sócios com (a). Isso reduz 60M de empresas para um conjunto tratável.
- [ ] **P1.6** Construção da tabela `vinculos` via matching de sócios (§4.3), com nível de confiança.
- [ ] **P1.7** Cálculo dos graus de risco (§4.2) e materialização das tabelas finais no PostgreSQL.
- [ ] **P1.8** Testes de sanidade: conferir manualmente 10 empresas conhecidas (grandes sancionadas públicas) contra o Portal da Transparência.
- [ ] **P1.9** Automatizar o pipeline completo em um comando (`make pipeline`) + GitHub Action mensal.

**Critério de conclusão da Fase 1:** banco PostgreSQL populado, com ao menos um caso real de vínculo grau 1 validado manualmente.

### FASE 2 — API (Semanas 4–5: 27/07 → 10/08) — Dev 2
- [ ] **P2.1** FastAPI com endpoints:
  - `GET /busca?q=` → busca por nome/CNPJ (full-text no PostgreSQL).
  - `GET /empresas/{cnpj}` → ficha completa (dados cadastrais, sanções, contratos, sócios, grau de risco).
  - `GET /empresas/{cnpj}/grafo` → nós e arestas do vínculo (profundidade 1–2) para visualização.
  - `GET /orgaos/{codigo}/fornecedores?risco=` → fornecedores de um órgão filtrados por grau.
  - `GET /estatisticas` → números agregados para a home (total sancionadas, valor contratado sob alerta etc.).
- [ ] **P2.2** Paginação, rate limiting básico, CORS, cache (respostas são estáticas entre atualizações mensais).
- [ ] **P2.3** Documentação OpenAPI pública (a API aberta em si é argumento extra de reúso/transparência).
- [ ] **P2.4** Deploy em Railway/Fly.io/Render com banco gerenciado.

### FASE 3 — Frontend (Semanas 4–7: 27/07 → 24/08) — Dev 3 (líder), apoio Dev 2
- [ ] **P3.1** Next.js + Tailwind; layout mobile-first; identidade visual simples e séria (não parecer "site de denúncia sensacionalista").
- [ ] **P3.2** Home: busca central + 3 números de impacto + explicação em 2 frases do que a ferramenta faz.
- [ ] **P3.3** Página de ficha da empresa: badge de grau de risco, sanções (com "o que isso significa?" expansível em linguagem simples), contratos, sócios.
- [ ] **P3.4** Visualização do grafo de vínculos (vis.js ou d3-force): empresa central, sócios, empresas relacionadas coloridas por grau.
- [ ] **P3.5** Página de órgão: lista de fornecedores ordenável por grau de risco e valor.
- [ ] **P3.6** Páginas institucionais: Metodologia (com limitações — §4.4), Fontes de Dados (com links para dados.gov.br), Glossário em linguagem simples.
- [ ] **P3.7** Acessibilidade WCAG 2.1 AA: contraste, navegação por teclado, aria-labels, textos alternativos; rodar Lighthouse/axe e corrigir. **Documentar isso — conta em "apresentação e usabilidade" e em "benefício para a sociedade" (edital 2026 não tem mais critério de inclusividade próprio).**
- [ ] **P3.8** Deploy na Vercel com domínio final.

### FASE 4 — Polimento e conteúdo (Semana 8: 24/08 → 31/08) — todos
- [ ] **P4.1** Teste com 3–5 pessoas fora do grupo (idealmente não-técnicas); corrigir fricções.
- [ ] **P4.2** Revisão de todos os textos: tom informativo, não acusatório (§1.4).
- [ ] **P4.3** Encontrar e destacar 2–3 casos reais interessantes que a ferramenta revela (serão o coração do vídeo demo).
- [ ] **P4.4** Página "Sobre o projeto" citando o concurso e a equipe.

### FASE 5 — Submissão (Semana 9: 31/08 → 11/09) — todos, liderança Dev 3
- [ ] **P5.1** Vídeo demo (3–5 min): problema → solução → demonstração com caso real → impacto. Roteiro antes de gravar.
- [ ] **P5.2** Preencher o formulário de inscrição da CGU (etapa 1 obrigatória).
- [ ] **P5.3** Submeter a iniciativa no dados.gov.br como "reúso" e enviar para homologação (etapa 2 obrigatória). **Fazer até 05/09 — a homologação depende de aprovação de terceiros, não deixar para o último dia.**
- [ ] **P5.4** Conferir confirmação das duas etapas; guardar comprovantes.

---

## 6. Divisão de Responsabilidades

| Papel | Responsável | Escopo |
|---|---|---|
| Dados & Pipeline | Dev 1 | Fases 1; manutenção do cruzamento; página de Metodologia |
| Backend & Infra | Dev 2 | Fase 2; deploy geral; apoio no pipeline e no grafo do front |
| Frontend & Apresentação | Dev 3 | Fases 3 e 5; acessibilidade; vídeo e materiais de inscrição |

> Os critérios de maior peso (relevância/impacto e benefício à sociedade, peso 2 cada) são comunicados pelo vídeo e pelos textos — o papel do Dev 3 não é secundário. Reservar tempo real para a apresentação.

## 7. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Dump do CNPJ pesado demais para as máquinas do grupo | Atraso na Fase 1 | DuckDB streaming; processar por lotes; usar uma VM spot barata se necessário |
| Falsos positivos no matching de sócios | Credibilidade | Níveis de confiança explícitos + página de metodologia + tom não acusatório |
| Homologação no dados.gov.br demorar | Perder o prazo | Submeter até 05/09 |
| Escopo crescer demais | Não entregar MVP | Grau 2 de risco, emendas parlamentares e dados estaduais são explicitamente FASE FUTURA |
| Layout dos CSVs do governo mudar | Pipeline quebra | Validar contra dicionário de dados; testes de schema no CI |

## 8. Fora de Escopo (v1) — citar como roadmap na inscrição
- Contratos estaduais e municipais.
- Cruzamento com emendas parlamentares e convênios.
- Alertas por e-mail / monitoramento contínuo de um CNPJ.
- Grau 2 de risco completo.

## 9. Definição de Pronto (MVP para submissão)
1. Plataforma pública no ar, com domínio próprio, funcionando em mobile.
2. Busca por qualquer empresa retorna ficha com sanções + contratos federais + sócios.
3. Ao menos os graus de risco 0 e 1 calculados e exibidos, com grafo visual.
4. Página de metodologia e glossário em linguagem simples publicados.
5. Lighthouse acessibilidade ≥ 90.
6. Vídeo demo gravado e ambas as etapas de inscrição concluídas.
